from dataclasses import dataclass
from datetime import date,timedelta
@dataclass(frozen=True)
class Interval: key:str; miles:int|None=None; months:int|None=None
def due_status(current_miles,last_miles,last_date,interval,today=None):
 today=today or date.today(); miles_left=None if interval.miles is None or last_miles is None else interval.miles-(current_miles-last_miles); date_due=None if interval.months is None or last_date is None else last_date+timedelta(days=round(interval.months*30.4375)); overdue=(miles_left is not None and miles_left<=0) or (date_due is not None and date_due<=today); due_soon=(miles_left is not None and 0<miles_left<=max(500,interval.miles*.1)) or (date_due is not None and today<date_due<=today+timedelta(days=30)); return {'overdue':overdue,'due_soon':due_soon,'miles_remaining':miles_left,'date_due':date_due.isoformat() if date_due else None}
