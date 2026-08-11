from pathlib import Path
from datetime import datetime
from .normalizer import ingest
from .db import SessionLocal
from .models import DiagnosticSession,DTC,Measurement,CANFrame,Vehicle
from .config import settings

def persist_file(path:str,vehicle_id:str|None=None):
    s,raw,out=ingest(path,vehicle_id)
    with SessionLocal() as db:
        vehicle_id=s.vehicle_id
        if not db.get(Vehicle,vehicle_id): db.add(Vehicle(id=vehicle_id)); db.flush()
        existing=db.query(DiagnosticSession).filter_by(vehicle_id=vehicle_id,sha256=s.sha256).first()
        if existing: return {'status':'duplicate','session_id':existing.id,'sha256':s.sha256}
        sid=f'{vehicle_id}:{s.sha256[:24]}'
        row=DiagnosticSession(id=sid,vehicle_id=vehicle_id,source_format=s.source_format,source_name=s.source_name,sha256=s.sha256,parser_version='0.1',warnings=s.warnings,raw_path=str(raw),normalized_path=str(out))
        db.add(row); db.flush()
        for d in s.dtcs: db.add(DTC(session_id=sid,module=d.module,code=d.code,status=d.status,description=d.description,freeze_frame=d.freeze_frame))
        for m in s.measurements:
            val_num=m.value if isinstance(m.value,(int,float)) else None; val_text=None if val_num is not None else str(m.value)
            db.add(Measurement(session_id=sid,module=m.module,name=m.name,value_num=val_num,value_text=val_text,unit=m.unit,raw=m.raw))
        for f in s.can_frames: db.add(CANFrame(session_id=sid,ts_epoch=f.timestamp_epoch,interface=f.interface,arbitration_id=f.arbitration_id,is_extended=f.is_extended,dlc=f.dlc,data_hex=f.data_hex,decoded=f.decoded))
        db.commit(); return {'status':'imported','session_id':sid,'sha256':s.sha256,'dtcs':len(s.dtcs),'measurements':len(s.measurements),'can_frames':len(s.can_frames)}

if __name__=='__main__':
    import argparse,json; p=argparse.ArgumentParser(); p.add_argument('path'); p.add_argument('--vehicle-id'); a=p.parse_args(); print(json.dumps(persist_file(a.path,a.vehicle_id),indent=2))
