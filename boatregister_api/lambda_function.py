import os
import simplejson as json
from tables import gets, puts, posts
from shuffle import shuffle
import get_upload_credentials

def lambda_handler(event, context):
    # print(json.dumps(event))
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
    pp = event.get('pathParameters', {})
    scope = pp.get('scope', 'public')
    table = pp.get('table', '')    
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
        if rq['http']['path'].endswith('upload_credentials'):
            bucket = os.environ.get('UPLOAD_BUCKET', None)
            pool = os.environ.get('ID_POOL', None)
            return get_upload_credentials.handler(pool, bucket)
        return gets(scope, table, qsp, rq['timeEpoch'])
    elif method == 'PUT':
        return puts(scope, table, json.loads(event['body']))
    elif method == 'POST':
        if rq['http']['path'].endswith('shuffle'):
            return shuffle()
        return posts(scope, table, json.loads(event['body']))
    else:
        return {
            'statusCode': 200,
            'body': json.dumps("sorry, I didn't understand that")
        }
