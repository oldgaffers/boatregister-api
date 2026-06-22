import json
import boto3

def guest(pool, bucket):
        idpool = f'eu-west-1:{pool}'
        cognito = boto3.client('cognito-identity')
        response = cognito.get_id(IdentityPoolId=idpool)
        identityId = response['IdentityId']
        return {
            'statusCode': 200,
            'headers': { 'content-type': 'application/json'},
            'body': json.dumps({
                'bucketName': bucket,
                 'region': 'eu-west-1',
                 'identityId': identityId,
                 'identityPoolId': idpool,
            })
        }

def member(pool, bucket, user):
        idpool = f'eu-west-1:{pool}'
        cognito = boto3.client('cognito-identity')
        response = cognito.get_open_id_token_for_developer_identity(
            IdentityPoolId=idpool,
            Logins={'oga.org.uk': user}
        )
        identityId = response['IdentityId']
        return {
            'statusCode': 200,
            'headers': { 'content-type': 'application/json'},
            'body': json.dumps({
                'bucketName': bucket,
                 'region': 'eu-west-1',
                 'identityId': identityId,
                 'identityPoolId': idpool,
                 'token': response['Token']
            })
        }