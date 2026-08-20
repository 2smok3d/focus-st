"""Integration tests for the Diagnostic Workbench (V4).

Postgres-or-skip. Verifies case construction, the transparent hypothesis scoring model,
live re-ranking as test results come in, diagnostic-tree traversal (next pending test),
the evidence-ledger finding, and input validation.
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
        for f in ("schema.sql", "schema_v2.sql", "schema_v3.sql", "schema_v4.sql"):
            conn.execute(text((DB / f).read_text()))
    from app.seed import seed as seed_fn
    from app.seed_ref import seed_reference
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        seed_reference(s)
    yield


@pytest.fixture(autouse=True)
def _clean_cases():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE diagnostic_cases RESTART IDENTITY CASCADE"))
    yield


def _seed(s):
    from app.workbench import seed_example_case
    seed_example_case(s)


def test_seed_builds_case_with_ranked_hypotheses():
    from app import workbench
    with session_scope() as s:
        _seed(s)
        cases = workbench.list_cases(s)
        assert len(cases) == 1 and cases[0]["code"] == "DG-0004"
        view = workbench.case_view(s, cases[0]["id"])
    assert len(view["hypotheses"]) == 4
    assert len(view["tests"]) == 4
    # Evidence on the PCV side makes that hypothesis lead before any test is run.
    assert view["hypotheses"][0]["key"] == "pcv-intake-leak"
    assert view["next_test"] == "Visual intake + PCV plumbing inspection"


def test_prior_reflects_linked_evidence():
    from app import workbench
    with session_scope() as s:
        _seed(s)
        cid = workbench.list_cases(s)[0]["id"]
        ranked = {h["key"]: h for h in workbench.rank_hypotheses(s, cid)}
    # pcv-intake-leak has 2 linked evidence (P04DB + intake) → 1.0 + 0.6*2 = 2.2
    assert ranked["pcv-intake-leak"]["prior"] == 2.2
    # a hypothesis with no linked evidence keeps the base prior
    assert ranked["boost-leak"]["prior"] == 1.0


def test_results_reorder_hypotheses_live():
    from app import workbench
    with session_scope() as s:
        _seed(s)
        cid = workbench.list_cases(s)[0]["id"]
        tests = {t["name"]: t["id"] for t in workbench.case_view(s, cid)["tests"]}
        # PCV inspection passes → that hypothesis is pushed down
        workbench.record_result(s, tests["Visual intake + PCV plumbing inspection"], "pass")
        # smoke test fails → the boost-leak hypothesis is promoted
        workbench.record_result(s, tests["Smoke test (pressurize intake tract)"], "fail")
        ranked = workbench.rank_hypotheses(s, cid)
    assert ranked[0]["key"] == "boost-leak"                 # now leads
    by = {h["key"]: h for h in ranked}
    assert by["boost-leak"]["score"] > by["pcv-intake-leak"]["score"]
    # a passing 'confirms' test lowers its hypothesis below the base prior
    assert by["pcv-intake-leak"]["score"] < 2.2


def test_refutes_polarity_inverts_contribution():
    from app import service, workbench
    with session_scope() as s:
        v = service.get_vehicle(s)
        case = workbench.open_case(s, v, "polarity check")
        workbench.add_hypothesis(s, case, "h1", "hypothesis one")
        t = workbench.add_test(s, case, "ruling-out test", bears_on="h1",
                               polarity="refutes", weight=1.0)
        workbench.record_result(s, t.id, "fail")   # a failing 'refutes' test lowers h1
        ranked = workbench.rank_hypotheses(s, case.id)
    assert ranked[0]["score"] == pytest.approx(0.0)         # 1.0 base − 1.0


def test_finding_ledger_recorded():
    from app import workbench
    with session_scope() as s:
        _seed(s)
        view = workbench.case_view(s, workbench.list_cases(s)[0]["id"])
    assert view["findings"]
    f = view["findings"][0]
    assert "PCV" in f["text"] and f["supporting"] and f["derived_by"]


def test_invalid_inputs_rejected():
    from app import service, workbench
    with session_scope() as s:
        v = service.get_vehicle(s)
        case = workbench.open_case(s, v, "validation")
        with pytest.raises(ValueError):
            workbench.add_test(s, case, "bad", polarity="sideways")
        t = workbench.add_test(s, case, "ok", bears_on="x")
        with pytest.raises(ValueError):
            workbench.record_result(s, t.id, "maybe")
