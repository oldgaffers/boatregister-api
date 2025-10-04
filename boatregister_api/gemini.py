import json
from google import genai
import boto3

api_key = None

def set_api_key():
    if api_key is None:
        ssm = boto3.client('ssm')
        r = ssm.get_parameter(Name='/GEMINI/API_KEY', WithDecryption=False)
        api_key = r['Parameter']['Value']

def summarize_search_results(builder_name, snippets):
    """
    Summarize web search results into structured JSON using Google Gemini.
    
    Args:
        builder_name: Name of the ship builder to research
        snippets: list with search results, e.g.:
                 [{'title':'snippet': 'text', 'link': 'uri'},  ...]
    Returns:
        Dictionary with structured historical summary
    """
    set_api_key()
    print('S', api_key, snippets)
    # Format snippets for the prompt
    formatted_snippets = "\n\n".join([
        f"{s['title']}: {s['snippet']}\nSource: {s['link']}\n" 
        for s in snippets
    ])
    
    # Get list of URLs for sources
    source_urls = [s['link'] for s in snippets]
    
    # Create the prompt
    prompt = f"""You are a maritime historian. Using the following web sources:

{formatted_snippets}

Write a structured historical summary of '{builder_name}' as JSON with these keys:
- origins: Brief history of how the company started
- early_work: Description of their early shipbuilding projects
- notable_vessels: List of significant ships they built
- legacy: Their lasting impact on maritime history
- sources: List of source URLs used

Return ONLY valid JSON, no other text."""
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    response_text = response.text
    
    # Parse JSON (handle potential markdown code blocks)
    if response_text.strip().startswith("```"):
        # Remove markdown code block markers
        response_text = response_text.strip()
        response_text = response_text.split("```json")[1] if "```json" in response_text else response_text.split("```")[1]
        response_text = response_text.rsplit("```", 1)[0].strip()
    
    result = json.loads(response_text)
    
    # Ensure sources are included
    if 'sources' not in result or not result['sources']:
        result['sources'] = source_urls
    
    return result

