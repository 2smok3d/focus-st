"""Integration tests for Observation V2 + config/env snapshots + event ledger (V5).

Postgres-or-skip. Covers: canonical-unit environment storage, the config_at projection
(the roadmap achievement test — configuration as of time T), unit-aware measurement
comparison, the append-only event ledger + auto MEASUREMENT_RECORDED, and validation.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import engine, session_scope

DB = Path(__file__).resolve().parent.parent / "db"


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        return True
    except OperationalError:
        return False


pytestmark = pytest.mark.skipif(not _db_up(), reason="Postgres not reachable — skipping DB integration")


@pytest.fixture(scope="module", autouse=True)
def _schema():
    with engine.begin() as conn:
        for f in ("schema.sql", "schema_v2.sql", "schema_v3.sql", "schema_v4.sql", "schema_v5.sql"):
            conn.execute(text((DB / f).read_text()))
    from app.seed import seed as seed_fn
    from app.seed_ref import seed_reference
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        seed_reference(s)
    yield


@pytest.fixture(autouse=True)
def _clean():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE observations, configuration_snapshots, environment_snapshots, "
                          "machine_events, component_states RESTART IDENTITY CASCADE"))
    yield


def test_environment_stored_in_canonical_units():
    from app import observations as ob, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        env = ob.record_environment(s, v, ambient=108, ambient_unit="°F",
                                    baro=29.5, baro_unit="inHg", humidity_pct=18)
    assert env.ambient_c == pytest.approx(42.2, abs=0.1)   # 108°F
    assert env.baro_kpa == pytest.approx(99.9, abs=0.2)    # 29.5 inHg


def test_config_at_projects_state_and_settings_over_time():
    """Achievement test: the configuration as of time T, from twin state + ledger."""
    from app import observations as ob, service, twin
    t0 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    t1 = dt.datetime(2026, 3, 1, tzinfo=dt.timezone.utc)
    t2 = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)
    with session_scope() as s:
        v = service.get_vehicle(s)
        twin.record_state(s, v, "intercooler", condition="stock",
                          knowledge_state="OEM_ASSERTED", observed_at=t0)
        twin.record_state(s, v, "intercooler", condition="modified",
                          knowledge_state="DIRECTLY_OBSERVED", installed_part="Depo FMIC", observed_at=t2)
        ob.record_event(s, v, "TUNE_CHANGED", detail="Stage-1 tune", occurred_at=t2)
        early = ob.config_at(s, v, t1)     # between t0 and t2
        late = ob.config_at(s, v, dt.datetime(2026, 7, 1, tzinfo=dt.timezone.utc))
    assert early["components"]["intercooler"]["condition"] == "stock"
    assert "TUNE_CHANGED" not in early["settings"]
    assert late["components"]["intercooler"]["condition"] == "modified"
    assert late["settings"]["TUNE_CHANGED"]["detail"] == "Stage-1 tune"


def test_snapshot_materializes_current_config():
    from app import observations as ob, service, twin
    with session_scope() as s:
        v = service.get_vehicle(s)
        twin.record_state(s, v, "radiator", condition="failed", knowledge_state="DIRECTLY_OBSERVED")
        snap = ob.snapshot_config(s, v, code="snap-1")
    assert snap.config["components"]["radiator"]["condition"] == "failed"
    assert snap.code == "snap-1"


def test_measurements_compared_unit_aware():
    from app import observations as ob, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        a = ob.record_observation(s, v, subject_slug="cylinders", method="compression",
                                  value=145, unit="psi")
        b = ob.record_observation(s, v, subject_slug="cylinders", method="compression",
                                  value=1000, unit="kPa")   # 145 psi ≈ 1000 kPa
        c = ob.record_observation(s, v, subject_slug="cylinders", method="compression",
                                  value=120, unit="psi")
    assert ob.measurements_agree(a, b) is True
    assert ob.measurements_agree(a, c) is False


def test_observation_appends_measurement_event():
    from app import observations as ob, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        ob.record_observation(s, v, subject_slug="cylinders", method="compression",
                              value=145, unit="psi")
        kinds = [e["kind"] for e in ob.events_for(s, v.id)]
    assert "MEASUREMENT_RECORDED" in kinds


def test_invalid_event_kind_and_unit_rejected():
    from app import observations as ob, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        with pytest.raises(ValueError):
            ob.record_event(s, v, "TELEPORTED")
        with pytest.raises(Exception):
            ob.record_observation(s, v, subject_slug="x", value=1, unit="smoots")
