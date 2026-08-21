"""Telemetry V2 (Milestone E) — normalize → derive → detect events.

The heart (frame building, derived signals, event detection) is **pure** so it runs in
CI without a database. Raw measurements are never mutated; this layer projects them into
time-aligned frames, computes derived channels (boost error, charge-temp delta, …), and
detects operating events (WOT_PULL, KNOCK_EVENT, OVER_TEMP, BOOST_DEFICIT, MISFIRE_EVENT).
Detected events can be persisted per diagnostic session and attached to a case as
telemetry evidence — closing the loop from a datalog to a diagnosis.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import analysis

# Canonical channel registry: name → (unit, normal_range, warn_range, description).
CHANNELS: dict[str, dict] = {
    "rpm": dict(unit="rpm", normal=(600, 6800), warn=(0, 7000), description="Engine speed"),
    "boost_actual": dict(unit="psi", normal=(-10, 22), warn=(-15, 26), description="Manifold/boost pressure"),
    "boost_cmd": dict(unit="psi", normal=(-10, 22), warn=(-15, 26), description="Commanded/target boost"),
    "knock": dict(unit="deg", normal=(-2, 0), warn=(-6, 0), description="Knock retard (negative = retard)"),
    "misfire": dict(unit="count", normal=(0, 0), warn=(0, 2), description="Misfire counter"),
    "stft": dict(unit="%", normal=(-8, 8), warn=(-15, 15), description="Short-term fuel trim"),
    "coolant": dict(unit="°C", normal=(80, 105), warn=(80, 110), description="Coolant temperature"),
    "iat": dict(unit="°C", normal=(0, 60), warn=(0, 75), description="Intake/charge-air temperature"),
    "rail": dict(unit="bar", normal=(40, 200), warn=(30, 220), description="Fuel-rail pressure"),
    # derived
    "boost_error": dict(unit="psi", normal=(-2, 2), warn=(-4, 4), derived=True,
                        formula="boost_cmd - boost_actual", description="Boost target vs actual"),
    "charge_temp_delta": dict(unit="°C", normal=(0, 25), warn=(0, 40), derived=True,
                              formula="iat - min(iat)", description="Charge-air heat above the run's floor"),
}

# Detection thresholds (documented + tunable).
WOT_BOOST_PSI = 8.0        # boost above this ⇒ under load
KNOCK_RETARD_DEG = 3.0     # retard at/below -this ⇒ knock event
OVERTEMP_C = 110.0         # coolant above this ⇒ over-temp
BOOST_DEFICIT_PSI = 3.0    # actual below target by this during a pull ⇒ deficit
HEATSOAK_DELTA_C = 30.0    # charge-temp delta above this at low rpm ⇒ heat soak


@dataclass
class Event:
    kind: str
    t_start: float | None = None
    t_end: float | None = None
    severity: str = "info"
    channel: str | None = None
    detail: str = ""

    def as_dict(self) -> dict:
        return {"kind": self.kind, "t_start": self.t_start, "t_end": self.t_end,
                "severity": self.severity, "channel": self.channel, "detail": self.detail}


def frame_from_measurements(measurements: list[dict]) -> list[dict]:
    """Group flat measurements into time-aligned samples keyed by canonical role.

    Each measurement is {pid, value, t_offset_s}; roles come from analysis._match.
    Returns samples sorted by time: [{"t": float, "<role>": value, ...}, ...].
    """
    by_t: dict[float, dict] = {}
    for m in measurements:
        role = analysis._match(m["pid"])
        if role is None:
            continue
        t = float(m.get("t_offset_s") or 0.0)
        by_t.setdefault(t, {"t": t})[role] = float(m["value"])
    return [by_t[t] for t in sorted(by_t)]


def derive(frame: list[dict]) -> list[dict]:
    """Add derived channels to each sample (returns a new list; inputs untouched)."""
    iats = [s["iat"] for s in frame if "iat" in s]
    iat_floor = min(iats) if iats else None
    out = []
    for s in frame:
        d = dict(s)
        if "boost_cmd" in s and "boost_actual" in s:
            d["boost_error"] = s["boost_cmd"] - s["boost_actual"]
        if "iat" in s and iat_floor is not None:
            d["charge_temp_delta"] = s["iat"] - iat_floor
        out.append(d)
    return out


def detect_events(frame: list[dict]) -> list[Event]:
    """Detect operating events over a (optionally derived) frame."""
    if not frame:
        return []
    frame = derive(frame)
    events: list[Event] = []

    # WOT pulls: contiguous spans with boost_actual above the load threshold.
    span_start = None
    for i, s in enumerate(frame):
        boosted = s.get("boost_actual", -99) >= WOT_BOOST_PSI
        if boosted and span_start is None:
            span_start = s["t"]
        if (not boosted or i == len(frame) - 1) and span_start is not None:
            end = s["t"]
            peak = max(x.get("boost_actual", -99) for x in frame if span_start <= x["t"] <= end)
            events.append(Event("WOT_PULL", span_start, end, "info", "boost_actual",
                                f"WOT pull, peak boost {peak:g} psi"))
            # boost deficit within the pull
            worst = max((x.get("boost_error", 0) for x in frame if span_start <= x["t"] <= end),
                        default=0)
            if worst >= BOOST_DEFICIT_PSI:
                events.append(Event("BOOST_DEFICIT", span_start, end, "warn", "boost_error",
                                    f"Actual below target by up to {worst:g} psi during the pull"))
            span_start = None

    # Knock events (per sample beyond the retard threshold).
    for s in frame:
        if s.get("knock", 0) <= -KNOCK_RETARD_DEG:
            sev = "critical" if s["knock"] <= -2 * KNOCK_RETARD_DEG else "warn"
            events.append(Event("KNOCK_EVENT", s["t"], s["t"], sev, "knock",
                                f"Knock retard {s['knock']:g}°"))

    # Over-temp (coolant).
    hot = [s for s in frame if s.get("coolant", -99) >= OVERTEMP_C]
    if hot:
        events.append(Event("OVER_TEMP", hot[0]["t"], hot[-1]["t"], "critical", "coolant",
                            f"Coolant peaked {max(s['coolant'] for s in hot):g}°C"))

    # Misfire events (counter rising).
    prev = None
    for s in frame:
        mf = s.get("misfire")
        if mf is not None and prev is not None and mf > prev:
            events.append(Event("MISFIRE_EVENT", s["t"], s["t"], "warn", "misfire",
                                f"Misfire count rose to {mf:g}"))
        if mf is not None:
            prev = mf

    # Heat soak: high charge-temp delta while off-load (low boost).
    soak = [s for s in frame if s.get("charge_temp_delta", 0) >= HEATSOAK_DELTA_C
            and s.get("boost_actual", 0) < WOT_BOOST_PSI]
    if soak:
        events.append(Event("HEAT_SOAK", soak[0]["t"], soak[-1]["t"], "warn", "charge_temp_delta",
                            f"Charge-air {max(s['charge_temp_delta'] for s in soak):g}°C above floor off-load"))
    return events


# ---- DB layer -------------------------------------------------------------
def seed_channels(session) -> str:
    from sqlalchemy import select
    from .tmodels import TelemetryChannel
    n = 0
    for name, spec in CHANNELS.items():
        if session.scalar(select(TelemetryChannel).where(TelemetryChannel.canonical_name == name)):
            continue
        nlo, nhi = spec.get("normal", (None, None))
        wlo, whi = spec.get("warn", (None, None))
        session.add(TelemetryChannel(canonical_name=name, unit=spec.get("unit"),
                                     description=spec.get("description"), normal_min=nlo, normal_max=nhi,
                                     warn_min=wlo, warn_max=whi, derived=spec.get("derived", False),
                                     formula=spec.get("formula")))
        n += 1
    session.flush()
    return f"Telemetry channel registry seeded: +{n} channels ({len(CHANNELS)} total)."


def run_pipeline(session, session_id: int) -> list[dict]:
    """Detect + persist telemetry events for a diagnostic session's measurements."""
    from sqlalchemy import delete, select
    from .models import Measurement
    from .tmodels import TelemetryEvent
    rows = session.scalars(select(Measurement).where(Measurement.session_id == session_id)).all()
    frame = frame_from_measurements(
        [{"pid": m.pid, "value": m.value, "t_offset_s": m.t_offset_s} for m in rows])
    events = detect_events(frame)
    session.execute(delete(TelemetryEvent).where(TelemetryEvent.session_id == session_id))
    for e in events:
        session.add(TelemetryEvent(session_id=session_id, kind=e.kind, t_start=e.t_start,
                                   t_end=e.t_end, severity=e.severity, channel=e.channel, detail=e.detail))
    session.flush()
    return [e.as_dict() for e in events]


def events_to_case(session, case, events: list[dict]) -> int:
    """Attach detected telemetry events to a diagnostic case as evidence."""
    from . import workbench
    n = 0
    for e in events:
        workbench.add_evidence(session, case, "telemetry", ref=e["kind"], detail=e["detail"],
                               component_slug=_event_component(e["kind"]))
        n += 1
    return n


def _event_component(kind: str) -> str | None:
    return {"BOOST_DEFICIT": "wastegate", "WOT_PULL": "turbocharger", "OVER_TEMP": "radiator",
            "KNOCK_EVENT": "spark-plugs", "MISFIRE_EVENT": "coils",
            "HEAT_SOAK": "intercooler"}.get(kind)
