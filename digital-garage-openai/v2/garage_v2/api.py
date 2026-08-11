from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse

from .parts import load_parts, search_catalog, shopping_links, slot_by_id
from .vehicle_state import CURRENT_SEED_EVENTS, current_seed_snapshot

BASE = Path(__file__).resolve().parents[1]
ENGINE_BAY_FILE = BASE / "data" / "focus_st_2017_engine_bay.json"
VISUAL_FILE = BASE / "visual_engine_bay.html"

app = FastAPI(
    title="Digital Mechanic's Garage v2",
    version="2.0.0-dev",
    description="Read-first digital mechanic platform for the 2017 Ford Focus ST.",
)


def load_engine_bay() -> dict:
    return json.loads(ENGINE_BAY_FILE.read_text(encoding="utf-8"))


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "vehicle": "focus-st-2017", "vehicle_writes": False}


@app.get("/", response_class=HTMLResponse)
def root() -> str:
    return """
    <html><body style='font-family:system-ui;background:#0b0d10;color:#e8edf3;padding:30px'>
    <h1>Digital Mechanic's Garage v2</h1>
    <p>2017 Ford Focus ST · read-first vehicle digital twin</p>
    <ul>
      <li><a href='/visual/engine-bay'>Interactive Engine Bay</a></li>
      <li><a href='/docs'>API Docs</a></li>
      <li><a href='/data/engine-bay'>Engine Bay JSON</a></li>
      <li><a href='/data/parts'>Parts Knowledge JSON</a></li>
      <li><a href='/state/current'>Current Vehicle State</a></li>
    </ul>
    </body></html>
    """


@app.get("/visual/engine-bay")
def visual_engine_bay() -> FileResponse:
    return FileResponse(VISUAL_FILE, media_type="text/html")


@app.get("/data/engine-bay")
def engine_bay() -> dict:
    return load_engine_bay()


@app.get("/data/engine-bay/{component_id}")
def engine_bay_component(component_id: str) -> dict:
    for component in load_engine_bay().get("components", []):
        if component.get("id") == component_id:
            return component
    raise HTTPException(404, "component not found")


@app.get("/data/parts")
def parts() -> dict:
    return load_parts()


@app.get("/data/parts/{slot}")
def part_slot(slot: str) -> dict:
    item = slot_by_id(slot)
    if not item:
        raise HTTPException(404, "part slot not found")
    return item


@app.get("/search/parts")
def parts_search(q: str = Query(min_length=1)) -> dict:
    return {
        "query": q,
        "fitment_warning": "Search results are discovery only; independently verify fitment before purchase.",
        "matches": search_catalog(q),
        "shopping": shopping_links(q),
    }


@app.get("/shopping-links")
def shopping(q: str = Query(min_length=1)) -> dict:
    return {
        "query": q,
        "fitment_warning": "Search links are not proof of fitment.",
        "links": shopping_links(q),
    }


@app.get("/state/current")
def current_state() -> dict:
    component_ids = [c["id"] for c in load_engine_bay().get("components", [])]
    snapshots = current_seed_snapshot(component_ids)
    return {
        "vehicle_id": "focus-st-2017",
        "seed_event_count": len(CURRENT_SEED_EVENTS),
        "source_policy": "existing /FOST and legacy repo are read-only evidence; v2 derived state is separate",
        "components": {k: vars(v) for k, v in snapshots.items()},
    }


@app.get("/safety")
def safety() -> dict:
    return {
        "read_only_default": True,
        "implemented_vehicle_write_actions": [],
        "approval_required": [
            "clear_dtc",
            "risky_actuator_test",
            "module_configuration",
            "ecu_or_module_flash",
            "ecu_write",
            "arbitrary_can_transmit",
        ],
    }
