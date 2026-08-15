"""FastMCP server — how Claude talks to the garage.

Read-first by design. Every query tool is exposed. The ONLY write tool is
`propose_change`, which records a pending proposal for a human to approve via the
CLI — the MCP surface deliberately has no approve tool, so an agent can see
everything and change nothing without a name on it.

Run:  python -m app.mcp_server      (stdio transport)
"""
from __future__ import annotations

import datetime as dt

from fastmcp import FastMCP
from sqlalchemy import select

from . import domain, service
from .db import session_scope
from .models import Dtc, Issue, Mod, Source, Spec

mcp = FastMCP("digital-garage")


# --- reads -----------------------------------------------------------------
@mcp.tool
def get_vehicle() -> dict:
    """Return the tracked vehicle's identity and drivetrain summary."""
    with session_scope() as s:
        v = service.get_vehicle(s)
        return {"vin": v.vin, "year": v.year, "make": v.make, "model": v.model,
                "trim": v.trim, "engine": v.engine, "transmission": v.transmission,
                "notes": v.notes}


@mcp.tool
def get_specs(category: str | None = None) -> list[dict]:
    """List graded vehicle specs. Optionally filter by category
    (engine, drivetrain, chassis, fluids, torque). Each spec carries a
    verification state (UNVERIFIED..VEHICLE_VERIFIED)."""
    with session_scope() as s:
        v = service.get_vehicle(s)
        stmt = select(Spec).where(Spec.vehicle_id == v.id)
        if category:
            stmt = stmt.where(Spec.category == category)
        rows = s.scalars(stmt.order_by(Spec.category, Spec.name)).all()
        return [{"category": r.category, "name": r.name, "value": r.value,
                 "unit": r.unit, "verification": r.verification} for r in rows]


@mcp.tool
def get_mods() -> list[dict]:
    """List installed modifications (parts diverging from stock)."""
    with session_scope() as s:
        v = service.get_vehicle(s)
        rows = s.scalars(select(Mod).where(Mod.vehicle_id == v.id).order_by(Mod.slot)).all()
        return [{"id": r.id, "slot": r.slot, "part_name": r.part_name,
                 "part_number": r.part_number, "stage": r.stage,
                 "verification": r.verification} for r in rows]


@mcp.tool
def get_issues(status: str | None = None) -> list[dict]:
    """List known issues/faults. Optional status: open, monitoring, resolved."""
    with session_scope() as s:
        v = service.get_vehicle(s)
        stmt = select(Issue).where(Issue.vehicle_id == v.id)
        if status:
            stmt = stmt.where(Issue.status == status)
        rows = s.scalars(stmt.order_by(Issue.opened_at.desc())).all()
        return [{"id": r.id, "title": r.title, "status": r.status,
                 "severity": r.severity, "root_cause": r.root_cause,
                 "verification": r.verification} for r in rows]


@mcp.tool
def maintenance_due(current_miles: int | None = None) -> list[dict]:
    """What maintenance is overdue / due-soon / ok at the given odometer reading.
    Sorted worst-first."""
    with session_scope() as s:
        v = service.get_vehicle(s)
        return service.due_list(s, v.id, current_miles=current_miles, today=dt.date.today())


@mcp.tool
def find_dtc(code: str) -> list[dict]:
    """Look up every recorded occurrence of a DTC (e.g. P0299) across diagnostic
    sessions, with the module and status it was seen in."""
    with session_scope() as s:
        rows = s.scalars(select(Dtc).where(Dtc.code == code.strip().upper())).all()
        return [{"session_id": r.session_id, "code": r.code, "module": r.module,
                 "status": r.status, "description": r.description} for r in rows]


@mcp.tool
def list_sessions() -> list[dict]:
    """List ingested diagnostic sessions (FORScan/candump/datalog) with row counts."""
    with session_scope() as s:
        v = service.get_vehicle(s)
        return service.list_sessions(s, v.id)


@mcp.tool
def session_summary(session_id: int) -> dict:
    """Summarize a datalog session: channel stats + turbo-relevant findings
    (boost tracking, knock, misfire, fuel-trim drift, temps, rail pressure).
    Answers 'was that pull safe?' from an ingested log."""
    with session_scope() as s:
        return service.session_summary(s, session_id)


@mcp.tool
def parts_search(query: str, part_number: str | None = None) -> dict:
    """Generate retailer search links for a part (Amazon, eBay, RockAuto, Summit,
    Google), scoped to the vehicle when no part number is given."""
    return domain.parts_search_links(query, part_number=part_number)


@mcp.tool
def check_recalls(refresh: bool = False) -> list[dict]:
    """List recall / safety campaigns for the vehicle. With refresh=True, re-seed
    the known baseline and try a live NHTSA fetch first (non-fatal if the network
    is unavailable). Per-VIN completion isn't in the free API — 'unknown' status
    means confirm at a dealer."""
    with session_scope() as s:
        v = service.get_vehicle(s)
        if refresh:
            service.refresh_recalls(s, v, live=True)
        return service.list_recalls(s, v.id)


@mcp.tool
def list_sources() -> list[dict]:
    """List evidence sources with their authority rank (1 best .. 6 unknown)."""
    with session_scope() as s:
        rows = s.scalars(select(Source).order_by(Source.authority)).all()
        return [{"id": r.id, "name": r.name, "authority": r.authority,
                 "authority_label": domain.authority_label(r.authority)} for r in rows]


@mcp.tool
def list_proposals(status: str = "pending") -> list[dict]:
    """List change proposals (pending by default). Read-only — approval is
    human-only via the CLI."""
    with session_scope() as s:
        return service.list_proposals(s, status=status or None)


# --- the only write: propose (never commit) --------------------------------
@mcp.tool
def propose_change(entity: str, patch: dict, op: str = "insert",
                   entity_id: int | None = None, rationale: str | None = None) -> dict:
    """Propose a change to the vehicle record for HUMAN APPROVAL. This does NOT
    modify the car's data — it records a pending proposal that a person must
    approve via `python -m app.cli approve`.

    entity: one of 'mod', 'issue', 'spec', 'service_event'.
    patch:  the fields to set (validated against an allow-list per entity).
    op:     'insert' (default) or 'update' (requires entity_id).
    Always include a clear `rationale` — the human reviewing it needs your reasoning.
    """
    with session_scope() as s:
        v = service.get_vehicle(s)
        return service.propose_change(s, v.id, entity, patch, op=op,
                                      entity_id=entity_id, rationale=rationale,
                                      proposed_by="mcp-agent")


@mcp.tool
def log_receipt(text: str) -> dict:
    """Parse a pasted purchase/service receipt and file it as a pending proposal
    (a parts purchase or a service event) for HUMAN APPROVAL. Does not modify the
    car's record — a person approves via `python -m app.cli approve`."""
    with session_scope() as s:
        v = service.get_vehicle(s)
        return service.propose_from_receipt(s, v.id, text, proposed_by="mcp-agent")


if __name__ == "__main__":
    mcp.run()
