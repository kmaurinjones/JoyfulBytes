# # Bing Web Search API
import os
import requests

def search_bing(search_term: str):
    """
    Search Bing 
    """

    # Define variables
    subscription_key = os.environ['BING_SEARCH_V7_SUBSCRIPTION_KEY']
    endpoint = os.environ['BING_SEARCH_V7_ENDPOINT']
    assert subscription_key, endpoint

    search_url = "https://api.bing.microsoft.com/v7.0/search"

    # Make the request
    ### params docs: https://learn.microsoft.com/en-us/bing/search-apis/bing-web-search/reference/query-parameters
    headers = {"Ocp-Apim-Subscription-Key": subscription_key}
    params = {
        "q": search_term,
        "count": 50,
        "textDecorations": True,
        "textFormat": "HTML",
        # "safeSearch": "Off",
        "safeSearch": "Strict",
        "freshness": "Day", # results from only the last 24 hours
        "setLang": "en-US",
        "cc": "CA",
    }

    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()
    search_results = response.json()

    return search_results

