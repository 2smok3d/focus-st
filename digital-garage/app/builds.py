"""Build Lab + Constraint Solver (Milestone D).

A build scenario is a forked exploration of a goal — it lists what you *want*, and the
constraint-rule library computes the rest: what each item REQUIRES, what it RECOMMENDS,
and what CONFLICTS. Builds are therefore *computed*, not hard-coded shopping lists.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .engmodels import RELATIONS, BuildItem, BuildScenario, ConstraintRule
from .models import Vehicle

# Seed rules for the Focus ST: (subject, relation, object, note).
RULES = [
    ("big-turbo", "requires", "tune", "A larger turbo must be tuned to run safely."),
    ("big-turbo", "requires", "fueling", "Bigger airflow needs more fuel (injectors/HPFP)."),
    ("big-turbo", "requires", "intercooler", "Higher output needs adequate charge cooling."),
    ("big-turbo", "recommends", "oil-cooler", "Thermal headroom for sustained load."),
    ("big-turbo", "recommends", "colder-plugs", "Colder heat range under more boost."),
    ("big-turbo", "conflicts", "stock-charge-pipe", "Stock charge pipe can pop off under boost."),
    ("e85", "requires", "fueling", "E85 needs ~30% more fuel flow."),
    ("e85", "recommends", "tune", "Ethanol content must be tuned for."),
    ("stage-2", "requires", "tune", "Stage-2 hardware requires a matching calibration."),
    ("stage-2", "recommends", "intercooler", "Charge cooling for the extra output."),
]


def seed_constraints(session: Session) -> str:
    n = 0
    for subj, rel, obj, note in RULES:
        if session.scalar(select(ConstraintRule).where(
                ConstraintRule.subject_tag == subj, ConstraintRule.relation == rel,
                ConstraintRule.object_tag == obj)) is None:
            session.add(ConstraintRule(subject_tag=subj, relation=rel, object_tag=obj, note=note))
            n += 1
    session.flush()
    return f"Constraint rules seeded: +{n} ({len(RULES)} total)."


def new_scenario(session: Session, vehicle: Vehicle, name: str, *, goal: str | None = None,
                 code: str | None = None) -> BuildScenario:
    sc = BuildScenario(vehicle_id=vehicle.id, name=name, goal=goal, code=code)
    session.add(sc)
    session.flush()
    return sc


def add_item(session: Session, scenario: BuildScenario, tag: str, name: str, *,
             component_slug: str | None = None, est_cost=None, note: str | None = None) -> BuildItem:
    row = BuildItem(scenario_id=scenario.id, tag=tag, name=name, component_slug=component_slug,
                    est_cost=est_cost, note=note)
    session.add(row)
    session.flush()
    return row


def solve(session: Session, scenario_id: int) -> dict:
    """Compute a scenario against the constraint rules.

    Returns satisfied/unmet REQUIREs, missing RECOMMENDs, active CONFLICTs, an estimated
    cost, and a readiness verdict — all derived, not hard-coded.
    """
    items = session.scalars(select(BuildItem).where(BuildItem.scenario_id == scenario_id)).all()
    present = {it.tag for it in items}
    rules = session.scalars(select(ConstraintRule)).all()

    requires_met, requires_unmet, recommends, conflicts = [], [], [], []
    for r in rules:
        if r.subject_tag not in present:
            continue
        if r.relation == "requires":
            (requires_met if r.object_tag in present else requires_unmet).append(
                {"subject": r.subject_tag, "object": r.object_tag, "note": r.note})
        elif r.relation == "recommends" and r.object_tag not in present:
            recommends.append({"subject": r.subject_tag, "object": r.object_tag, "note": r.note})
        elif r.relation in ("conflicts", "incompatible") and r.object_tag in present:
            conflicts.append({"subject": r.subject_tag, "object": r.object_tag,
                              "relation": r.relation, "note": r.note})

    est_cost = float(sum((it.est_cost or 0) for it in items))
    valid = not requires_unmet and not conflicts
    return {
        "scenario_id": scenario_id,
        "items": [{"tag": it.tag, "name": it.name, "component": it.component_slug,
                   "est_cost": float(it.est_cost) if it.est_cost is not None else None} for it in items],
        "requires_met": requires_met, "requires_unmet": requires_unmet,
        "recommends": recommends, "conflicts": conflicts,
        "est_cost": est_cost, "valid": valid,
    }


def list_scenarios(session: Session, vehicle_id: int) -> list[dict]:
    out = []
    for sc in session.scalars(select(BuildScenario).where(
            BuildScenario.vehicle_id == vehicle_id).order_by(BuildScenario.id)):
        r = solve(session, sc.id)
        out.append({"id": sc.id, "code": sc.code, "name": sc.name, "goal": sc.goal,
                    "valid": r["valid"], "unmet": len(r["requires_unmet"]),
                    "conflicts": len(r["conflicts"]), "est_cost": r["est_cost"]})
    return out
