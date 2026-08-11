"""NHTSA recall client. Network use is explicit; results must be timestamped and VIN-specific status is separate."""
import json,urllib.parse,urllib.request
from datetime import datetime,timezone
BASE='https://api.nhtsa.gov/recalls/recallsByVehicle'
def recalls_by_vehicle(year:int,make:str,model:str):
    qs=urllib.parse.urlencode({'modelYear':year,'make':make,'model':model}); url=f'{BASE}?{qs}'
    with urllib.request.urlopen(url,timeout=15) as r: data=json.load(r)
    return {'retrieved_at':datetime.now(timezone.utc).isoformat(),'query':{'year':year,'make':make,'model':model},'vin_specific':False,'results':data.get('results',[])}
