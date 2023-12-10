import simplejson as json
import boto3
import smtplib
from datetime import datetime, timedelta
from decimal import Decimal

ssm = boto3.client('ssm')
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def sendmail(mail):
    # print('sendmail', mail)
    r = ssm.get_parameter(Name='MAIL_HOST')
    host = r['Parameter']['Value']
    r = ssm.get_parameter(Name='MAIL_PORT')
    port = int(r['Parameter']['Value'])
    r = ssm.get_parameter(Name='MAIL_USER')
    user = r['Parameter']['Value']
    r = ssm.get_parameter(Name='MAIL_PASSWORD', WithDecryption=True)
    password = r['Parameter']['Value']
    server = smtplib.SMTP_SSL(host, port)
    server.login(user, password)
    fromaddr = user
    toaddrs  = []
    headers = [f'From: {fromaddr}']
    if 'to' in mail:
        headers.append(f"To: {', '.join(mail['to'])}")
        toaddrs.extend(mail['to'])
    if 'cc' in mail:
        headers.append(f"Cc: {', '.join(mail['cc'])}")
        toaddrs.extend(mail['cc'])
    if 'bcc' in mail:
        toaddrs.extend(mail['bcc'])
    toaddrs.append(user) # make sure boatregister is included
    headers.append(f"Subject: {mail['subject']}")
    msg = "\r\n".join(headers + mail['message'].split("\n"))
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()
    # print('mail sent', json.dumps(headers))
    return {
        'statusCode': 200,
        'body': json.dumps('your mail has been sent')
    }

def json_from_object(bucket, key):
    r = s3.get_object(Bucket=bucket, Key=key)
    text = r["Body"].read().decode('utf-8')
    return json.loads(text)
    
def gold():
    d = datetime.now()
    prev = (d - timedelta(days=1)).date().isoformat()
    return json_from_object('boatregister', f'gold/{prev}.json')

def getMember(member):
    g = gold()
    n = [m for m in g if m['ID'] == member]
    if len(n) > 0:
        return n[0]
    return None

def getDear(members):
    n = [o['Firstname'] for o in members]
    if len(n) > 0:
        return ' and '.join(n)
    return "folks"

def compose_contact(body):
    if 'member' not in body:
        return None
    member = getMember(body['member'])
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
    return mail

def compose_enquiry(body):
    mail = { 'subject': body['topic']}
    text = [f"{body['name']} has expressed interest in {body['topic']}.", 'The details are:']
    mail['message'] = "\n".join(text + [f"{field}: {body[field]}" for field in body.keys()])
    mail['to'] = [ body['email'], f"{body['topic']}@oga.org.uk"]
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
    # print('enquiry', json.dumps(body))
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

def rbc60registrationmail(data, email):
    mail = {
        'subject': 'RBC60 registration received',
        'to': [ "oga60@oga.org.uk", "president@oga.org.uk" ],
        'cc': [ email ],
        'message': json.dumps(data, indent=4),
    }
    return sendmail(mail)

def register(body, ddb_table):
    item = {
     "topic": "RBC 60",
     "email": body['user']['email'],
     "created_at": body['payment']['create_time'],
     "id": 0,
    }
    del body['user']
    item['data'] = body
    ddb_table.put_item(Item=item)
    # print('put to member_entries', item)
    return rbc60registrationmail(item['data'], item['email'])

def compose_profile(body):
    mail = { 'subject': f"Membership data change request for {body['firstname']} {body['lastname']} ({body['member']})"}
    text = [f"Member {body['firstname']} {body['lastname']} ({body['member']}) would like to make some changes."]
    text.append(body['text'])
    for key in ['salutation', 'telephone', 'mobile', 'area', 'town']:
        if key in body and body[key].strip() != '':
            text.append(f"{key}: {body[key]}")
    for key in ['GDPR', 'smallboats']:
        text.append(f"{key}: {body[key]}")
    text.append(f"Interest Areas: {','.join(body['interests'])}")
    mail['message'] = "\n".join(text)
    mail['to'] = ["membership@oga.org.uk"]
    return mail

def profile(body):
    return sendmail(compose_profile(body))

def map_values(d):
    r = {}
    for k in d.keys():
        val = d[k]
        if isinstance(val, Decimal):
            val = int(val)
        r[k] = val
    return r

def putChangedFields(ddb_table, body):
    data = {**body}
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

def lambda_handler(event, context):
    # print(json.dumps(event))
    if 'scope' in event['pathParameters']:
        scope = event['pathParameters']['scope']
    else:
        scope = 'public'
    if 'table' in event['pathParameters']:
        table = event['pathParameters']['table']
    else:
        table = ''
    if table in ['', 'contact', 'enquiry']:
        ddb_table = None # dummy tables
    else:
        ddb_table = dynamodb.Table(f"{scope}_{table}")
    if 'authorizer' in event['requestContext']:
        claims = event['requestContext']['authorizer']['claims']
    else:
        claims = {}
    if 'https://oga.org.uk/roles' in claims:
        oga_claims = claims['https://oga.org.uk/roles']
        if scope in oga_claims:
            # print('scope matches')
            pass
        else:
            return {
                'statusCode': 403,
                'body': json.dumps("user does not have permission to access this table")
            } 
    qsp = event['queryStringParameters']
    # print('claims', claims)
    if event['httpMethod'] == 'GET':
        try:
            # print('qsp', qsp)
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
        except:
            return {
                'statusCode': 404,
                'body': json.dumps("that doesn't seem to be here")
            }
    elif event['httpMethod'] == 'PUT':
        try:
            body = json.loads(event['body'])
            # print(json.dumps(body))
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
    elif event['httpMethod'] == 'POST':
        body = json.loads(event['body'])
        if table == 'contact':
            return contact(body)
        if table == 'enquiry':
            return enquiry(body)
        if table == 'register':
            return register(body, ddb_table)
        if table == 'profile':
            return profile(body)
        if 'to' in body or 'cc' in body or 'bcc' in body:
            return sendmail(body)
        if ddb_table is not None:
            putChangedFields(ddb_table, body)
        return {
            'statusCode': 200,
            'body': json.dumps("put data to table")
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps("sorry, I didn't understand that")
        }
