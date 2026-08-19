"""Machine State Engine (V3) — record component condition over time and project the
digital twin against the reference model.

Core ideas (V4 machine-OS framing):
  - A component's state is a *timeline* of observations; recording a new state
    supersedes the prior current one rather than overwriting it.
  - `MachineState(T)` is reconstructable for any T from `[observed_at, superseded_at)`.
  - `reference_vs_actual` overlays the recorded states on the reference component tree
    so the UI/agents can show OEM-vs-your-machine at a glance. A component with no
    recorded observation reports condition=stock / knowledge=UNKNOWN — "unknown", not
    "wrong": absence of a mod is assumed stock, but we don't claim to have verified it.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import refservice as rs
from .models import Vehicle
from .refmodels import Component, System, VehicleVariant
from .twinmodels import CONDITIONS, KNOWLEDGE_STATES, ComponentState, MachineCapability


def _resolve_component_id(session: Session, variant: VehicleVariant, slug: str) -> int | None:
    sys_ids = [s.id for s in session.scalars(select(System).where(System.variant_id == variant.id))]
    comp = session.scalar(select(Component).where(
        Component.system_id.in_(sys_ids), Component.slug == slug))
    return comp.id if comp else None


def record_state(session: Session, vehicle: Vehicle, component_slug: str, *,
                 condition: str = "stock", knowledge_state: str = "UNKNOWN",
                 installed_part: str | None = None, confidence: float = 0.0,
                 hours: float | None = None, miles: int | None = None, cycles: int | None = None,
                 note: str | None = None, source_label: str | None = None,
                 observed_at: dt.datetime | None = None) -> ComponentState:
    """Record a new component-state observation, superseding the current one (if any)."""
    if condition not in CONDITIONS:
        raise ValueError(f"invalid condition '{condition}'")
    if knowledge_state not in KNOWLEDGE_STATES:
        raise ValueError(f"invalid knowledge_state '{knowledge_state}'")
    when = observed_at or dt.datetime.now(dt.timezone.utc)

    current = session.scalar(select(ComponentState).where(
        ComponentState.vehicle_id == vehicle.id,
        ComponentState.component_slug == component_slug,
        ComponentState.superseded_at.is_(None)))
    if current is not None:
        current.superseded_at = when

    comp_id = None
    if vehicle.variant_id:
        variant = session.get(VehicleVariant, vehicle.variant_id)
        if variant:
            comp_id = _resolve_component_id(session, variant, component_slug)

    row = ComponentState(
        vehicle_id=vehicle.id, component_id=comp_id, component_slug=component_slug,
        condition=condition, knowledge_state=knowledge_state, installed_part=installed_part,
        confidence=confidence, hours=hours, miles=miles, cycles=cycles,
        observed_at=when, note=note, source_label=source_label)
    session.add(row)
    session.flush()
    return row


def current_states(session: Session, vehicle_id: int) -> dict[str, ComponentState]:
    rows = session.scalars(select(ComponentState).where(
        ComponentState.vehicle_id == vehicle_id,
        ComponentState.superseded_at.is_(None))).all()
    return {r.component_slug: r for r in rows}


def state_at(session: Session, vehicle_id: int, when: dt.datetime) -> dict[str, ComponentState]:
    """MachineState(T): the state of each component as of time `when`."""
    rows = session.scalars(select(ComponentState).where(
        ComponentState.vehicle_id == vehicle_id,
        ComponentState.observed_at <= when)).all()
    out: dict[str, ComponentState] = {}
    for r in rows:
        if r.superseded_at is not None and r.superseded_at <= when:
            continue  # this observation was already replaced by `when`
        prev = out.get(r.component_slug)
        if prev is None or r.observed_at > prev.observed_at:
            out[r.component_slug] = r
    return out


def _state_dict(s: ComponentState | None) -> dict:
    if s is None:
        return {"condition": "stock", "knowledge_state": "UNKNOWN", "installed_part": None,
                "confidence": 0.0, "observed": False}
    return {"condition": s.condition, "knowledge_state": s.knowledge_state,
            "installed_part": s.installed_part, "confidence": s.confidence,
            "note": s.note, "observed": True,
            "observed_at": s.observed_at.isoformat() if s.observed_at else None}


def reference_vs_actual(session: Session, variant_slug: str = "focus-st") -> dict | None:
    """Overlay recorded component states on the reference system → component tree."""
    variant = session.scalar(select(VehicleVariant).where(VehicleVariant.slug == variant_slug))
    if variant is None:
        return None
    vehicle = session.scalar(select(Vehicle).where(Vehicle.variant_id == variant.id))
    states = current_states(session, vehicle.id) if vehicle else {}

    def walk(nodes: list[dict]) -> list[dict]:
        out = []
        for n in nodes:
            comps = [{"slug": c["slug"], "name": c["name"],
                      "actual": _state_dict(states.get(c["slug"]))} for c in n["components"]]
            out.append({"slug": n["slug"], "name": n["name"],
                        "components": comps, "children": walk(n["children"])})
        return out

    tree = walk(rs.system_tree(session, variant_slug))
    changed = [{"slug": slug, "condition": st.condition, "installed_part": st.installed_part,
                "knowledge_state": st.knowledge_state}
               for slug, st in sorted(states.items()) if st.condition != "stock"]
    return {"variant": variant_slug, "vin": vehicle.vin if vehicle else None,
            "tree": tree, "deviations": changed}


def set_capability(session: Session, vehicle: Vehicle, capability: str,
                   supported: bool = True, note: str | None = None) -> MachineCapability:
    row = session.scalar(select(MachineCapability).where(
        MachineCapability.vehicle_id == vehicle.id, MachineCapability.capability == capability))
    if row is None:
        row = MachineCapability(vehicle_id=vehicle.id, capability=capability,
                                supported=supported, note=note)
        session.add(row)
    else:
        row.supported, row.note = supported, note
    session.flush()
    return row


def capabilities(session: Session, vehicle_id: int) -> list[dict]:
    rows = session.scalars(select(MachineCapability).where(
        MachineCapability.vehicle_id == vehicle_id).order_by(MachineCapability.capability)).all()
    return [{"capability": r.capability, "supported": r.supported, "note": r.note} for r in rows]


def seed_twin(session: Session, variant_slug: str = "focus-st") -> str:
    """Seed the Focus ST twin from confirmed on-vehicle observations (idempotent).

    These mirror the VEHICLE_VERIFIED facts already in the V1 seed: the Depo 'Beast'
    intercooler (a mod) and the cracked radiator (a confirmed failure). Only components
    that exist in the reference model are recorded; others await a broader model.
    """
    variant = session.scalar(select(VehicleVariant).where(VehicleVariant.slug == variant_slug))
    if variant is None:
        return "No reference variant — run `seed-ref` first."
    vehicle = session.scalar(select(Vehicle).where(Vehicle.variant_id == variant.id))
    if vehicle is None:
        return f"No vehicle linked to variant '{variant_slug}'."

    observed = [
        ("intercooler", "modified", "DIRECTLY_OBSERVED", 0.95,
         "Depo 'Beast' FMIC (28×8.25×5.5). Pressure-tested OK to ~15 psi.", "Depo 'Beast' FMIC"),
        ("radiator", "failed", "DIRECTLY_OBSERVED", 0.95,
         "Through-hole crack, front-left of core. Decided fix: Mishimoto radiator.", None),
    ]
    existing = current_states(session, vehicle.id)
    recorded = 0
    for slug, cond, know, conf, note, part in observed:
        if slug in existing:
            continue
        record_state(session, vehicle, slug, condition=cond, knowledge_state=know,
                     confidence=conf, installed_part=part, note=note,
                     source_label="on-vehicle observation")
        recorded += 1

    # Capability profile — the Focus ST is a modern CAN/OBD car.
    for cap in ("can_bus", "obd", "dtc", "ecu_telemetry"):
        set_capability(session, vehicle, cap, True)

    return (f"Seeded twin for {vehicle.vin}: {recorded} component state(s) recorded, "
            f"{len(existing) + recorded} tracked · capability profile set.")
