from decimal import Decimal
from updates import update_tables
from places import geocode
from emails import compose_contact, compose_profile, compose_enquiry
from mail import sendmail
from summarise import buildersummary
import boto3
import simplejson as json
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource('dynamodb')

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

def paramMap(val):
    if val == 'true':
        return True
    if val == 'false':
        return False
    try:
        return int(val)
    except:
        return val

def queryOrScan(ddb_table, attr, values, fields):
    if len(values) == 1:
        data = ddb_table.query(KeyConditionExpression=Key(attr).eq(values[0]), ProjectionExpression=', '.join(fields))
        total = data['ScannedCount']
        items = data['Items']
    else:
        fe = Attr(attr).is_in(values)
        data = ddb_table.scan(FilterExpression=fe, ProjectionExpression=', '.join(fields))
        more = True
        items = data['Items']
        total = data['ScannedCount']
        while more:
            if 'LastEvaluatedKey' in data:
                data = ddb_table.scan(FilterExpression=fe, ProjectionExpression=', '.join(fields), ExclusiveStartKey=data['LastEvaluatedKey'])
                items.extend(data['Items'])
                total += data['ScannedCount']
            else:
                more = False
    return items, total

def gets(scope, table, qsp, timestamp):
    total = 0
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
        else:
            ddb_table = dynamodb.Table(f"{scope}_{table}")
        if qsp is None:
            p = {}
            fields = []
        else:
            p = qsp
            f = p.pop('fields', '').strip()
            if ','  in f:
                fields = [x.strip() for x in f.split(',')]
            elif f == '':
                f = []
            else:
                fields = [f]
        if 'id' in p:
            ids = [int(n) for n in p['id'].split(',')]
            items, total = queryOrScan(ddb_table, 'id', ids, fields)
        elif 'member' in p:
            members = [int(n) for n in p['member'].split(',')]
            items, total = queryOrScan(ddb_table, 'membership', members, fields)
        else:
            scan_kwargs = {}
            if len(fields) > 0:
                scan_kwargs['ProjectionExpression'] = ', '.join(fields)
            if p != {}:
                scan_kwargs['FilterExpression'] = Attr(list(p.keys())[0]).eq(paramMap(list(p.values())[0]))
            data = ddb_table.scan(**scan_kwargs)
            items = data['Items']
            total = data['ScannedCount']
            more = True
            while more:
                if 'LastEvaluatedKey' in data:
                    scan_kwargs['ExclusiveStartKey'] = data['LastEvaluatedKey']
                    data = ddb_table.scan(**scan_kwargs)
                    items.extend(data['Items'])
                    total += data['ScannedCount']
                else:
                    more = False
        return {
            'statusCode': 200,
            'body': json.dumps({ 'Items': items, 'Count': len(items), 'ScannedCount': total})
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
