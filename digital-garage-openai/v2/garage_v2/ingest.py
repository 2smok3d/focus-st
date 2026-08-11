from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

DTC_RE = re.compile(r"\b([PBCU][0-9A-F]{4})\b", re.I)
CANDUMP_RE = re.compile(r"^\((?P<ts>\d+(?:\.\d+)?)\)\s+(?P<iface>\S+)\s+(?P<id>[0-9A-Fa-f]+)#(?P<data>[0-9A-Fa-f]*)")


@dataclass
class NormalizedEvidence:
    original_name: str
    source_format: str
    sha256: str
    byte_size: int
    imported_at: str
    raw_path: str
    normalized_path: str
    parser: str
    parser_version: str
    warnings: list[str]
    metadata: dict[str, Any]
    dtcs: list[dict[str, Any]]
    measurements: list[dict[str, Any]]
    can_frames: list[dict[str, Any]]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_format(path: Path, text: str) -> str:
    low = path.name.lower()
    if CANDUMP_RE.search(text.splitlines()[0] if text.splitlines() else "") or "can0" in text[:500]:
        return "socketcan-candump"
    if low.endswith(".csv"):
        if "forscan" in text[:2000].lower():
            return "forscan-csv"
        return "generic-csv"
    if low.endswith(".json"):
        return "json"
    if "forscan" in text[:3000].lower() or "dtc" in text[:500].lower():
        return "forscan-text"
    if low.endswith((".log", ".txt")):
        return "text-log"
    return "unknown-text"


def parse_dtcs(text: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = DTC_RE.search(line)
        if not match:
            continue
        code = match.group(1).upper()
        key = f"{code}|{line.strip()}"
        if key in seen:
            continue
        seen.add(key)
        status = "unknown"
        lower = line.lower()
        for candidate in ("permanent", "pending", "stored", "current", "history"):
            if candidate in lower:
                status = candidate
                break
        module_match = re.search(r"\b(PCM|BCM|ABS|APIM|IPC|TCM|RCM|PSCM|HVAC|GEM)\b", line, re.I)
        out.append({
            "code": code,
            "status": status,
            "module": module_match.group(1).upper() if module_match else None,
            "raw_line": line.strip(),
        })
    return out


def parse_candump(text: str) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    for line in text.splitlines():
        m = CANDUMP_RE.match(line.strip())
        if not m:
            continue
        data = m.group("data").upper()
        arb = int(m.group("id"), 16)
        frames.append({
            "elapsed_or_epoch_seconds": float(m.group("ts")),
            "channel": m.group("iface"),
            "arbitration_id": arb,
            "arbitration_id_hex": f"0x{arb:X}",
            "is_extended_id": arb > 0x7FF,
            "dlc": len(data) // 2,
            "data_hex": data,
            "decoded_signals": {},
        })
    return frames


def _header_index(headers: list[str], candidates: tuple[str, ...]) -> int | None:
    normalized = [h.strip().lower().replace(" ", "_") for h in headers]
    for candidate in candidates:
        if candidate in normalized:
            return normalized.index(candidate)
    return None


def parse_csv(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    measurements: list[dict[str, Any]] = []
    warnings: list[str] = []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel
        rows = list(csv.reader(f, dialect))
    if not rows:
        return measurements, ["empty CSV"]
    headers = rows[0]
    time_i = _header_index(headers, ("time", "timestamp", "datetime", "elapsed", "seconds"))
    pid_i = _header_index(headers, ("pid", "parameter", "name", "signal"))
    value_i = _header_index(headers, ("value", "val", "reading"))
    unit_i = _header_index(headers, ("unit", "units"))
    module_i = _header_index(headers, ("module", "ecu"))
    if pid_i is not None and value_i is not None:
        for row in rows[1:]:
            if len(row) <= max(pid_i, value_i):
                continue
            measurements.append({
                "timestamp": row[time_i] if time_i is not None and time_i < len(row) else None,
                "module": row[module_i] if module_i is not None and module_i < len(row) else None,
                "pid": row[pid_i],
                "value": row[value_i],
                "unit": row[unit_i] if unit_i is not None and unit_i < len(row) else None,
            })
    else:
        # Wide datalog: first column commonly time, every other header is a signal.
        if len(headers) > 1:
            for row in rows[1:]:
                timestamp = row[0] if row else None
                for i, header in enumerate(headers[1:], start=1):
                    if i >= len(row) or row[i] == "":
                        continue
                    measurements.append({"timestamp": timestamp, "pid": header, "value": row[i], "unit": None, "module": None})
            warnings.append("CSV interpreted as wide-format datalog; units/modules may require mapping")
        else:
            warnings.append("CSV header layout not recognized")
    return measurements, warnings


def normalize_file(source: str | os.PathLike[str], data_root: str | os.PathLike[str]) -> NormalizedEvidence:
    src = Path(source).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(src)
    root = Path(data_root).expanduser().resolve()
    raw_dir = root / "raw"
    processed_dir = root / "processed"
    raw_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    digest = sha256_file(src)
    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", src.name)
    raw_path = raw_dir / f"{digest}__{safe_name}"
    normalized_path = processed_dir / f"{digest}.json"

    if not raw_path.exists():
        shutil.copy2(src, raw_path)

    text = src.read_text(encoding="utf-8-sig", errors="replace")
    source_format = detect_format(src, text)
    warnings: list[str] = []
    dtcs = parse_dtcs(text)
    measurements: list[dict[str, Any]] = []
    can_frames: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}

    if source_format == "socketcan-candump":
        can_frames = parse_candump(text)
    elif source_format in {"generic-csv", "forscan-csv"}:
        measurements, csv_warnings = parse_csv(src)
        warnings.extend(csv_warnings)
    elif source_format == "json":
        try:
            obj = json.loads(text)
            metadata["json_top_level_type"] = type(obj).__name__
        except json.JSONDecodeError as e:
            warnings.append(f"invalid JSON: {e}")
    elif source_format == "unknown-text":
        warnings.append("format not confidently identified; DTC extraction only")

    record = NormalizedEvidence(
        original_name=src.name,
        source_format=source_format,
        sha256=digest,
        byte_size=src.stat().st_size,
        imported_at=datetime.now(timezone.utc).isoformat(),
        raw_path=str(raw_path),
        normalized_path=str(normalized_path),
        parser="garage_v2.ingest",
        parser_version="2.0.0-dev",
        warnings=warnings,
        metadata=metadata,
        dtcs=dtcs,
        measurements=measurements,
        can_frames=can_frames,
    )

    # Normalized derivatives are deterministic records; raw evidence is never rewritten.
    if not normalized_path.exists():
        normalized_path.write_text(json.dumps(asdict(record), indent=2, ensure_ascii=False), encoding="utf-8")
    return record


def cli() -> None:
    import argparse
    p = argparse.ArgumentParser(description="Normalize FORScan/OBD/CAN evidence into the Digital Garage evidence vault")
    p.add_argument("source")
    p.add_argument("--data-root", default=os.environ.get("GARAGE_DATA_ROOT", "./garage-data"))
    args = p.parse_args()
    result = normalize_file(args.source, args.data_root)
    print(json.dumps(asdict(result), indent=2))


if __name__ == "__main__":
    cli()
