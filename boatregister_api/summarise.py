import simplejson as json
import openai
import os
from builders import fetch_boatbuilder_history

def buildersummary_internal(builders, builder):
    # You should set your OpenAI API key as an environment variable: OPENAI_API_KEY
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set.")
    openai.api_key = api_key

    prompt = f"Summarise the builder: {builder}. Give a concise summary suitable for a boat registry."
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a historian."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200
        )
        summary = response.choices[0].message["content"].strip()
        return summary
    except Exception as e:
        return f"Error: {str(e)}"


def buildersummary(builders, builder, place, timestamp):
    summary = fetch_boatbuilder_history(builders, builder, place)
    if not summary:
        return {
            'statusCode': 404,
            'body': json.dumps("that doesn't seem to be here")
        }
    return {
        'statusCode': 200,
        'body': json.dumps(summary)
    }