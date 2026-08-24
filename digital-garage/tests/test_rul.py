"""RUL — remaining-useful-life / predictive maintenance.

Pure maths (usage rate + due-date projection) runs without a DB. A Postgres-or-skip test
records an odometer series and a service event, then checks the service dates the interval.
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import engine, session_scope
from app.rul import project_due, usage_rate

DB = __import__("pathlib").Path(__file__).resolve().parent.parent / "db"


# ---- pure engine (no DB) --------------------------------------------------
def test_usage_rate_fits_miles_per_day():
    r = usage_rate([(0, 1000), (10, 1300), (20, 1600)])
    assert r == pytest.approx(30.0, abs=0.5)


def test_usage_rate_unknown_when_too_few_or_flat():
    assert usage_rate([(0, 1000), (10, 1300)]) is None          # too few
    assert usage_rate([(0, 1000), (10, 1000), (20, 1000)]) is None   # no accrual


def test_project_due_picks_the_soonest_limit():
    today = dt.date(2026, 1, 1)
    # 3000 mi left at 30 mi/day ≈ 100 days; 12 months ≈ 365 days → mileage wins
    p = project_due(3000, 12.0, 30.0, today=today)
    assert p["basis"] == "mileage" and p["days_remaining"] == pytest.approx(100, abs=1)
    assert p["projected_date"] == "2026-04-11"


def test_project_due_uses_time_when_time_comes_first():
    p = project_due(9000, 2.0, 30.0, today=dt.date(2026, 1, 1))
    assert p["basis"] == "time"                                  # 2 months < 300 days of miles


def test_project_due_none_without_a_basis():
    assert project_due(3000, None, None) is None                # mileage limit but unknown rate
    assert project_due(None, None, 30.0) is None                # nothing to project


def test_project_due_reports_overdue_as_negative():
    p = project_due(-600, None, 30.0, today=dt.date(2026, 1, 1))
    assert p["days_remaining"] < 0 and p["basis"] == "mileage"


# ---- service integration (Postgres-or-skip) -------------------------------
def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        return True
    except OperationalError:
        return False


dbonly = pytest.mark.skipif(not _db_up(), reason="Postgres not reachable — skipping DB integration")


@dbonly
def test_maintenance_rul_dates_a_logged_interval():
    with engine.begin() as conn:
        for f in sorted(DB.glob("schema*.sql"), key=lambda p: (len(p.stem), p.stem)):
            conn.execute(text(f.read_text()))
    from app import rul, service
    from app.models import MaintenanceInterval, OdometerReading, ServiceEvent
    from app.seed import seed as seed_fn
    ITEM = "rul-oil-test"
    from sqlalchemy import delete
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        veh = service.get_vehicle(s)
        now = dt.datetime.now(dt.timezone.utc)
        base = 90000
        # isolate a clean, monotonic odometer series for the fit (seed readings would
        # interleave and confound the rate); the baseline is restored in the teardown
        s.execute(delete(OdometerReading).where(OdometerReading.vehicle_id == veh.id))
        # a steady ~30 mi/day accrual over three months
        for days_ago, add in [(90, 0), (60, 900), (30, 1800), (0, 2700)]:
            s.add(OdometerReading(vehicle_id=veh.id, miles=base + add,
                                  recorded_at=now - dt.timedelta(days=days_ago)))
        s.add(MaintenanceInterval(vehicle_id=veh.id, item=ITEM, interval_miles=5000,
                                  interval_months=6, verification="OEM_VERIFIED"))
        s.add(ServiceEvent(vehicle_id=veh.id, item=ITEM,
                           performed_at=(now - dt.timedelta(days=30)).date(), miles=base + 1800))
    try:
        with session_scope() as s:
            veh = service.get_vehicle(s)
            r = rul.maintenance_rul(s, veh.id)
        assert r["usage"]["known"] and r["usage"]["miles_per_day"] == pytest.approx(30, abs=3)
        mine = [p for p in r["projected"] if p["item"] == ITEM]
        assert mine, "the logged interval should get a projected date"
        p = mine[0]
        assert p["projected_date"] and p["basis"] in ("mileage", "time")
        # serviced at 91800 with a 5000 mi interval → next at 96800; ~2300 mi left at ~30/day
        assert p["days_remaining"] > 0
    finally:
        from sqlalchemy import delete
        with session_scope() as s:
            veh = service.get_vehicle(s)
            s.execute(delete(ServiceEvent).where(ServiceEvent.item == ITEM))
            s.execute(delete(MaintenanceInterval).where(MaintenanceInterval.item == ITEM))
            s.execute(delete(OdometerReading).where(OdometerReading.vehicle_id == veh.id))
            # restore the seed's baseline odometer so later tests see the canonical mileage
            s.add(OdometerReading(vehicle_id=veh.id, miles=86390))
