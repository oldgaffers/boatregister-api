import json
import anthropic
import os

def summarize_search_results(builder_name, snippets):
    """
    Summarize web search results into structured JSON.
    
    Args:
        builder_name: Name of the ship builder to research
        snippets: Dictionary with search results, e.g.:
                 {'url1': 'text content...', 'url2': 'text content...'}
    
    Returns:
        Dictionary with structured historical summary
    """
    
    # Format snippets for the prompt
    formatted_snippets = "\n\n".join([
        f"Source: {url}\n{content}" 
        for url, content in snippets.items()
    ])
    
    # Get list of URLs for sources
    source_urls = list(snippets.keys())
    
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

    # Initialize Anthropic client
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    
    # Call Claude API
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    # Extract and parse JSON from response
    response_text = message.content[0].text
    
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


# Example usage
if __name__ == "__main__":
    # Example snippets from web search
    example_snippets = {
        "https://example.com/harland-wolff": """
        Harland and Wolff was founded in 1861 in Belfast, Northern Ireland. 
        The company became one of the world's leading shipbuilders, known for 
        building the RMS Titanic and her sister ships Olympic and Britannic.
        """,
        "https://example.com/belfast-shipbuilding": """
        In its early years, Harland and Wolff focused on iron-hulled sailing ships. 
        Their first major contract was for three ships for the Bibby Line in 1862. 
        The company revolutionized shipbuilding with innovative construction techniques.
        """
    }
    
    builder = "Harland and Wolff"
    
    try:
        summary = summarize_search_results(builder, example_snippets)
        print(json.dumps(summary, indent=2))
    except Exception as e:
        print(f"Error: {e}")