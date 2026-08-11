from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import Iterable

from .domain import ServiceRecord, ServiceTask


@dataclass(frozen=True)
class DueStatus:
    task_id: str
    name: str
    status: str
    miles_remaining: int | None
    months_remaining: int | None
    last_mileage: int | None
    last_date: str | None
    reason: str


def _months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month) - (1 if b.day < a.day else 0)


def evaluate_task(task: ServiceTask, records: Iterable[ServiceRecord], current_mileage: int, today: date | None = None, severe_use: bool = False) -> DueStatus:
    today = today or date.today()
    matching = [r for r in records if r.task_id == task.id]
    last = max(matching, key=lambda r: (r.service_date, r.mileage_mi), default=None)

    mi_interval = task.severe_interval_miles if severe_use and task.severe_interval_miles else task.interval_miles
    mo_interval = task.severe_interval_months if severe_use and task.severe_interval_months else task.interval_months

    miles_remaining = None
    months_remaining = None
    if mi_interval is not None:
        base = last.mileage_mi if last else 0
        miles_remaining = base + mi_interval - current_mileage
    if mo_interval is not None:
        if last:
            elapsed = _months_between(last.service_date, today)
            months_remaining = mo_interval - elapsed
        else:
            months_remaining = 0

    overdue = (miles_remaining is not None and miles_remaining < 0) or (months_remaining is not None and months_remaining < 0)
    due_now = (miles_remaining is not None and miles_remaining <= 0) or (months_remaining is not None and months_remaining <= 0)
    due_soon = (miles_remaining is not None and 0 < miles_remaining <= max(500, int((mi_interval or 0) * .10))) or (
        months_remaining is not None and 0 < months_remaining <= 1
    )

    if overdue:
        status = "overdue"
    elif due_now:
        status = "due"
    elif due_soon:
        status = "due_soon"
    else:
        status = "ok"

    reason_bits: list[str] = []
    if miles_remaining is not None:
        reason_bits.append(f"{miles_remaining:+d} mi to interval")
    if months_remaining is not None:
        reason_bits.append(f"{months_remaining:+d} months to interval")
    if not last:
        reason_bits.append("no matching completed service record")

    return DueStatus(
        task_id=task.id,
        name=task.name,
        status=status,
        miles_remaining=miles_remaining,
        months_remaining=months_remaining,
        last_mileage=last.mileage_mi if last else None,
        last_date=last.service_date.isoformat() if last else None,
        reason="; ".join(reason_bits),
    )


# Conservative placeholders are intentionally distinguished from Ford-published requirements.
# Mature records must link source claims before a task is labelled OEM-required.
SEED_TASKS = [
    ServiceTask(id="engine_oil_filter", name="Engine oil & filter", system="lubrication", interval_miles=5000, interval_months=6, severe_interval_miles=3500, severe_interval_months=6, oem_required=False, notes="Garage reliability interval placeholder; use Ford oil-life monitor / exact owner-manual rules as authoritative service requirement."),
    ServiceTask(id="spark_plugs_inspect", name="Spark plug condition / gap inspection", system="ignition", interval_miles=10000, interval_months=12, severe_interval_miles=7500, severe_interval_months=12, oem_required=False, notes="Modified/tuned-car inspection strategy, not presented as Ford scheduled replacement interval."),
    ServiceTask(id="tire_measurements", name="Tire pressure, tread & damage inspection", system="wheels_tires", interval_miles=5000, interval_months=3, oem_required=False),
    ServiceTask(id="brake_measurements", name="Brake pad / rotor measurement", system="brakes", interval_miles=10000, interval_months=6, oem_required=False),
    ServiceTask(id="charge_air_inspection", name="Charge-air tract / clamps / couplers inspection", system="forced_induction", interval_miles=10000, interval_months=12, severe_interval_miles=5000, severe_interval_months=6, oem_required=False, notes="Modification-aware reliability inspection."),
    ServiceTask(id="pcv_inspection", name="PCV / crankcase-ventilation inspection", system="emissions", interval_miles=10000, interval_months=12, severe_interval_miles=5000, severe_interval_months=6, oem_required=False, notes="Elevated because this vehicle has P04DB history."),
    ServiceTask(id="cooling_inspection", name="Cooling-system visual / level / leak inspection", system="cooling", interval_miles=5000, interval_months=3, oem_required=False),
]


def maintenance_dashboard(current_mileage: int, records: Iterable[ServiceRecord], severe_use: bool = False) -> list[dict]:
    result = [evaluate_task(t, records, current_mileage, severe_use=severe_use) for t in SEED_TASKS]
    rank = {"overdue": 0, "due": 1, "due_soon": 2, "ok": 3}
    result.sort(key=lambda x: (rank[x.status], x.name))
    return [asdict(x) for x in result]
