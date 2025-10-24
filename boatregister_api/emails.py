from golds3 import getMember
from email import sendmail

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

def contact(body):
    return sendmail(compose_contact(body))

def compose_profile(body):
    id = body.get('id', body.get('member', None))
    mail = { 'subject': f"Membership data change request for {body['firstname']} {body['lastname']} ({id})"}
    mail['message'] = body['text']
    mail['to'] = ["membership@oga.org.uk"]
    return mail

def profile(body):
    mail = compose_profile(body)
    return sendmail(mail)