from mcp.server.fastmcp import FastMCP
from .parts import shopping_links
from .normalizer import ingest
from .config import settings
mcp=FastMCP('Digital Automotive Garage')
@mcp.tool()
def garage_get_vehicle()->dict: return {'vehicle_id':settings.vehicle_id,'year':2017,'make':'Ford','model':'Focus ST','vehicle_writes_enabled':settings.allow_vehicle_writes}
@mcp.tool()
def diagnostics_ingest_file(path:str)->dict:
 s,raw,out=ingest(path); return {'source_format':s.source_format,'sha256':s.sha256,'dtcs':[d.model_dump() for d in s.dtcs],'measurement_count':len(s.measurements),'can_frame_count':len(s.can_frames),'warnings':s.warnings,'raw_path':str(raw),'normalized_path':str(out)}
@mcp.tool()
def parts_search_links(query:str)->dict: return shopping_links(query)
@mcp.tool()
def safety_capabilities()->dict: return {'read_only_default':True,'requires_human_approval':['clear DTC','actuator command','module configuration','flash/reprogramming','CAN transmission'],'implemented_vehicle_write_tools':[]}
if __name__=='__main__': mcp.run()
