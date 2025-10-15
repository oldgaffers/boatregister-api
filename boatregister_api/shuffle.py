import json
import boto3
import requests

ssm = boto3.client('ssm')

def shuffle():
    # print(json.dumps(event))
    url = 'https://api.github.com/repos/oldgaffers/boatregister/actions/workflows/shuffle_editors_choice.yml/dispatches'
    r = ssm.get_parameter(Name='GITHUB_TOKEN', WithDecryption=True)
    github_token = r['Parameter']['Value']
    headers = {
        'Authorization': f'Bearer {github_token}',
        'Accept': 'application/vnd.github+json',
        'Content-Type': 'application/json',
    }
    response = requests.post(url, headers=headers, data=json.dumps({'ref': 'main'}))
    if response.ok:
        outcome = 'boats shuffled'
        # print(outcome)
        return {
            'statusCode': 200,
            'body': json.dumps(outcome)
        } 
    # print('error', response.text)
    return {
        'statusCode': response.status_code,
        'body': json.dumps(response.json())
    }
