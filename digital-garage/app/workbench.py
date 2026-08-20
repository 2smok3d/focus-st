"""Diagnostic Workbench (V4) — open cases, record tests, rank hypotheses, log findings.

The ranking is a **transparent, documented heuristic**, never a calibrated probability.
Each hypothesis accrues a *support score*:

    score(h) = prior(h) + Σ test contributions

  prior(h)  = 1.0  + 0.6 · (# case evidence bearing on h's component)
  a completed test t with `bears_on == h.key`, weight w, contributes:
      polarity=confirms:  fail (fault found) → +w   ·  pass (ruled out) → −w
      polarity=refutes:   fail               → −w   ·  pass            → +w
      inconclusive / pending → 0

Hypotheses are then **ranked** by score; a normalized `support` fraction is reported
across the positive-scoring hypotheses purely to show relative standing. We never claim
these are true probabilities — the workbench surfaces reasoning + evidence, and a human
still decides. Findings are recorded as an auditable ledger (what supports/contradicts).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from .dxmodels import (
    POLARITY,
    TEST_RESULTS,
    CaseEvidence,
    CaseFinding,
    CaseHypothesis,
    CaseSymptom,
    CaseTest,
    DiagnosticCase,
)
from .models import Vehicle

PRIOR_BASE = 1.0
PRIOR_PER_EVIDENCE = 0.6


def open_case(session: Session, vehicle: Vehicle, title: str, *, code: str | None = None,
              symptoms: list[str] | None = None, note: str | None = None) -> DiagnosticCase:
    case = DiagnosticCase(vehicle_id=vehicle.id, title=title, code=code, note=note,
                          status="open")
    session.add(case)
    session.flush()
    for desc in symptoms or []:
        session.add(CaseSymptom(case_id=case.id, description=desc))
    session.flush()
    return case


def add_evidence(session: Session, case: DiagnosticCase, kind: str, ref: str | None = None,
                 detail: str | None = None, component_slug: str | None = None) -> CaseEvidence:
    row = CaseEvidence(case_id=case.id, kind=kind, ref=ref, detail=detail,
                       component_slug=component_slug)
    session.add(row)
    session.flush()
    return row


def add_hypothesis(session: Session, case: DiagnosticCase, key: str, description: str,
                   component_slug: str | None = None, note: str | None = None) -> CaseHypothesis:
    row = CaseHypothesis(case_id=case.id, key=key, description=description,
                         component_slug=component_slug, note=note)
    session.add(row)
    session.flush()
    return row


def add_test(session: Session, case: DiagnosticCase, name: str, *, expected: str | None = None,
             bears_on: str | None = None, polarity: str = "confirms", weight: float = 1.0,
             component_slug: str | None = None, source_label: str | None = None,
             sort: int = 0) -> CaseTest:
    if polarity not in POLARITY:
        raise ValueError(f"invalid polarity '{polarity}'")
    row = CaseTest(case_id=case.id, name=name, expected=expected, bears_on=bears_on,
                   polarity=polarity, weight=weight, component_slug=component_slug,
                   source_label=source_label, sort=sort, result="pending")
    session.add(row)
    session.flush()
    return row


def record_result(session: Session, test_id: int, result: str, *, actual: str | None = None,
                  interpretation: str | None = None) -> CaseTest:
    if result not in TEST_RESULTS:
        raise ValueError(f"invalid result '{result}'")
    test = session.get(CaseTest, test_id)
    if test is None:
        raise LookupError(f"no test #{test_id}")
    test.result = result
    test.actual = actual
    test.interpretation = interpretation
    test.performed_at = dt.datetime.now(dt.timezone.utc)
    session.flush()
    return test


def add_finding(session: Session, case: DiagnosticCase, text: str, *, supporting: str | None = None,
                contradicting: str | None = None, derived_by: str | None = None) -> CaseFinding:
    row = CaseFinding(case_id=case.id, text=text, supporting=supporting,
                      contradicting=contradicting, derived_by=derived_by)
    session.add(row)
    session.flush()
    return row


def conclude(session: Session, case: DiagnosticCase, hypothesis_key: str, text: str,
             *, supporting: str, derived_by: str = "workbench") -> CaseFinding:
    """Promote a hypothesis to a Finding — enforced by the Domain Constitution.

    A HYPOTHESIS → FINDING promotion requires confirming evidence (see
    docs/DOMAIN-CONSTITUTION.md); `epistemics.promote` raises EpistemicError if
    `supporting` is empty, so a guess can never be silently asserted as a conclusion.
    """
    from . import epistemics as ep
    bridge = ep.CONFIRMING_EVIDENCE if supporting else None
    ep.promote(ep.Kind.HYPOTHESIS, ep.Kind.FINDING, bridge)  # raises without evidence

    hyp = session.scalar(select(CaseHypothesis).where(
        CaseHypothesis.case_id == case.id, CaseHypothesis.key == hypothesis_key))
    if hyp is None:
        raise LookupError(f"no hypothesis '{hypothesis_key}' in case {case.id}")
    hyp.status = "confirmed"
    session.flush()
    return add_finding(session, case, text, supporting=supporting, derived_by=derived_by)


def _test_contribution(test: CaseTest) -> float:
    if test.result not in ("pass", "fail"):
        return 0.0
    fault_found = test.result == "fail"
    if test.polarity == "confirms":
        return test.weight if fault_found else -test.weight
    # refutes: a failing test refutes the hypothesis, a passing one supports it
    return -test.weight if fault_found else test.weight


def rank_hypotheses(session: Session, case_id: int) -> list[dict]:
    """Score + rank a case's hypotheses. Returns ranked dicts (highest score first)."""
    hyps = session.scalars(select(CaseHypothesis).where(CaseHypothesis.case_id == case_id)).all()
    evidence = session.scalars(select(CaseEvidence).where(CaseEvidence.case_id == case_id)).all()
    tests = session.scalars(select(CaseTest).where(CaseTest.case_id == case_id)).all()

    scored = []
    for h in hyps:
        n_ev = sum(1 for e in evidence if e.component_slug and e.component_slug == h.component_slug)
        prior = PRIOR_BASE + PRIOR_PER_EVIDENCE * n_ev
        contrib = sum(_test_contribution(t) for t in tests if t.bears_on == h.key)
        scored.append({"key": h.key, "description": h.description, "component_slug": h.component_slug,
                       "status": h.status, "prior": round(prior, 3),
                       "score": round(prior + contrib, 3),
                       "tests_applied": sum(1 for t in tests if t.bears_on == h.key
                                            and t.result in ("pass", "fail"))})
    scored.sort(key=lambda d: d["score"], reverse=True)
    # Relative support across positive-scoring hypotheses (presentation only).
    pos_total = sum(d["score"] for d in scored if d["score"] > 0)
    for d in scored:
        d["support"] = round(d["score"] / pos_total, 3) if (pos_total > 0 and d["score"] > 0) else 0.0
    return scored


