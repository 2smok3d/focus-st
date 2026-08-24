"""RUL — remaining-useful-life / predictive maintenance (extends MAINT5).

MAINT5 says *what state* each maintenance item is in (ok / due_soon / due / overdue). RUL
answers the next question a person actually asks — **when**: it fits the machine's own usage
rate (miles/day) from its odometer history and projects each interval's due-by *date*, so a
mileage limit and a time limit are compared on one axis (whichever arrives first drives the
projection).

Honest and dependency-light, in this platform's grain: the usage rate is a plain OLS fit
(reusing DI's `fit_trend`), the projection is arithmetic, and every output is a *projection*
— clearly labelled, never asserted as fact. If the machine has too little odometer history to
establish a rate, mileage-based items simply have no date and say so.
"""
from __future__ import annotations

import datetime as dt

DAYS_PER_MONTH = 30.44
HORIZON_DAYS = 90          # "coming up" window for the predictive rollup


def usage_rate(points: list[tuple[float, float]]) -> float | None:
    """Miles per day from odometer history. `points` is [(day, miles), ...]. Returns the
    fitted slope when it is positive and well-formed, else None (unknown rate). Pure."""
    from .trends import fit_trend

    tr = fit_trend(points)
    if tr is None or tr.slope_per_day <= 0:
        return None
    return tr.slope_per_day


def project_due(miles_remaining: int | None, months_remaining: float | None,
                miles_per_day: float | None, *, today: dt.date | None = None) -> dict | None:
    """Project a single item's due date from whichever limit arrives first. Pure —
    returns {projected_date, days_remaining, basis} or None when nothing can be projected."""
    today = today or dt.date.today()
    candidates: list[tuple[float, str]] = []
    if miles_remaining is not None and miles_per_day and miles_per_day > 0:
        candidates.append((miles_remaining / miles_per_day, "mileage"))
    if months_remaining is not None:
        candidates.append((months_remaining * DAYS_PER_MONTH, "time"))
    if not candidates:
        return None
    days, basis = min(candidates, key=lambda c: c[0])   # soonest limit drives
    return {"projected_date": (today + dt.timedelta(days=round(days))).isoformat(),
            "days_remaining": round(days), "basis": basis}


# ---- service: project every logged interval for one machine --------------------
def maintenance_rul(session, vehicle_id: int, today: dt.date | None = None) -> dict:
    """Fit the machine's usage rate and project a due-by date for every maintenance item
    with enough information. Read-only. A projection, not a claim — labelled as such."""
    import datetime as _dt

    from sqlalchemy import select

    from . import service
    from .models import OdometerReading

    today = today or _dt.date.today()

    readings = session.scalars(
        select(OdometerReading).where(OdometerReading.vehicle_id == vehicle_id)
        .order_by(OdometerReading.recorded_at, OdometerReading.id)
    ).all()
    rate = None
    span_days = 0.0
    if len(readings) >= 3:
        t0 = readings[0].recorded_at
        pts = [((r.recorded_at - t0).total_seconds() / 86400.0, float(r.miles)) for r in readings]
        span_days = pts[-1][0]
        rate = usage_rate(pts)

    usage = {"miles_per_day": round(rate, 2) if rate else None,
             "miles_per_year": round(rate * 365.0) if rate else None,
             "readings": len(readings), "span_days": round(span_days, 1),
             "known": rate is not None}

    current_miles = service.latest_odometer(session, vehicle_id)
    projected: list[dict] = []
    for r in service.due_list(session, vehicle_id, current_miles=current_miles, today=today):
        # only items we actually have history for can be projected
        if r["last_miles"] is None and r["last_date"] is None:
            continue
        p = project_due(r["miles_remaining"], r["months_remaining"], rate, today=today)
        if p is None:
            continue
        projected.append({"item": r["item"], "status": r["status"].replace("-", "_"),
                          "miles_remaining": r["miles_remaining"],
                          "months_remaining": r["months_remaining"],
                          "verification": r.get("verification"), **p})

    projected.sort(key=lambda x: x["days_remaining"])
    coming_up = sum(1 for p in projected if 0 <= p["days_remaining"] <= HORIZON_DAYS)
    overdue_proj = sum(1 for p in projected if p["days_remaining"] < 0)
    return {"usage": usage, "horizon_days": HORIZON_DAYS,
            "coming_up": coming_up, "overdue": overdue_proj,
            "projected": projected}
