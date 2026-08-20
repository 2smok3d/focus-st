"""Integration tests for maintenance + known-issue normalization into claims.

Postgres-or-skip. Verifies grades are preserved from the V1 source authority, that
on-vehicle issues reach VEHICLE_VERIFIED and apply only to this car, and that the
migration is idempotent and non-destructive.
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
    with engine.begin() as conn:
        for f in ("schema.sql", "schema_v2.sql", "schema_v3.sql"):
            conn.execute(text((DB / f).read_text()))
    from app.seed import seed as seed_fn
    from app.seed_ref import seed_reference
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        seed_reference(s)
        from app.migrate_knowledge import migrate_knowledge
        migrate_knowledge(s)
    yield


def test_maintenance_grades_from_source_authority():
    from app import refservice as rs
    with session_scope() as s:
        oil = rs.get_claim(s, "engine-oil-filter", "interval_miles")
        assert oil["value"] == "5000" and oil["unit"] == "mi"
        assert oil["resolved"]["verification"] == "OEM_VERIFIED"
        plugs = rs.get_claim(s, "spark-plugs", "interval_miles")
        assert plugs["resolved"]["verification"] == "CORROBORATED"  # community — not inflated


def test_dual_interval_emits_both_properties():
    from app import refservice as rs
    with session_scope() as s:
        miles = rs.get_claim(s, "engine-oil-filter", "interval_miles")
        months = rs.get_claim(s, "engine-oil-filter", "interval_months")
    assert miles["value"] == "5000" and months["value"] == "6" and months["unit"] == "mo"


def test_vehicle_verified_issue_scoped_to_this_car():
    from app import refservice as rs
    with session_scope() as s:
        rad = rs.get_claim(s, "radiator-cracked-through-hole-front-left-of-core", "known_issue")
    assert rad["resolved"]["verification"] == "VEHICLE_VERIFIED"
    # observed on THIS car → applicability is the variant only (not a year/market range)
    assert rad["applicability"] == {"variant": "focus-st"}


def test_platform_issue_is_corroborated():
    from app import refservice as rs
    with session_scope() as s:
        evap = rs.get_claim(s, "evap-purge-valve-campaign-18s32-26s40-verify-status-for-this",
                            "known_issue")
    assert evap["resolved"]["verification"] == "CORROBORATED"
    assert evap["applicability"]["variant"] == "focus-st"
    assert "years" in evap["applicability"]  # platform-level → year/market applicability


def test_known_recall_is_corroborated():
    from app import refservice as rs
    with session_scope() as s:
        rc = rs.get_claim(s, "18S32", "campaign")
    assert rc["subject_type"] == "recall"
    assert "EVAP" in rc["value"]
    # KB-noted Ford campaign awaiting VIN confirmation → conservative grade
    assert rc["resolved"]["verification"] == "CORROBORATED"


def test_nhtsa_origin_grades_authoritative():
    """A government-sourced (NHTSA) campaign is graded from its origin, not just its
    stored verification — reaching OEM_VERIFIED (authority 1)."""
    from sqlalchemy import select
    from app import refservice as rs, service
    from app.migrate_knowledge import migrate_recalls_to_claims
    from app.models import Recall
    with session_scope() as s:
        v = service.get_vehicle(s)
        # guard: the DB persists across runs — only add the synthetic recall once
        if s.scalar(select(Recall).where(Recall.campaign_number == "NHTSA-TEST-99")) is None:
            s.add(Recall(vehicle_id=v.id, campaign_number="NHTSA-TEST-99", origin="nhtsa",
                         component="Test system", summary="Synthetic NHTSA campaign for grading test.",
                         status="unknown", verification="CORROBORATED"))
            s.flush()
        migrate_recalls_to_claims(s)
    with session_scope() as s:
        claim = rs.get_claim(s, "NHTSA-TEST-99", "campaign")
    assert claim["resolved"]["verification"] == "OEM_VERIFIED"
    assert claim["evidence"][0]["authority"] == 1


def test_migration_is_idempotent():
    from app.migrate_knowledge import migrate_knowledge
    with session_scope() as s:
        again = migrate_knowledge(s)
    assert "Maintenance → claims: 0 created." in again
    assert "Known issues → claims: 0 created." in again
    assert "Recalls/TSBs → claims: 0 created." in again
