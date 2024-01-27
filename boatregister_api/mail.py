import simplejson as json
import boto3
import smtplib

ssm = boto3.client('ssm')
ses = boto3.client('ses')

def sendusingses(fromaddr, mail):
    print('sendusingses', json.dumps(mail))
    toaddrs = mail.get('to', [])
    toaddrs.append('julian.cable@yahoo.com')
    ses.send_email(
        Source=fromaddr,
        Destination={
            'ToAddresses': toaddrs,
            'CcAddresses': mail.get('cc', []),
            'BccAddresses': mail.get('bcc', [])
        },
        Message={
            'Subject': {
                'Data': mail['subject'],
                'Charset': 'utf-8'
            },
            'Body': {
                'Text': {
                    'Data': "\r\n".join(mail['message'].split("\n")),
                    'Charset': 'utf-8'
                },
            }
        },
    )

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
    fromaddr = user
    toaddrs  = []
    headers = [f'From: {fromaddr}']
    if 'reply-to' in mail:
        headers.append(f"Reply-To: {mail['reply-to']}")
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
    try:
        server = smtplib.SMTP_SSL(host, port)
        server.login(user, password)
        server.sendmail(fromaddr, toaddrs, msg)
        server.quit()
        # print('mail sent', json.dumps(headers))
    except Exception as e:
        print(e)
        sendusingses(fromaddr, mail)
    return {
        'statusCode': 200,
        'body': json.dumps('your mail has been sent')
    }