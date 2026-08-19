"""Integration tests for the V2 reference model + seed + refservice.

These exercise the real Postgres schema (JSONB, the verification_state domain, the
reference tables). CI has no database, so the whole module **skips** when the
configured Postgres isn't reachable — it still runs locally where a DB is up, and
never breaks the pure-unit CI suite.

Covered (per the V2 engineering requirements):
  - migration integrity   — schema.sql + schema_v2.sql apply idempotently
  - reference graph        — manufacturer→platform→variant→systems→components tree
  - conflicting claims     — the oil-capacity discrepancy caps + flags conflict
  - export compatibility   — seeding the reference layer leaves the V1 vehicle intact
"""
from __future__ import annotations

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
    # Apply canonical DDL (idempotent) so the module is self-contained.
    with engine.begin() as conn:
        conn.execute(text((DB / "schema.sql").read_text()))
        conn.execute(text((DB / "schema_v2.sql").read_text()))
    # A vehicle row is needed for the digital-twin link; seed V1 if empty.
    from app.seed import seed as seed_fn
    with session_scope() as s:
        seed_fn(s, if_empty=True)
    yield


def test_seed_reference_is_idempotent():
    from app.seed_ref import seed_reference
    with session_scope() as s:
        first = seed_reference(s)
    with session_scope() as s:
        second = seed_reference(s)
    # Same variant/system/component/claim counts on a re-run — no duplication.
    assert "Focus ST" in first
    assert first == second


def test_variant_header_and_tree():
    from app import refservice as rs
    with session_scope() as s:
        hdr = rs.variant_header(s, "focus-st")
        assert hdr["manufacturer"] == "Ford"
        assert hdr["engine"]["displacement_cc"] == 1999
        assert hdr["transmission"]["gears"] == 6
        tree = rs.system_tree(s, "focus-st")
    # Powertrain is the single top-level system; forced-induction is a child of it.
    assert [n["slug"] for n in tree] == ["powertrain"]
    child_slugs = {c["slug"] for c in tree[0]["children"]}
    assert {"engine", "forced-induction", "fuel", "ignition", "cooling"} <= child_slugs


def test_component_relationships_resolve():
    from app import refservice as rs
    with session_scope() as s:
        turbo = rs.get_component(s, "focus-st", "turbocharger")
    rels = {(r["dir"], r["relation"]) for r in turbo["relationships"]}
    assert ("→", "lubricated_by") in rels
    assert ("→", "controlled_by") in rels          # wastegate
    assert ("←", "affects") in rels                # pcv affects turbo


def test_oil_capacity_conflict_is_capped_and_flagged():
    from app import refservice as rs
    with session_scope() as s:
        claim = rs.get_claim(s, "lubrication", "oil_capacity")
    # Two OEM-authority sources disagree → verdict capped below OEM_VERIFIED + flagged.
    assert claim["conflict"] is True
    assert claim["resolved"]["verification"] == "CORROBORATED"
    assert claim["resolved"]["conflict"] is True
    assert claim["resolved"]["confidence"] < 0.5
    with session_scope() as s:
        conflicts = rs.list_conflicts(s)
    assert any(c["property"] == "oil_capacity" for c in conflicts)


def test_vehicle_verified_claim_reaches_top_tier():
    from app import refservice as rs
    with session_scope() as s:
        claim = rs.get_claim(s, "radiator", "condition")
    assert claim["resolved"]["verification"] == "VEHICLE_VERIFIED"


def test_export_compatibility_vehicle_linked_not_mutated():
    """Seeding the reference layer links the vehicle but preserves its V1 fields."""
    from app import service
    from app.export import write_export
    with session_scope() as s:
        v = service.get_vehicle(s)
        assert v.variant_id is not None          # digital-twin link established
        assert v.vin == "1FADP3L94HL223134"      # V1 identity untouched
        # The existing export path still runs against the linked vehicle.
        res = write_export(s, v.id, current_miles=None,
                           repo_root=Path("/tmp"), json_dir=Path("/tmp"))
        assert "garage_json" in res
