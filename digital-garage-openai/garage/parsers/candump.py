import re
from pathlib import Path
from ..schema import NormalizedCANFrame
HASH=re.compile(r'^\((?P<ts>[\d.]+)\)\s+(?P<if>\S+)\s+(?P<id>[0-9A-Fa-f]+)#(?P<data>[0-9A-Fa-f]*)$')
BRACKET=re.compile(r'^(?P<if>\S+)\s+(?P<id>[0-9A-Fa-f]+)\s+\[(?P<dlc>\d+)\]\s*(?P<data>.*)$')
def parse(path:Path):
 out=[]; warnings=[]
 for n,line in enumerate(path.read_text(errors='replace').splitlines(),1):
  s=line.strip(); m=HASH.match(s)
  if m:
   data=m.group('data').upper(); aid=int(m.group('id'),16); out.append(NormalizedCANFrame(timestamp_epoch=float(m.group('ts')),interface=m.group('if'),arbitration_id=aid,is_extended=aid>0x7FF,dlc=len(data)//2,data_hex=data)); continue
  m=BRACKET.match(s)
  if m:
   data=''.join(m.group('data').split()).upper(); aid=int(m.group('id'),16); out.append(NormalizedCANFrame(interface=m.group('if'),arbitration_id=aid,is_extended=aid>0x7FF,dlc=int(m.group('dlc')),data_hex=data)); continue
  if s: warnings.append(f'line {n}: unparsed')
 return out,warnings
