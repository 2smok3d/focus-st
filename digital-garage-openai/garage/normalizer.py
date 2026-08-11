import hashlib,shutil,re
from pathlib import Path
from .config import settings
from .schema import NormalizedSession
from .parsers import forscan,candump
def sha256(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
 return h.hexdigest()
def detect(path):
 path=Path(path); name=path.name.lower()
 if path.suffix.lower() in {'.log','.txt'}:
  first=path.read_text(errors='ignore')[:1000]
  if '#' in first and re.search(r'\bcan\d+\s+[0-9A-Fa-f]{3,8}[# ]',first): return 'candump'
  if 'forscan' in first.lower() or 'dtc' in name or 'info_' in name or 'log_' in name: return 'forscan'
 if path.suffix.lower()=='.csv': return 'forscan_csv'
 return 'generic_text'
def ingest(src,vehicle_id=None):
 path=Path(src); digest=sha256(path); vehicle_id=vehicle_id or settings.vehicle_id; root=Path(settings.data_root); raw=root/'raw'/vehicle_id/digest[:2]; raw.mkdir(parents=True,exist_ok=True); raw_path=raw/f'{digest}__{path.name}'
 if not raw_path.exists(): shutil.copy2(path,raw_path)
 fmt=detect(path); dtcs=[]; measurements=[]; frames=[]; warnings=[]
 if fmt in {'forscan','forscan_csv'}: dtcs,measurements,warnings=forscan.parse(path)
 elif fmt=='candump': frames,warnings=candump.parse(path)
 else: warnings.append('generic_text: preserved raw file; no structured parser matched')
 s=NormalizedSession(vehicle_id=vehicle_id,source_format=fmt,source_name=path.name,sha256=digest,dtcs=dtcs,measurements=measurements,can_frames=frames,warnings=warnings); normalized=root/'normalized'/vehicle_id; normalized.mkdir(parents=True,exist_ok=True); out=normalized/f'{digest}.json'; out.write_text(s.model_dump_json(indent=2)); return s,raw_path,out
