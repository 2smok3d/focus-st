"""Seed typed graph overlays over the Focus ST components (Milestone A ontology).

Classifies the reference edges into domain overlays — airflow, coolant, lubrication —
so the same components can be traversed as several distinct graphs, and adds the few
components those flows need (air filter, water pump, oil pump). Also creates one
example Assembly (the charge-air path) to exercise the Machine → System → Assembly →
Component level. Idempotent; additive to seed_ref.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .refmodels import Assembly, Component, ComponentRelationship, System, VehicleVariant

# components to ensure exist: (system_slug, comp_slug, name)
EXTRA_COMPONENTS = [
    ("engine", "oil-pump", "Oil Pump"),
    ("cooling", "water-pump", "Water Pump"),
    ("forced-induction", "air-filter", "Air Filter / Intake"),
]

# overlay edges: (from, relation, to, domain, medium, direction)
OVERLAY_EDGES = [
    # AIRFLOW — filter → turbo → intercooler → charge pipe → throttle → manifold → head
    ("air-filter", "feeds", "turbocharger", "airflow", "air", "forward"),
    ("turbocharger", "outputs_to", "intercooler", "airflow", "air", "forward"),
    ("intercooler", "outputs_to", "charge-piping", "airflow", "air", "forward"),
    ("charge-piping", "feeds", "throttle-body", "airflow", "air", "forward"),
    ("throttle-body", "feeds", "intake-manifold", "airflow", "air", "forward"),
    ("intake-manifold", "feeds", "head", "airflow", "air", "forward"),
    # COOLANT — pump → block → head → thermostat → radiator → pump
    ("water-pump", "feeds", "block", "coolant", "coolant", "forward"),
    ("block", "feeds", "head", "coolant", "coolant", "forward"),
    ("head", "feeds", "thermostat", "coolant", "coolant", "forward"),
    ("thermostat", "feeds", "radiator", "coolant", "coolant", "forward"),
    ("radiator", "returns_to", "water-pump", "coolant", "coolant", "forward"),
    ("turbocharger", "cooled_by", "coolant", "coolant", "coolant", "bidirectional"),
    # LUBRICATION — pump → oil system → turbo (feed) → back to sump
    ("oil-pump", "feeds", "lubrication", "lubrication", "oil", "forward"),
    ("lubrication", "lubricates", "turbocharger", "lubrication", "oil", "forward"),
    ("turbocharger", "returns_to", "lubrication", "lubrication", "oil", "forward"),
]

# example assembly: (system_slug, assembly_slug, name, [component slugs])
ASSEMBLIES = [
    ("forced-induction", "charge-air-path", "Charge-Air Path",
     ["intercooler", "charge-piping", "throttle-body"]),
]


def seed_graph(session: Session, variant_slug: str = "focus-st") -> str:
    variant = session.scalar(select(VehicleVariant).where(VehicleVariant.slug == variant_slug))
    if variant is None:
        return "No reference variant — run `seed-ref` first."
    sysmap = {s.slug: s for s in session.scalars(
        select(System).where(System.variant_id == variant.id))}
    comps = {c.slug: c for c in session.scalars(
        select(Component).join(System).where(System.variant_id == variant.id))}

    added_c = 0
    for sys_slug, cslug, cname in EXTRA_COMPONENTS:
        if cslug not in comps and sys_slug in sysmap:
            c = Component(system_id=sysmap[sys_slug].id, slug=cslug, name=cname)
            session.add(c)
            session.flush()
            comps[cslug] = c
            added_c += 1

    # assemblies + membership
    added_a = 0
    for sys_slug, aslug, aname, members in ASSEMBLIES:
        if sys_slug not in sysmap:
            continue
        asm = session.scalar(select(Assembly).where(
            Assembly.system_id == sysmap[sys_slug].id, Assembly.slug == aslug))
        if asm is None:
            asm = Assembly(system_id=sysmap[sys_slug].id, slug=aslug, name=aname)
            session.add(asm)
            session.flush()
            added_a += 1
        for m in members:
            if m in comps and comps[m].assembly_id != asm.id:
                comps[m].assembly_id = asm.id
    session.flush()

    # overlay edges: upsert domain/medium/direction on existing edges, else create.
    added_e = tagged_e = 0
    for a, rel, b, domain, medium, direction in OVERLAY_EDGES:
        if a not in comps or b not in comps:
            continue
        edge = session.scalar(select(ComponentRelationship).where(
            ComponentRelationship.from_component_id == comps[a].id,
            ComponentRelationship.to_component_id == comps[b].id,
            ComponentRelationship.relation == rel))
        if edge is None:
            session.add(ComponentRelationship(
                from_component_id=comps[a].id, to_component_id=comps[b].id, relation=rel,
                domain=domain, medium=medium, direction=direction))
            added_e += 1
        else:
            edge.domain, edge.medium, edge.direction = domain, medium, direction
            tagged_e += 1
    session.flush()
    return (f"Graph overlays seeded: +{added_c} components, +{added_a} assemblies, "
            f"{added_e} new / {tagged_e} classified edges across airflow/coolant/lubrication.")
