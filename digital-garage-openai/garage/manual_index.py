"""Copyright-safe local service-library indexer: records metadata and hashes, never copies or republishes manuals."""
from pathlib import Path
import hashlib,json,mimetypes

def sha256(path:Path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
 return h.hexdigest()
def build_index(root:str,out:str|None=None):
 base=Path(root); records=[]
 for p in sorted(x for x in base.rglob('*') if x.is_file()):
  records.append({'relative_path':str(p.relative_to(base)),'name':p.name,'extension':p.suffix.lower(),'mime':mimetypes.guess_type(p.name)[0],'bytes':p.stat().st_size,'sha256':sha256(p)})
 result={'root':str(base),'count':len(records),'documents':records}
 if out: Path(out).write_text(json.dumps(result,indent=2))
 return result
if __name__=='__main__':
 import argparse; a=argparse.ArgumentParser(); a.add_argument('root'); a.add_argument('--out',default='service_library_index.json'); ns=a.parse_args(); r=build_index(ns.root,ns.out); print(f"indexed {r['count']} files -> {ns.out}")
