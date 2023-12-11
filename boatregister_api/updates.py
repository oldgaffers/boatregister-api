import json
import urllib.request

boatRegisterHome = 'https://oldgaffers.github.io'

def get_filterable():
  f = urllib.request.urlopen(f'{boatRegisterHome}/boatregister/filterable.json')
  return json.loads(f.read())

def get_boat(oga_no):
  f = urllib.request.urlopen(f'{boatRegisterHome}/boatregister/page-data/boat/{oga_no}/page-data.json')
  d = json.loads(f.read())
  return d['result']['pageContext']['boat']

def update_extra(ddb_table, oga_no, update):
    r = ddb_table.get_item(Key={ 'oga_no': oga_no })
    if 'Item' in r:
        existing = r['Item']
        relevant = {k:v for (k,v) in existing.items() if k in update.keys()}
        print(oga_no, relevant) 
        ddb_table.put_item(Item={**existing, **update})
    else:
        ddb_table.put_item(Item={'oga_no': oga_no, **update})

def update_tables(dynamodb, body):
    print('update_tables', json.dumps(body))
    ddb_table = dynamodb.Table('public_crewing') # we should rename this
    for oga_no in body:
        print(oga_no)
        full = get_boat(oga_no)
        home_port = full.get('home_port', '').strip()
        if home_port != '':
            update_extra(ddb_table, oga_no, { 'home_port': home_port })
