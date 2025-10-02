import json
import boto3
from openai import OpenAI

ssm = boto3.client('ssm')

r = ssm.get_parameter(Name='/OPENAI/API_KEY', WithDecryption=False)
OPENAI_API_KEY = r['Parameter']['Value']

def summarise(builder_name, search_results):
    
    snippets = "\n".join(
        f"- {r['title']}: {r['snippet']} ({r['link']})" for r in search_results
    )

    query_prompt = f"""
    You are a maritime historian. Using the following web sources:
    {snippets}

    Write a structured historical summary of '{builder_name}' as JSON with keys:
    origins, early_work, wartime, growth_innovation, decline_closure, legacy, sources.
    Sources should be a list of URLs.
    """
    client = OpenAI(api_key = OPENAI_API_KEY)
    completion = client.chat.completions.create(
        model="gpt-5",
        messages=[{"role": "user", "content": query_prompt}],
        response_format={"type": "json_object"}
    )

    return json.loads(completion.choices[0].message.content)