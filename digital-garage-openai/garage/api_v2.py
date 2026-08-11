from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from sqlalchemy import select,func
from .db import SessionLocal
from .models import DiagnosticSession,DTC,Vehicle,MaintenanceRecord,PartOption
from .persist import persist_file
from .parts import shopping_links
from .recalls import recalls_by_vehicle
from .calculators import tire_diameter_in,speed_error_percent,rpm_at_speed,psi_to_kpa,f_to_c,cost_per_mile
app=FastAPI(title='Digital Garage API',version='0.2.0')
class IngestRequest(BaseModel): path:str; vehicle_id:str|None=None
@app.get('/health')
def health(): return {'ok':True,'version':'0.2.0','vehicle_write_tools':False}
@app.post('/ingest')
def ingest(req:IngestRequest):
 try: return persist_file(req.path,req.vehicle_id)
 except Exception as e: raise HTTPException(400,str(e))
@app.get('/sessions')
def sessions(limit:int=100):
 with SessionLocal() as db:
  rows=db.scalars(select(DiagnosticSession).order_by(DiagnosticSession.id.desc()).limit(min(limit,500))).all()
  return [{'id':r.id,'vehicle_id':r.vehicle_id,'format':r.source_format,'file':r.source_name,'sha256':r.sha256,'warnings':r.warnings,'raw_path':r.raw_path,'normalized_path':r.normalized_path} for r in rows]
@app.get('/dtcs')
def dtcs(limit:int=200):
 with SessionLocal() as db:
  rows=db.scalars(select(DTC).order_by(DTC.id.desc()).limit(min(limit,1000))).all()
  return [{'session_id':r.session_id,'module':r.module,'code':r.code,'status':r.status,'description':r.description,'freeze_frame':r.freeze_frame} for r in rows]
@app.get('/parts/search-links')
def part_links(q:str): return shopping_links(q)
@app.get('/recalls/model')
def recalls(year:int=2017,make:str='Ford',model:str='Focus'):
 try: return recalls_by_vehicle(year,make,model)
 except Exception as e: raise HTTPException(502,f'NHTSA lookup failed: {e}')
@app.get('/calc/tire')
def tire(width:int,aspect:int,wheel:float,stock_diameter:float|None=None):
 d=tire_diameter_in(width,aspect,wheel); return {'diameter_in':d,'speed_error_percent':speed_error_percent(stock_diameter,d) if stock_diameter else None}
@app.get('/calc/rpm')
def rpm(mph:float,tire_diameter:float,gear_ratio:float,final_drive:float): return {'rpm':rpm_at_speed(mph,tire_diameter,gear_ratio,final_drive)}
@app.get('/calc/convert')
def convert(psi:float|None=None,fahrenheit:float|None=None): return {'kpa':psi_to_kpa(psi) if psi is not None else None,'celsius':f_to_c(fahrenheit) if fahrenheit is not None else None}
@app.get('/safety')
def safety(): return {'read_only_default':True,'vehicle_write_tools':[],'human_approval_required':['DTC clear','actuator commands','module configuration','flash/reprogramming','CAN transmit']}
