"""Phase 2 — migrate V1 `specs` into V2 claims with provenance.

The V1 `specs` table holds fact-checked values, each with a `verification` grade and a
`source_id`. V2 wants those facts as **claims** attached to the reference model
(variant / engine / transmission / component), each backed by **evidence** whose
authority comes from the spec's source. This is the migration path the architecture
calls for: the structured facts move into the canonical claim model while the V1
`specs` rows stay put and keep driving the existing exports (Markdown/JSON are
projections — nothing is deleted).

The mapping is explicit and conservative: only specs with a known target are migrated;
anything unmapped is reported, never guessed. Claims already present (e.g. the ones
`seed_ref` seeds directly, like the oil-capacity conflict) are left untouched — the
migrator never downgrades or overwrites an existing claim.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import provenance as pv
from .models import Source, Spec, Vehicle
from .refmodels import Claim, ClaimEvidence, VehicleVariant

# (category, name) → (subject_type, subject_key, property). subject_key uses the same
# identifiers seed_ref established (engine "r9da", the component slugs, the variant slug,
# transmission "mt82") so migrated claims coexist with seeded ones without collision.
SPEC_MAP: dict[tuple[str, str], tuple[str, str, str]] = {
    ("engine", "Rated power"):        ("engine", "r9da", "rated_power"),
    ("engine", "Rated torque"):       ("engine", "r9da", "rated_torque"),
    ("engine", "Compression ratio"):  ("engine", "r9da", "compression_ratio"),
    ("engine", "Firing order"):       ("engine", "r9da", "firing_order"),
    ("engine", "Spark plug gap"):     ("component", "spark-plugs", "gap"),
    ("drivetrain", "Final drive"):    ("transmission", "mt82", "final_drive"),
    ("drivetrain", "1st gear"):       ("transmission", "mt82", "ratio_1"),
    ("drivetrain", "2nd gear"):       ("transmission", "mt82", "ratio_2"),
    ("drivetrain", "3rd gear"):       ("transmission", "mt82", "ratio_3"),
    ("drivetrain", "4th gear"):       ("transmission", "mt82", "ratio_4"),
    ("drivetrain", "5th gear"):       ("transmission", "mt82", "ratio_5"),
    ("drivetrain", "6th gear"):       ("transmission", "mt82", "ratio_6"),
    ("chassis", "Wheels"):            ("variant", "focus-st", "wheel_size"),
    ("chassis", "Wheel offset"):      ("variant", "focus-st", "wheel_offset"),
    ("chassis", "Bolt pattern"):      ("variant", "focus-st", "bolt_pattern"),
    ("chassis", "Tire size"):         ("variant", "focus-st", "tire_size"),
    ("fluids", "Engine oil"):         ("component", "lubrication", "oil_spec"),
    ("fluids", "Engine oil capacity"): ("component", "lubrication", "oil_capacity"),
    ("fluids", "Transmission fluid"): ("transmission", "mt82", "fluid_spec"),
    ("fluids", "Coolant"):            ("component", "coolant", "spec"),
    ("torque", "Wheel lug nut"):      ("variant", "focus-st", "lug_torque"),
    ("torque", "Spark plug"):         ("component", "spark-plugs", "install_torque"),
}

# V1 stored verification directly; V2 derives it from evidence authority. Where a spec
# has no source authority, fall back by its recorded grade.
_GRADE_AUTHORITY = {"OEM_VERIFIED": 1, "CORROBORATED": 4, "UNVERIFIED": 6, "VEHICLE_VERIFIED": 2}


def migrate_specs_to_claims(session: Session, variant_slug: str = "focus-st") -> str:
    variant = session.scalar(select(VehicleVariant).where(VehicleVariant.slug == variant_slug))
    if variant is None:
        return "No reference variant — run `seed-ref` first."
    vehicle = session.scalar(select(Vehicle).where(Vehicle.variant_id == variant.id))
    if vehicle is None:
        return f"No vehicle linked to variant '{variant_slug}'."

    ap = {"variant": variant_slug, "years": variant.years, "market": variant.market}
    created, skipped, unmapped = 0, 0, []

    for spec in session.scalars(select(Spec).where(Spec.vehicle_id == vehicle.id)):
        target = SPEC_MAP.get((spec.category, spec.name))
        if target is None:
            unmapped.append(f"{spec.category}/{spec.name}")
            continue
        subject_type, subject_key, prop = target

        existing = session.scalar(select(Claim).where(
            Claim.subject_type == subject_type, Claim.subject_key == subject_key, Claim.prop == prop))
        if existing is not None:
            skipped += 1
            continue

        authority = _spec_authority(session, spec)
        on_vehicle = spec.verification == "VEHICLE_VERIFIED"
        src = session.get(Source, spec.source_id) if spec.source_id else None
        label = src.name if src else f"V1 spec ({spec.verification})"

        claim = Claim(subject_type=subject_type, subject_key=subject_key, prop=prop,
                      value=spec.value, unit=spec.unit, applicability=ap)
        session.add(claim)
        session.flush()
        session.add(ClaimEvidence(claim_id=claim.id, authority=authority, stance=pv.SUPPORTS,
                                  on_vehicle=on_vehicle, source_label=label))
        verdict = pv.resolve_verdict(
            [pv.Evidence(authority=authority, stance=pv.SUPPORTS, on_vehicle=on_vehicle, source_label=label)])
        claim.verification = verdict.verification.name
        claim.confidence = verdict.confidence
        claim.conflict = verdict.conflict
        claim.notes = f"Migrated from V1 spec [{spec.category}] {spec.name}. {verdict.rationale}"
        session.flush()
        created += 1

    msg = f"Migrated {created} spec(s) → claims · {skipped} already present."
    if unmapped:
        msg += f" Unmapped ({len(unmapped)}): {', '.join(unmapped)}"
    return msg


def _spec_authority(session: Session, spec: Spec) -> int:
    if spec.source_id:
        src = session.get(Source, spec.source_id)
        if src and src.authority:
            return src.authority
    return _GRADE_AUTHORITY.get(spec.verification, 6)
