"""Datalog analysis — turn stored measurements into a session summary.

`summarize_measurements()` is pure (takes plain rows) so it unit-tests without a
database. It computes per-channel statistics and a short list of plain-language
findings for the channels that matter on a turbo car: boost tracking, knock,
misfire, fuel-trim drift, temperatures, rail pressure.

Channel identity is matched by name (FORScan/PID labels vary), so the summarizer
is tolerant of missing or differently-named channels — it reports on what's
there and stays silent about what isn't.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# name → matcher for the channels we call out explicitly
_CH = {
    "rpm": re.compile(r"\brpm\b|engine speed", re.I),
    "boost_actual": re.compile(r"\bboost\b|manifold|\bmap\b|\bpsi\b", re.I),
    "boost_cmd": re.compile(r"(desired|commanded|target).*(boost|map)|boost.*(desired|target)", re.I),
    "knock": re.compile(r"knock|detonation|kr\b", re.I),
    "misfire": re.compile(r"misfire", re.I),
    "stft": re.compile(r"short.*trim|\bstft\b", re.I),
    "ltft": re.compile(r"long.*trim|\bltft\b", re.I),
    "coolant": re.compile(r"coolant|\bect\b", re.I),
    "iat": re.compile(r"intake air|charge air|\biat\b|\bact\b|\bcat\b", re.I),
    "rail_actual": re.compile(r"(fuel\s*rail|rail\s*press).*(actual)?|\bhpfp\b", re.I),
    "rail_cmd": re.compile(r"(desired|commanded).*rail", re.I),
    "lambda": re.compile(r"lambda|afr|equivalence|\bo2\b", re.I),
}


@dataclass
class _Stat:
    n: int
    min: float
    max: float
    mean: float
    last: float

    def as_dict(self) -> dict:
        return {"n": self.n, "min": round(self.min, 3), "max": round(self.max, 3),
                "mean": round(self.mean, 3), "last": round(self.last, 3)}


def _stat(values: list[float]) -> _Stat | None:
    if not values:
        return None
    return _Stat(len(values), min(values), max(values),
                 sum(values) / len(values), values[-1])


def _match(pid: str) -> str | None:
    for key, pat in _CH.items():
        if pat.search(pid):
            return key
    return None


def summarize_measurements(measurements: list[dict], *, dtc_count: int = 0,
                           can_count: int = 0) -> dict:
    """measurements: [{pid, value, unit, t_offset_s}]. Returns stats + findings."""
    by_pid: dict[str, list[float]] = {}
    units: dict[str, str | None] = {}
    for m in measurements:
        v = m.get("value")
        if v is None:
            continue
        by_pid.setdefault(m["pid"], []).append(float(v))
        units.setdefault(m["pid"], m.get("unit"))

    channels = {pid: {**_stat(vals).as_dict(), "unit": units.get(pid)}
                for pid, vals in by_pid.items() if _stat(vals)}

    # map recognized roles → the first matching channel's stats
    role: dict[str, tuple[str, _Stat]] = {}
    for pid, vals in by_pid.items():
        key = _match(pid)
        st = _stat(vals)
        if key and st and key not in role:
            role[key] = (pid, st)

    findings: list[dict] = []

    def add(level, text):
        findings.append({"level": level, "text": text})

    if "boost_actual" in role:
        pid, st = role["boost_actual"]
        line = f"Peak {pid}: {st.max:g}{_u(units.get(pid))} (mean {st.mean:.1f})."
        if "boost_cmd" in role:
            _, cst = role["boost_cmd"]
            gap = cst.max - st.max
            if gap > 2:
                add("warn", f"Underboost vs target: commanded peak {cst.max:g} but actual peak {st.max:g} "
                            f"(~{gap:.1f} short) — check for a charge leak before trusting the log.")
            else:
                add("info", line + f" Tracks target (cmd peak {cst.max:g}).")
        else:
            add("info", line)

    if "knock" in role:
        pid, st = role["knock"]
        # knock retard is usually negative; count meaningful events
        events = sum(1 for m in measurements if _match(m["pid"]) == "knock"
                     and m.get("value") is not None and abs(float(m["value"])) >= 1.0)
        worst = min(st.min, -st.max, key=lambda x: x)  # most-negative-ish
        if events:
            add("warn", f"Knock activity on '{pid}': {events} sample(s) ≥1° (worst {min(st.min, st.max):g}). "
                        f"Correlate with fuel/octane and boost before another WOT pull.")
        else:
            add("info", f"No significant knock on '{pid}'.")

    if "misfire" in role:
        pid, st = role["misfire"]
        if st.max > 0:
            add("warn", f"Misfire counts present on '{pid}' (max {st.max:g}). Identify the cylinder before load.")
        else:
            add("info", f"No misfires counted on '{pid}'.")

    for trim in ("stft", "ltft"):
        if trim in role:
            pid, st = role[trim]
            drift = max(abs(st.min), abs(st.max))
            lvl = "warn" if drift >= 10 else "info"
            add(lvl, f"{trim.upper()} '{pid}' range {st.min:g}…{st.max:g}% (|drift| {drift:g}%)"
                     + (" — investigate fueling/leaks." if lvl == "warn" else "."))

    if "coolant" in role:
        pid, st = role["coolant"]
        lvl = "warn" if st.max >= 110 else "info"
        add(lvl, f"Coolant peak {st.max:g}{_u(units.get(pid))}" + (" — running hot." if lvl == "warn" else "."))
    if "iat" in role:
        pid, st = role["iat"]
        lvl = "warn" if st.max >= 60 else "info"
        add(lvl, f"Charge/intake air peak {st.max:g}{_u(units.get(pid))}"
                 + (" — heat-soak territory." if lvl == "warn" else "."))

    if "rail_actual" in role and "rail_cmd" in role:
        _, a = role["rail_actual"]
        _, c = role["rail_cmd"]
        if c.max - a.min > 400:  # bar/psi-agnostic: large shortfall
            add("warn", f"Fuel rail actual dips well below commanded (cmd max {c.max:g}, actual min {a.min:g}) "
                        f"— possible fuel-supply limit under load.")

    if dtc_count:
        add("warn", f"{dtc_count} DTC(s) captured in this session — review alongside the log.")

    order = {"warn": 0, "info": 1}
    findings.sort(key=lambda f: order.get(f["level"], 2))
    return {
        "samples": len(measurements),
        "channels_recorded": len(channels),
        "duration_s": _duration(measurements),
        "dtc_count": dtc_count,
        "can_frame_count": can_count,
        "recognized": {k: v[0] for k, v in role.items()},
        "findings": findings,
        "channels": channels,
    }


def _u(unit) -> str:
    return f" {unit}" if unit else ""


def _duration(measurements: list[dict]) -> float:
    ts = [m["t_offset_s"] for m in measurements if m.get("t_offset_s") is not None]
    return round(max(ts) - min(ts), 2) if ts else 0.0
