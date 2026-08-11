from dataclasses import dataclass,asdict
from typing import Optional
@dataclass
class ForumClaim:
 source_url:str; thread_title:str; post_date:Optional[str]=None; author:Optional[str]=None; model_year:Optional[int]=None; mileage:Optional[int]=None; climate:Optional[str]=None; fuel:Optional[str]=None; tune:Optional[str]=None; modifications:Optional[str]=None; symptom:Optional[str]=None; dtcs:Optional[str]=None; tests:Optional[str]=None; action:Optional[str]=None; outcome:Optional[str]=None; followup:Optional[str]=None; corroborations:int=0; counterexamples:int=0; confidence:str='anecdote'; notes:Optional[str]=None
 def to_dict(self): return asdict(self)
