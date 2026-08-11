from .db import Base,engine,SessionLocal
from .models import Vehicle
from .config import settings
Base.metadata.create_all(engine)
with SessionLocal() as db:
    if not db.get(Vehicle,settings.vehicle_id):
        db.add(Vehicle(id=settings.vehicle_id,year=2017,make='Ford',model='Focus ST',trim='ST1')); db.commit()
print('garage database ready')
