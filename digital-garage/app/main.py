"""FastAPI — local HTTP surface over the truth store.

Reads are open. Writes to the vehicle record go through /proposals (pending) and
only land via /proposals/{id}/approve, which requires an approver name. That is
the same approval boundary the CLI and MCP server honor.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import domain, service
from .db import get_session
from .models import Issue, MaintenanceInterval, Mod, Source, Spec

app = FastAPI(
    title="Digital Garage",
    version="0.1.0",
    description="Local truth store for a 2017 Ford Focus ST. Reads open; "
                "vehicle-record writes require human approval.",
)

_STATIC = Path(__file__).resolve().parent / "static"


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse("/ui")


@app.get("/ui", include_in_schema=False)
def approve_ui():
    """One-tap approval console for the proposal queue (served same-origin so it
    talks to this API without CORS). Open on your phone against the running API."""
    return FileResponse(_STATIC / "approve.html", media_type="text/html")


def _commit(s: Session):
    try:
        s.commit()
    except Exception:
        s.rollback()
        raise


# --- schemas ---------------------------------------------------------------
class ProposalIn(BaseModel):
    entity: str = Field(..., examples=["mod"])
    patch: dict = Field(..., examples=[{"slot": "Intercooler", "part_name": "Mishimoto FMIC"}])
    op: str = "insert"
    entity_id: int | None = None
    rationale: str | None = None
    proposed_by: str = "agent"


class ReceiptIn(BaseModel):
    # Either a structured receipt or raw email text. The Gmail Apps Script posts
    # the structured form; paste-in uses `text`.
    vendor: str | None = None
    date: str | None = None
    total: float | None = None
    currency: str | None = None
    items: list[str] | None = None
    order_id: str | None = None
    url: str | None = None
    email_id: str | None = None
    text: str | None = Field(None, description="Raw email body, if unstructured.")


class ApproveIn(BaseModel):
    approved_by: str = Field(..., examples=["Brandon"])


class RejectIn(BaseModel):
    approved_by: str | None = None
    reason: str | None = None


# --- meta ------------------------------------------------------------------
@app.get("/health")
def health():
    return {"ok": True}


@app.get("/vehicle")
def vehicle(s: Session = Depends(get_session)):
    v = service.get_vehicle(s)
    return {"id": v.id, "vin": v.vin, "year": v.year, "make": v.make,
            "model": v.model, "trim": v.trim, "engine": v.engine,
            "transmission": v.transmission, "notes": v.notes}


@app.get("/specs")
def specs(category: str | None = None, s: Session = Depends(get_session)):
    v = service.get_vehicle(s)
    stmt = select(Spec).where(Spec.vehicle_id == v.id)
    if category:
        stmt = stmt.where(Spec.category == category)
    rows = s.scalars(stmt.order_by(Spec.category, Spec.name)).all()
    return [{"category": r.category, "name": r.name, "value": r.value, "unit": r.unit,
             "verification": r.verification} for r in rows]


@app.get("/mods")
def mods(s: Session = Depends(get_session)):
    v = service.get_vehicle(s)
    rows = s.scalars(select(Mod).where(Mod.vehicle_id == v.id).order_by(Mod.slot)).all()
    return [{"id": r.id, "slot": r.slot, "part_name": r.part_name, "part_number": r.part_number,
             "stage": r.stage, "cost": float(r.cost) if r.cost is not None else None,
             "installed_on": r.installed_on.isoformat() if r.installed_on else None,
             "verification": r.verification} for r in rows]


@app.get("/issues")
def issues(status: str | None = None, s: Session = Depends(get_session)):
    v = service.get_vehicle(s)
    stmt = select(Issue).where(Issue.vehicle_id == v.id)
    if status:
        stmt = stmt.where(Issue.status == status)
    rows = s.scalars(stmt.order_by(Issue.opened_at.desc())).all()
    return [{"id": r.id, "title": r.title, "status": r.status, "severity": r.severity,
             "root_cause": r.root_cause, "verification": r.verification,
             "opened_at": r.opened_at.isoformat() if r.opened_at else None} for r in rows]


@app.get("/maintenance/due")
def maintenance_due(miles: int | None = Query(None, ge=0),
                    s: Session = Depends(get_session)):
    v = service.get_vehicle(s)
    return service.due_list(s, v.id, current_miles=miles, today=dt.date.today())


@app.get("/sessions")
def sessions(s: Session = Depends(get_session)):
    """List ingested diagnostic sessions with row counts."""
    v = service.get_vehicle(s)
    return service.list_sessions(s, v.id)


@app.get("/sessions/{session_id}/summary")
def session_summary(session_id: int, s: Session = Depends(get_session)):
    """Datalog summary: channel stats + turbo-relevant findings for a session."""
    try:
        return service.session_summary(s, session_id)
    except LookupError as e:
        raise HTTPException(404, str(e))


@app.get("/parts/search")
def parts_search(q: str, part_number: str | None = None):
    return domain.parts_search_links(q, part_number=part_number)


@app.get("/export/snapshot")
def export_snapshot(miles: int | None = Query(None, ge=0), s: Session = Depends(get_session)):
    """The full car as one JSON feed (vehicle, specs, mods, issues, due, costs) —
    what garage.json contains and the dashboard can read."""
    from .export import build_snapshot
    v = service.get_vehicle(s)
    return build_snapshot(s, v.id, current_miles=miles)


@app.get("/recalls")
def recalls(s: Session = Depends(get_session)):
    """Known + fetched recall campaigns for this vehicle."""
    v = service.get_vehicle(s)
    return service.list_recalls(s, v.id)


@app.post("/recalls/refresh")
def recalls_refresh(live: bool = True, s: Session = Depends(get_session)):
    """Re-seed the known baseline and (by default) fetch from NHTSA. Live-fetch
    failure is reported in the response but non-fatal."""
    v = service.get_vehicle(s)
    res = service.refresh_recalls(s, v, live=live)
    _commit(s)
    return res


class RecallStatusIn(BaseModel):
    status: str = Field(..., examples=["completed"])


@app.post("/recalls/{campaign}/status")
def recall_status(campaign: str, body: RecallStatusIn, s: Session = Depends(get_session)):
    v = service.get_vehicle(s)
    try:
        res = service.set_recall_status(s, v.id, campaign, body.status)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))
    _commit(s)
    return res


@app.get("/sources")
def sources(s: Session = Depends(get_session)):
    rows = s.scalars(select(Source).order_by(Source.authority)).all()
    return [{"id": r.id, "name": r.name, "kind": r.kind, "authority": r.authority,
             "authority_label": domain.authority_label(r.authority), "url": r.url} for r in rows]


# --- approval boundary -----------------------------------------------------
@app.get("/proposals")
def list_proposals(status: str | None = "pending", s: Session = Depends(get_session)):
    return service.list_proposals(s, status=status)


@app.post("/proposals", status_code=201)
def create_proposal(body: ProposalIn, s: Session = Depends(get_session)):
    v = service.get_vehicle(s)
    try:
        res = service.propose_change(
            s, v.id, body.entity, body.patch, op=body.op, entity_id=body.entity_id,
            rationale=body.rationale, proposed_by=body.proposed_by)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _commit(s)
    return res


@app.post("/receipts", status_code=201)
def ingest_receipt(body: ReceiptIn, s: Session = Depends(get_session)):
    """Accept a Gmail receipt (structured or raw text) and file it as a pending
    proposal. This is the endpoint the Gmail Apps Script posts to."""
    v = service.get_vehicle(s)
    payload: dict | str = body.text if body.text else body.model_dump(exclude_none=True)
    try:
        res = service.propose_from_receipt(s, v.id, payload)
    except ValueError as e:
        raise HTTPException(422, str(e))
    _commit(s)
    return res


@app.post("/proposals/{proposal_id}/approve")
def approve(proposal_id: int, body: ApproveIn, s: Session = Depends(get_session)):
    try:
        res = service.approve_proposal(s, proposal_id, body.approved_by)
        export = service.maybe_autoexport(s, service.get_vehicle(s).id)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))
    _commit(s)
    if export:
        res["exported"] = export
    return res


@app.post("/proposals/{proposal_id}/reject")
def reject(proposal_id: int, body: RejectIn, s: Session = Depends(get_session)):
    try:
        res = service.reject_proposal(s, proposal_id, body.approved_by or "", body.reason)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(422, str(e))
    _commit(s)
    return res


# ---------------------------------------------------------------------------
# V2 reference / intelligence — read-only endpoints mirroring the MCP tools.
# The only write surface stays the /proposals queue above; nothing here mutates.
# ---------------------------------------------------------------------------
@app.get("/v2/variant/{slug}")
def v2_variant(slug: str, s: Session = Depends(get_session)):
    from . import refservice
    header = refservice.variant_header(s, slug)
    if header is None:
        raise HTTPException(404, f"No reference variant '{slug}'.")
    return header


@app.get("/v2/systems/{slug}")
def v2_systems(slug: str, s: Session = Depends(get_session)):
    from . import refservice
    return refservice.system_tree(s, slug)


@app.get("/v2/component/{slug}/{comp_slug}")
def v2_component(slug: str, comp_slug: str, s: Session = Depends(get_session)):
    from . import refservice
    comp = refservice.get_component(s, slug, comp_slug)
    if comp is None:
        raise HTTPException(404, f"No component '{comp_slug}' on '{slug}'.")
    return comp


@app.get("/v2/claim")
def v2_claim(subject_key: str, prop: str, s: Session = Depends(get_session)):
    """A single claim with its evidence and a freshly re-resolved verdict."""
    from . import refservice
    claim = refservice.get_claim(s, subject_key, prop)
    if claim is None:
        raise HTTPException(404, f"No claim {subject_key}:{prop}.")
    return claim


@app.get("/v2/claims")
def v2_claims(subject_type: str, subject_key: str, s: Session = Depends(get_session)):
    from . import refservice
    return refservice.claims_for(s, subject_type, subject_key)


@app.get("/v2/conflicts")
def v2_conflicts(s: Session = Depends(get_session)):
    from . import refservice
    return refservice.list_conflicts(s)


@app.get("/v2/knowledge/{slug}")
def v2_knowledge(slug: str, s: Session = Depends(get_session)):
    from . import knowledge
    return knowledge.quality_report(s, slug)


@app.get("/v2/trends")
def v2_trends(s: Session = Depends(get_session)):
    from . import trends
    return trends.component_trends(s, service.get_vehicle(s).id)


@app.get("/v2/anomalies")
def v2_anomalies(s: Session = Depends(get_session)):
    from . import anomaly
    return anomaly.component_anomalies(s, service.get_vehicle(s).id)


@app.get("/v2/rul")
def v2_rul(s: Session = Depends(get_session)):
    from . import rul
    return rul.maintenance_rul(s, service.get_vehicle(s).id)


@app.get("/v2/integrity")
def v2_integrity(s: Session = Depends(get_session)):
    from . import integrity
    return integrity.vehicle_integrity(s, service.get_vehicle(s).id)


@app.get("/v2/corroboration/{slug}")
def v2_corroboration(slug: str, s: Session = Depends(get_session)):
    from . import corroborate
    return corroborate.corroboration_candidates(s, slug)


@app.get("/v2/fitment/{slug}")
def v2_fitment(slug: str, s: Session = Depends(get_session)):
    from . import fitment
    return fitment.catalog_fitment(s, slug)


@app.get("/v2/intel/{slug}")
def v2_intel(slug: str, s: Session = Depends(get_session)):
    """The full intelligence projection for a machine (same dict `cli intel` writes)."""
    from . import intel
    return intel.build_intel(s, slug)
