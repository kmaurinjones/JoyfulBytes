# utils for interacting with the OpenAI API

import os
import json
from openai import OpenAI
import anthropic
import replicate
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed
from tqdm import tqdm
import requests
import base64

client = OpenAI(
    api_key=os.environ['OPENAI_API_KEY']
)

def batch_prompt_oai(prompts: list[str], 
                    model: str = "gpt-4o-mini-2024-07-18", 
                    max_workers: int = 20,
                    timeout: int = 30,
                    tqdm_desc: str = None) -> list[dict]:
    """
    Process multiple prompts concurrently using the OpenAI API.
    
    Args:
        prompts: List of prompts to process
        model: OpenAI model to use
        max_workers: Maximum number of concurrent threads
        timeout: Timeout in seconds for each API call
        tqdm_desc: Description for the progress bar (defaults to "Processing prompts")
    
    Returns:
        List of API responses in the same order as the input prompts
    """
    def _process_single_prompt(prompt: str):
        messages = [{"role": "user", "content": prompt}]
        
        if not model.startswith("o1"):
            messages.insert(0, {
                "role": "system", 
                "content": "You always return information in a strict JSON dictionary format one ONE line, to be parsed easily by a python function."
            })

        completion = client.chat.completions.create(
            model=model,
            messages=messages
        )
        
        response_str = completion.choices[0].message.content.strip()
        return json.loads(response_str)

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_process_single_prompt, prompt): i 
            for i, prompt in enumerate(prompts)
        }
        
        for future in tqdm(as_completed(futures), 
                         total=len(prompts),
                         desc=tqdm_desc or "Processing prompts"):
            idx = futures[future]
            try:
                with tqdm(total=timeout, 
                         desc="Timeout", 
                         unit="s", 
                         leave=False) as pbar:
                    for _ in range(timeout):
                        try:
                            result = future.result(timeout=1)
                            results.append((idx, result))
                            break
                        except TimeoutError:
                            pbar.update(1)
                            continue
            except Exception as e:
                # just skip it. It's not a big deal.
                continue
    
    # Sort results back to original order
    results.sort(key=lambda x: x[0])
    return [r[1] for r in results]

def validate_news_stories(results: list[dict[str, str]], tqdm_desc: str = None, model: str = "gpt-4o-mini-2024-07-18"):
    """
    Use the OpenAI API to validate a news story against a set of criteria.
    """

    example_response = {"ranking": 3.45, "explanation": "This headline ..."}

    base_prompt = """
    # Instruction
    You are an expert evaluator for a project dedicated to creating AI-generated cartoons that spread joy and positivity.
    Your task is to read the following headline and assess how well it aligns with our mission of delivering uplifting, feel-good content
    that can be transformed into inspiring cartoons.
    Additionally, you must also factor in quality of the source. We don't want spam or clickbait, but we also don't want to miss out on a good story.

    Use an overall ranking from 0.00 to 10.00, rounded to the nearest hundreth, where lower scores indicate poor alignment and higher scores indicate good alignment.
    Include a brief explanation for your ranking, in no more than 1-2 sentences, max 30 words.
    Your response must be in a strict JSON dictionary format on a single line, to be parsed easily by a python function.
    Your response must not include any backticks, code blocks, or other formatting, as this will break the JSON parsing.

    # Ranking Criteria
    Use the following criteria to guide your ranking:
    1. **Local Focus**: The story should ideally involve individuals, small communities, or local efforts, especially in small towns or neighborhoods.
    2. **Non-Celebrity**: The story should not feature major celebrities or public figures.
    3. **Non-Political**: Avoid headlines that involve politics, government policy, or political issues.
    4. **Uplifting and Positive**: The story should leave readers with a sense of joy, hope, or inspiration - perfect for cartoon adaptation.
    5. **Acts of Kindness or Community Support**: Bonus points for stories involving selfless acts of kindness, community collaboration, or personal achievements.
    6. **Uncommon Stories**: Prefer stories that are unique, heartwarming, or pleasantly surprising, rather than common or generic good news.
    7. **Avoid Negative Contexts**: Headlines should not involve sadness, tragedy, or negative events, even if the outcome is positive.
    8. **Visual Potential**: Consider whether the story could be effectively conveyed through a cartoon format.

    # Headline Information
    {headline}

    # Example Response
    {example_response}

    # Your Response
    """

    # batch process the results
    prompts = [
        base_prompt.format(
            headline=json.dumps(headline),
            example_response=json.dumps(example_response),
        ) for headline in results
    ]

    return batch_prompt_oai(prompts, model=model, tqdm_desc=tqdm_desc)

