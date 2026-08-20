"""Workshop Engine service (Milestone C) — work orders, job readiness, and mandatory
post-repair verification.

Two commitments from the roadmap:
  * Job readiness (#13): before work starts, compute what fraction of the required
    parts / tools / procedure is in hand — "READY: 82%" with the specific blockers.
  * Repair verification (#16): "part replaced" is NEVER "problem fixed". Completing the
    work moves a work order to VERIFICATION_REQUIRED, not VERIFIED. Only a passing
    post-repair verification promotes it — enforced through the Domain Constitution's
    FINDING → VERIFIED_REPAIR bridge — and closing it writes an automatic service event.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ServiceEvent, Vehicle
from .womodels import (
    VERIFY_RESULT,
    WorkOrder,
    WorkOrderPart,
    WorkOrderTask,
    WorkOrderTool,
    WorkOrderVerification,
)


def open_work_order(session: Session, vehicle: Vehicle, title: str, *, code: str | None = None,
                    component_slug: str | None = None, from_finding_id: int | None = None,
                    note: str | None = None) -> WorkOrder:
    wo = WorkOrder(vehicle_id=vehicle.id, title=title, code=code, component_slug=component_slug,
                   from_finding_id=from_finding_id, note=note, status="draft", repair_state="planned")
    session.add(wo)
    session.flush()
    return wo


def add_task(session, wo, description, *, seq=None):
    row = WorkOrderTask(work_order_id=wo.id, description=description,
                        seq=seq if seq is not None else len(wo.tasks))
    session.add(row); session.flush(); return row


def add_part(session, wo, name, *, part_number=None, qty=1, available=False):
    row = WorkOrderPart(work_order_id=wo.id, name=name, part_number=part_number,
                        qty=qty, available=available)
    session.add(row); session.flush(); return row


def add_tool(session, wo, name, *, available=False):
    row = WorkOrderTool(work_order_id=wo.id, name=name, available=available)
    session.add(row); session.flush(); return row


def job_readiness(session: Session, wo_id: int) -> dict:
    """Fraction of required parts/tools/procedure in hand, with the specific blockers."""
    parts = session.scalars(select(WorkOrderPart).where(WorkOrderPart.work_order_id == wo_id)).all()
    tools = session.scalars(select(WorkOrderTool).where(WorkOrderTool.work_order_id == wo_id)).all()
    has_procedure = session.scalar(select(WorkOrderTask.id).where(
        WorkOrderTask.work_order_id == wo_id)) is not None

    items = len(parts) + len(tools) + 1                       # +1 for the procedure item
    satisfied = sum(1 for p in parts if p.available) + sum(1 for t in tools if t.available) \
        + (1 if has_procedure else 0)
    blockers = [f"part: {p.name}" for p in parts if not p.available]
    blockers += [f"tool: {t.name}" for t in tools if not t.available]
    if not has_procedure:
        blockers.append("procedure: none defined")
    pct = round(100 * satisfied / items) if items else 0
    return {"ready_pct": pct, "ready": pct == 100, "blockers": blockers,
            "items": items, "satisfied": satisfied}


def mark_ready(session: Session, wo: WorkOrder) -> WorkOrder:
    """DRAFT → READY when everything is in hand, else BLOCKED (with blockers listed)."""
    r = job_readiness(session, wo.id)
    wo.status = "ready" if r["ready"] else "blocked"
    session.flush()
    return wo


def start(session: Session, wo: WorkOrder) -> WorkOrder:
    if wo.status not in ("ready", "blocked", "draft"):
        raise ValueError(f"cannot start a work order in status '{wo.status}'")
    wo.status = "in_progress"
    session.flush()
    return wo


def complete_task(session: Session, task_id: int) -> WorkOrderTask:
    t = session.get(WorkOrderTask, task_id)
    if t is None:
        raise LookupError(f"no task #{task_id}")
    t.done = True
    session.flush()
    return t


def complete_work(session: Session, wo: WorkOrder) -> WorkOrder:
    """Work done → VERIFICATION_REQUIRED. Repair performed, outcome not yet known."""
    if wo.status != "in_progress":
        raise ValueError(f"cannot complete work from status '{wo.status}'")
    wo.status = "verification_required"
    wo.repair_state = "repair_performed"
    session.flush()
    return wo


def verify(session: Session, wo: WorkOrder, test: str, result: str, *,
           observation_id: int | None = None, note: str | None = None) -> WorkOrderVerification:
    """Record a post-repair verification. A PASS promotes the work order to VERIFIED —
    through the constitution's FINDING → VERIFIED_REPAIR bridge; a FAIL keeps it in
    VERIFICATION_REQUIRED (the repair did not fix the problem)."""
    if result not in VERIFY_RESULT:
        raise ValueError(f"invalid result '{result}'")
    if wo.status not in ("work_complete", "verification_required"):
        raise ValueError(f"nothing to verify from status '{wo.status}'")
    row = WorkOrderVerification(work_order_id=wo.id, test=test, result=result,
                                observation_id=observation_id, note=note)
    session.add(row)
    if result == "pass":
        from . import epistemics as ep
        ep.promote(ep.Kind.FINDING, ep.Kind.VERIFIED_REPAIR, ep.POST_REPAIR_VERIFICATION)
        wo.status = "verified"
        wo.repair_state = "repair_verified"
    session.flush()
    return row


def close(session: Session, wo: WorkOrder, *, miles: int | None = None,
          cost=None, vendor: str | None = None) -> ServiceEvent:
    """Close a VERIFIED work order and write the automatic service record."""
    if wo.status != "verified":
        raise ValueError("a work order can only be closed after it is VERIFIED "
                         f"(status is '{wo.status}').")
    wo.status = "closed"
    wo.closed_at = dt.datetime.now(dt.timezone.utc)
    ev = ServiceEvent(vehicle_id=wo.vehicle_id, item=wo.title, performed_at=dt.date.today(),
                      miles=miles, cost=cost, vendor=vendor,
                      note=(wo.outcome or f"Work order {wo.code or wo.id} — verified repair."))
    session.add(ev)
    session.flush()
    return ev


def work_order_view(session: Session, wo_id: int) -> dict | None:
    wo = session.get(WorkOrder, wo_id)
    if wo is None:
        return None
    r = job_readiness(session, wo_id)
    return {
        "id": wo.id, "code": wo.code, "title": wo.title, "status": wo.status,
        "repair_state": wo.repair_state, "component": wo.component_slug, "outcome": wo.outcome,
        "readiness": r,
        "tasks": [{"id": t.id, "seq": t.seq, "description": t.description, "done": t.done}
                  for t in sorted(wo.tasks, key=lambda t: t.seq)],
        "parts": [{"name": p.name, "part_number": p.part_number, "qty": p.qty,
                   "available": p.available} for p in wo.parts],
        "tools": [{"name": t.name, "available": t.available} for t in wo.tools],
        "verifications": [{"test": v.test, "result": v.result, "note": v.note}
                          for v in wo.verifications],
    }


def list_work_orders(session: Session, vehicle_id: int | None = None) -> list[dict]:
    stmt = select(WorkOrder).order_by(WorkOrder.id)
    if vehicle_id is not None:
        stmt = stmt.where(WorkOrder.vehicle_id == vehicle_id)
    out = []
    for wo in session.scalars(stmt):
        r = job_readiness(session, wo.id)
        out.append({"id": wo.id, "code": wo.code, "title": wo.title, "status": wo.status,
                    "repair_state": wo.repair_state, "ready_pct": r["ready_pct"]})
    return out
