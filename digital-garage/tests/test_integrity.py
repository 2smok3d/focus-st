"""INTEG — datalog signal-plausibility checks.

The pure `check_measurements` runs without a DB. A Postgres-or-skip test stores a session
with a stuck sensor and an out-of-range spike, then checks the service flags them.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import engine, session_scope
from app.integrity import check_measurements

DB = __import__("pathlib").Path(__file__).resolve().parent.parent / "db"


# ---- pure engine (no DB) --------------------------------------------------
def _clean(n=30):
    out = []
    for i in range(n):
        out.append({"pid": "Engine RPM", "value": 1000 + i * 100, "unit": "rpm", "t_offset_s": i * 0.1})
        out.append({"pid": "Boost", "value": 5 + i * 0.5, "unit": "psi", "t_offset_s": i * 0.1})
    return out


def test_clean_log_flags_nothing():
    assert check_measurements(_clean())["findings"] == []


def test_flags_a_frozen_dynamic_channel():
    m = [{"pid": "Coolant Temp", "value": 90.0, "unit": "C", "t_offset_s": i * 0.1} for i in range(25)]
    r = check_measurements(m)
    assert r["by_kind"].get("frozen") == 1
    assert r["findings"][0]["role"] == "coolant"


def test_frozen_needs_enough_samples():
    m = [{"pid": "Coolant Temp", "value": 90.0, "unit": "C", "t_offset_s": i * 0.1} for i in range(5)]
    assert "frozen" not in check_measurements(m)["by_kind"]


def test_flags_out_of_range_and_nonfinite():
    m = _clean(25) + [
        {"pid": "Engine RPM", "value": 99999, "unit": "rpm", "t_offset_s": 9.0},
        {"pid": "Lambda", "value": float("nan"), "unit": "", "t_offset_s": 9.1},
    ]
    r = check_measurements(m)
    assert r["by_kind"].get("out_of_range") == 1 and r["by_kind"].get("nonfinite") == 1


def test_flags_time_disorder():
    m = [{"pid": "Boost", "value": 10, "t_offset_s": 5.0},
         {"pid": "Boost", "value": 11, "t_offset_s": 3.0}]
    assert check_measurements(m)["by_kind"].get("time_disorder") == 1


def test_generous_bands_dont_flag_tuning_extremes():
    # ~28 psi of boost and a ~250°F charge temp are aggressive but plausible — and they
    # vary (not frozen), so nothing is flagged. Samples are time-ordered (as stored logs are).
    m = []
    for i in range(30):
        m.append({"pid": "Boost", "value": 26 + (i % 4), "unit": "psi", "t_offset_s": i * 0.1})
        m.append({"pid": "Charge Air Temp", "value": 250 - i, "unit": "F", "t_offset_s": i * 0.1})
    assert check_measurements(m)["findings"] == []


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
def test_vehicle_integrity_flags_a_stored_session():
    with engine.begin() as conn:
        for f in sorted(DB.glob("schema*.sql"), key=lambda p: (len(p.stem), p.stem)):
            conn.execute(text(f.read_text()))
    from app import integrity, service
    from app.models import DiagnosticSession, Measurement
    from app.seed import seed as seed_fn
    sha = uuid.uuid4().hex
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        veh = service.get_vehicle(s)
        ds = DiagnosticSession(vehicle_id=veh.id, kind="datalog", sha256=sha,
                               raw_path="/tmp/integ-test.csv", note="integ-test")
        s.add(ds)
        s.flush()
        for i in range(25):                       # a stuck coolant sensor
            s.add(Measurement(session_id=ds.id, pid="Coolant Temp", value=90.0, unit="C", t_offset_s=i * 0.1))
        s.add(Measurement(session_id=ds.id, pid="Engine RPM", value=99999.0, unit="rpm", t_offset_s=2.6))
        sid = ds.id
    try:
        with session_scope() as s:
            veh = service.get_vehicle(s)
            r = integrity.vehicle_integrity(s, veh.id)
        mine = [rep for rep in r["reports"] if rep["session_id"] == sid]
        assert mine, "the flawed session should be flagged"
        kinds = mine[0]["by_kind"]
        assert kinds.get("frozen") == 1 and kinds.get("out_of_range") == 1
    finally:
        from sqlalchemy import delete
        with session_scope() as s:
            s.execute(delete(DiagnosticSession).where(DiagnosticSession.id == sid))
