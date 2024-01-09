import simplejson as json
import boto3
import smtplib

ssm = boto3.client('ssm')

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
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()
    # print('mail sent', json.dumps(headers))
    return {
        'statusCode': 200,
        'body': json.dumps('your mail has been sent')
    }