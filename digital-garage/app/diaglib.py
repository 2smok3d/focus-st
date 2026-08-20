"""Diagnostic Core service (Milestone B) — failure-mode library, symptom matching,
information-gain next-test selection, and confidence bands.

Design commitments (roadmap #9–11):
  * Failure modes are authored once, independent of any case.
  * A symptom maps to *candidate* failure modes (keyword match) — a starting point,
    not a conclusion.
  * The "best next test" is chosen by a transparent utility — discriminating power per
    unit cost/risk — so the workbench recommends one test, not a list of ten.
  * Confidence is reported in bands (LOW / MODERATE / HIGH / VERY_HIGH), never invented
    percentages.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .fmmodels import (
    DiagnosticTest,
    FailureMode,
    FailureModeComponent,
    FailureModeSymptom,
)

CONFIDENCE_BANDS = ["LOW", "MODERATE", "HIGH", "VERY_HIGH"]


def confidence_band(support: float, *, has_evidence: bool = True) -> str:
    """Map a relative-support fraction to a confidence band. No evidence ⇒ LOW."""
    if not has_evidence:
        return "LOW"
    if support < 0.35:
        return "LOW"
    if support < 0.55:
        return "MODERATE"
    if support < 0.75:
        return "HIGH"
    return "VERY_HIGH"


def failure_mode(session: Session, slug: str) -> dict | None:
    fm = session.scalar(select(FailureMode).where(FailureMode.slug == slug))
    if fm is None:
        return None
    comps = session.scalars(select(FailureModeComponent.component_slug).where(
        FailureModeComponent.failure_mode_id == fm.id)).all()
    tests = session.scalars(select(DiagnosticTest).where(DiagnosticTest.discriminates == slug)).all()
    return {
        "slug": fm.slug, "name": fm.name, "system": fm.system_slug, "severity": fm.severity,
        "description": fm.description, "expected_observations": fm.expected_observations,
        "disconfirming_evidence": fm.disconfirming_evidence, "consequences": fm.consequences,
        "components": list(comps),
        "tests": [{"slug": t.slug, "name": t.name, "effect": t.effect,
                   "info_gain": t.info_gain, "cost": t.cost, "risk": t.risk} for t in tests],
    }


def candidates_for_symptom(session: Session, text: str) -> list[dict]:
    """Match a free-text symptom to candidate failure modes by keyword overlap."""
    words = {w for w in _tokens(text)}
    scored: dict[int, int] = {}
    fm_by_id = {fm.id: fm for fm in session.scalars(select(FailureMode))}
    for row in session.scalars(select(FailureModeSymptom)):
        kw = set(_tokens(row.keywords or row.symptom))
        overlap = len(words & kw)
        if overlap:
            scored[row.failure_mode_id] = max(scored.get(row.failure_mode_id, 0), overlap)
    out = [{"slug": fm_by_id[fid].slug, "name": fm_by_id[fid].name,
            "system": fm_by_id[fid].system_slug, "match": score}
           for fid, score in scored.items() if fid in fm_by_id]
    out.sort(key=lambda d: d["match"], reverse=True)
    return out


def candidates_for_components(session: Session, component_slugs: list[str]) -> list[str]:
    """Failure-mode slugs whose possible components intersect the given components."""
    if not component_slugs:
        return []
    rows = session.scalars(select(FailureModeComponent.failure_mode_id).where(
        FailureModeComponent.component_slug.in_(component_slugs))).all()
    fm_by_id = {fm.id: fm.slug for fm in session.scalars(select(FailureMode))}
    return sorted({fm_by_id[i] for i in rows if i in fm_by_id})


def _tokens(text: str) -> list[str]:
    import re
    return [w for w in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(w) > 2]


def _utility(t: DiagnosticTest) -> float:
    """Transparent next-test utility: discriminating power per unit cost + risk.

    A cheap, safe, highly-discriminating test wins over an expensive or risky one.
    """
    return t.info_gain / (t.cost + 0.5 * (t.risk - 1))


def recommend_next_test(session: Session, candidate_slugs: list[str],
                        done_test_slugs: list[str] | None = None) -> list[dict]:
    """Rank the pending tests that discriminate the live candidate failure modes by
    information-gain utility. The first row is the single best next test."""
    done = set(done_test_slugs or [])
    tests = session.scalars(select(DiagnosticTest).where(
        DiagnosticTest.discriminates.in_(candidate_slugs))).all()
    ranked = []
    for t in tests:
        if t.slug in done:
            continue
        ranked.append({"slug": t.slug, "name": t.name, "discriminates": t.discriminates,
                       "effect": t.effect, "info_gain": t.info_gain, "cost": t.cost,
                       "risk": t.risk, "time_min": t.time_min,
                       "utility": round(_utility(t), 3), "purpose": t.purpose,
                       "required_tools": t.required_tools})
    ranked.sort(key=lambda d: d["utility"], reverse=True)
    return ranked