def re_validate_news_stories(results: list[dict[str, str]], tqdm_desc: str = None, model: str = "o1-mini-2024-09-12"):
    """
    Re-validate the news stories to ensure they are still valid.
    """
    return validate_news_stories(results, tqdm_desc, model)

def summarize_webpage(webpage_text: str, model: str = "o1-mini-2024-09-12", tqdm_desc: str = None):
    """
    Summarize webpage content into key story points in less than 200 words.
    
    Args:
        webpage_text: String containing the webpage content
        model: OpenAI model to use
        tqdm_desc: Description for the progress bar
    
    Returns:
        Dictionary containing the summary
    """
    example_response = {"summary": "Brief summary of key points..."}

    base_prompt = """
    # Instruction
    You are a skilled content summarizer.
    Extract and condense the most important elements of this story into a clear, engaging summary of less than 200 words.
    Focus on the key narrative points while maintaining the emotional core of the story.
    In particular, think about how this story could be transformed into a cartoon.
    Remain faithful to the original story, but also think about how to visualize it in a cartoon.
    However, do not explicitly mention the visual style, not any mention of a cartoon in your summary.
    You MUST use double newlines ("\n\n") to separate your summary into small, easily readable paragraphs for the user.

    NOTE:
    - This summary will serve as both a story summary for the user that provides context to the image,
    as well as story context for the image generation model.
    - Be sure to use markdown formatting, including bolding and italicizing, to make the summary more engaging.
    - Write it grammatically in a tense that reads naturally for a user reading about this story the day it was written. Therefore, mirror the tense of the original story.
    - Begin the summary with the location of the story, such as "Sault Ste. Marie -- ", as in many news articles.

    Your response must be in a strict JSON dictionary format on a single line, to be parsed easily by a python function.
    Include both the summary and its word count in your response.
    Your response must not include any backticks, code blocks, or other formatting, as this will break the JSON parsing.

    # Example Response
    {example_response}

    # Webpage Text
    {webpage_text}
    """.replace("    ", "").strip()

    # just one here
    prompts = [
        base_prompt.format(
            example_response=json.dumps(example_response),
            webpage_text=json.dumps(webpage_text)
        )
    ]

    results = batch_prompt_oai(prompts, model=model, tqdm_desc=tqdm_desc)
    return results[0] if results else None

def create_image_gen_prompt(story_text: str, model: str = "o1-mini-2024-09-12", tqdm_desc: str = None, feedback: dict[str, float] = None):
    """
    Create an image generation prompt from the given text.

    Feedback is optional, and can be used to guide the image generation prompt in the event that the image is being re-generated.
    """
    
    example_response = {"full_prompt":"..."}

    base_prompt = """
    # Instruction
    Write an instruction prompt that generates an image in 200 words or less in the following style:
    The scene shows the following story using loose, confident ink brush strokes and gentle gray watercolor shading.
    You must return your response in a strict JSON dictionary format on a single line, to be parsed easily by a python function.
    Your response must not include any backticks, code blocks, or other formatting, as this will break the JSON parsing.

    # Style
    Key style elements:
    - Any human characters in the image must be diverse in terms of age, gender, and ethnicity
    - Be creative with the artistic style - consider various approaches like watercolor, digital art, pencil sketches, bold colors, or minimalist designs
    - Feel free to experiment with different compositions, perspectives, and layouts
    - The mood and tone should match the story's emotional content
    - Visual elements should support and enhance the narrative
    - Maintain clear focus on the key story elements
    - Consider including symbolic or metaphorical elements that reinforce the story's message
    - Do NOT include any text in the image

    # Example Response
    {example_response}

    # Story
    {story}
    """.replace("    ", "").strip()

    # Add feedback if it exists
    if feedback:
        base_prompt += f"\n\n# BEFORE GENERATING IMAGE\n"
        base_prompt += "- You have already tried to generated this image once, and here were the results. Given these weak areas of the previous attempt, be sure to address them even more explicitly in your new prompt:"
        base_prompt += f"\n\n{json.dumps(feedback)}"

    # just one here
    prompts = [
        base_prompt.format(
            example_response=json.dumps(example_response),
            story=json.dumps(story_text)
        )
    ]

    return batch_prompt_oai(prompts, model=model, tqdm_desc=tqdm_desc)

