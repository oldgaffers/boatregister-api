import json
import requests
import boto3
from summarise_with_openai import summarise
from gemini import summarize_search_results

ssm = boto3.client('ssm')
# --- Web Search Engines ---

def web_search_serpapi(query: str, num_results: int = 5) -> list:
    """Query Google via SerpAPI and return simplified results."""
    r = ssm.get_parameter(Name='/SERPAPI/API_KEY', WithDecryption=False)
    API_KEY = r['Parameter']['Value']
    params = {"q": query, "engine": "google", "api_key": API_KEY, "num": num_results}
    res = requests.get("https://serpapi.com/search.json", params=params)
    res.raise_for_status()
    data = res.json()
    return [
        {"title": item.get("title"), "link": item.get("link"), "snippet": item.get("snippet")}
        for item in data.get("organic_results", [])
    ]

def web_search_bing(query: str, num_results: int = 5) -> list:
    """Query Bing Web Search API and return simplified results."""
    r = ssm.get_parameter(Name='/BING/API_KEY', WithDecryption=False)
    API_KEY = r['Parameter']['Value']
    headers = {"Ocp-Apim-Subscription-Key": API_KEY}
    params = {"q": query, "count": num_results}
    res = requests.get("https://api.bing.microsoft.com/v7.0/search", headers=headers, params=params)
    res.raise_for_status()
    data = res.json()
    return [
        {"title": item.get("name"), "link": item.get("url"), "snippet": item.get("snippet")}
        for item in data.get("webPages", {}).get("value", [])
    ]


# --- Core Functions ---

def fetch_boatbuilder_history(table, builder_name: str, place: str, engine: str = "serpapi") -> dict:
    """
    Get a structured boatbuilder history.
    - Check DynamoDB cache first
    - If not found, search + summarize
    - Store result in DynamoDB
    """
    response = table.get_item(Key={"builder": builder_name})
    if "Item" in response:
        print(f"[CACHE HIT] Returning cached result for {builder_name}")
        return response["Item"]["history"]

    print(f"[CACHE MISS] Fetching new result for {builder_name}")
    return _generate_and_store_history(table, builder_name, place, engine)


def refresh_boatbuilder_history(builder_name: str, engine: str = "serpapi") -> dict:
    """
    Force refresh the history of a boatbuilder:
    - Always re-query web + OpenAI
    - Overwrites the cached entry in DynamoDB
    """
    print(f"[REFRESH] Overwriting cache for {builder_name}")
    return _generate_and_store_history(builder_name, engine)


def delete_boatbuilder_history(table, builder_name: str) -> bool:
    """
    Delete a boatbuilder's history from DynamoDB.
    Returns True if deletion was successful, False if the item did not exist.
    """
    try:
        response = table.delete_item(
            Key={"builder": builder_name},
            ReturnValues="ALL_OLD"
        )
        if "Attributes" in response:
            print(f"[DELETE] Removed {builder_name} from cache")
            return True
        else:
            print(f"[DELETE] No entry found for {builder_name}")
            return False
    except Exception as e:
        print(f"[ERROR] Could not delete {builder_name}: {e}")
        return False


# --- Internal Helper ---

def _generate_and_store_history(table, builder_name: str, place: str, engine: str) -> dict:
    """Private helper to search web, summarize, and store in DynamoDB."""

    # Step 1: Search
    query = f"History of {builder_name} boatbuilder in {place}"
    if engine == "serpapi":
        search_results = web_search_serpapi(query)
    elif engine == "bing":
        search_results = web_search_bing(query)
    else:
        raise ValueError("Unknown search engine")

    # history_json = summarise(builder_name, search_results)
    history_json = summarize_search_results(builder_name, search_results)

    # Step 3: Store
    table.put_item(Item={
        "builder": builder_name,
        "history": history_json
    })

    return history_json
