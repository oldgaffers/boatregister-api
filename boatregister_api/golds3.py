import boto3
import simplejson as json

s3 = boto3.client('s3')

def json_from_object(bucket, key):
    r = s3.get_object(Bucket=bucket, Key=key)
    text = r["Body"].read().decode('utf-8')
    return json.loads(text)
    
def gold():
    return json_from_object('boatregister', 'gold/latest.json')

def getMember(member):
    g = gold()
    n = [m for m in g if m['ID'] == member and m['Status'] not in ['Deceased', 'Left OGA']]
    if len(n) > 0:
        return n[0]
    return None