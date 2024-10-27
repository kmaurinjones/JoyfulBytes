# # Getting Page Text Content
import requests
from bs4 import BeautifulSoup
def get_page_text_content(url, timeout=5):
    """
    Get and return the text content of a webpage, with a timeout, headers, and randomized delay.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Make the request with headers
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)

        return text
    except requests.RequestException as e:
        return ""
