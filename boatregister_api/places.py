import json
import urllib.request
import urllib.parse
from decimal import Decimal

def geonames(place):
  url = f'https://secure.geonames.org/searchJSON?username=oga_boatregister&country=uk&country=ie&name={urllib.parse.quote(place)}'
  print(url)
  f = urllib.request.urlopen(url)
  return json.loads(f.read())

def choose(names, name):
  print(json.dumps(names))
  places = [gn for gn in names if gn['fcl'] == 'P']
  if len(places) > 0:
    exact = [gn for gn in places if gn['name'] == name]
    if len(exact) > 0:
      return exact[0]
    return places[0]
  return names[0]

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
  return data

def geocode(dynamodb, qsp, timestamp):
  name = qsp['name']
  ddb_table = dynamodb.Table('geonames_cache')
  r = ddb_table.get_item(Key={ 'name': name })
  if 'Item' in r:
    data = mapDdbData(r['Item'])
    return {
      'statusCode': 200,
      'body': json.dumps(data)
    }
  p = geonames(name)
  n = p.get('totalResultsCount', 0)
  if n == 1:
    data = p['geonames'][0]
  if n > 1:
    data = choose(p['geonames'], name)
  if n == 0:
    data = { 'message': 'not found' }
  ddb_table.put_item(Item={**qsp, **data, 'timestamp': timestamp + 86400 })
  return {
      'statusCode': 200,
      'body': json.dumps(data)
  }

def mapfromgoogle(p):
  l = p['geometry']['location']
  print('L', l)
  return {'lat': Decimal(l['lat']), 'lng': Decimal(l['lng'])}

def googlegeolocate(place):
  api_key = 'AIzaSyCZDcYQUxHFyGDz7Gal58EMrACIHcvcAuw'
  url = f'https://maps.googleapis.com/maps/api/geocode/json?key={api_key}&address={urllib.parse.quote(place)}'
  f = urllib.request.urlopen(url)
  r = f.read()
  j = json.loads(r)
  if 'status' in j and j['status'] == 'OK':
    all = j['results']
    return [mapfromgoogle(p) for p in all]
  return None
