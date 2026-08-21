"""Tests for Telemetry V2 (Milestone E).

The frame/derive/detect engine is pure and tested without a database; a small
Postgres-or-skip section covers the channel registry, event persistence, and the
telemetry → diagnostic-case evidence bridge.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app import telemetry as tel

# ---- pure engine (no DB) --------------------------------------------------

def test_derive_boost_error_and_charge_temp_delta():
    frame = [{"t": 0, "boost_cmd": 20, "boost_actual": 20, "iat": 40},
             {"t": 1, "boost_cmd": 20, "boost_actual": 16, "iat": 55}]
    d = tel.derive(frame)
    assert d[0]["boost_error"] == 0
    assert d[1]["boost_error"] == 4                 # 20 - 16
    assert d[1]["charge_temp_delta"] == 15          # 55 - min(40)


def test_detect_wot_pull_and_boost_deficit():
    frame = [
        {"t": 0.0, "rpm": 900, "boost_actual": -8, "boost_cmd": -8},
        {"t": 0.5, "rpm": 3200, "boost_actual": 12, "boost_cmd": 13},
        {"t": 1.0, "rpm": 5200, "boost_actual": 15, "boost_cmd": 20},   # 5 psi short
        {"t": 1.5, "rpm": 6200, "boost_actual": 14, "boost_cmd": 20},
        {"t": 2.0, "rpm": 3000, "boost_actual": 2, "boost_cmd": 2},
    ]
    kinds = {e.kind for e in tel.detect_events(frame)}
    assert "WOT_PULL" in kinds
    assert "BOOST_DEFICIT" in kinds                 # actual trailed target by ≥3 psi


def test_detect_knock_and_over_temp():
    frame = [
        {"t": 0.0, "rpm": 5000, "boost_actual": 18, "knock": 0, "coolant": 98},
        {"t": 0.5, "rpm": 6000, "boost_actual": 20, "knock": -7, "coolant": 112},
    ]
    events = tel.detect_events(frame)
    knock = next(e for e in events if e.kind == "KNOCK_EVENT")
    assert knock.severity == "critical"             # -7 ≤ -2*threshold
    assert any(e.kind == "OVER_TEMP" and e.severity == "critical" for e in events)


def test_clean_pull_has_no_fault_events():
    frame = [
        {"t": 0.0, "rpm": 900, "boost_actual": -8, "boost_cmd": -8, "knock": 0, "coolant": 90},
        {"t": 1.0, "rpm": 5200, "boost_actual": 20, "boost_cmd": 20, "knock": 0, "coolant": 96},
        {"t": 1.5, "rpm": 6200, "boost_actual": 20, "boost_cmd": 20, "knock": 0, "coolant": 98},
    ]
    kinds = {e.kind for e in tel.detect_events(frame)}
    assert "WOT_PULL" in kinds                       # the pull is detected
    assert kinds & {"BOOST_DEFICIT", "KNOCK_EVENT", "OVER_TEMP"} == set()   # but no faults


def test_frame_from_measurements_groups_by_time():
    ms = [{"pid": "Boost (psi)", "value": 18, "t_offset_s": 1.0},
          {"pid": "Knock (deg)", "value": -1, "t_offset_s": 1.0},
          {"pid": "RPM", "value": 5200, "t_offset_s": 1.0}]
    frame = tel.frame_from_measurements(ms)
    assert len(frame) == 1
    assert frame[0]["boost_actual"] == 18 and frame[0]["knock"] == -1


# ---- DB layer (Postgres-or-skip) -----------------------------------------
DB = Path(__file__).resolve().parent.parent / "db"


def _db_up() -> bool:
    from app.db import engine
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        return True
    except OperationalError:
        return False


dbonly = pytest.mark.skipif(not _db_up(), reason="Postgres not reachable — skipping DB integration")


@dbonly
def test_pipeline_persists_events_and_feeds_a_case():
    from app.db import engine, session_scope
    with engine.begin() as conn:
        for f in ("schema.sql", "schema_v2.sql", "schema_v3.sql", "schema_v4.sql", "schema_v5.sql",
                  "schema_v6.sql", "schema_v7.sql", "schema_v8.sql", "schema_v9.sql", "schema_v10.sql"):
            conn.execute(text((DB / f).read_text()))
    from sqlalchemy import delete
    from app import service, telemetry, workbench
    from app.models import DiagnosticSession, Measurement
    from app.seed import seed as seed_fn
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        telemetry.seed_channels(s)
        v = service.get_vehicle(s)
        # the DB persists across runs — clear any prior copy of this synthetic session
        s.execute(delete(DiagnosticSession).where(DiagnosticSession.sha256 == "tel-test-sha"))
        s.flush()
        ds = DiagnosticSession(vehicle_id=v.id, kind="datalog", sha256="tel-test-sha",
                               raw_path="/tmp/x")
        s.add(ds); s.flush()
        for t, boost, cmd, knock in [(0.0, -8, -8, 0), (1.0, 15, 20, 0), (1.5, 14, 20, -7)]:
            s.add(Measurement(session_id=ds.id, pid="Boost (psi)", value=boost, t_offset_s=t))
            s.add(Measurement(session_id=ds.id, pid="Boost cmd (psi)", value=cmd, t_offset_s=t))
            s.add(Measurement(session_id=ds.id, pid="Knock (deg)", value=knock, t_offset_s=t))
        s.flush()
        events = telemetry.run_pipeline(s, ds.id)
        kinds = {e["kind"] for e in events}
        assert {"WOT_PULL", "BOOST_DEFICIT", "KNOCK_EVENT"} <= kinds
        # re-running is idempotent (replaces, not appends)
        again = telemetry.run_pipeline(s, ds.id)
        assert len(again) == len(events)
        # feed into a diagnostic case as evidence
        case = workbench.open_case(s, v, "from telemetry")
        n = telemetry.events_to_case(s, case, events)
        view = workbench.case_view(s, case.id)
    assert n == len(events)
    assert any(e["kind"] == "telemetry" for e in view["known_data"])
