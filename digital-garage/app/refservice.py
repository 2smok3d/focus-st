"""Read/query layer over the V2 reference model + claim provenance.

Pure DB reads that project the canonical reference graph into plain dicts for the
CLI, API, and (later) the dashboard. Verdicts are stored on each claim (resolved at
write time by provenance.resolve_verdict), but this layer can also *re-resolve* a
claim's live evidence on demand so the display never drifts from the rules.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import provenance as pv
from .refmodels import (
    Claim,
    ClaimEvidence,
    Component,
    ComponentRelationship,
    Engine,
    Manufacturer,
    System,
    Transmission,
    VehiclePlatform,
    VehicleVariant,
)


def get_variant(session: Session, slug: str) -> VehicleVariant | None:
    return session.scalar(select(VehicleVariant).where(VehicleVariant.slug == slug))


def variant_header(session: Session, slug: str) -> dict | None:
    """Manufacturer → platform → variant + engine/transmission summary."""
    v = get_variant(session, slug)
    if v is None:
        return None
    platform = session.get(VehiclePlatform, v.platform_id)
    maker = session.get(Manufacturer, platform.manufacturer_id) if platform else None
    eng = session.scalar(select(Engine).where(Engine.variant_id == v.id))
    trans = session.scalar(select(Transmission).where(Transmission.variant_id == v.id))
    return {
        "slug": v.slug,
        "name": v.name,
        "trim": v.trim,
        "market": v.market,
        "years": v.years,
        "manufacturer": maker.name if maker else None,
        "platform": platform.name if platform else None,
        "platform_code": platform.code if platform else None,
        "engine": {
            "code": eng.code, "displacement_cc": eng.displacement_cc, "config": eng.config,
            "aspiration": eng.aspiration, "power": eng.power, "torque": eng.torque,
        } if eng else None,
        "transmission": {"code": trans.code, "type": trans.type, "gears": trans.gears} if trans else None,
    }


def system_tree(session: Session, slug: str) -> list[dict]:
    """Nested system → subsystem → components tree for a variant."""
    v = get_variant(session, slug)
    if v is None:
        return []
    systems = session.scalars(
        select(System).where(System.variant_id == v.id).order_by(System.sort, System.name)
    ).all()
    comps_by_sys: dict[int, list[dict]] = {}
    for s in systems:
        rows = session.scalars(
            select(Component).where(Component.system_id == s.id).order_by(Component.name)
        ).all()
        comps_by_sys[s.id] = [{"slug": c.slug, "name": c.name, "oem_hint": c.oem_hint} for c in rows]

    def node(s: System) -> dict:
        return {
            "slug": s.slug, "name": s.name, "description": s.description,
            "components": comps_by_sys.get(s.id, []),
            "children": [node(c) for c in systems if c.parent_id == s.id],
        }

    return [node(s) for s in systems if s.parent_id is None]


def get_component(session: Session, variant_slug: str, comp_slug: str) -> dict | None:
    """A component with its system, typed relationships, and attached claims."""
    v = get_variant(session, variant_slug)
    if v is None:
        return None
    sys_ids = [s.id for s in session.scalars(select(System).where(System.variant_id == v.id))]
    comp = session.scalar(
        select(Component).where(Component.system_id.in_(sys_ids), Component.slug == comp_slug)
    )
    if comp is None:
        return None
    sys = session.get(System, comp.system_id)
    # outgoing + incoming edges, resolved to component names
    edges = []
    for rel in session.scalars(select(ComponentRelationship).where(
            ComponentRelationship.from_component_id == comp.id)):
        other = session.get(Component, rel.to_component_id)
        edges.append({"dir": "→", "relation": rel.relation,
                      "other": other.name if other else "?", "note": rel.note})
    for rel in session.scalars(select(ComponentRelationship).where(
            ComponentRelationship.to_component_id == comp.id)):
        other = session.get(Component, rel.from_component_id)
        edges.append({"dir": "←", "relation": rel.relation,
                      "other": other.name if other else "?", "note": rel.note})
    return {
        "slug": comp.slug, "name": comp.name, "description": comp.description,
        "oem_hint": comp.oem_hint, "system": sys.name if sys else None,
        "relationships": edges,
        "claims": claims_for(session, "component", comp.slug),
    }


def _claim_dict(session: Session, c: Claim, *, with_evidence: bool = False) -> dict:
    d = {
        "id": c.id, "subject_type": c.subject_type, "subject_key": c.subject_key,
        "property": c.prop, "value": c.value, "unit": c.unit,
        "verification": c.verification, "confidence": c.confidence,
        "conflict": c.conflict, "notes": c.notes, "applicability": c.applicability,
    }
    if with_evidence:
        evs = session.scalars(
            select(ClaimEvidence).where(ClaimEvidence.claim_id == c.id)
            .order_by(ClaimEvidence.authority)
        ).all()
        d["evidence"] = [{
            "authority": e.authority, "stance": e.stance, "on_vehicle": e.on_vehicle,
            "label": e.source_label, "page": e.page, "section": e.section,
        } for e in evs]
    return d


def claims_for(session: Session, subject_type: str, subject_key: str) -> list[dict]:
    rows = session.scalars(select(Claim).where(
        Claim.subject_type == subject_type, Claim.subject_key == subject_key
    ).order_by(Claim.prop)).all()
    return [_claim_dict(session, c) for c in rows]


def get_claim(session: Session, subject_key: str, prop: str) -> dict | None:
    """A single claim, with full evidence and a freshly re-resolved verdict.

    Re-resolving from live evidence guarantees the displayed verdict always matches
    the current provenance rules, not a value that was stored under older logic.
    """
    c = session.scalar(select(Claim).where(Claim.subject_key == subject_key, Claim.prop == prop))
    if c is None:
        return None
    d = _claim_dict(session, c, with_evidence=True)
    ev_objs = [pv.Evidence(authority=e["authority"], stance=e["stance"],
                           on_vehicle=e["on_vehicle"], source_label=e["label"] or "")
               for e in d["evidence"]]
    d["resolved"] = pv.resolve_verdict(ev_objs).as_dict()
    return d


def list_conflicts(session: Session) -> list[dict]:
    """Every claim currently flagged as conflicting — the disagreement surface."""
    rows = session.scalars(select(Claim).where(Claim.conflict.is_(True)).order_by(Claim.subject_key)).all()
    return [_claim_dict(session, c) for c in rows]