def recommend_next_test(session: Session, case_id: int) -> list[dict]:
    """Recommend the best next test for a case via the failure-mode library.

    Maps the case's hypotheses (their components) to candidate failure modes, then ranks
    the discriminating tests by information-gain utility — the single best next test
    first. Tests whose name matches an already-recorded case test are treated as done.
    """
    from . import diaglib
    hyps = session.scalars(select(CaseHypothesis).where(CaseHypothesis.case_id == case_id)).all()
    comp_slugs = [h.component_slug for h in hyps if h.component_slug]
    candidates = diaglib.candidates_for_components(session, comp_slugs)
    done_names = {t.name for t in session.scalars(select(CaseTest).where(
        CaseTest.case_id == case_id, CaseTest.result != "pending"))}
    ranked = diaglib.recommend_next_test(session, candidates)
    return [r for r in ranked if r["name"] not in done_names]


def case_view(session: Session, case_id: int) -> dict | None:
    """The full workbench view for a case: symptoms, known data, tests, ranked hypotheses,
    findings — everything a human needs to decide the next test."""
    case = session.get(DiagnosticCase, case_id)
    if case is None:
        return None
    tests = session.scalars(select(CaseTest).where(CaseTest.case_id == case_id)
                            .order_by(CaseTest.sort, CaseTest.id)).all()
    findings = session.scalars(select(CaseFinding).where(CaseFinding.case_id == case_id)
                               .order_by(CaseFinding.created_at)).all()
    ranked = rank_hypotheses(session, case_id)
    next_test = next((t for t in tests if t.result == "pending"), None)
    return {
        "id": case.id, "code": case.code, "title": case.title, "status": case.status,
        "outcome": case.outcome,
        "symptoms": [s.description for s in case.symptoms],
        "known_data": [{"kind": e.kind, "ref": e.ref, "detail": e.detail,
                        "component": e.component_slug} for e in case.evidence],
        "tests": [{"id": t.id, "name": t.name, "expected": t.expected, "actual": t.actual,
                   "result": t.result, "bears_on": t.bears_on, "interpretation": t.interpretation}
                  for t in tests],
        "hypotheses": ranked,
        "findings": [{"text": f.text, "supporting": f.supporting, "contradicting": f.contradicting,
                      "derived_by": f.derived_by} for f in findings],
        "next_test": next_test.name if next_test else None,
        "recommended_test": (recommend_next_test(session, case_id) or [{}])[0].get("name"),
    }


