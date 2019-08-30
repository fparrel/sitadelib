import requests
from lxml import etree
import re
from pyproj import Proj, transform

# Regex patters to parse html
pat = re.compile(r"popup\('afficherCarteParcelle.do\?CSRF_TOKEN=([0-9A-Z\-]*)&p=([0-9A-Z]*)&f=([0-9A-Z]*)','gde'\)")
patcenter = re.compile(r"tabPastilles.push\(new Point\(([0-9]*\.?[0-9]*),([0-9]*\.?[0-9]*)\)\)")
patproj = re.compile(r'"([0-9]*)",\s*new GeoBox\(')
patboxes = re.compile(r'new GeoBox\(\s*([0-9]*\.?[0-9]*),\s*([0-9]*\.?[0-9]*),\s*([0-9]*\.?[0-9]*),\s*([0-9]*\.?[0-9]*)\)')
patcsrf = re.compile(r"CSRF_TOKEN=([0-9A-Z\-]*)")

# "standard" lon, lat projection
proj_out = Proj(init='epsg:4326')

# To get sessionId and CSRF token
def getSessionIdAndCsrf():
  #url = 'https://www.cadastre.gouv.fr/scpc/rechercherParReferenceCadastrale.do'
  url = 'https://www.cadastre.gouv.fr/scpc/accueil.do'
  r = requests.get(url)
  jsessionid = r.cookies['JSESSIONID']
  html = r.text.encode(r.encoding)
  csrf_token = patcsrf.findall(html)[0]
  return jsessionid,csrf_token

# Get projection, center and boxes from values from sitadel CSV
def getCenterAndBoxes(cadastrefromsitadel, ville, codepostal, departement, jsessionid, csrf_token):
  # Sitadel: Parcel + section. Example: 0044ZH = parcel 44, section ZH
  sections = "000" + cadastrefromsitadel[-2:]
  parcelle = cadastrefromsitadel[:-2]

  # Use search form to get the cadastre full parcel id
  r = requests.get("https://www.cadastre.gouv.fr/scpc/rechercherParReferenceCadastrale.do",params={"CSRF_TOKEN":csrf_token,"ville":ville,"codePostal":codepostal,"codeDepartement":departement,"rechercheType":"1","sections":sections,"numeroParcelle":parcelle,"nbResultatParPage":"10"},cookies={"JSESSIONID":jsessionid})
  html = r.text.encode(r.encoding)
  t = etree.HTML(html)
  try:
    csrf_token, p, f = list(map(pat.findall, t.xpath('//tbody[@class="parcelles"]//a/@onclick')))[0][0]
  except:
    open('dump.html','w').write(html)
    raise Exception('Cannot get parcelleid, check dump.html')

  # Parse display results to get coordinates and their projection
  url = 'https://www.cadastre.gouv.fr/scpc/afficherCarteParcelle.do?CSRF_TOKEN=%(csrf_token)s&p=%(p)s&f=%(f)s&dontSaveLastForward&keepVolatileSession='%{'csrf_token':csrf_token,'p':p,'f':f}
  r = requests.get(url,cookies={"JSESSIONID":jsessionid})
  html = r.text.encode(r.encoding)
  center = map(float,patcenter.findall(html)[0])
  proj = patproj.findall(html)[0]
  boxes = map(lambda i:map(float,i),patboxes.findall(html))
  return proj, center, boxes

def main():
  jsessionid,csrf_token = getSessionIdAndCsrf()
  fromsitadel = "0044ZH"
  ville = "L'ABERGEMENT-CLEMENCIAT"
  codepostal = "01400"
  departement = "001"
  print "Inputs: %s %s %s %s" % (fromsitadel, ville, codepostal, departement)
  proj, center, boxes = getCenterAndBoxes(fromsitadel, ville, codepostal, departement, jsessionid, csrf_token)
  print "Proj: %s Center: %s Boxes: %s" % (proj, center, boxes)
  proj_in = Proj(init='epsg:'+proj)
  lon, lat = transform(proj_in,proj_out,center[0],center[1])
  print "Coordinates of center lat: %f lon: %f" % (lat, lon)

if __name__=='__main__':
  main()

