"""Integration tests for the Machine State Engine (V3 temporal digital twin).

Postgres-or-skip (same pattern as test_refmodel): exercises the real schema
(component_states + machine_capabilities). Covered:
  - condition + epistemic knowledge_state recorded per component
  - supersession — a new observation replaces the current one, one row stays current
  - MachineState(T) — historical reconstruction returns the state as of a past T
  - reference-vs-actual projection overlays states on the reference tree
  - capability profile per machine
  - validation of condition / knowledge_state values
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
        for f in ("schema.sql", "schema_v2.sql", "schema_v3.sql"):
            conn.execute(text((DB / f).read_text()))
    from app.seed import seed as seed_fn
    from app.seed_ref import seed_reference
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        seed_reference(s)
    yield


@pytest.fixture(autouse=True)
def _clean_twin():
    """Isolate each test: clear recorded machine state so order doesn't matter."""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE component_states, machine_capabilities RESTART IDENTITY"))
    yield


def test_seed_twin_records_deviations():
    from app import service, twin
    with session_scope() as s:
        twin.seed_twin(s)
    with session_scope() as s:
        v = service.get_vehicle(s)
        states = twin.current_states(s, v.id)
    assert states["intercooler"].condition == "modified"
    assert states["intercooler"].installed_part == "Depo 'Beast' FMIC"
    assert states["radiator"].condition == "failed"
    # epistemic state is recorded distinctly from condition
    assert states["radiator"].knowledge_state == "DIRECTLY_OBSERVED"


def test_supersession_keeps_one_current_row():
    from app import service, twin
    with session_scope() as s:
        twin.seed_twin(s)
        v = service.get_vehicle(s)
        twin.record_state(s, v, "radiator", condition="healthy",
                          knowledge_state="DIRECTLY_OBSERVED",
                          installed_part="Mishimoto aluminum radiator", confidence=0.9)
    with session_scope() as s:
        v = service.get_vehicle(s)
        cur = twin.current_states(s, v.id)
    assert cur["radiator"].condition == "healthy"
    assert cur["radiator"].installed_part == "Mishimoto aluminum radiator"


def test_machine_state_at_past_time_reconstructs_history():
    """Self-contained timeline on a dedicated component with explicit timestamps."""
    from app import service, twin
    slug = "thermostat"
    t1 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    between = dt.datetime(2026, 3, 1, tzinfo=dt.timezone.utc)
    t2 = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)
    with session_scope() as s:
        v = service.get_vehicle(s)
        twin.record_state(s, v, slug, condition="suspect", knowledge_state="INFERRED",
                          observed_at=t1)
        twin.record_state(s, v, slug, condition="healthy", knowledge_state="DIRECTLY_OBSERVED",
                          observed_at=t2)
    with session_scope() as s:
        v = service.get_vehicle(s)
        past = twin.state_at(s, v.id, between)   # between t1 and t2
        now = twin.current_states(s, v.id)
    # As of `between` the earlier observation stands; the current state is the later one.
    assert past[slug].condition == "suspect"
    assert now[slug].condition == "healthy"


def test_reference_vs_actual_overlays_tree():
    from app import twin
    with session_scope() as s:
        twin.seed_twin(s)
        rva = twin.reference_vs_actual(s, "focus-st")
    assert rva["vin"] == "1FADP3L94HL223134"
    # unobserved components default to stock/UNKNOWN (assumed stock, not verified)
    flat = {}
    def collect(nodes):
        for n in nodes:
            for c in n["components"]:
                flat[c["slug"]] = c["actual"]
            collect(n["children"])
    collect(rva["tree"])
    assert flat["turbocharger"]["condition"] == "stock"
    assert flat["turbocharger"]["observed"] is False
    assert flat["intercooler"]["condition"] == "modified"
    assert {d["slug"] for d in rva["deviations"]} >= {"intercooler", "radiator"}


def test_capability_profile():
    from app import service, twin
    with session_scope() as s:
        twin.seed_twin(s)
        v = service.get_vehicle(s)
        caps = {c["capability"]: c["supported"] for c in twin.capabilities(s, v.id)}
    assert caps.get("obd") is True
    assert caps.get("dtc") is True


def test_invalid_condition_and_knowledge_rejected():
    from app import service, twin
    with session_scope() as s:
        v = service.get_vehicle(s)
        with pytest.raises(ValueError):
            twin.record_state(s, v, "turbocharger", condition="exploded")
        with pytest.raises(ValueError):
            twin.record_state(s, v, "turbocharger", knowledge_state="VIBES")
