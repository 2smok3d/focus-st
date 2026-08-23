"""Data intelligence — degradation trends over the Observation V2 history.

A trend is a time-ordered series of observations of the *same* thing (one component,
one metric, one operating condition) fitted to a straight line. The pure engine
(`fit_trend`) is DB-free and does the maths — slope, R², direction, and a drift
classification; the service layer (`component_trends`) groups a machine's observations
into series and reports the notable ones.

Deliberately metric-agnostic: it reports *direction* and *drift strength*, not
"good/bad" — whether a falling number is degradation (compression) or improvement
(blow-by) depends on the metric, which the caller knows. Confounder-aware: a series
measured across a wide ambient-temperature range is flagged, because temperature can
masquerade as drift.
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, asdict

# A series needs at least this many points to fit, and this much fitted change (as a
# fraction of the mean) with this much correlation to count as real drift rather than noise.
MIN_POINTS = 3
DRIFT_PCT = 0.05      # ≥5% fitted change end-to-end
DRIFT_R2 = 0.5        # linear fit explains ≥50% of the variance
FLAT_EPS = 1e-9
AMBIENT_SPREAD_C = 15.0   # a series spanning more than this in ambient °C is confounder-flagged


@dataclass(frozen=True)
class Trend:
    n: int
    slope_per_day: float
    intercept: float
    r2: float
    direction: str          # "rising" | "falling" | "flat"
    span_days: float
    first: float
    last_fitted: float
    delta: float            # fitted end-to-end change
    pct_change: float       # delta / mean, signed
    drift: bool             # notable, sustained change (not noise)
    mean: float

    def as_dict(self) -> dict:
        return asdict(self)


def fit_trend(points: list[tuple[float, float]]) -> Trend | None:
    """Fit value ~ x by ordinary least squares. `points` is [(x, value), ...] with x in
    days (or any monotone unit). Returns None if there are too few points or no spread in x.
    Pure — no DB, no clock."""
    pts = [(float(x), float(y)) for x, y in points if x is not None and y is not None]
    n = len(pts)
    if n < MIN_POINTS:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0 = min(xs)
    xs = [x - x0 for x in xs]                       # anchor at 0 for a meaningful intercept
    span = max(xs)
    if span <= FLAT_EPS:                            # all at one instant — no time axis
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= FLAT_EPS:
        return None
    slope = sxy / sxx
    intercept = my - slope * mx
    r2 = (sxy * sxy) / (sxx * syy) if syy > FLAT_EPS else 1.0
    first_fit = intercept
    last_fit = intercept + slope * span
    delta = last_fit - first_fit
    pct = delta / my if abs(my) > FLAT_EPS else 0.0
    direction = "flat"
    if slope > FLAT_EPS and abs(pct) >= FLAT_EPS:
        direction = "rising"
    elif slope < -FLAT_EPS and abs(pct) >= FLAT_EPS:
        direction = "falling"
    drift = abs(pct) >= DRIFT_PCT and r2 >= DRIFT_R2 and direction != "flat"
    return Trend(n=n, slope_per_day=slope, intercept=intercept, r2=round(r2, 4),
                 direction=direction, span_days=round(span, 3), first=round(first_fit, 4),
                 last_fitted=round(last_fit, 4), delta=round(delta, 4),
                 pct_change=round(pct, 4), drift=drift, mean=round(my, 4))


# ---- service: group a machine's observations into series and fit each ----------
def component_trends(session, vehicle_id: int) -> list[dict]:
    """Fit a trend for every (component, metric, operating-condition) series with enough
    history for one machine. Returns the notable (drifting) series first, each with a
    plain-language summary and a confounder flag when ambient varied widely."""
    from sqlalchemy import select
    from .obsmodels import EnvironmentSnapshot, Observation

    rows = session.scalars(
        select(Observation).where(
            Observation.vehicle_id == vehicle_id, Observation.value.is_not(None))
        .order_by(Observation.observed_at, Observation.id)
    ).all()

    series: dict[tuple, list[Observation]] = {}
    for o in rows:
        key = (o.subject_slug or "?", o.obs_type or "?", o.operating_condition or "?", o.unit or "")
        series.setdefault(key, []).append(o)

    out: list[dict] = []
    for (slug, otype, cond, unit), obs in series.items():
        if len(obs) < MIN_POINTS:
            continue
        t0 = obs[0].observed_at
        points = [((o.observed_at - t0).total_seconds() / 86400.0, o.value) for o in obs]
        tr = fit_trend(points)
        if tr is None:
            continue
        # confounder: did ambient temperature swing across the series?
        ambients = []
        for o in obs:
            if o.environment_id:
                env = session.get(EnvironmentSnapshot, o.environment_id)
                if env and env.ambient_c is not None:
                    ambients.append(env.ambient_c)
        confounded = bool(ambients) and (max(ambients) - min(ambients) > AMBIENT_SPREAD_C)
        d = tr.as_dict()
        d.update({"subject": slug, "metric": otype, "condition": cond, "unit": unit,
                  "confounded": confounded,
                  "summary": _summary(slug, otype, unit, tr, confounded)})
        out.append(d)

    # notable first, then by magnitude of change
    out.sort(key=lambda d: (not d["drift"], -abs(d["pct_change"])))
    return out


def _summary(slug: str, metric: str, unit: str, tr: Trend, confounded: bool) -> str:
    if tr.direction == "flat" or not tr.drift:
        base = f"{slug} {metric} stable ({tr.n} obs over {tr.span_days:.0f}d)."
    else:
        pct = abs(tr.pct_change) * 100
        u = f" {unit}" if unit else ""
        base = (f"{slug} {metric} {tr.direction} {pct:.0f}% over {tr.span_days:.0f}d "
                f"({tr.first:.1f}→{tr.last_fitted:.1f}{u}, R²={tr.r2:.2f}).")
    if confounded:
        base += " ⚠ ambient temperature varied widely — confirm before trusting the trend."
    return base
