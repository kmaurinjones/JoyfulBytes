import os
import json
from datetime import datetime
from tqdm import tqdm
import sys
import logging
from config import CONFIG
from utils.search import search_bing
from utils.validation import extract_search_results
from utils.ai import (
    validate_news_stories, create_image_gen_prompt, \
    generate_image, validate_generated_image,
    summarize_webpage
)
from utils.scraping import get_page_text_content
import requests

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main.log'),
        logging.StreamHandler()  # Also print to console
    ]
)
logger = logging.getLogger(__name__)

# get current datetime YYYY-MM-DD-HH-MM-SS
run_start_time = datetime.now().strftime("%Y%m%d-%H%M%S")

logger.info(f"Starting new run at {run_start_time}")
logger.info(f"Processing {len(CONFIG['search_queries'])} search terms: {CONFIG['search_queries'][:3]}")

### read in search terms from ./config.py file
search_terms = CONFIG["search_queries"]

### Iterate through each search term and get the search results
search_results = []
for search_term in tqdm(search_terms, desc="Searching Bing with Search Terms", total=len(search_terms)):
    try:
        result = search_bing(search_term)
        search_results.append(result)
        logger.info(f"Successfully retrieved {len(result)} results for search term: {search_term}")
    except Exception as e:
        logger.error(f"Error searching for term '{search_term}': {str(e)}")

values = extract_search_results(search_results)

logger.info(f"Extracted {len(values)} valid search results")

# validate the news stories
logger.info("Starting news story validation")
rankings = validate_news_stories(values, tqdm_desc="Validating news stories")

# Create a new list combining rankings with original story data
stories_rankings = []
for idx, ranking_info in enumerate(rankings):
    stories_rankings.append({
        'ranking': ranking_info['ranking'],
        'result': values[idx]  # Original story data from values
    })

logger.info(f"Completed story validation. Highest ranking: {max([r['ranking'] for r in stories_rankings])}")

# sort by ranking (now using stories_rankings instead of rankings)
rankings_stories = sorted(stories_rankings, key=lambda x: x['ranking'], reverse=True)

logger.info(f"Found {len(rankings_stories)} stories with maximum ranking of {max([r['ranking'] for r in rankings_stories])}")

# Get text content for top stories
for story in tqdm(rankings_stories, desc="Trying to get text content"):
    url = story['result']['url']  # Changed from story['result']['url']
    try:
        response = get_page_text_content(url=url, timeout=10)
        if response.strip() and len(response.strip().split()) > 300: # ensure there's enough content
            story['text_content'] = response
            logger.info(f"Successfully retrieved content from URL: {url}")
            break
    except Exception as e:
        logger.error(f"Error getting content for {url}: {str(e)}")
        continue

if not any(story.get('text_content') for story in rankings_stories):
    logger.error("Failed to find any valid story content")
    sys.exit(1)

logger.info("Generating story summary")
chosen_story_summary = summarize_webpage(story['text_content'], tqdm_desc="Generating story summary")
chosen_story_summary = chosen_story_summary['summary']
logger.info(f"Generated summary of length: {len(chosen_story_summary)}")

logger.info("Starting image generation and validation process")
image_dir = "./data/images"
image_gen_attempts = 5
score_threshold = 8
file_type = "png"
feedback = None

for attempt in range(1, image_gen_attempts + 1):
    logger.info(f"Attempt {attempt}/{image_gen_attempts} to generate valid image")
    
    try:
        # Format feedback as improvement suggestions if available
        formatted_feedback = None
        if feedback and isinstance(feedback, dict):
            formatted_feedback = {
                "improvements_needed": [
                    f"Improve {k.replace('_', ' ')}" 
                    for k, v in feedback.items() 
                    if v < score_threshold
                ]
            }
        
        # Generate new prompt with formatted feedback
        image_prompt = create_image_gen_prompt(
            story_text=chosen_story_summary,
            model="o1-mini-2024-09-12",
            feedback=formatted_feedback,
            tqdm_desc=f"Creating image generation prompt (attempt {attempt}/{image_gen_attempts})"
        )
        image_prompt = image_prompt[0]['full_prompt']
        logger.info(f"Generated prompt: {image_prompt}")

        generated_image_bytes = generate_image(image_prompt, file_type=file_type)
        image_validation = validate_generated_image(generated_image_bytes, image_prompt)

        logger.info(f"Image validation: {image_validation}")
        
        if isinstance(image_validation, dict):
            # Calculate mean of text-related scores
            text_scores = [v for k, v in image_validation.items() if 'text' in k.lower()]
            text_mean = sum(text_scores) / len(text_scores) if text_scores else 0
            
            # Calculate mean of all scores
            all_scores = list(image_validation.values())
            overall_mean = sum(all_scores) / len(all_scores) if all_scores else 0
            
            logger.info(f"Text score mean: {text_mean:.2f}, Overall mean: {overall_mean:.2f}")
            
            # Check if the image meets the quality criteria
            # if text_mean > score_threshold and overall_mean > score_threshold:
            if overall_mean > score_threshold:
                logger.info("Generated image meets quality criteria")
                
                # Save the successful image
                output_filename = f'./data/images/{run_start_time}-{attempt}.{file_type}'
                with open(output_filename, 'wb') as f:
                    f.write(generated_image_bytes)
                logger.info(f"Successfully saved generated image to {output_filename}")

                # Update the generated-map.json file
                map_file_path = "./data/generated-map.json"
                current_date = datetime.now().strftime("%Y-%m-%d")
                
                try:
                    # Read existing map if it exists
                    if os.path.exists(map_file_path):
                        with open(map_file_path, 'r') as f:
                            generated_map = json.load(f)

                        # also write the file to "./data/most-recent-image.png" -- this will be rendered in the README
                        with open("./data/most-recent-image.png", 'wb') as f:
                            f.write(generated_image_bytes)
                    else:
                        generated_map = {}
                    
                    # Find the date field from the result dictionary
                    date_value = None
                    for key in rankings_stories[0]['result']:
                        if 'date' in key.lower():
                            date_value = rankings_stories[0]['result'][key]
                            break

                    # Convert ISO date format to readable format
                    date_str = rankings_stories[0]['result']['datePublished']
                    try:
                        # Try the full ISO format first
                        formatted_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%B %d, %Y")
                    except ValueError:
                        try:
                            # Try without milliseconds
                            formatted_date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").strftime("%B %d, %Y")
                        except ValueError:
                            # If all else fails, just use the date portion
                            formatted_date = datetime.strptime(date_str.split('T')[0], "%Y-%m-%d").strftime("%B %d, %Y")

                    generated_map[current_date] = {
                        "date": formatted_date,
                        "image_path": output_filename,
                        "story_summary": chosen_story_summary,
                        "story_url": rankings_stories[0]['result']['url'],
                        **rankings_stories[0]['result'] # add all other fields from the result
                    }
                    
                    # Write updated map back to file
                    with open(map_file_path, 'w') as f:
                        json.dump(generated_map, f, indent=4)
                    
                    logger.info(f"Successfully updated generated-map.json for date {current_date}")
                except Exception as e:
                    logger.error(f"Error updating generated-map.json: {str(e)}")
                
                break
            else:
                logger.info("Image quality below threshold. Updating prompt with feedback and retrying...")
                feedback = image_validation  # Store validation results for next attempt
                
    except Exception as e:
        logger.error(f"Error in attempt {attempt}: {str(e)}")
        feedback = None  # Reset feedback on error
        continue
