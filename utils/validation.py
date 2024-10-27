# utils for validating search results

def extract_values(data):
    """
    Extract all 'values' from a nested dictionary or list.
    """
    values = []

    def recursive_extract(d):
        if isinstance(d, dict):
            for key, value in d.items():
                if key == 'value' and isinstance(value, list):
                    values.extend(value)
                else:
                    recursive_extract(value)
        elif isinstance(d, list):
            for item in d:
                recursive_extract(item)

    recursive_extract(data)
    return values

def only_webpages_news_results(search_results):
    """
    Filter out search results that are not webpages or news results.
    Returns the 'value' array from webPages if it exists.
    """
    if isinstance(search_results, dict):
        # Extract webPages.value if it exists
        if 'webPages' in search_results and 'value' in search_results['webPages']:
            return search_results['webPages']['value']
    return []

def extract_search_results(search_results):
    """
    Extract the search results from the search results.
    """
    # # filter out search results that are not webpages or news results
    # search_results = only_webpages_news_results(search_results)

    values = []
    for search_result in search_results:
        # extract the values from the search result
        results = extract_values(search_result)
        
        for result in results:
            required_fields = ['snippet', 'url', 'isFamilyFriendly', 'name', 'datePublishedFreshnessText', 'datePublished']
            if all(field in result for field in required_fields) and result not in values:
                values.append(result)
                
    return values
