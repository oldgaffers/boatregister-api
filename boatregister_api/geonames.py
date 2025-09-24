import json
import urllib.request
import urllib.parse

def geonames(place):
  url = f'https://secure.geonames.org/searchJSON?username=oga_boatregister&featureCode=p&country=uk&country=ie&name_equals={urllib.parse.quote(place)}'
  # print(url)
  f = urllib.request.urlopen(url)
  p = json.loads(f.read())
  n = p.get('totalResultsCount', 0)
  if n == 1:
    data = p['geonames'][0]
  if n > 1:
    sorted_names = sorted(p['geonames'], key=lambda k: k['population'], reverse=True)
    data = sorted_names[0]
  if n == 0:
    data = { 'message': 'not found' }
  return data
