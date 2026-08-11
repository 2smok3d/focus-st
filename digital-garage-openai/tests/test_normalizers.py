from pathlib import Path
from garage.parsers.candump import parse as parse_can
from garage.parsers.forscan import parse_text
def test_candump(tmp_path:Path):
 p=tmp_path/'a.log'; p.write_text('(1469439874.299591) can1 080#00000191\n'); frames,w=parse_can(p); assert not w and frames[0].arbitration_id==0x80 and frames[0].data_hex=='00000191'
def test_dtc(tmp_path:Path):
 p=tmp_path/'dtc.txt'; p.write_text('PCM: P04DB crankcase ventilation disconnected'); dtcs,_,_=parse_text(p); assert dtcs[0].code=='P04DB'
