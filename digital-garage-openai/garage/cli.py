import argparse,json
from .normalizer import ingest
def main():
 p=argparse.ArgumentParser(prog='garage'); sp=p.add_subparsers(dest='cmd',required=True); i=sp.add_parser('ingest'); i.add_argument('path'); i.add_argument('--vehicle-id'); a=p.parse_args()
 if a.cmd=='ingest':
  s,raw,out=ingest(a.path,a.vehicle_id); print(json.dumps({'source_format':s.source_format,'sha256':s.sha256,'dtcs':len(s.dtcs),'measurements':len(s.measurements),'can_frames':len(s.can_frames),'warnings':s.warnings,'raw':str(raw),'normalized':str(out)},indent=2))
if __name__=='__main__': main()
