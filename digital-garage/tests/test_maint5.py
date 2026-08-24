"""MAINT5 — five-state maintenance vocabulary (DUE vs OVERDUE).

The split logic is pure; a Postgres-or-skip test drives it through the real
`maintenance_summary` with a seeded interval + service event + odometer.
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import engine, session_scope
from app.service import _past_due_state

DB = __import__("pathlib").Path(__file__).resolve().parent.parent / "db"


# ---- pure split logic (no DB) ---------------------------------------------
def test_just_past_is_due_well_past_is_overdue():
    assert _past_due_state(-300, None) == "due"          # 300 mi past, within 500 margin
    assert _past_due_state(-5000, None) == "overdue"     # well past
    assert _past_due_state(None, -0.5) == "due"          # half a month past
    assert _past_due_state(None, -3.0) == "overdue"      # months well past


def test_worst_dimension_drives_the_split():
    # miles only just past, but time well past → OVERDUE (whichever is worse)
    assert _past_due_state(-100, -6.0) == "overdue"
    # both only just past → DUE
    assert _past_due_state(-100, -0.4) == "due"


# ---- integration through maintenance_summary (Postgres-or-skip) -----------
def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        return True
    except OperationalError:
        return False


@pytest.mark.skipif(not _db_up(), reason="Postgres not reachable — skipping DB integration")
def test_maintenance_summary_buckets_due_vs_overdue():
    with engine.begin() as conn:
        for f in sorted(DB.glob("schema*.sql"), key=lambda p: (len(p.stem), p.stem)):
            conn.execute(text(f.read_text()))
    from app import service
    from app.models import MaintenanceInterval, OdometerReading, ServiceEvent
    from app.seed import seed as seed_fn
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        veh = service.get_vehicle(s)
        # clean slate for the two items this test drives
        from sqlalchemy import delete
        for item in ("m5-due", "m5-overdue"):
            s.execute(delete(ServiceEvent).where(ServiceEvent.item == item))
            s.execute(delete(MaintenanceInterval).where(MaintenanceInterval.item == item))
        # unambiguously the latest reading (the seed vehicle already has an earlier one)
        s.add(OdometerReading(vehicle_id=veh.id, miles=100000,
                              recorded_at=dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=1)))
        # DUE: 5k interval, last done at 94,800 → due at 99,800, 200 mi past (within 500 margin)
        s.add(MaintenanceInterval(vehicle_id=veh.id, item="m5-due", interval_miles=5000))
        s.add(ServiceEvent(vehicle_id=veh.id, item="m5-due",
                           performed_at=dt.date(2025, 1, 1), miles=94800))
        # OVERDUE: 5k interval, last done at 90,000 → due at 95,000, 5,000 mi past
        s.add(MaintenanceInterval(vehicle_id=veh.id, item="m5-overdue", interval_miles=5000))
        s.add(ServiceEvent(vehicle_id=veh.id, item="m5-overdue",
                           performed_at=dt.date(2025, 1, 1), miles=90000))
    with session_scope() as s:
        veh = service.get_vehicle(s)
        summary = service.maintenance_summary(s, veh.id)
    by_item = {i["item"]: i["status"] for i in summary["items"]}
    assert by_item["m5-due"] == "due"
    assert by_item["m5-overdue"] == "overdue"
    assert "due" in summary["counts"] and summary["counts"]["due"] >= 1
    # both past-due items count toward the act-now total
    assert summary["attention"] >= 2

    # clean up the rows this test injected into the shared DB (intervals, service
    # events, and the odometer reading) so they never leak into other tests / projections.
    from sqlalchemy import delete
    with session_scope() as s:
        for item in ("m5-due", "m5-overdue"):
            s.execute(delete(ServiceEvent).where(ServiceEvent.item == item))
            s.execute(delete(MaintenanceInterval).where(MaintenanceInterval.item == item))
        s.execute(delete(OdometerReading).where(OdometerReading.miles == 100000))
