from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from fastapi import Query
from fastapi.responses import FileResponse

from .api import app
from .diagnostics_v2 import p04db_seed_case, generic_boost_case
from .maintenance_v2 import maintenance_dashboard

BASE = Path(__file__).resolve().parents[1]
DASHBOARD = BASE / "dashboard_v21.html"


@app.get("/dashboard")
def dashboard_v21() -> FileResponse:
    return FileResponse(DASHBOARD, media_type="text/html")


@app.get("/diagnostics/p04db")
def diagnostics_p04db() -> dict:
    case = p04db_seed_case()
    return {
        "id": str(case.id),
        "vehicle_id": case.vehicle_id,
        "title": case.title,
        "symptom": case.symptom,
        "status": case.status.value,
        "severity": case.severity,
        "dtcs": case.dtcs,
        "hypotheses": case.ranked_hypotheses(),
        "tests": case.next_tests(),
        "safety": "Preserve scan evidence before clearing codes; replacement is not a diagnostic test.",
    }


@app.get("/diagnostics/boost")
def diagnostics_boost(code: str | None = None) -> dict:
    case = generic_boost_case(code)
    return {
        "id": str(case.id),
        "title": case.title,
        "symptom": case.symptom,
        "dtcs": case.dtcs,
        "hypotheses": case.ranked_hypotheses(),
        "tests": case.next_tests(),
    }


@app.get("/maintenance/preview")
def maintenance_preview(mileage: int = Query(ge=0), severe_use: bool = False) -> dict:
    # No historical service is invented here. Empty records intentionally expose missing-history risk.
    items = maintenance_dashboard(mileage, records=[], severe_use=severe_use)
    return {
        "vehicle_id": "focus-st-2017",
        "mileage_mi": mileage,
        "severe_use": severe_use,
        "items": items,
        "disclaimer": "Garage reliability strategies are not automatically Ford-required intervals. Link OEM schedule claims before labeling a task OEM-required.",
    }
