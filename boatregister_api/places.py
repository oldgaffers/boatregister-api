import json
from geonames import geonames
from google import googlegeolocate

def mapDdbData(item):
  data = { **item }
  if 'lat' in data:
    data['lat'] = float(data['lat'])
  if 'lng' in data:
    data['lng'] = float(data['lng'])
  if 'population' in data:
    data['population'] = int(data['population'])
  if 'geonameId' in data:
    data['geonameId'] = int(data['geonameId'])
  if 'timestamp' in data:
    data['timestamp'] = int(data['timestamp'])
  return data

def save(ddb_table, qsp, data, timestamp):
  ddb_table.put_item(Item={**qsp, **data, 'timestamp': timestamp + 86400 })

def geocode(dynamodb, qsp, timestamp):
  name = qsp['name']
  ddb_table = dynamodb.Table('geonames_cache')
  r = ddb_table.get_item(Key={ 'name': name })
  if 'Item' in r:
    item = r['Item']
    if 'message' in item:
      data = googlegeolocate(name)
      save(ddb_table, qsp, data, timestamp)
    data = mapDdbData(item)
    return {
      'statusCode': 200,
      'body': json.dumps(data)
    }
  data = geonames(name)
  if 'message' in data:
    data = googlegeolocate(name)
  save(ddb_table, qsp, data, timestamp)
  return {
      'statusCode': 200,
      'body': json.dumps(data)
  }
