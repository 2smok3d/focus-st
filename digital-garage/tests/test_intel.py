"""Integration test for the vehicle-intelligence projection (Milestone G bridge).

Postgres-or-skip. Verifies build_intel aggregates the V2 backend into one JSON-able dict
reflecting the seeded state, and that write_intel emits valid JSON.
"""
from __future__ import annotations

import json
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
def _seeded():
    with engine.begin() as conn:
        for f in sorted((DB).glob("schema*.sql"), key=lambda p: (len(p.stem), p.stem)):
            conn.execute(text(f.read_text()))
    from app.migrate_knowledge import migrate_knowledge
    from app.migrate_specs import migrate_specs_to_claims
    from app.seed import seed as seed_fn
    from app.seed_graph import seed_graph
    from app.seed_ref import seed_reference
    from app.telemetry import seed_channels
    from app.twin import seed_twin
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        seed_reference(s)
        seed_graph(s)
        seed_twin(s)
        migrate_specs_to_claims(s)
        migrate_knowledge(s)
        seed_channels(s)
    yield


def test_build_intel_aggregates_platform_state():
    from app.intel import build_intel
    with session_scope() as s:
        d = build_intel(s, "focus-st")
    assert d["vehicle"]["vin"] == "1FADP3L94HL223134"
    assert d["reference"]["manufacturer"] == "Ford"
    # systems tree with component counts
    assert d["systems"] and any(sys["components"] > 0 for sys in d["systems"])
    # graph overlays present
    assert {"airflow", "coolant", "lubrication"} <= set(d["overlays"])
    # twin deviations reflect the seeded intercooler(mod)+radiator(failed)
    assert {x["slug"] for x in d["twin"]["deviations"]} >= {"intercooler", "radiator"}
    # knowledge projection carries the graded claims + the oil-capacity conflict
    assert d["knowledge"]["total_claims"] > 0
    assert d["knowledge"]["conflicts"] >= 1
    assert d["telemetry"]["channels"] >= 1


def test_write_intel_emits_valid_json(tmp_path):
    from app.intel import write_intel
    out = tmp_path / "intel.json"
    with session_scope() as s:
        p = write_intel(s, "focus-st", out=out)
    assert p == out
    doc = json.loads(out.read_text())              # must be valid JSON
    assert doc["variant"] == "focus-st" and "generated_at" in doc


def test_intel_carries_search_index():
    """The projection carries a self-contained universal-search index — the machine's
    reference components (with their system) and its graded claims."""
    from app.intel import build_intel
    with session_scope() as s:
        d = build_intel(s, "focus-st")
    si = d["search_index"]
    assert si["components"] and si["claims"]
    # components carry slug + name + system for search + display
    assert all({"slug", "name", "system"} <= set(c) for c in si["components"])
    # a known component and a known claim property are searchable
    assert any(c["slug"] == "intercooler" for c in si["components"])
    assert any(cl["prop"] == "lug_torque" for cl in si["claims"])


def test_intel_carries_maintenance_status():
    """The projection surfaces the maintenance-due engine bucketed by status, and an
    interval with no service on record reads `needs_log` — never a false `overdue`."""
    from app.intel import build_intel
    with session_scope() as s:
        d = build_intel(s, "focus-st")
    m = d["maintenance"]
    assert m and m["tracked"] >= 1
    assert set(m["counts"]) == {"overdue", "due_soon", "needs_log", "unknown", "ok"}
    # seeded FST has intervals but no service events → all needs_log, nothing to act on
    assert m["counts"]["needs_log"] >= 1
    assert m["attention"] == m["counts"]["overdue"] + m["counts"]["due_soon"]
    # an item lacking history must not be reported as overdue
    for it in m["items"]:
        if it["last_miles"] is None and it["last_date"] is None:
            assert it["status"] != "overdue"


def test_build_intel_is_fleet_wide_and_variant_scoped():
    """A non-focus machine projects its own state, and knowledge is scoped per-variant:
    the ZZR600's claim count must not bleed the Focus ST's claims into its intel."""
    from app.commission import commission_machine
    from app.intel import build_intel
    with session_scope() as s:
        commission_machine(s, "zzr600")          # idempotent
        z = build_intel(s, "zzr600")
        f = build_intel(s, "focus-st")
    # the projection is about the ZZR600, not the Focus ST
    assert z["variant"] == "zzr600"
    assert z["vehicle"] and z["vehicle"]["vin"] != f["vehicle"]["vin"]
    # it carries its own reference model + systems tree
    assert z["reference"] and z["systems"]
    # per-variant knowledge scoping: focus-st migrated claims must not appear under zzr600
    assert z["knowledge"]["total_claims"] < f["knowledge"]["total_claims"]


def test_write_intel_all_covers_every_commissioned_machine():
    from app.commission import commission_all
    from app.intel import write_intel_all
    with session_scope() as s:
        commission_all(s)                          # idempotent
        paths = write_intel_all(s)
    slugs = {p.parent.name for p in paths}
    assert {"focus-st", "zzr600", "rz350", "tz250", "toyota-pickup"} <= slugs
    for p in paths:
        doc = json.loads(p.read_text())
        assert doc["variant"] == p.parent.name and "generated_at" in doc
