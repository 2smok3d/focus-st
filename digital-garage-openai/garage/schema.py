from typing import Any,Optional
from pydantic import BaseModel,Field
class NormalizedDTC(BaseModel):
 module:Optional[str]=None; code:str; status:Optional[str]=None; description:Optional[str]=None; freeze_frame:dict[str,Any]=Field(default_factory=dict)
class NormalizedMeasurement(BaseModel):
 timestamp:Optional[str]=None; module:Optional[str]=None; name:str; value:Any; unit:Optional[str]=None; raw:dict[str,Any]=Field(default_factory=dict)
class NormalizedCANFrame(BaseModel):
 timestamp_epoch:Optional[float]=None; interface:Optional[str]=None; arbitration_id:int; is_extended:bool=False; dlc:int; data_hex:str; decoded:dict[str,Any]=Field(default_factory=dict)
class NormalizedSession(BaseModel):
 schema_version:str='garage.session.v1'; vehicle_id:str; source_format:str; source_name:str; sha256:str; mileage:Optional[int]=None; timezone:Optional[str]=None; dtcs:list[NormalizedDTC]=Field(default_factory=list); measurements:list[NormalizedMeasurement]=Field(default_factory=list); can_frames:list[NormalizedCANFrame]=Field(default_factory=list); warnings:list[str]=Field(default_factory=list)
