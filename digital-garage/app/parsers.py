"""Ingest — raw-preserving parsers for diagnostic artifacts.

Contract: nothing is normalized until the original bytes are stored on disk with
their SHA-256. `ingest()` is the single entry point — it hashes, dedupes against
the store, persists the raw file, then runs the format-specific parser to fill
DTCs / measurements / CAN frames. If a parse is later improved, the raw file is
still there to re-run against.

Supported kinds:
  - forscan : FORScan DTC/report text or CSV export
  - candump : Linux SocketCAN `candump -l` log lines
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import CanFrame, DiagnosticSession, Dtc, Measurement


@dataclass
class ParseResult:
    dtcs: list[dict] = field(default_factory=list)
    measurements: list[dict] = field(default_factory=list)
    can_frames: list[dict] = field(default_factory=list)
    captured_at: dt.datetime | None = None

    @property
    def counts(self) -> dict[str, int]:
        return {"dtcs": len(self.dtcs), "measurements": len(self.measurements),
                "can_frames": len(self.can_frames)}


# ---------------------------------------------------------------------------
# FORScan
# ---------------------------------------------------------------------------
# A DTC token: P/C/B/U + 4 hex-ish chars, e.g. P0299, U0100, C1234, P04DB.
_DTC_RE = re.compile(r"\b([PCBU][0-9][0-9A-F]{3})\b")
_MODULE_RE = re.compile(r"\b(PCM|ECM|TCM|ABS|BCM|IPC|APIM|ACM|PSCM|RCM|SODL|SODR)\b")
_STATUS_RE = re.compile(r"\b(permanent|pending|current|history|stored|confirmed)\b", re.I)


def parse_forscan(text: str) -> ParseResult:
    """Parse FORScan output. Handles both the CSV export and free-form report
    text (one DTC per line with optional module + status + description)."""
    res = ParseResult()

    # CSV export? First non-empty line looks like a header with commas.
    sniff = next((ln for ln in text.splitlines() if ln.strip()), "")
    if sniff.count(",") >= 2 and _looks_like_csv_header(sniff):
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            norm = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
            code = _first(norm, "code", "dtc", "trouble code")
            if not code or not _DTC_RE.fullmatch(code):
                continue
            res.dtcs.append({
                "code": code.upper(),
                "module": _first(norm, "module", "ecu", "unit") or None,
                "status": _first(norm, "status", "state") or None,
                "description": _first(norm, "description", "desc", "fault") or None,
            })
        return res

    # Free-form report text.
    for line in text.splitlines():
        m = _DTC_RE.search(line)
        if not m:
            continue
        code = m.group(1).upper()
        module = (mm.group(1) if (mm := _MODULE_RE.search(line)) else None)
        status = (sm.group(1).lower() if (sm := _STATUS_RE.search(line)) else None)
        # Description = the remainder after the code, cleaned up (drop a leading
        # status word and any stray module token so it isn't redundant).
        desc = line[m.end():].strip(" -:\t")
        desc = _MODULE_RE.sub("", desc).strip(" -:\t")
        if status:
            desc = re.sub(rf"^{status}\b", "", desc, flags=re.I).strip(" -:\t")
        desc = desc or None
        res.dtcs.append({"code": code, "module": module, "status": status,
                         "description": desc})
    return res


def _looks_like_csv_header(line: str) -> bool:
    low = line.lower()
    return any(h in low for h in ("code", "dtc", "module", "description", "status"))


def _first(d: dict, *keys: str) -> str:
    for k in keys:
        if k in d and d[k]:
            return d[k]
    return ""


# ---------------------------------------------------------------------------
# candump  (SocketCAN `candump -l` format)
#   (1699999999.123456) can0 1A0#11223344AABBCCDD
# ---------------------------------------------------------------------------
_CANDUMP_RE = re.compile(
    r"\((?P<ts>\d+\.\d+)\)\s+\S+\s+(?P<id>[0-9A-Fa-f]+)#(?P<data>[0-9A-Fa-f]*)"
)


def parse_candump(text: str) -> ParseResult:
    res = ParseResult()
    t0: float | None = None
    for line in text.splitlines():
        m = _CANDUMP_RE.search(line)
        if not m:
            continue
        ts = float(m.group("ts"))
        if t0 is None:
            t0 = ts
            res.captured_at = dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
        data = m.group("data").upper()
        res.can_frames.append({
            "t_offset_s": round(ts - t0, 6),
            "can_id": m.group("id").upper(),
            "dlc": len(data) // 2,
            "data_hex": data or None,
        })
    return res


# ---------------------------------------------------------------------------
# Datalog CSV  (FORScan / generic time-series export)
#   Time,RPM,Boost (psi),Knock,STFT (%),...
#   0.00,850,-8.1,0,1.2,...
# First column is time (seconds, or HH:MM:SS[.mmm]); the rest are numeric PIDs.
# ---------------------------------------------------------------------------
_TIME_HEADER = re.compile(r"\b(time|timestamp|seconds|elapsed)\b|^t$", re.I)
_UNIT_IN_HEADER = re.compile(r"[(\[]\s*([^)\]]{1,12})\s*[)\]]")
_HMS = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2}(?:\.\d+)?)$")


def _num(cell: str):
    try:
        return float(str(cell).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None


def _parse_time_cell(cell: str):
    s = str(cell).strip()
    v = _num(s)
    if v is not None:
        return v
    m = _HMS.match(s)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return None


def _clean_pid(h: str) -> str:
    return _UNIT_IN_HEADER.sub("", h).strip() or h.strip()


def _unit_from_header(h: str):
    m = _UNIT_IN_HEADER.search(h)
    return m.group(1).strip() if m else None


def parse_datalog(text: str) -> ParseResult:
    res = ParseResult()
    rows = [r for r in csv.reader(io.StringIO(text)) if any(c.strip() for c in r)]
    if len(rows) < 2:
        return res
    header = [h.strip() for h in rows[0]]
    tidx = next((i for i, h in enumerate(header) if _TIME_HEADER.search(h)), 0)
    t0 = None
    for r in rows[1:]:
        if len(r) <= tidx:
            continue
        t = _parse_time_cell(r[tidx])
        if t is None:
            continue
        if t0 is None:
            t0 = t
        toff = round(t - t0, 4)
        for i, cell in enumerate(r):
            if i == tidx or i >= len(header):
                continue
            val = _num(cell)
            if val is None:
                continue
            res.measurements.append({"pid": _clean_pid(header[i]) or f"col{i}",
                                     "value": val, "unit": _unit_from_header(header[i]),
                                     "t_offset_s": toff})
    return res


PARSERS = {"forscan": parse_forscan, "candump": parse_candump, "datalog": parse_datalog}


# ---------------------------------------------------------------------------
# Raw store + ingest
# ---------------------------------------------------------------------------
def _store_raw(kind: str, sha: str, content: bytes) -> Path:
    """Persist bytes byte-for-byte under data/raw/<kind>/<sha>.bin."""
    dest_dir = settings.raw_dir / kind
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{sha}.bin"
    if not dest.exists():
        dest.write_bytes(content)
    return dest


def ingest(
    session: Session,
    vehicle_id: int,
    kind: str,
    content: bytes,
    *,
    miles: int | None = None,
    source_id: int | None = None,
    note: str | None = None,
) -> dict:
    """Hash → dedupe → store raw → parse → persist normalized rows.

    Returns a summary dict. If the exact bytes were ingested before (same
    SHA-256), the existing session is returned untouched — ingest is idempotent.
    """
    kind = kind.lower()
    if kind not in PARSERS:
        raise ValueError(f"Unknown kind '{kind}'. Supported: {sorted(PARSERS)}")

    sha = hashlib.sha256(content).hexdigest()
    existing = session.scalar(select(DiagnosticSession).where(DiagnosticSession.sha256 == sha))
    if existing is not None:
        return {"status": "duplicate", "session_id": existing.id, "sha256": sha,
                "message": "Identical artifact already ingested."}

    raw_path = _store_raw(kind, sha, content)
    result = PARSERS[kind](content.decode("utf-8", errors="replace"))

    ds = DiagnosticSession(
        vehicle_id=vehicle_id, kind=kind, captured_at=result.captured_at,
        miles=miles, sha256=sha, raw_path=str(raw_path), source_id=source_id, note=note,
    )
    session.add(ds)
    session.flush()

    for d in result.dtcs:
        session.add(Dtc(session_id=ds.id, **d))
    for m in result.measurements:
        session.add(Measurement(session_id=ds.id, **m))
    for f in result.can_frames:
        session.add(CanFrame(session_id=ds.id, **f))
    session.flush()

    # Durable observations from the log's peaks, so degradation trends fit real data
    # over time (not just the sample seed). A side benefit — never fail an ingest on it.
    obs_recorded = _record_session_observations(session, vehicle_id, ds, result.measurements)

    out = {"status": "ingested", "session_id": ds.id, "sha256": sha,
           "raw_path": str(raw_path), "counts": result.counts}
    if obs_recorded:
        out["observations_recorded"] = obs_recorded
    return out


def _record_session_observations(session: Session, vehicle_id: int,
                                 ds: DiagnosticSession, measurements: list[dict]) -> int:
    """Record per-channel peaks from a session as durable observations, timestamped at the
    log's capture time so they form a series across sessions. Best-effort and isolated:
    a bad unit or a missing vehicle skips that observation, never the ingest."""
    if not measurements:
        return 0
    try:
        from . import analysis, observations as ob
        from .models import Vehicle
        vehicle = session.get(Vehicle, vehicle_id)
        if vehicle is None:
            return 0
        when = ds.captured_at or ds.ingested_at or dt.datetime.now(dt.timezone.utc)
        recorded = 0
        for spec in analysis.peak_observations(measurements):
            try:
                ob.record_observation(
                    session, vehicle, subject_slug=spec["subject_slug"], obs_type="electronic",
                    method=spec["method"], value=spec["value"], unit=spec["unit"],
                    operating_condition=spec["operating_condition"], observed_at=when,
                    note=f"datalog session #{ds.id}")
                recorded += 1
            except Exception:
                # unknown unit (fails quantity validation) or similar — retry unitless so
                # the value still forms a trend series; if that also fails, skip this one.
                try:
                    ob.record_observation(
                        session, vehicle, subject_slug=spec["subject_slug"], obs_type="electronic",
                        method=spec["method"], value=spec["value"], unit=None,
                        operating_condition=spec["operating_condition"], observed_at=when,
                        note=f"datalog session #{ds.id} (unit '{spec['unit']}' not normalized)")
                    recorded += 1
                except Exception:
                    continue
        return recorded
    except Exception:
        return 0
