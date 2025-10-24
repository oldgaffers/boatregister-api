from decimal import Decimal
from updates import update_tables
from places import geocode
from emails import compose_contact, compose_profile, compose_enquiry
from mail import sendmail
from summarise import buildersummary
import boto3
import simplejson as json

dynamodb = boto3.resource('dynamodb')

def paramMap(val):
    if val == 'true':
        return True
    if val == 'false':
        return False
    try:
        return int(val)
    except:
        return val

def enquiry(body):
    sns = boto3.client('sns')
    sns.publish(
        TopicArn='arn:aws:sns:eu-west-1:651845762820:boatenquiry',
        Message=json.dumps(body),
        Subject=body['boat_name']
    )
    # print('sent message')
    return {
        'statusCode': 200,
        'body': json.dumps("Ok")
    }

def map_values(d):
    r = {}
    for k in d.keys():
        val = d[k]
        if isinstance(val, Decimal):
            val = int(val)
        r[k] = val
    return r

def putChangedFields(scope, table, body):
    ddb_table = dynamodb.Table(f"{scope}_{table}")
    data = json.loads(json.dumps(body), parse_float=Decimal)
    if 'key' in body:
        r = ddb_table.get_item(Key=body['key'])
        if 'Item' in r:
            existing = r['Item']
            data = {**existing, **body}
        else:
            print('no existing data for', body['key'])
        del data['key']
    data = map_values(data)
    ddb_table.put_item(Item=data)

def gets(scope, table, qsp, timestamp):
    try:
        if table == 'place':
            return geocode(dynamodb, qsp, timestamp) 
        if table == 'builder':
            if 'builder' not in qsp:
                return {
                    'statusCode': 400,
                    'body': json.dumps("missing builder parameter")
                }
            ddb_table = dynamodb.Table(f"{scope}_{table}")
            return buildersummary(ddb_table, qsp['builder'], qsp.get('place'), timestamp)
        if scope != 'public' and table == 'members':
            ddb_table = dynamodb.Table('members')
            sf = json.loads(qsp.get('sf', None))
            fields = json.loads(qsp.get('fields', []))
            data = ddb_table.scan(ScanFilter=sf)
            items = [{k:item[k] for k in item.keys() if k in fields} for item in data['Items']]
        else:
            ddb_table = dynamodb.Table(f"{scope}_{table}")
            if qsp is None:
                data = ddb_table.scan()
                items = data['Items']
            else:
                sf = {key: { 'AttributeValueList': [paramMap(value)], 'ComparisonOperator': 'EQ'} for key, value in qsp.items()}
                data = ddb_table.scan(ScanFilter=sf)
                items = [{k:item[k] for k in item.keys() if k not in ['hide','paym']} for item in data['Items'] if 'hide' not in item or not item['hide']]
        meta = data.pop('ResponseMetadata')
        return {
            'statusCode': meta['HTTPStatusCode'],
            'body': json.dumps({ 'Items': items, 'Count': len(items), 'ScannedCount': data['ScannedCount']})
        }
    except Exception as e:
        print(f"[ERROR] Could not get from {scope} {table}: {e}")
        return {
            'statusCode': 404,
            'body': json.dumps("that doesn't seem to be here")
        }

def puts(scope, table, body):
    if table in ['', 'contact', 'enquiry']:
        return {
            'statusCode': 404,
            'body': json.dumps("that doesn't seem to be here")
        }
    ddb_table = dynamodb.Table(f"{scope}_{table}")
    try:
        response = ddb_table.put_item(Item=body)
        if 'email' in body:
            sendmail(compose_enquiry(body))
        return {
            'statusCode': response['ResponseMetadata']['HTTPStatusCode'],
            'body': json.dumps('')
        }
    except:
        return {
            'statusCode': 404,
            'body': json.dumps("that doesn't seem to be here")
        }

def posts(scope, table, body):
    if table == 'update':
        update_tables(dynamodb, body)
        return {
            'statusCode': 200,
            'body': json.dumps("triggered update from boatregister")
        }
    if table == 'contact':
        return sendmail(compose_contact(body))
    if table == 'enquiry':
        return enquiry(body)
    if table == 'profile':
        return sendmail(compose_profile(body))
    if 'to' in body or 'cc' in body or 'bcc' in body:
        return sendmail(body)
    if table != '':
        putChangedFields(scope, table, body)
    return {
        'statusCode': 200,
        'body': json.dumps("put data to table")
    }