def generate_image(prompt: str, model: str = "ideogram", file_type: str = "png"):
    """
    Generate an image from the given prompt and return the image data.

    Ideogram API docs: https://replicate.com/ideogram-ai/ideogram-v2-turbo
    
    Args:
        prompt: Text prompt for image generation
        model: Model choice ("flux" or "ideogram")
        file_type: Output file format (for flux model only)
        
    Returns:
        bytes: Raw image data if successful, None if failed
    """
    if model == "flux":
        output = replicate.run(
            model,
            input={
                "prompt": prompt,
                "aspect_ratio": "16:9",  # 16:9 is good for most cartoons
                "output_format": file_type, # can be one of ["png", "webp", "jpg"]
                "output_quality": 100,
                "style_type": "Realistic",
                "safety_tolerance": 2,  # 5 is most permissive and 0 is most strict
                "prompt_upsampling": True
            }
        )

        # download the image
        return output.read()

    elif model == "ideogram":
        # this returns a URL that requires a GET request to download the image
        output = replicate.run(
            "ideogram-ai/ideogram-v2-turbo",
            input={
                "prompt": prompt,
                "resolution": "1344x768",
                "style_type": "Auto",
                "aspect_ratio": "16:9",
                "negative_prompt": "", # optional string of text to NOT include
                "magic_prompt_option": "Auto"
            }
        )

        # download the image
        return requests.get(output).content
    
    else:
        raise ValueError(f"Invalid model: {model}")

def validate_generated_image_old(image_data: bytes, image_gen_prompt: str, model: str = "gpt-4o-2024-08-06"):
    """
    Validate the generated image with the given criteria.
    """
    # Convert bytes to base64
    base64_image = base64.b64encode(image_data).decode('utf-8')
    
    example_response = {"text_accuracy": 8.50,"text_legibility": 7.25,"text_coherence": 9.00,"character_diversity": 6.75,"theme_relevance": 8.50,"emotional_impact": 7.00,"visual_appeal": 8.25,"clarity": 9.50,"cohesiveness": 8.00,"creativity": 7.75,"uplifting_suitability": 8.50}

    base_prompt = """
    # Instruction
    You are an expert evaluator of images.
    You need to evaluate how well the image aligns with the following criteria.
    Your explanation should be in no more than 1-2 sentences, max 30 words.
    For each criterion, provide a score between 0.00 and 10.00, using decimal precision to reflect nuance.

    # Grading Criteria
    - text_accuracy (0-10): The text caption's accuracy and match with the image generation prompt
    - text_legibility (0-10): How readable and clear the text caption is for humans
    - text_coherence (0-10): How well the text caption makes sense in the image context
    - character_diversity (0-10): Diversity of human characters in terms of age, gender, ethnicity, and physical ability
    - theme_relevance (0-10): How closely the image matches its intended theme or subject
    - emotional_impact (0-10): How well it evokes positive emotions (joy, hope, inspiration, warmth)
    - visual_appeal (0-10): Quality of composition, colors, and style, without distracting elements
    - clarity (0-10): Clarity of content without blur, distortion, or artifacts
    - cohesiveness (0-10): How harmoniously all elements work together
    - creativity (0-10): Level of uniqueness and originality, avoiding clichés
    - uplifting_suitability (0-10): Alignment with light-hearted, joyful narratives

    # Prompt Used to Generate Image
    {image_gen_prompt}

    Provide a single score between 0.00 (does not meet any criteria) to 10.00 (perfectly meets all criteria), considering all the above aspects.
    Use decimal precision, rounded to the nearest hundredth to reflect nuance.

    You must return your response in a strict JSON dictionary format on a single line, to be parsed easily by a python function.
    Your response must not include any backticks, code blocks, or other formatting, as this will break the JSON parsing.

    # Example Response
    {example_response}
    """.replace("    ", "").strip()

    for _ in range(3):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": base_prompt.format(
                            example_response=json.dumps(example_response), 
                            image_gen_prompt=json.dumps(image_gen_prompt),
                        )},
                        {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/webp;base64,{base64_image}",
                        },
                        },
                    ],
                    }
                ],
                # max_tokens=200, # no reason to limit this
            )

            return json.loads(response.choices[0].message.content.strip())
        except Exception as e:
            return f"<|Error validating image: {e}|>"        
    return None

