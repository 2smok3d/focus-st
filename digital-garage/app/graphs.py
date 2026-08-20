"""Graph overlays over the reference components (Milestone A ontology).

The same components belong to several overlaid graphs — mechanical, airflow, coolant,
lubrication, electrical. This layer queries one overlay and traces flow through it, so
diagnosis can reason about what actually passes between components (air, coolant, oil)
rather than a single generic tree.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .refmodels import Component, ComponentRelationship, System, VehicleVariant


def _components(session: Session, variant_id: int) -> dict[int, Component]:
    return {c.id: c for c in session.scalars(
        select(Component).join(System).where(System.variant_id == variant_id))}


def overlay_edges(session: Session, variant_slug: str, domain: str) -> list[dict]:
    """All edges of one overlay (domain), as {from, to, relation, medium, direction}."""
    variant = session.scalar(select(VehicleVariant).where(VehicleVariant.slug == variant_slug))
    if variant is None:
        return []
    comps = _components(session, variant.id)
    ids = set(comps)
    out = []
    for e in session.scalars(select(ComponentRelationship).where(
            ComponentRelationship.domain == domain)):
        if e.from_component_id in ids and e.to_component_id in ids:
            out.append({"from": comps[e.from_component_id].slug, "to": comps[e.to_component_id].slug,
                        "from_name": comps[e.from_component_id].name,
                        "to_name": comps[e.to_component_id].name,
                        "relation": e.relation, "medium": e.medium, "direction": e.direction})
    return out


def domains(session: Session, variant_slug: str) -> list[str]:
    variant = session.scalar(select(VehicleVariant).where(VehicleVariant.slug == variant_slug))
    if variant is None:
        return []
    comp_ids = set(_components(session, variant.id))
    found = set()
    for e in session.scalars(select(ComponentRelationship)):
        if e.from_component_id in comp_ids and e.to_component_id in comp_ids:
            found.add(e.domain)
    return sorted(found)


def trace(session: Session, variant_slug: str, domain: str, start: str,
          _seen: set | None = None) -> list[str]:
    """Trace flow downstream from `start` within one overlay (following forward edges).

    Cycle-safe (a coolant loop returns to the pump). Returns the ordered slugs visited.
    """
    edges = overlay_edges(session, variant_slug, domain)
    adj: dict[str, list[str]] = {}
    for e in edges:
        adj.setdefault(e["from"], []).append(e["to"])
        if e["direction"] == "bidirectional":
            adj.setdefault(e["to"], []).append(e["from"])
    order: list[str] = []
    seen: set[str] = set()

    def walk(node: str) -> None:
        if node in seen:
            return
        seen.add(node)
        order.append(node)
        for nxt in adj.get(node, []):
            walk(nxt)

    walk(start)
    return order
