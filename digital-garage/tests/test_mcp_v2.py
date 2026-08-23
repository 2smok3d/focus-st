"""Phase 6 — evidence-grounded MCP V2: reference/provenance reads + propose_claim.

Postgres-or-skip. Exercises the service/refservice layer the MCP tools wrap: reading a
claim with its evidence + re-resolved verdict, and the propose→approve boundary for a
new claim (no mutation until a human approves; verdict computed from evidence; adding
evidence strengthens monotonically).
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
    from app.seed import seed as seed_fn
    from app.seed_ref import seed_reference
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        seed_reference(s)
    yield
    # This module writes `test-*` claims through the approval boundary into the shared
    # persistent DB. Purge them (and any derived rows) so they never leak into the
    # canonical projections regenerated from this database.
    from sqlalchemy import delete
    from app.kbmodels import ResearchTask
    from app.models import ChangeProposal
    from app.refmodels import Claim, ClaimEvidence
    with session_scope() as s:
        ids = [c.id for c in s.scalars(select(Claim).where(Claim.subject_key.like("test-%")))]
        for cid in ids:
            s.execute(delete(ClaimEvidence).where(ClaimEvidence.claim_id == cid))
        s.execute(delete(Claim).where(Claim.id.in_(ids)))
        s.execute(delete(ResearchTask).where(ResearchTask.subject.like("%test-%")))
        s.execute(delete(ChangeProposal).where(ChangeProposal.entity == "claim"))


def _get_claim(subject_key, prop):
    from app.refmodels import Claim
    with session_scope() as s:
        return s.scalar(select(Claim).where(Claim.subject_key == subject_key, Claim.prop == prop))


def test_get_claim_carries_evidence_and_resolved_verdict():
    from app import refservice
    with session_scope() as s:
        conflicts = refservice.list_conflicts(s)
    assert conflicts, "seed_reference seeds at least one conflicting claim"
    c = conflicts[0]
    with session_scope() as s:
        d = refservice.get_claim(s, c["subject_key"], c["property"])
    assert d is not None
    assert d["evidence"] and all("authority" in e for e in d["evidence"])
    # the verdict is re-resolved live from the evidence, not a stored guess
    assert "resolved" in d and "verification" in d["resolved"]


def test_propose_claim_records_pending_and_does_not_mutate():
    from app import service
    key = "test-widget"
    assert _get_claim(key, "torque_spec") is None
    with session_scope() as s:
        v = service.get_vehicle(s)
        res = service.propose_claim(
            s, v.id, subject_type="component", subject_key=key, prop="torque_spec",
            value="35", unit="lbft",
            evidence=[{"authority": 1, "stance": "supports", "on_vehicle": False,
                       "label": "OEM workshop manual"}],
            rationale="From the FSM torque table.")
    assert res["status"] == "pending"
    # the claim must NOT exist yet — proposing never mutates canon
    assert _get_claim(key, "torque_spec") is None


def test_approving_claim_proposal_creates_it_with_computed_verdict():
    from app import service
    key = "test-clamp"
    with session_scope() as s:
        v = service.get_vehicle(s)
        res = service.propose_claim(
            s, v.id, subject_type="component", subject_key=key, prop="material",
            value="stainless",
            evidence=[{"authority": 1, "stance": "supports", "on_vehicle": False,
                       "label": "OEM parts catalog"}],
            rationale="Catalog lists SS band clamp.")
    with session_scope() as s:
        out = service.approve_proposal(s, res["proposal_id"], approved_by="tester")
    assert out["status"] == "approved" and out["entity"] == "claim"
    claim = _get_claim(key, "material")
    assert claim is not None and claim.value == "stainless"
    # verdict was computed from the single OEM source, not asserted
    assert claim.verification in {"OEM_VERIFIED", "CORROBORATED", "UNVERIFIED"}
    assert claim.confidence is not None


def test_corroborating_evidence_is_monotonic():
    from app import service
    from app.provenance import Verification
    key = "test-hose"
    # First: one unverified community source.
    with session_scope() as s:
        v = service.get_vehicle(s)
        r1 = service.propose_claim(
            s, v.id, subject_type="component", subject_key=key, prop="diameter",
            value="19", unit="mm",
            evidence=[{"authority": 5, "stance": "supports", "on_vehicle": False,
                       "label": "forum thread"}], rationale="community")
    with session_scope() as s:
        service.approve_proposal(s, r1["proposal_id"], approved_by="tester")
    before = _get_claim(key, "diameter").verification
    # Then: corroborate with an OEM source on the SAME claim.
    with session_scope() as s:
        v = service.get_vehicle(s)
        r2 = service.propose_claim(
            s, v.id, subject_type="component", subject_key=key, prop="diameter",
            value="19", unit="mm",
            evidence=[{"authority": 1, "stance": "supports", "on_vehicle": False,
                       "label": "OEM manual"}], rationale="OEM confirms")
    with session_scope() as s:
        service.approve_proposal(s, r2["proposal_id"], approved_by="tester")
    after = _get_claim(key, "diameter").verification
    # grade may only climb (or hold) — never demote when stronger evidence is added
    assert Verification[after] >= Verification[before]


def test_propose_claim_rejects_bad_evidence():
    from app import service
    with session_scope() as s:
        v = service.get_vehicle(s)
        with pytest.raises(ValueError):
            service.propose_claim(s, v.id, subject_type="component", subject_key="x",
                                  prop="p", evidence=[])                      # no evidence
        with pytest.raises(ValueError):
            service.propose_claim(s, v.id, subject_type="component", subject_key="x",
                                  prop="p",
                                  evidence=[{"authority": 99, "stance": "supports"}])  # bad authority
