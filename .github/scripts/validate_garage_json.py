#!/usr/bin/env python3
"""Validate the published garage.json the dashboard consumes.

Runs in CI with no dependencies. Checks the file parses and carries the shape
garage.html expects, so a bad export can't silently break the live dashboard.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PATH = ROOT / "web" / "vehicles" / "focus-st" / "garage.json"

REQUIRED_TOP = {
    "generated_at", "vehicle", "specs", "mods", "issues",
    "maintenance_due", "recalls", "costs", "sources",
}
REQUIRED_VEHICLE = {"vin", "year", "make", "model"}
REQUIRED_COSTS = {"mods", "parts", "service", "total"}
DUE_STATUSES = {"overdue", "due-soon", "ok", "unknown"}


def fail(msg: str) -> None:
    print(f"::error::garage.json: {msg}")
    sys.exit(1)


def main() -> None:
    if not PATH.exists():
        fail(f"missing at {PATH}")
    try:
        data = json.loads(PATH.read_text())
    except json.JSONDecodeError as e:
        fail(f"invalid JSON: {e}")

    missing = REQUIRED_TOP - data.keys()
    if missing:
        fail(f"missing top-level keys: {sorted(missing)}")

    if not isinstance(data["vehicle"], dict) or (REQUIRED_VEHICLE - data["vehicle"].keys()):
        fail(f"vehicle missing keys: {sorted(REQUIRED_VEHICLE - data.get('vehicle', {}).keys())}")

    if REQUIRED_COSTS - data["costs"].keys():
        fail(f"costs missing keys: {sorted(REQUIRED_COSTS - data['costs'].keys())}")

    for arr in ("specs", "mods", "issues", "maintenance_due", "recalls", "sources"):
        if not isinstance(data[arr], list):
            fail(f"'{arr}' must be a list")

    for d in data["maintenance_due"]:
        if d.get("status") not in DUE_STATUSES:
            fail(f"maintenance_due status '{d.get('status')}' not in {sorted(DUE_STATUSES)}")

    print(f"garage.json OK — {len(data['mods'])} mods, {len(data['recalls'])} recalls, "
          f"{len(data['maintenance_due'])} maintenance items, total ${data['costs']['total']}.")


if __name__ == "__main__":
    main()
