from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from .parts import search_catalog, shopping_links, slot_by_id
from .vehicle_state import CURRENT_SEED_EVENTS, current_seed_snapshot

BASE = Path(__file__).resolve().parents[1]
ENGINE_BAY_FILE = BASE / "data" / "focus_st_2017_engine_bay.json"

mcp = FastMCP("Digital Mechanic's Garage v2")


def load_engine_bay() -> dict:
    return json.loads(ENGINE_BAY_FILE.read_text(encoding="utf-8"))


@mcp.tool()
def garage_vehicle_profile() -> dict:
    return {
        "vehicle_id": "focus-st-2017",
        "year": 2017,
        "make": "Ford",
        "model": "Focus ST",
        "engine": "2.0L GTDI EcoBoost I4",
        "transmission": "Getrag-Ford MMT6 6-speed manual",
        "write_mode": "disabled",
    }


@mcp.tool()
def garage_current_component_state(component_id: str | None = None) -> dict:
    ids = [c["id"] for c in load_engine_bay().get("components", [])]
    state = current_seed_snapshot(ids)
    if component_id:
        if component_id not in state:
            return {"error": "component not found", "component_id": component_id}
        return vars(state[component_id])
    return {key: vars(value) for key, value in state.items()}


@mcp.tool()
def garage_engine_bay_component(component_id: str) -> dict:
    for component in load_engine_bay().get("components", []):
        if component.get("id") == component_id:
            return component
    return {"error": "component not found", "component_id": component_id}


@mcp.tool()
def garage_engine_bay_list(system: str | None = None, state: str | None = None) -> list[dict]:
    components = load_engine_bay().get("components", [])
    if system:
        components = [c for c in components if c.get("system") == system]
    if state:
        components = [c for c in components if c.get("state") == state]
    return components


@mcp.tool()
def garage_part_slot(slot: str) -> dict:
    return slot_by_id(slot) or {"error": "part slot not found", "slot": slot}


@mcp.tool()
def garage_parts_search(query: str) -> dict:
    return {
        "query": query,
        "catalog_matches": search_catalog(query),
        "shopping_links": shopping_links(query),
        "warning": "Marketplace search results do not prove fitment.",
    }


@mcp.tool()
def garage_safety_capabilities() -> dict:
    return {
        "read_only_default": True,
        "implemented_vehicle_write_tools": [],
        "human_approval_required": [
            "clear DTC",
            "risky actuator command",
            "module configuration",
            "flash/reprogramming",
            "ECU write",
            "arbitrary CAN transmission",
        ],
    }


@mcp.tool()
def garage_seed_evidence_summary() -> dict:
    return {
        "event_count": len(CURRENT_SEED_EVENTS),
        "events": [vars(e) for e in CURRENT_SEED_EVENTS],
        "policy": "legacy Drive/repo records remain unchanged and are used only as read-only evidence",
    }


if __name__ == "__main__":
    mcp.run()
