import simplejson as json
from tables import gets, puts, posts

def lambda_handler(event, context):
    print(json.dumps(event))
    scope = event['pathParameters'].get('scope', 'public')
    table = event['pathParameters'].get('table', '')
    rq = event['requestContext']
    if 'authorizer' in rq:
        auth = rq['authorizer']
        if 'jwt' in auth:
            claims = auth['jwt']['claims']
        else:
            claims = auth['claims']
    else:
        claims = {'https://oga.org.uk/roles': '[]'}
    roles = claims['https://oga.org.uk/roles'][1:-1].split(' ')
    roles.append('public')
    if scope in roles:
        # print('scope matches')
        pass
    else:
        return {
            'statusCode': 403,
            'body': json.dumps("user does not have permission to access this table")
        } 
    method = event.get('httpMethod', rq['http']['method'])
    qsp = event.get('queryStringParameters', {})
    if method == 'GET':
        return gets(scope, table, qsp, rq['timeEpoch'])
    elif method == 'PUT':
        return puts(scope, table, json.loads(event['body']))
    elif method == 'POST':
        return posts(scope, table, json.loads(event['body']))
    else:
        return {
            'statusCode': 200,
            'body': json.dumps("sorry, I didn't understand that")
        }
