import json
import urllib.request
import urllib.parse
import boto3

ssm = boto3.client('ssm')
r = ssm.get_parameter(Name='GOOGLE/GEO_API_KEY')
api_key = r['Parameter']['Value']

def googlegeolocate(place):
  url = f'https://maps.googleapis.com/maps/api/geocode/json?key={api_key}&address={urllib.parse.quote(place)}'
  f = urllib.request.urlopen(url)
  r = f.read()
  j = json.loads(r)
  if 'status' in j and j['status'] == 'OK':
    wanted = None
    for p in j['results']:
      cc = [a['short_name'] for a in p['address_components'] if 'country' in a['types']]
      if len(cc) > 0:
        country = cc[0]
        if country in ['GB', 'IE']:
          wanted = p
    if wanted is not None:
      l = p['geometry']['location']
      return {**l, 'name': place, 'address_components': p['address_components']}
  return {'message': 'not found'}
