from decimal import Decimal
from updates import update_tables
from places import geocode
from mail import sendmail
from summarise import buildersummary
import boto3
import simplejson as json

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def json_from_object(bucket, key):
    r = s3.get_object(Bucket=bucket, Key=key)
    text = r["Body"].read().decode('utf-8')
    return json.loads(text)
    
def gold():
    return json_from_object('boatregister', 'gold/latest.json')

def getMember(member):
    g = gold()
    n = [m for m in g if m['ID'] == member and m['Status'] != 'Left OGA']
    if len(n) > 0:
        return n[0]
    return None

def getDear(members):
    n = [o['Firstname'] for o in members]
    if len(n) > 0:
        return ' and '.join(n)
    return "folks"

def compose_contact(body):
    id = body.get('id', body.get('member', None))
    # print('compose_contact', id)
    if id is None:
        return None
    member = getMember(id)
    dear = getDear([member])
    your = 'your '
    name = 'an OGA member'
    if 'name' in body and len(body['name'].strip()) > 0:
        name = body['name']
    text = [
        f"Dear {dear},",
        f"{name} would like to contact you regarding:",
        f"{body['text']}."
    ]
    text.append(f"They can be contacted at {body['email']}.")
    text.append("If our records are out of date and this email is not appropriate, please accept our apologies.")
    text.append("You can contact us by replying to this email or via our website oga.org.uk.")
    mail = { 'subject': 'hello from an OGA member' }
    mail['message'] = "\n".join(text)
    mail['to'] = [member['Email']]
    # print('compose_contact', mail)
    return mail

def compose_enquiry(body):
    mail = { 'subject': body['topic']}
    text = [f"{body['name']} has expressed interest in {body['topic']}.", 'The details are:']
    mail['message'] = "\n".join(text + [f"{field}: {body[field]}" for field in body.keys()])
    mail['to'] = [ body['email'], f"{body['topic']}@oga.org.uk"]
    # print('compose_enquiry', mail)
    return mail

def paramMap(val):
    if val == 'true':
        return True
    if val == 'false':
        return False
    try:
        return int(val)
    except:
        return val

def contact(body):
    return sendmail(compose_contact(body))
    
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

def compose_profile(body):
    id = body.get('id', body.get('member', None))
    mail = { 'subject': f"Membership data change request for {body['firstname']} {body['lastname']} ({id})"}
    mail['message'] = body['text']
    mail['to'] = ["membership@oga.org.uk"]
    return mail

def profile(body):
    mail = compose_profile(body)
    return sendmail(mail)

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
    ddb_table = dynamodb.Table(f"{scope}_{table}")
    try:
        if qsp is None:
            data = ddb_table.scan()
            items = data['Items']
        elif table == 'place':
            return geocode(dynamodb, qsp.get('builder', None), timestamp) 
        elif table == 'builder':
            if 'builder' not in qsp:
                return {
                    'statusCode': 400,
                    'body': json.dumps("missing builder parameter")
                }
            return buildersummary(ddb_table, qsp['builder'], timestamp)            
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
        print(e)
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
        return contact(body)
    if table == 'enquiry':
        return enquiry(body)
    if table == 'profile':
        return profile(body)
    if 'to' in body or 'cc' in body or 'bcc' in body:
        return sendmail(body)
    if table != '':
        putChangedFields(scope, table, body)
    return {
        'statusCode': 200,
        'body': json.dumps("put data to table")
    }
