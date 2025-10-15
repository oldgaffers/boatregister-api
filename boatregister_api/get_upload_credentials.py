import json
import boto3

def handler(pool, bucket):
        idpool = f'eu-west-1:{pool}'
        cognito = boto3.client('cognito-identity')
        response = cognito.get_id(IdentityPoolId=idpool)
        identityId = response['IdentityId']
        print(identityId)
        return {
            'statusCode': 200,
            'headers': { 'content-type': 'application/json'},
            'body': json.dumps({
                'bucketName': bucket,
                 'region': 'eu-west-1',
                 'identityId': identityId,
            })
        }
