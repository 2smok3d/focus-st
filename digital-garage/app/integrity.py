"""INTEG — datalog integrity / signal-plausibility checks.

The compendium wants CAN-bus intrusion detection (a deep-learning IDS over the bus). Rebuilt
*in this platform's grain* as honest, deterministic **signal-plausibility** checks over a
parsed datalog — the read-time integrity layer a tuner actually needs: is this log sound
enough to trust before I diagnose from it?

Four checks, deliberately unit-tolerant so they don't cry wolf across psi/kPa or °C/°F logs:

  • frozen      — a recognized *dynamic* channel (rpm/boost/coolant/…) that never moves across
                  a whole session: a stuck or disconnected sensor.
  • nonfinite   — NaN / ±inf values: a parser or capture artifact.
  • out_of_range— a value outside a *generous* physical band (rpm < 0 or > 12000; a temperature
                  channel below −60 or above 350 in any unit; lambda/AFR ≤ 0 or absurdly high).
                  Bands are wide on purpose — they catch garbage (999, −273), not tuning extremes.
  • time_disorder — sample timestamps that go backwards: a corrupt or interleaved log.

Findings are surfaced (intel / CLI / API / MCP), not asserted as vehicle facts — a plausibility
flag on the *log*, not a claim about the *car*. Recording findings into the durable machine-event
ledger at ingest is a deliberate later step; this unit is the read-time analyzer.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from .analysis import _match     # reuse the datalog channel recognizer

# A recognized channel in this set should vary within a real session; frozen ⇒ suspect sensor.
_DYNAMIC = {"rpm", "boost_actual", "coolant", "iat", "rail_actual", "lambda"}

# Generous physical bands per role (min, max). Wide enough to tolerate unit ambiguity — they
# flag broken sensors, never tuning extremes. None ⇒ that side is unbounded.
_BANDS = {
    "rpm": (-10.0, 12000.0),
    "coolant": (-60.0, 350.0),
    "iat": (-60.0, 350.0),
    "lambda": (0.0001, 40.0),      # ≤0 is impossible; >40 is garbage
}

FROZEN_MIN = 20        # a dynamic channel needs at least this many samples to call it frozen


@dataclass(frozen=True)
class Finding:
    kind: str          # "frozen" | "nonfinite" | "out_of_range" | "time_disorder"
    channel: str | None
    role: str | None
    severity: str      # "info" | "warn" | "error"
    detail: str

    def as_dict(self) -> dict:
        return asdict(self)


def check_measurements(measurements: list[dict]) -> dict:
    """Run the plausibility checks over parsed measurements ([{pid, value, unit, t_offset_s}]).
    Pure — no DB. Returns {findings, channels, samples, by_kind}."""
    by_pid: dict[str, list[float]] = {}
    units: dict[str, str | None] = {}
    offsets: list[float] = []
    samples = 0
    nonfinite: dict[str, int] = {}

    for m in measurements:
        pid = m.get("pid")
        if pid is None:
            continue
        v = m.get("value")
        samples += 1
        if m.get("t_offset_s") is not None:
            offsets.append(float(m["t_offset_s"]))
        if v is None:
            continue
        fv = float(v)
        if not math.isfinite(fv):
            nonfinite[pid] = nonfinite.get(pid, 0) + 1
            continue
        by_pid.setdefault(pid, []).append(fv)
        units.setdefault(pid, m.get("unit"))

    findings: list[Finding] = []

    for pid, cnt in nonfinite.items():
        findings.append(Finding("nonfinite", pid, _match(pid), "error",
                                f"{cnt} non-finite (NaN/inf) sample(s) on '{pid}'."))

    for pid, vals in by_pid.items():
        role = _match(pid)
        # frozen dynamic channel
        if role in _DYNAMIC and len(vals) >= FROZEN_MIN and min(vals) == max(vals):
            findings.append(Finding("frozen", pid, role, "warn",
                                    f"'{pid}' held constant at {vals[0]:g} for all "
                                    f"{len(vals)} samples — stuck or disconnected?"))
        # out-of-range against a generous physical band
        band = _BANDS.get(role)
        if band:
            lo, hi = band
            bad = [v for v in vals if v < lo or v > hi]
            if bad:
                findings.append(Finding("out_of_range", pid, role, "error",
                                        f"'{pid}' has {len(bad)} sample(s) outside the plausible "
                                        f"{lo:g}‥{hi:g} band (e.g. {bad[0]:g})."))

    # timestamps going backwards ⇒ corrupt / interleaved log
    inversions = sum(1 for a, b in zip(offsets, offsets[1:]) if b < a)
    if inversions:
        findings.append(Finding("time_disorder", None, None, "warn",
                                f"{inversions} sample(s) have a timestamp earlier than the one "
                                f"before — the log may be corrupt or interleaved."))

    by_kind: dict[str, int] = {}
    for f in findings:
        by_kind[f.kind] = by_kind.get(f.kind, 0) + 1
    return {"findings": [f.as_dict() for f in findings], "channels": len(by_pid),
            "samples": samples, "by_kind": by_kind}


# ---- service: check stored sessions --------------------------------------------
def _session_measurements(session, diag_session_id: int) -> list[dict]:
    from sqlalchemy import select

    from .models import Measurement
    rows = session.scalars(
        select(Measurement).where(Measurement.session_id == diag_session_id)
        .order_by(Measurement.t_offset_s, Measurement.id)
    ).all()
    return [{"pid": m.pid, "value": m.value, "unit": m.unit, "t_offset_s": m.t_offset_s}
            for m in rows]


def session_integrity(session, diag_session_id: int) -> dict:
    """Integrity report for one stored diagnostic session."""
    res = check_measurements(_session_measurements(session, diag_session_id))
    res["session_id"] = diag_session_id
    return res


def vehicle_integrity(session, vehicle_id: int, *, limit: int = 10) -> dict:
    """Run the checks over a machine's most recent datalog sessions and roll them up.
    Returns per-session reports (only those with findings) + totals."""
    from sqlalchemy import select

    from .models import DiagnosticSession
    sessions = session.scalars(
        select(DiagnosticSession).where(DiagnosticSession.vehicle_id == vehicle_id)
        .order_by(DiagnosticSession.captured_at.desc().nullslast(), DiagnosticSession.id.desc())
        .limit(limit)
    ).all()

    reports: list[dict] = []
    totals: dict[str, int] = {}
    total_findings = 0
    for ds in sessions:
        r = check_measurements(_session_measurements(session, ds.id))
        if not r["findings"]:
            continue
        total_findings += len(r["findings"])
        for k, n in r["by_kind"].items():
            totals[k] = totals.get(k, 0) + n
        reports.append({"session_id": ds.id, "label": ds.note or ds.kind or f"#{ds.id}",
                        "findings": r["findings"], "by_kind": r["by_kind"],
                        "channels": r["channels"], "samples": r["samples"]})

    return {"sessions_checked": len(sessions), "sessions_flagged": len(reports),
            "findings": total_findings, "by_kind": totals, "reports": reports}
