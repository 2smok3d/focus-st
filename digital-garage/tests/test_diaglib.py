"""Integration tests for the Diagnostic Core (Milestone B). Postgres-or-skip.

Covers: failure-mode library, symptom → candidate matching, information-gain next-test
selection (and re-ranking as tests are done), component→candidate lookup, the workbench
recommendation integration, and confidence bands.
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
        for f in ("schema.sql", "schema_v2.sql", "schema_v3.sql", "schema_v4.sql",
                  "schema_v5.sql", "schema_v6.sql", "schema_v7.sql", "schema_v8.sql"):
            conn.execute(text((DB / f).read_text()))
    from app.seed import seed as seed_fn
    from app.seed_diaglib import seed_diaglib
    from app.seed_ref import seed_reference
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        seed_reference(s)
        seed_diaglib(s)
    yield


def test_confidence_bands():
    from app.diaglib import confidence_band
    assert confidence_band(0.2) == "LOW"
    assert confidence_band(0.5) == "MODERATE"
    assert confidence_band(0.7) == "HIGH"
    assert confidence_band(0.9) == "VERY_HIGH"
    assert confidence_band(0.9, has_evidence=False) == "LOW"   # no evidence caps at LOW


def test_symptom_maps_to_candidate_failure_modes():
    from app import diaglib
    with session_scope() as s:
        cands = {c["slug"] for c in diaglib.candidates_for_symptom(s, "low boost with a whistle")}
    assert "charge-air-leak" in cands
    assert "wastegate-fault" in cands


def test_next_test_picks_highest_utility_and_reranks():
    from app import diaglib
    with session_scope() as s:
        rec = diaglib.recommend_next_test(s, ["charge-air-leak", "wastegate-fault", "turbo-mechanical"])
        top = rec[0]
        # after doing the top test, it drops out and the next-best leads
        rec2 = diaglib.recommend_next_test(
            s, ["charge-air-leak", "wastegate-fault", "turbo-mechanical"], done_test_slugs=[top["slug"]])
    assert all(r["utility"] <= top["utility"] for r in rec)      # sorted by utility
    assert top["slug"] not in {r["slug"] for r in rec2}          # removed once done
    # utility rewards cheap/safe discriminating tests: cost is reflected
    smoke = next(r for r in rec if r["slug"] == "smoke-test")
    assert smoke["utility"] == pytest.approx(0.45, abs=0.01)     # 0.9 / (2 + 0)


def test_components_map_to_candidates():
    from app import diaglib
    with session_scope() as s:
        cands = diaglib.candidates_for_components(s, ["wastegate", "turbocharger"])
    assert set(cands) == {"wastegate-fault", "turbo-mechanical"}


def test_workbench_recommends_next_test_from_hypotheses():
    from app import service, workbench
    with session_scope() as s:
        v = service.get_vehicle(s)
        case = workbench.open_case(s, v, "boost complaint")
        workbench.add_hypothesis(s, case, "h-wg", "wastegate fault", component_slug="wastegate")
        workbench.add_hypothesis(s, case, "h-turbo", "turbo wear", component_slug="turbocharger")
        rec = workbench.recommend_next_test(s, case.id)
        view = workbench.case_view(s, case.id)
    slugs = {r["discriminates"] for r in rec}
    assert slugs <= {"wastegate-fault", "turbo-mechanical"}
    assert view["recommended_test"] == rec[0]["name"]           # surfaced in the case view


def test_failure_mode_detail_lists_tests():
    from app import diaglib
    with session_scope() as s:
        fm = diaglib.failure_mode(s, "charge-air-leak")
    assert "intercooler" in fm["components"]
    assert any(t["slug"] == "smoke-test" for t in fm["tests"])
