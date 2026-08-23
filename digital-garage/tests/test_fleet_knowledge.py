"""F1 — normalize fleet manual specs into graded claims.

Postgres-or-skip. Verifies the seeder turns a machine's manual spec table into per-variant
claims with honest grading (web-verified → CORROBORATED, ⚠️ verify → UNVERIFIED) and is
idempotent.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from app.db import engine, session_scope

DB = __import__("pathlib").Path(__file__).resolve().parent.parent / "db"


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
        for f in sorted(DB.glob("schema*.sql"), key=lambda p: (len(p.stem), p.stem)):
            conn.execute(text(f.read_text()))
    from app.commission import commission_machine
    from app.seed import seed as seed_fn
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        commission_machine(s, "zzr600")
    yield


def test_pure_parsing_of_spec_table():
    from app.seed_fleet_knowledge import _confidence_tag, _prop, _spec_rows
    md = (
        "## Specification (verified)\n"
        "| System | Spec | Confidence |\n"
        "|---|---|---|\n"
        "| Displacement | 599 cc | verified |\n"
        "| Final drive | Chain (525) | ⚠️ verify |\n"
        "| Frame | Aluminium perimeter | corroborated |\n"
        "\nsome prose, not a row\n"
    )
    rows = list(_spec_rows(md))
    assert ("Displacement", "599 cc", "verified") in rows
    assert len(rows) == 3
    assert _prop("Bore × stroke") == "bore_stroke"
    assert _confidence_tag("⚠️ verify") == "verify"
    assert _confidence_tag("verified") == "verified"


def test_seeds_graded_claims_and_is_idempotent():
    from app import knowledge
    from app.seed_fleet_knowledge import seed_fleet_knowledge
    with session_scope() as s:
        msg1 = seed_fleet_knowledge(s, slugs=("zzr600",))
    assert "zzr600" in msg1
    with session_scope() as s:
        q = knowledge.quality_report(s, "zzr600")
    assert q["total"] >= 10
    # honest grading: web-verified specs are CORROBORATED, never OEM_VERIFIED (no factory
    # doc in hand); the ⚠️ rows land as UNVERIFIED.
    assert "OEM_VERIFIED" not in q["by_verification"]
    assert q["by_verification"].get("CORROBORATED", {}).get("n", 0) >= 1
    assert q["by_verification"].get("UNVERIFIED", {}).get("n", 0) >= 1
    # second pass creates nothing new
    with session_scope() as s:
        msg2 = seed_fleet_knowledge(s, slugs=("zzr600",))
    assert "zzr600: 0 claim(s)" in msg2


def test_claims_are_variant_scoped():
    from app.refmodels import Claim
    from app.seed_fleet_knowledge import seed_fleet_knowledge
    with session_scope() as s:
        seed_fleet_knowledge(s, slugs=("zzr600",))
    with session_scope() as s:
        rows = s.scalars(select(Claim).where(
            Claim.subject_type == "variant", Claim.subject_key == "zzr600")).all()
        assert rows
        for c in rows:
            assert c.applicability and c.applicability.get("variant") == "zzr600"
