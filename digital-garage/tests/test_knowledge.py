"""Tests for Milestone F — Knowledge Operations.

Entity normalization is pure (runs in CI without a DB); the quality dashboard, research
queue, and alias resolution are covered Postgres-or-skip.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app import knowledge as kb

# ---- pure --------------------------------------------------------------
def test_normalize_identifier_collapses_separators():
    assert kb.normalize_identifier("22R-E") == "22RE"
    assert kb.normalize_identifier("22R E") == "22RE"
    assert kb.normalize_identifier("22r.e") == "22RE"
    assert kb.normalize_identifier("R9DA") == "R9DA"


# ---- DB (Postgres-or-skip) --------------------------------------------
from app.db import engine, session_scope  # noqa: E402

DB = Path(__file__).resolve().parent.parent / "db"


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        return True
    except OperationalError:
        return False


dbonly = pytest.mark.skipif(not _db_up(), reason="Postgres not reachable — skipping DB integration")


@pytest.fixture(scope="module")
def _seeded():
    with engine.begin() as conn:
        for f in ("schema.sql", "schema_v2.sql", "schema_v3.sql", "schema_v4.sql", "schema_v5.sql",
                  "schema_v6.sql", "schema_v7.sql", "schema_v8.sql", "schema_v9.sql", "schema_v10.sql",
                  "schema_v11.sql", "schema_v12.sql"):
            conn.execute(text((DB / f).read_text()))
    from app.migrate_knowledge import migrate_knowledge
    from app.migrate_specs import migrate_specs_to_claims
    from app.seed import seed as seed_fn
    from app.seed_ref import seed_reference
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        seed_reference(s)
        migrate_specs_to_claims(s)
        migrate_knowledge(s)
    yield


@dbonly
def test_quality_report_counts_and_conflicts(_seeded):
    with session_scope() as s:
        r = kb.quality_report(s)
    assert r["total"] > 0
    assert r["conflicts"] >= 1                       # the seeded oil-capacity conflict
    # graded knowledge: OEM + community present, verification distribution sums to total
    assert sum(d["n"] for d in r["by_verification"].values()) == r["total"]


@dbonly
def test_research_tasks_generated_from_conflict_and_idempotent(_seeded):
    from app.knowledge import generate_research_tasks, list_research_tasks
    with session_scope() as s:
        generate_research_tasks(s)
    with session_scope() as s:
        again = generate_research_tasks(s)          # second pass adds nothing
        tasks = list_research_tasks(s)
    assert "generated: +0" in again
    conflict_tasks = [t for t in tasks if t["kind"] == "conflict"]
    assert conflict_tasks and conflict_tasks[0]["priority"] == "high"
    # highest priority sorts first
    assert tasks[0]["priority"] in ("critical", "high")


@dbonly
def test_alias_resolution_prefers_registered_then_normalizes(_seeded):
    from app.knowledge import add_alias, resolve_alias
    with session_scope() as s:
        add_alias(s, "Toyota 22R-E", "22RE", kind="engine")
    with session_scope() as s:
        assert resolve_alias(s, "Toyota 22R-E") == "22RE"     # exact registered alias
        assert resolve_alias(s, "22R E") == "22RE"            # normalized match to canonical
        assert resolve_alias(s, "R9DA") == "R9DA"             # unknown → normalized input
