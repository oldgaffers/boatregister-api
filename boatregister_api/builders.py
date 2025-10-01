import json
import requests
import boto3
from openai import OpenAI

# === Setup ===
client = OpenAI()

ssm = boto3.client('ssm')
r = ssm.get_parameter(Name='SERPAPI/API_KEY', WithDecryption=False)
SERP_API_KEY = r['Parameter']['Value']
SERP_URL = "https://serpapi.com/search.json"

BING_API_KEY = "your_bing_api_key_here"
BING_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"


# --- Web Search Engines ---

def web_search_serpapi(query: str, num_results: int = 5) -> list:
    """Query Google via SerpAPI and return simplified results."""
    params = {"q": query, "engine": "google", "api_key": SERP_API_KEY, "num": num_results}
    res = requests.get(SERP_URL, params=params)
    res.raise_for_status()
    data = res.json()
    return [
        {"title": item.get("title"), "link": item.get("link"), "snippet": item.get("snippet")}
        for item in data.get("organic_results", [])
    ]


def web_search_bing(query: str, num_results: int = 5) -> list:
    """Query Bing Web Search API and return simplified results."""
    headers = {"Ocp-Apim-Subscription-Key": BING_API_KEY}
    params = {"q": query, "count": num_results}
    res = requests.get(BING_ENDPOINT, headers=headers, params=params)
    res.raise_for_status()
    data = res.json()
    return [
        {"title": item.get("name"), "link": item.get("url"), "snippet": item.get("snippet")}
        for item in data.get("webPages", {}).get("value", [])
    ]


# --- Core Functions ---

def fetch_boatbuilder_history(table, builder_name: str, engine: str = "serpapi") -> dict:
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
    return _generate_and_store_history(builder_name, engine)


def refresh_boatbuilder_history(builder_name: str, engine: str = "serpapi") -> dict:
    """
    Force refresh the history of a boatbuilder:
    - Always re-query web + OpenAI
    - Overwrites the cached entry in DynamoDB
    """
    print(f"[REFRESH] Overwriting cache for {builder_name}")
    return _generate_and_store_history(builder_name, engine)


def delete_boatbuilder_history(builder_name: str) -> bool:
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

def _generate_and_store_history(builder_name: str, engine: str) -> dict:
    """Private helper to search web, summarize, and store in DynamoDB."""

    # Step 1: Search
    query = f"History of {builder_name} boatbuilder"
    if engine == "serpapi":
        search_results = web_search_serpapi(query)
    elif engine == "bing":
        search_results = web_search_bing(query)
    else:
        raise ValueError("Unknown search engine")

    snippets = "\n".join(
        f"- {r['title']}: {r['snippet']} ({r['link']})" for r in search_results
    )

    # Step 2: Summarize
    query_prompt = f"""
    You are a maritime historian. Using the following web sources:
    {snippets}

    Write a structured historical summary of '{builder_name}' as JSON with keys:
    origins, early_work, wartime, growth_innovation, decline_closure, legacy, sources.
    Sources should be a list of URLs.
    """

    completion = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": query_prompt}],
        response_format={"type": "json_object"}
    )

    history_json = json.loads(completion.choices[0].message.content)

    # Step 3: Store
    table.put_item(Item={
        "builder": builder_name,
        "history": history_json
    })

    return history_json
