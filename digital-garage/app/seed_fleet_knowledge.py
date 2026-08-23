"""F1 — normalize the fleet's verified manual specs into graded reference claims.

The four non-flagship machines (zzr600, rz350, tz250, toyota-pickup) each carry a
web-verified specification table in their `manual.md`, every row tagged with a
confidence: `verified`, `corroborated`, or `⚠️ verify`. This turns those rows into V2
reference **claims** attached to the variant, each backed by **evidence** whose
authority reflects the confidence tag — so the trust grade is *computed*, never
asserted, and the ⚠️ rows land honestly as `UNVERIFIED`, feeding the per-variant
research queue.

Honest grading: a `verified` row is *web/spec-reference* verified, not the factory
manual in hand, so it maps to authority 3 (professional/trade → `CORROBORATED`), not
OEM. `corroborated` is enthusiast consensus (4); `⚠️ verify` is unconfirmed (6).

Idempotent: an existing claim for the same (subject, prop) is left untouched. Markdown
stays a projection; this writes into the canonical claim model. Flagship focus-st is
excluded — its claims come from the richer V1 migration pipeline.
"""
from __future__ import annotations

import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import provenance as pv
from .refmodels import Claim, ClaimEvidence, VehicleVariant

REPO = Path(__file__).resolve().parent.parent.parent
FLEET = ("zzr600", "rz350", "tz250", "toyota-pickup")

# manual confidence tag → (evidence authority, human label).
_CONF_AUTHORITY = {
    "verified": (3, "Manufacturer/spec-reference (web-verified)"),
    "corroborated": (4, "Enthusiast/community consensus"),
    "verify": (6, "Unconfirmed — needs factory service manual"),
}


def _prop(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_") or "spec"


def _clean(cell: str) -> str:
    return re.sub(r"\s+", " ", cell.replace("**", "").strip())


def _confidence_tag(cell: str) -> str:
    c = cell.lower()
    if "verify" in c or "⚠" in c:
        return "verify"
    if "corroborated" in c:
        return "corroborated"
    return "verified"


def _spec_rows(manual: str):
    """Yield (name, value, confidence_cell) for every data row of a
    `| System | Spec | Confidence |` table anywhere in the manual."""
    in_tbl = False
    for ln in manual.splitlines():
        s = ln.strip()
        if not s.startswith("|"):
            in_tbl = False
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if [c.lower() for c in cells[:3]] == ["system", "spec", "confidence"]:
            in_tbl = True
            continue
        if not in_tbl:
            continue
        if set("".join(cells)) <= set("-: "):          # |---|---|---| separator
            continue
        if len(cells) >= 3 and cells[0] and cells[1]:
            yield cells[0], cells[1], cells[2]


def seed_fleet_knowledge(session: Session, slugs: tuple[str, ...] = FLEET) -> str:
    per: dict[str, str] = {}
    for slug in slugs:
        variant = session.scalar(select(VehicleVariant).where(VehicleVariant.slug == slug))
        if variant is None:
            per[slug] = "no variant (commission first)"
            continue
        manual = REPO / "data" / "vehicles" / slug / "manual.md"
        if not manual.exists():
            per[slug] = "no manual"
            continue
        ap = {"variant": slug, "years": variant.years, "market": variant.market}
        created = 0
        for name, value, conf in _spec_rows(manual.read_text()):
            prop = _prop(name)
            if session.scalar(select(Claim).where(
                    Claim.subject_type == "variant", Claim.subject_key == slug,
                    Claim.prop == prop)) is not None:
                continue
            tag = _confidence_tag(conf)
            authority, label = _CONF_AUTHORITY[tag]
            claim = Claim(subject_type="variant", subject_key=slug, prop=prop,
                          value=_clean(value), unit=None, applicability=ap)
            session.add(claim)
            session.flush()
            session.add(ClaimEvidence(claim_id=claim.id, authority=authority, stance=pv.SUPPORTS,
                                      on_vehicle=False, source_label=label))
            verdict = pv.resolve_verdict([pv.Evidence(
                authority=authority, stance=pv.SUPPORTS, on_vehicle=False, source_label=label)])
            claim.verification = verdict.verification.name
            claim.confidence = verdict.confidence
            claim.conflict = verdict.conflict
            claim.notes = f"From {slug} manual spec [{name}] ({tag}). {verdict.rationale}"
            session.flush()
            created += 1
        per[slug] = f"{created} claim(s)"
    return "Fleet knowledge → claims: " + ", ".join(f"{k}: {v}" for k, v in per.items())
