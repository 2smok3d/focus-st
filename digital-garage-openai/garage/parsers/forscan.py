import csv,re
from pathlib import Path
from ..schema import NormalizedDTC,NormalizedMeasurement
DTC_RE=re.compile(r'\b([PBCU][0-3][0-9A-F]{3})(?:[-: ]?([0-9A-F]{2}))?\b',re.I)
def parse_text(path:Path):
 text=path.read_text(errors='replace'); dtcs=[]; seen=set()
 for line in text.splitlines():
  for m in DTC_RE.finditer(line):
   code=m.group(1).upper()
   if code not in seen: seen.add(code); dtcs.append(NormalizedDTC(code=code,description=line.strip()[:500]))
 return dtcs,[],[]
def parse_csv(path:Path):
 measurements=[]; warnings=[]
 with path.open(errors='replace',newline='') as f:
  sample=f.read(4096); f.seek(0)
  try: dialect=csv.Sniffer().sniff(sample,delimiters=',;\t')
  except csv.Error: dialect=csv.excel
  for i,row in enumerate(csv.DictReader(f,dialect=dialect),2):
   ts=row.get('Time') or row.get('Timestamp') or row.get('time')
   for k,v in row.items():
    if k is None or k.lower() in {'time','timestamp'} or v in (None,''): continue
    val=v.strip(); unit=None; m=re.match(r'^\s*(-?\d+(?:\.\d+)?)\s*([^\d\s].*)?$',val); parsed=float(m.group(1)) if m else val
    if m and m.group(2): unit=m.group(2).strip()
    measurements.append(NormalizedMeasurement(timestamp=ts,name=k.strip(),value=parsed,unit=unit,raw={'row':i}))
 return [],measurements,warnings
def parse(path:Path): return parse_csv(path) if path.suffix.lower()=='.csv' else parse_text(path)
