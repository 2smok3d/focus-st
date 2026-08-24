"""ANOM — anomaly detection over the Observation V2 history.

The compendium's headline ML ask is CAN/OBD anomaly detection (autoencoders, LSTMs, SHAP).
Rebuilt *in this platform's grain*: a pure, deterministic, dependency-light detector that is
**explainable by construction** — every flagged point carries the baseline it broke and the
score it crossed, reproducible offline in the cockpit. No heavy ML dependency, sub-second in CI.

Method: the robust modified z-score (Iglewicz & Hoaglin) — median and median-absolute-deviation
(MAD), which a few outliers cannot drag around the way mean/σ can. A point is anomalous when
`|0.6745·(v − median) / MAD|` exceeds `Z_THRESH`. When MAD collapses (a near-constant series),
fall back to mean/σ; a truly constant series has no anomalies.

Confounder-aware, like DI trends: a series measured across a wide ambient-temperature range is
flagged so a swing that merely tracks the weather is not mistaken for a fault.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

MIN_POINTS = 4          # need a baseline plus room for an outlier to stand out
Z_THRESH = 3.5          # modified z-score cut (Iglewicz & Hoaglin)
MAD_SCALE = 0.6745      # makes the modified z comparable to a standard z under normality
EPS = 1e-9


@dataclass(frozen=True)
class Anomaly:
    x: float            # the point's time coordinate (days from series start), for locating it
    value: float
    score: float        # signed modified z-score
    deviation: float    # value − baseline
    direction: str      # "high" | "low"

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AnomalyResult:
    n: int
    baseline: float | None      # the robust centre (median, or mean in the fallback)
    spread: float | None        # MAD (or σ in the fallback)
    method: str                 # "mad" | "std" | "none"
    threshold: float
    anomalies: list[Anomaly]

    def as_dict(self) -> dict:
        d = asdict(self)
        d["anomalies"] = [a.as_dict() for a in self.anomalies]
        d["count"] = len(self.anomalies)
        return d


def _median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def detect_anomalies(points: list[tuple[float, float]], *,
                     threshold: float = Z_THRESH) -> AnomalyResult:
    """Flag robust outliers in a series. `points` is [(x, value), ...]; x is only carried
    through for locating the flag (days from start, say). Pure — no DB, no clock."""
    pts = [(float(x), float(v)) for x, v in points if x is not None and v is not None]
    n = len(pts)
    if n < MIN_POINTS:
        return AnomalyResult(n=n, baseline=None, spread=None, method="none",
                             threshold=threshold, anomalies=[])

    values = [v for _, v in pts]
    med = _median(values)
    mad = _median([abs(v - med) for v in values])

    if mad > EPS:
        method, centre, spread = "mad", med, mad
        def score(v: float) -> float:
            return MAD_SCALE * (v - med) / mad
    else:
        # MAD collapses when a majority of points are identical (a near-constant series with a
        # lone spike). Iglewicz & Hoaglin's fallback is the *mean* absolute deviation about the
        # median — still robust (median-centred), but non-zero as long as one point differs, so
        # the spike is caught. A truly constant series (MeanAD == 0) flags nothing.
        mean_ad = sum(abs(v - med) for v in values) / n
        if mean_ad <= EPS:
            return AnomalyResult(n=n, baseline=round(med, 4), spread=0.0, method="none",
                                 threshold=threshold, anomalies=[])
        method, centre, spread = "meanad", med, mean_ad
        def score(v: float) -> float:
            return (v - med) / (1.253314 * mean_ad)

    flagged: list[Anomaly] = []
    for x, v in pts:
        z = score(v)
        if abs(z) >= threshold:
            flagged.append(Anomaly(x=round(x, 4), value=round(v, 4), score=round(z, 3),
                                   deviation=round(v - centre, 4),
                                   direction="high" if z > 0 else "low"))
    return AnomalyResult(n=n, baseline=round(centre, 4), spread=round(spread, 4),
                         method=method, threshold=threshold, anomalies=flagged)


# ---- service: scan a machine's observation series and report the anomalous ones ----
def component_anomalies(session, vehicle_id: int) -> list[dict]:
    """Group a machine's observations into (component, metric, operating-condition) series
    and run the robust detector over each. Returns series that carry at least one anomaly,
    most-anomalous first, each with a plain-language summary and DI's confounder flag."""
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
        res = detect_anomalies(points)
        if not res.anomalies:
            continue
        ambients = []
        for o in obs:
            if o.environment_id:
                env = session.get(EnvironmentSnapshot, o.environment_id)
                if env and env.ambient_c is not None:
                    ambients.append(env.ambient_c)
        confounded = bool(ambients) and (max(ambients) - min(ambients) > 15.0)
        d = res.as_dict()
        d.update({"subject": slug, "metric": otype, "condition": cond, "unit": unit,
                  "confounded": confounded,
                  "summary": _summary(slug, otype, unit, res, confounded)})
        out.append(d)

    out.sort(key=lambda d: -d["count"])
    return out


def _summary(slug: str, metric: str, unit: str, res: AnomalyResult, confounded: bool) -> str:
    u = f" {unit}" if unit else ""
    n = len(res.anomalies)
    worst = max(res.anomalies, key=lambda a: abs(a.score))
    noun = "anomaly" if n == 1 else "anomalies"
    base = (f"{slug} {metric}: {n} {noun} vs baseline {res.baseline:.1f}{u} — "
            f"worst {worst.value:.1f}{u} ({worst.direction}, z={worst.score:.1f}).")
    if confounded:
        base += " ⚠ ambient temperature varied widely — confirm before trusting."
    return base