def validate_generated_image(image_data: bytes, image_gen_prompt: str, model: str = "claude-3-sonnet-20240229"):
    """
    Validate the generated image with the given criteria using Anthropic's Claude API.
    """
    # Convert bytes to base64
    base64_image = base64.b64encode(image_data).decode('utf-8')
    
    example_response = {"text_accuracy": 8.50,"text_legibility": 7.25,"text_coherence": 9.00,"character_diversity": 6.75,"theme_relevance": 8.50,"emotional_impact": 7.00,"visual_appeal": 8.25,"clarity": 9.50,"cohesiveness": 8.00,"creativity": 7.75,"uplifting_suitability": 8.50}

    base_prompt = """
    # Instruction
    You are an expert evaluator of images.
    You need to evaluate how well the image aligns with the following criteria.
    Your explanation should be in no more than 1-2 sentences, max 30 words.
    For each criterion, provide a score between 0.00 and 10.00, using decimal precision to reflect nuance.

    # Grading Criteria
    - text_accuracy (0-10): The text caption's accuracy and match with the image generation prompt
    - text_legibility (0-10): How readable and clear the text caption is for humans
    - text_coherence (0-10): How well the text caption makes sense in the image context
    - character_diversity (0-10): Diversity of human characters in terms of age, gender, ethnicity, and physical ability
    - theme_relevance (0-10): How closely the image matches its intended theme or subject
    - emotional_impact (0-10): How well it evokes positive emotions (joy, hope, inspiration, warmth)
    - visual_appeal (0-10): Quality of composition, colors, and style, without distracting elements
    - clarity (0-10): Clarity of content without blur, distortion, or artifacts
    - cohesiveness (0-10): How harmoniously all elements work together
    - creativity (0-10): Level of uniqueness and originality, avoiding clichés
    - uplifting_suitability (0-10): Alignment with light-hearted, joyful narratives

    # Prompt Used to Generate Image
    {image_gen_prompt}

    Provide a single score between 0.00 (does not meet any criteria) to 10.00 (perfectly meets all criteria), considering all the above aspects.
    Use decimal precision, rounded to the nearest hundredth to reflect nuance.

    You must return your response in a strict JSON dictionary format on a single line, to be parsed easily by a python function.
    Your response must not include any backticks, code blocks, or other formatting, as this will break the JSON parsing.

    # Example Response
    {example_response}
    """.replace("    ", "").strip()

    anth_client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))

    for _ in range(3):
        try:
            response = anth_client.messages.create(
                model=model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": base64_image,
                                },
                            },
                            {
                                "type": "text",
                                "text": base_prompt.format(
                                    example_response=json.dumps(example_response),
                                    image_gen_prompt=json.dumps(image_gen_prompt),
                                )
                            }
                        ],
                    }
                ],
            )

            return json.loads(response.content[0].text.strip())
        except Exception as e:
            return f"<|Error validating image: {e}|>"        
    return None
