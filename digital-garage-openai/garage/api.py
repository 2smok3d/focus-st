from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from .normalizer import ingest
from .parts import shopping_links
app=FastAPI(title='Digital Garage API',version='0.1.0')
class IngestRequest(BaseModel): path:str; vehicle_id:str|None=None
@app.get('/health')
def health(): return {'ok':True}
@app.post('/ingest')
def ingest_file(req:IngestRequest):
 try:
  s,raw,out=ingest(req.path,req.vehicle_id); return {'session':s.model_dump(),'raw_path':str(raw),'normalized_path':str(out)}
 except Exception as e: raise HTTPException(400,str(e))
@app.get('/parts/search-links')
def part_links(q:str): return shopping_links(q)
@app.get('/safety')
def safety(): return {'vehicle_writes':'disabled by default','prohibited_by_default':['clear DTCs','module configuration write','ECU/module flash','arbitrary CAN transmit']}
