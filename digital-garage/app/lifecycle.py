"""Physical-component lifecycle service (V7).

A physical component is tracked independently of any machine: it accrues usage, is
installed and removed (possibly across different machines), is inspected, and keeps its
whole history. Removing it from a machine never deletes it — it returns to inventory.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from .lcmodels import (
    INSPECTION_RESULTS,
    ComponentInspection,
    ComponentInstallation,
    PhysicalComponent,
)
from .models import Vehicle


def register(session: Session, code: str, name: str, *, component_slug: str | None = None,
             manufacturer: str | None = None, part_number: str | None = None,
             note: str | None = None) -> PhysicalComponent:
    pc = session.scalar(select(PhysicalComponent).where(PhysicalComponent.code == code))
    if pc is None:
        pc = PhysicalComponent(code=code, name=name, component_slug=component_slug,
                               manufacturer=manufacturer, part_number=part_number, note=note)
        session.add(pc)
        session.flush()
    return pc


def _current_install(session: Session, pc_id: int) -> ComponentInstallation | None:
    return session.scalar(select(ComponentInstallation).where(
        ComponentInstallation.physical_component_id == pc_id,
        ComponentInstallation.removed_at.is_(None)))


def install(session: Session, pc: PhysicalComponent, vehicle: Vehicle, slot_slug: str,
            *, at: dt.datetime | None = None, note: str | None = None) -> ComponentInstallation:
    """Install the physical component into a machine slot. Auto-removes any prior
    open installation (a part can only be in one place at a time)."""
    when = at or dt.datetime.now(dt.timezone.utc)
    prev = _current_install(session, pc.id)
    if prev is not None:
        prev.removed_at = when
    row = ComponentInstallation(physical_component_id=pc.id, vehicle_id=vehicle.id,
                                slot_slug=slot_slug, installed_at=when, note=note)
    session.add(row)
    pc.status = "in_service"
    session.flush()
    return row


def remove(session: Session, pc: PhysicalComponent, *, at: dt.datetime | None = None,
           to_status: str = "in_inventory", note: str | None = None) -> None:
    """Remove from its machine. The physical component persists (goes to inventory)."""
    when = at or dt.datetime.now(dt.timezone.utc)
    cur = _current_install(session, pc.id)
    if cur is not None:
        cur.removed_at = when
        if note:
            cur.note = (cur.note + " | " if cur.note else "") + note
    pc.status = to_status
    session.flush()


def add_usage(session: Session, pc: PhysicalComponent, *, hours: float = 0.0,
              sessions: int = 0, miles: int = 0, cycles: int = 0) -> PhysicalComponent:
    pc.hours = (pc.hours or 0) + hours
    pc.sessions = (pc.sessions or 0) + sessions
    pc.miles = (pc.miles or 0) + miles
    pc.cycles = (pc.cycles or 0) + cycles
    session.flush()
    return pc


def inspect(session: Session, pc: PhysicalComponent, result: str, *, value: float | None = None,
            unit: str | None = None, method: str | None = None,
            at: dt.datetime | None = None, note: str | None = None) -> ComponentInspection:
    if result not in INSPECTION_RESULTS:
        raise ValueError(f"invalid inspection result '{result}'")
    if value is not None and unit is not None:
        from . import quantities as q
        q.to_canonical(value, unit)  # validate the measurement unit
    row = ComponentInspection(physical_component_id=pc.id, result=result, value=value, unit=unit,
                              method=method, inspected_at=at or dt.datetime.now(dt.timezone.utc),
                              note=note)
    session.add(row)
    pc.condition = result  # latest inspection sets current condition
    session.flush()
    return row


def lifecycle(session: Session, code: str) -> dict | None:
    pc = session.scalar(select(PhysicalComponent).where(PhysicalComponent.code == code))
    if pc is None:
        return None
    installs = session.scalars(select(ComponentInstallation).where(
        ComponentInstallation.physical_component_id == pc.id)
        .order_by(ComponentInstallation.installed_at)).all()
    inspections = session.scalars(select(ComponentInspection).where(
        ComponentInspection.physical_component_id == pc.id)
        .order_by(ComponentInspection.inspected_at)).all()
    veh = {v.id: v for v in session.scalars(select(Vehicle))}
    return {
        "code": pc.code, "name": pc.name, "component": pc.component_slug,
        "status": pc.status, "condition": pc.condition,
        "usage": {"hours": pc.hours, "sessions": pc.sessions, "miles": pc.miles, "cycles": pc.cycles},
        "installations": [{
            "vehicle": (veh[i.vehicle_id].vin if i.vehicle_id in veh else i.vehicle_id),
            "slot": i.slot_slug,
            "installed_at": i.installed_at.isoformat() if i.installed_at else None,
            "removed_at": i.removed_at.isoformat() if i.removed_at else None,
            "current": i.removed_at is None,
        } for i in installs],
        "inspections": [{
            "result": ins.result, "value": ins.value, "unit": ins.unit, "method": ins.method,
            "at": ins.inspected_at.isoformat() if ins.inspected_at else None,
        } for ins in inspections],
    }
