"""CORR — corroboration suggester.

Pure verdict-projection runs without a DB. A Postgres-or-skip test creates an UNVERIFIED
claim, proposes a real source through the approval boundary, approves it, and checks the
claim was promoted — verdict recomputed from evidence, never asserted.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.corroborate import min_authority_to_promote, project_verdict
from app.db import engine, session_scope
from app.provenance import SUPPORTS, Evidence

DB = __import__("pathlib").Path(__file__).resolve().parent.parent / "db"


# ---- pure engine (no DB) --------------------------------------------------
def test_projection_promotes_with_a_stronger_source():
    ev = [Evidence(authority=5, stance=SUPPORTS)]                 # a single anecdote
    assert project_verdict(ev, Evidence(authority=2, stance=SUPPORTS))["verification"] == "OEM_VERIFIED"
    assert project_verdict(ev, Evidence(authority=3, stance=SUPPORTS))["verification"] == "CORROBORATED"


def test_min_authority_reports_the_easiest_source_that_works():
    # an anecdote-backed claim is lifted by a trade (auth 3-4) source, not by another anecdote
    assert min_authority_to_promote([Evidence(authority=5, stance=SUPPORTS)], "UNVERIFIED") == 4
    # no evidence at all → still an authority-4 source promotes it
    assert min_authority_to_promote([], "UNVERIFIED") == 4


def test_min_authority_none_when_nothing_would_promote():
    # already OEM-verified: no supporting source can raise it further (short of on-vehicle)
    ev = [Evidence(authority=1, stance=SUPPORTS)]
    assert min_authority_to_promote(ev, "OEM_VERIFIED") is None


# ---- service integration (Postgres-or-skip) -------------------------------
def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        return True
    except OperationalError:
        return False


dbonly = pytest.mark.skipif(not _db_up(), reason="Postgres not reachable — skipping DB integration")


@dbonly
def test_corroboration_flow_promotes_through_approval():
    with engine.begin() as conn:
        for f in sorted(DB.glob("schema*.sql"), key=lambda p: (len(p.stem), p.stem)):
            conn.execute(text(f.read_text()))
    from app import corroborate, service
    from app.refmodels import Claim, ClaimEvidence
    from app.seed import seed as seed_fn
    KEY = "corr-test-widget"
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        veh = service.get_vehicle(s)
        c = Claim(subject_type="component", subject_key=KEY, prop="torque", value="100",
                  unit="lb-ft", applicability={"variant": "focus-st"}, verification="UNVERIFIED")
        s.add(c)
        s.flush()
        s.add(ClaimEvidence(claim_id=c.id, authority=5, stance="supports", source_label="a forum post"))
        cid = c.id
    try:
        # it shows up as a promotable candidate
        with session_scope() as s:
            r = corroborate.corroboration_candidates(s, "focus-st")
        mine = [x for x in r["candidates"] if x["claim_id"] == cid]
        assert mine and mine[0]["promotable"] and mine[0]["min_authority_to_promote"] == 4

        # proposing needs a real named source; it files a pending proposal, mutating nothing yet
        with session_scope() as s:
            veh = service.get_vehicle(s)
            prop = corroborate.propose_corroboration(s, veh.id, cid, authority=2,
                                                     source_label="Ford workshop manual §204")
            pid = prop["proposal_id"]
        with session_scope() as s:
            assert s.get(Claim, cid).verification == "UNVERIFIED"      # not changed by proposing

        # approval merges the evidence and re-resolves upward
        with session_scope() as s:
            service.approve_proposal(s, pid, approved_by="tester")
        with session_scope() as s:
            assert s.get(Claim, cid).verification == "OEM_VERIFIED"
    finally:
        from sqlalchemy import delete
        with session_scope() as s:
            ids = [row.id for row in s.scalars(select_claims(KEY))]
            for i in ids:
                s.execute(delete(ClaimEvidence).where(ClaimEvidence.claim_id == i))
            s.execute(delete(Claim).where(Claim.subject_key == KEY))
            s.execute(text("delete from change_proposals where entity='claim' and patch->>'subject_key' = :k"),
                      {"k": KEY})


def select_claims(key):
    from sqlalchemy import select

    from app.refmodels import Claim
    return select(Claim).where(Claim.subject_key == key)
