import json
import urllib.request
import urllib.parse

def choose(names, name):
  places = [gn for gn in names if gn['fcl'] == 'P']
  if len(places) > 0:
    exact = [gn for gn in places if gn['name'] == name]
    if len(exact) > 0:
      return exact[0]
    return places[0]
  return names[0]

def geonames(place):
  url = f'https://secure.geonames.org/searchJSON?username=oga_boatregister&country=uk&country=ie&name={urllib.parse.quote(place)}'
  # print(url)
  f = urllib.request.urlopen(url)
  p = json.loads(f.read())
  n = p.get('totalResultsCount', 0)
  if n == 1:
    data = p['geonames'][0]
  if n > 1:
    data = choose(p['geonames'], place)
  if n == 0:
    data = { 'message': 'not found' }
  return data
