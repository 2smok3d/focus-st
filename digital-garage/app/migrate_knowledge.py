"""Phase 2 (cont.) — normalize V1 maintenance intervals + known issues into claims.

The V1 `maintenance_intervals` and `issues` tables hold graded, source-backed facts
about a vehicle. This lifts them into the canonical claim/evidence model so they carry
the same provenance as everything else, while leaving the V1 rows (and the exports and
`due` calculations that read them) untouched — Markdown/JSON stay projections.

Modeling:
  - a maintenance interval → claims `maintenance:<item> · interval_miles|interval_months`,
    evidence authority taken from the interval's source (OEM manual → OEM_VERIFIED,
    community → CORROBORATED).
  - a known issue → a claim `issue:<title> · known_issue`. A VEHICLE_VERIFIED issue is
    evidence observed on THIS car (on_vehicle → VEHICLE_VERIFIED verdict); a platform
    issue is community/OEM knowledge graded by its recorded verification.

Non-destructive + idempotent: an existing claim for the same subject/property is left
as-is (weaker evidence never overwrites stronger).
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import provenance as pv
from .models import Issue, MaintenanceInterval, Recall, Source, Vehicle
from .refmodels import Claim, ClaimEvidence, VehicleVariant

# Map a recorded verification grade to a source authority when no source row exists.
_GRADE_AUTHORITY = {"OEM_VERIFIED": 1, "CORROBORATED": 4, "UNVERIFIED": 6, "VEHICLE_VERIFIED": 2}


def _slug(text: str, maxlen: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:maxlen].strip("-")


def _authority(session: Session, source_id: int | None, verification: str) -> tuple[int, str]:
    """Return (authority, label) — prefer the linked source's rank, else the grade."""
    if source_id:
        src = session.get(Source, source_id)
        if src and src.authority:
            return src.authority, src.name
    return _GRADE_AUTHORITY.get(verification, 6), f"V1 record ({verification})"


def _resolve_targets(session: Session, variant_slug: str):
    variant = session.scalar(select(VehicleVariant).where(VehicleVariant.slug == variant_slug))
    if variant is None:
        return None, None, None
    vehicle = session.scalar(select(Vehicle).where(Vehicle.variant_id == variant.id))
    if vehicle is None:
        return variant, None, None
    ap = {"variant": variant_slug, "years": variant.years, "market": variant.market}
    return variant, vehicle, ap


def _add_claim(session, subject_type, subject_key, prop, value, unit, applicability,
               authority, label, on_vehicle, notes) -> bool:
    existing = session.scalar(select(Claim).where(
        Claim.subject_type == subject_type, Claim.subject_key == subject_key, Claim.prop == prop))
    if existing is not None:
        return False
    claim = Claim(subject_type=subject_type, subject_key=subject_key, prop=prop,
                  value=value, unit=unit, applicability=applicability)
    session.add(claim)
    session.flush()
    session.add(ClaimEvidence(claim_id=claim.id, authority=authority, stance=pv.SUPPORTS,
                              on_vehicle=on_vehicle, source_label=label))
    verdict = pv.resolve_verdict([pv.Evidence(authority=authority, stance=pv.SUPPORTS,
                                              on_vehicle=on_vehicle, source_label=label)])
    claim.verification = verdict.verification.name
    claim.confidence = verdict.confidence
    claim.conflict = verdict.conflict
    claim.notes = (notes + " " if notes else "") + verdict.rationale
    session.flush()
    return True


def migrate_maintenance_to_claims(session: Session, variant_slug: str = "focus-st") -> str:
    variant, vehicle, ap = _resolve_targets(session, variant_slug)
    if variant is None:
        return "No reference variant — run `seed-ref` first."
    if vehicle is None:
        return f"No vehicle linked to variant '{variant_slug}'."
    created = 0
    for mi in session.scalars(select(MaintenanceInterval).where(
            MaintenanceInterval.vehicle_id == vehicle.id)):
        auth, label = _authority(session, mi.source_id, mi.verification)
        key = _slug(mi.item)
        if mi.interval_miles is not None:
            created += _add_claim(session, "maintenance", key, "interval_miles",
                                  str(mi.interval_miles), "mi", ap, auth, label, False, mi.note)
        if mi.interval_months is not None:
            created += _add_claim(session, "maintenance", key, "interval_months",
                                  str(mi.interval_months), "mo", ap, auth, label, False, mi.note)
    return f"Maintenance → claims: {created} created."


def migrate_issues_to_claims(session: Session, variant_slug: str = "focus-st") -> str:
    variant, vehicle, ap = _resolve_targets(session, variant_slug)
    if variant is None:
        return "No reference variant — run `seed-ref` first."
    if vehicle is None:
        return f"No vehicle linked to variant '{variant_slug}'."
    created = 0
    for iss in session.scalars(select(Issue).where(Issue.vehicle_id == vehicle.id)):
        on_vehicle = iss.verification == "VEHICLE_VERIFIED"
        auth, label = _authority(session, None, iss.verification)
        # An on-vehicle observation applies to THIS car; a platform issue to the variant.
        applicability = {"variant": variant_slug} if on_vehicle else ap
        detail = f"status={iss.status}"
        if iss.severity:
            detail += f" · severity={iss.severity}"
        if iss.note:
            detail += f". {iss.note}"
        created += _add_claim(session, "issue", _slug(iss.title), "known_issue",
                              iss.title, None, applicability, auth, label, on_vehicle, detail)
    return f"Known issues → claims: {created} created."


# NHTSA is a primary government safety-data source; a KB-noted campaign awaiting VIN
# confirmation is only as strong as its recorded grade.
_ORIGIN_AUTHORITY = {"nhtsa": 1}


def migrate_recalls_to_claims(session: Session, variant_slug: str = "focus-st") -> str:
    """Normalize recall / safety-campaign records into claims.

    Stores the campaign's *derived structured facts* — number, affected component,
    remedy summary, status, and the "verify by VIN" citation note — never protected
    manual content. NHTSA-origin campaigns are government-authoritative; KB-noted Ford
    campaigns keep their recorded (conservative) grade until confirmed for this VIN.
    """
    variant, vehicle, ap = _resolve_targets(session, variant_slug)
    if variant is None:
        return "No reference variant — run `seed-ref` first."
    if vehicle is None:
        return f"No vehicle linked to variant '{variant_slug}'."
    created = 0
    for rc in session.scalars(select(Recall).where(Recall.vehicle_id == vehicle.id)):
        origin = (rc.origin or "").lower()
        auth = _ORIGIN_AUTHORITY.get(origin.split("-")[0], _GRADE_AUTHORITY.get(rc.verification, 4))
        label = "NHTSA recalls database" if origin.startswith("nhtsa") else f"KB / Ford campaign ({rc.verification})"
        value = rc.component or (rc.summary[:80] if rc.summary else rc.campaign_number)
        detail_bits = [f"status={rc.status}"]
        if rc.summary:
            detail_bits.append(rc.summary)
        if rc.remedy:
            detail_bits.append(f"Remedy: {rc.remedy}")
        if rc.note:
            detail_bits.append(rc.note)
        created += _add_claim(session, "recall", rc.campaign_number.upper(), "campaign",
                              value, None, ap, auth, label, False, " · ".join(detail_bits))
    return f"Recalls/TSBs → claims: {created} created."


def migrate_knowledge(session: Session, variant_slug: str = "focus-st") -> str:
    return (migrate_maintenance_to_claims(session, variant_slug)
            + "  " + migrate_issues_to_claims(session, variant_slug)
            + "  " + migrate_recalls_to_claims(session, variant_slug))