def seed_example_case(session: Session, variant_slug: str = "focus-st") -> str:
    """Seed the worked 'low / intermittent boost' case (DG-0004), grounded in real data:
    the P04DB crankcase-vent history + the post-MAF intake mod point upstream (PCV side),
    so the ranking leads with the unmetered-air / PCV hypothesis while the pressure tests
    are still pending. Idempotent."""
    from .refmodels import VehicleVariant
    variant = session.scalar(select(VehicleVariant).where(VehicleVariant.slug == variant_slug))
    if variant is None:
        return "No reference variant — run `seed-ref` first."
    vehicle = session.scalar(select(Vehicle).where(Vehicle.variant_id == variant.id))
    if vehicle is None:
        return f"No vehicle linked to variant '{variant_slug}'."
    if session.scalar(select(DiagnosticCase).where(
            DiagnosticCase.vehicle_id == vehicle.id, DiagnosticCase.code == "DG-0004")):
        return "Example case DG-0004 already present."

    case = open_case(session, vehicle, "Low / intermittent boost", code="DG-0004",
                     symptoms=["Intermittent turbo/whistle sound", "Low indicated boost"],
                     note="Worked example — boost complaint on a modified-intake, stock-turbo car.")
    # Known data (only PCV-side items carry a component so they weight that hypothesis).
    add_evidence(session, case, "dtc", "P04DB", "Crankcase-ventilation history", "pcv")
    add_evidence(session, case, "mod", "intake", "Aftermarket intake (post-MAF path) — unmetered-air risk", "pcv")
    add_evidence(session, case, "observation", "turbo", "Turbo is stock / low-mile — mechanical wear less likely", None)

    add_hypothesis(session, case, "pcv-intake-leak", "PCV / intake unmetered-air leak", "pcv")
    add_hypothesis(session, case, "boost-leak", "Charge-pipe / intercooler boost leak", "charge-piping")
    add_hypothesis(session, case, "wastegate", "Wastegate / boost-control fault", "wastegate")
    add_hypothesis(session, case, "turbo-mechanical", "Turbo mechanical wear", "turbocharger")

    add_test(session, case, "Visual intake + PCV plumbing inspection", bears_on="pcv-intake-leak",
             expected="No cracked/disconnected hoses; PCV routing correct", weight=0.8,
             component_slug="pcv", source_label="workbench", sort=1)
    add_test(session, case, "Smoke test (pressurize intake tract)", bears_on="boost-leak",
             expected="No smoke escaping under pressure", weight=1.0,
             component_slug="charge-piping", source_label="workbench", sort=2)
    add_test(session, case, "Boost target vs actual (datalog)", bears_on="wastegate",
             expected="Actual tracks target within tolerance", weight=1.0,
             component_slug="wastegate", source_label="workbench", sort=3)
    add_test(session, case, "Wastegate duty-cycle analysis", bears_on="wastegate",
             expected="Duty sane; no overboost/underboost correction pegging", weight=0.8,
             component_slug="wastegate", source_label="workbench", sort=4)

    add_finding(session, case,
                "Working hypothesis: unmetered-air / PCV-side leak — P04DB history and the "
                "post-MAF intake mod both point upstream. Pressure tests pending.",
                supporting="P04DB crankcase-vent history; post-MAF intake mod",
                contradicting="none yet — smoke test not performed",
                derived_by="workbench ranking heuristic v1")
    session.flush()
    ranked = rank_hypotheses(session, case.id)
    return (f"Seeded case {case.code} '{case.title}' · {len(ranked)} hypotheses "
            f"(leading: {ranked[0]['description']} @ support {ranked[0]['support']}).")


def list_cases(session: Session, vehicle_id: int | None = None) -> list[dict]:
    stmt = select(DiagnosticCase).order_by(DiagnosticCase.id)
    if vehicle_id is not None:
        stmt = stmt.where(DiagnosticCase.vehicle_id == vehicle_id)
    out = []
    for c in session.scalars(stmt):
        ranked = rank_hypotheses(session, c.id)
        lead = ranked[0] if ranked else None
        out.append({"id": c.id, "code": c.code, "title": c.title, "status": c.status,
                    "leading": lead["description"] if lead else None,
                    "support": lead["support"] if lead else None})
    return out
