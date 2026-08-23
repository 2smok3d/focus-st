"""Service layer — DB operations shared by the API, CLI, and MCP server.

This is where the approval boundary is enforced: `propose_change` only ever
writes a pending row to change_proposals; `approve_proposal` is the *only* path
that mutates a real entity, and it requires an approver name.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import domain
from . import provenance as pv
from .models import (
    CanFrame,
    ChangeProposal,
    DiagnosticSession,
    Dtc,
    Issue,
    MaintenanceInterval,
    Measurement,
    Mod,
    OdometerReading,
    Part,
    Recall,
    ServiceEvent,
    Spec,
    Vehicle,
)

# Maps a proposable entity name to its ORM class.
_ENTITY_MODELS = {
    "mod": Mod,
    "issue": Issue,
    "spec": Spec,
    "service_event": ServiceEvent,
    "parts": Part,
}

# Stances an evidence row can take toward a claim (from the provenance engine).
_EVIDENCE_STANCES = pv.STANCES

# Columns that must be coerced from ISO strings (JSON has no date type).
_DATE_FIELDS = {"installed_on", "opened_at", "resolved_at", "performed_at"}


def get_vehicle(session: Session, vin: str | None = None) -> Vehicle:
    stmt = select(Vehicle)
    if vin:
        stmt = stmt.where(Vehicle.vin == vin)
    v = session.scalar(stmt.order_by(Vehicle.id))
    if v is None:
        raise LookupError("No vehicle in the store. Run `python -m app.cli seed`.")
    return v


# ---------------------------------------------------------------------------
# Maintenance-due
# ---------------------------------------------------------------------------
def due_list(session: Session, vehicle_id: int, current_miles: int | None,
             today: dt.date | None = None) -> list[dict]:
    """Evaluate every maintenance interval against the latest matching service."""
    intervals = session.scalars(
        select(MaintenanceInterval).where(MaintenanceInterval.vehicle_id == vehicle_id)
    ).all()

    out: list[dict] = []
    for iv in intervals:
        last = session.scalar(
            select(ServiceEvent)
            .where(ServiceEvent.vehicle_id == vehicle_id, ServiceEvent.item == iv.item)
            .order_by(ServiceEvent.performed_at.desc())
        )
        status = domain.maintenance_due(
            item=iv.item,
            interval_miles=iv.interval_miles,
            interval_months=iv.interval_months,
            last_miles=last.miles if last else None,
            last_date=last.performed_at if last else None,
            current_miles=current_miles,
            today=today,
        )
        row = status.as_dict()
        row["verification"] = iv.verification
        out.append(row)

    order = {"overdue": 0, "due-soon": 1, "unknown": 2, "ok": 3}
    out.sort(key=lambda r: (order.get(r["status"], 9), r["miles_remaining"] if r["miles_remaining"] is not None else 1 << 30))
    return out


def latest_odometer(session: Session, vehicle_id: int) -> int | None:
    """Most-recent recorded mileage, or None if the vehicle has no odometer history."""
    row = session.scalar(
        select(OdometerReading)
        .where(OdometerReading.vehicle_id == vehicle_id)
        .order_by(OdometerReading.recorded_at.desc())
    )
    return row.miles if row else None


# The five maintenance states the intelligence layer speaks. `needs_log` is kept
# distinct from `overdue`: an item with a defined interval but no service on record
# isn't *known* to be past due — we simply have no history for it, and saying
# OVERDUE would be a claim we can't back.
MAINT_STATES = ("overdue", "due_soon", "needs_log", "unknown", "ok")


def maintenance_summary(session: Session, vehicle_id: int,
                        today: dt.date | None = None) -> dict:
    """Project the maintenance-due engine into status buckets for one machine,
    measured against its latest odometer reading. Read-only."""
    current_miles = latest_odometer(session, vehicle_id)
    counts = {s: 0 for s in MAINT_STATES}
    items: list[dict] = []
    for r in due_list(session, vehicle_id, current_miles=current_miles, today=today):
        logged = r["last_miles"] is not None or r["last_date"] is not None
        state = r["status"].replace("-", "_")            # "due-soon" → "due_soon"
        if state == "overdue" and not logged:
            state = "needs_log"
        counts[state] = counts.get(state, 0) + 1
        items.append({"item": r["item"], "status": state, "detail": r["detail"],
                      "miles_remaining": r["miles_remaining"],
                      "last_miles": r["last_miles"], "last_date": r["last_date"],
                      "verification": r.get("verification")})
    order = {s: i for i, s in enumerate(MAINT_STATES)}
    items.sort(key=lambda x: order.get(x["status"], 9))
    return {
        "current_miles": current_miles,
        "counts": counts,
        "attention": counts["overdue"] + counts["due_soon"],  # what a human should act on now
        "tracked": len(items),
        "items": items,
    }


# ---------------------------------------------------------------------------
# Approval boundary
# ---------------------------------------------------------------------------
def propose_change(session: Session, vehicle_id: int, entity: str, patch: dict,
                   *, op: str = "insert", entity_id: int | None = None,
                   rationale: str | None = None, proposed_by: str = "agent") -> dict:
    """Record a pending change. Never mutates the target entity."""
    ok, msg = domain.validate_patch(entity, patch)
    if not ok:
        raise ValueError(msg)

    prop = ChangeProposal(
        vehicle_id=vehicle_id, entity=entity, op=op, entity_id=entity_id,
        patch=patch, rationale=rationale, proposed_by=proposed_by, status="pending",
    )
    session.add(prop)
    session.flush()
    return {"proposal_id": prop.id, "status": "pending", "entity": entity, "patch": patch}


def _validate_claim_patch(patch: dict) -> None:
    """Structural checks a claim proposal must pass before it can be queued. The
    verdict is NOT decided here — it is computed from evidence on approval."""
    for req in ("subject_type", "subject_key", "prop"):
        if not patch.get(req):
            raise ValueError(f"claim proposal missing required field '{req}'.")
    evidence = patch.get("evidence") or []
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("claim proposal needs at least one evidence item.")
    for e in evidence:
        if not isinstance(e, dict):
            raise ValueError("each evidence item must be an object.")
        auth = e.get("authority")
        if not isinstance(auth, int) or not (1 <= auth <= 6):
            raise ValueError("evidence.authority must be an int 1 (best) .. 6 (unknown).")
        stance = e.get("stance", pv.SUPPORTS)
        if stance not in _EVIDENCE_STANCES:
            raise ValueError(f"evidence.stance must be one of {sorted(_EVIDENCE_STANCES)}.")


def propose_claim(session: Session, vehicle_id: int, *, subject_type: str, subject_key: str,
                  prop: str, value: str | None = None, unit: str | None = None,
                  applicability: dict | None = None, evidence: list[dict],
                  rationale: str | None = None, proposed_by: str = "agent") -> dict:
    """Propose a V2 reference *claim* for human approval. Records a pending proposal
    and NEVER mutates canonical knowledge. The claim's trust grade is computed from
    its evidence on approval, not asserted here."""
    patch = {"subject_type": subject_type, "subject_key": subject_key, "prop": prop,
             "value": value, "unit": unit, "applicability": applicability,
             "evidence": evidence}
    ok, msg = domain.validate_patch("claim", {k: v for k, v in patch.items() if v is not None})
    if not ok:
        raise ValueError(msg)
    _validate_claim_patch(patch)
    prop_row = ChangeProposal(vehicle_id=vehicle_id, entity="claim", op="insert",
                              patch=patch, rationale=rationale, proposed_by=proposed_by,
                              status="pending")
    session.add(prop_row)
    session.flush()
    return {"proposal_id": prop_row.id, "status": "pending", "entity": "claim",
            "subject": f"{subject_type}:{subject_key}:{prop}"}


def _apply_claim_proposal(session: Session, patch: dict) -> int:
    """Create (or corroborate) a claim from an approved proposal and re-resolve its
    verdict from ALL its evidence. Monotonic by construction: added evidence can only
    re-resolve against the full set, so a weaker source never demotes a stronger one."""
    from .refmodels import Claim, ClaimEvidence

    claim = session.scalar(select(Claim).where(
        Claim.subject_type == patch["subject_type"],
        Claim.subject_key == patch["subject_key"],
        Claim.prop == patch["prop"]))
    if claim is None:
        claim = Claim(subject_type=patch["subject_type"], subject_key=patch["subject_key"],
                      prop=patch["prop"], value=patch.get("value"), unit=patch.get("unit"),
                      applicability=patch.get("applicability"))
        session.add(claim)
        session.flush()

    for e in patch["evidence"]:
        session.add(ClaimEvidence(
            claim_id=claim.id, authority=e["authority"], stance=e.get("stance", pv.SUPPORTS),
            on_vehicle=bool(e.get("on_vehicle", False)), source_label=e.get("label")))
    session.flush()

    # Re-resolve from the claim's full evidence set (existing + newly added).
    rows = session.scalars(select(ClaimEvidence).where(ClaimEvidence.claim_id == claim.id)).all()
    ev_objs = [pv.Evidence(authority=r.authority, stance=r.stance,
                           on_vehicle=r.on_vehicle, source_label=r.source_label or "")
               for r in rows]
    verdict = pv.resolve_verdict(ev_objs)
    claim.verification = verdict.verification.name
    claim.confidence = verdict.confidence
    claim.conflict = verdict.conflict
    claim.notes = verdict.rationale
    session.flush()
    return claim.id


def list_sessions(session: Session, vehicle_id: int) -> list[dict]:
    from sqlalchemy import func
    rows = session.scalars(
        select(DiagnosticSession).where(DiagnosticSession.vehicle_id == vehicle_id)
        .order_by(DiagnosticSession.ingested_at.desc())
    ).all()
    out = []
    for ds in rows:
        dtc_n = session.scalar(select(func.count(Dtc.id)).where(Dtc.session_id == ds.id))
        meas_n = session.scalar(select(func.count(Measurement.id)).where(Measurement.session_id == ds.id))
        can_n = session.scalar(select(func.count(CanFrame.id)).where(CanFrame.session_id == ds.id))
        out.append({"id": ds.id, "kind": ds.kind, "miles": ds.miles,
                    "captured_at": ds.captured_at.isoformat() if ds.captured_at else None,
                    "ingested_at": ds.ingested_at.isoformat() if ds.ingested_at else None,
                    "sha256": ds.sha256, "dtcs": dtc_n, "measurements": meas_n,
                    "can_frames": can_n, "note": ds.note})
    return out


def session_summary(session: Session, session_id: int) -> dict:
    from . import analysis
    ds = session.get(DiagnosticSession, session_id)
    if ds is None:
        raise LookupError(f"Diagnostic session {session_id} not found.")
    meas = [{"pid": m.pid, "value": m.value, "unit": m.unit, "t_offset_s": m.t_offset_s}
            for m in session.scalars(select(Measurement).where(Measurement.session_id == session_id)
                                     .order_by(Measurement.id)).all()]
    dtc_n = len(session.scalars(select(Dtc).where(Dtc.session_id == session_id)).all())
    can_n = len(session.scalars(select(CanFrame).where(CanFrame.session_id == session_id)).all())
    summary = analysis.summarize_measurements(meas, dtc_count=dtc_n, can_count=can_n)
    summary["session_id"] = session_id
    summary["kind"] = ds.kind
    return summary


def _upsert_recall(session: Session, vehicle_id: int, row: dict) -> None:
    existing = session.scalar(select(Recall).where(
        Recall.vehicle_id == vehicle_id,
        Recall.campaign_number == row["campaign_number"]))
    if existing is None:
        session.add(Recall(vehicle_id=vehicle_id, **row))
        return
    # Update fields from the incoming row, but never downgrade a human-set status
    # (a confirmed 'completed' must survive a refresh) or weaken verification.
    from . import domain
    for k, v in row.items():
        if k == "status":
            continue
        if k == "verification" and not domain.can_override(v, existing.verification):
            continue
        if v is not None:
            setattr(existing, k, v)
    existing.fetched_at = dt.datetime.now(dt.timezone.utc)


def seed_known_recalls(session: Session, vehicle_id: int) -> int:
    from . import recalls
    for row in recalls.KNOWN:
        _upsert_recall(session, vehicle_id, dict(row))
    session.flush()
    return len(recalls.KNOWN)


def refresh_recalls(session: Session, vehicle: Vehicle, *, live: bool = True) -> dict:
    """Seed the known baseline, then (optionally) augment from NHTSA. Live-fetch
    failure is non-fatal — the baseline still stands."""
    from . import recalls
    seeded = seed_known_recalls(session, vehicle.id)
    fetched = 0
    error = None
    if live:
        try:
            rows = recalls.fetch_nhtsa(vehicle.make or "ford", vehicle.model or "focus",
                                       vehicle.year or 2017)
            for row in rows:
                _upsert_recall(session, vehicle.id, row)
            fetched = len(rows)
        except Exception as e:  # network/policy/parse — keep the baseline
            error = f"{type(e).__name__}: {e}"
    session.flush()
    return {"known_seeded": seeded, "nhtsa_fetched": fetched, "error": error}


def list_recalls(session: Session, vehicle_id: int) -> list[dict]:
    rows = session.scalars(select(Recall).where(Recall.vehicle_id == vehicle_id)
                           .order_by(Recall.origin, Recall.campaign_number)).all()
    return [{"campaign_number": r.campaign_number, "origin": r.origin,
             "component": r.component, "summary": r.summary, "remedy": r.remedy,
             "consequence": r.consequence, "status": r.status,
             "report_date": r.report_date.isoformat() if r.report_date else None,
             "verification": r.verification, "note": r.note} for r in rows]


def set_recall_status(session: Session, vehicle_id: int, campaign_number: str,
                      status: str) -> dict:
    if status not in ("unknown", "open", "completed"):
        raise ValueError("status must be unknown | open | completed")
    r = session.scalar(select(Recall).where(
        Recall.vehicle_id == vehicle_id, Recall.campaign_number == campaign_number))
    if r is None:
        raise LookupError(f"No recall {campaign_number} on record.")
    r.status = status
    if status == "completed":
        r.verification = "VEHICLE_VERIFIED"
    session.flush()
    return {"campaign_number": campaign_number, "status": status}


def propose_from_receipt(session: Session, vehicle_id: int, payload: dict | str,
                         *, proposed_by: str = "gmail-receipt") -> dict:
    """Parse a receipt, classify it, and file it as a pending proposal."""
    from . import receipts  # local import keeps domain/service import graph flat

    receipt = receipts.parse_receipt(payload)
    cls = receipts.classify(receipt)
    res = propose_change(session, vehicle_id, cls.entity, cls.patch,
                         rationale=cls.rationale, proposed_by=proposed_by)
    res["receipt"] = receipt.as_dict()
    res["classified_as"] = cls.entity
    return res


def list_proposals(session: Session, status: str | None = "pending") -> list[dict]:
    stmt = select(ChangeProposal).order_by(ChangeProposal.created_at.desc())
    if status:
        stmt = stmt.where(ChangeProposal.status == status)
    rows = session.scalars(stmt).all()
    return [{
        "id": p.id, "entity": p.entity, "op": p.op, "entity_id": p.entity_id,
        "patch": p.patch, "rationale": p.rationale, "status": p.status,
        "proposed_by": p.proposed_by, "approved_by": p.approved_by,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    } for p in rows]


def _coerce(patch: dict) -> dict:
    out = dict(patch)
    for f in _DATE_FIELDS:
        if isinstance(out.get(f), str) and out[f]:
            out[f] = dt.date.fromisoformat(out[f])
    return out


def maybe_autoexport(session: Session, vehicle_id: int) -> dict | None:
    """Regenerate MODS.md + garage.json after a record change, if enabled. Any
    failure is swallowed to a dict — a broken export must never fail an approval."""
    from .config import settings
    if not settings.auto_export:
        return None
    try:
        from . import export as export_mod
        return export_mod.write_export(session, vehicle_id)
    except Exception as e:  # export is a side effect, not part of the approval
        return {"error": f"{type(e).__name__}: {e}"}


def approve_proposal(session: Session, proposal_id: int, approved_by: str) -> dict:
    """Apply a pending proposal. The ONLY path that mutates a real entity."""
    if not approved_by or not approved_by.strip():
        raise ValueError("approved_by is required — a human name must be on the change.")

    prop = session.get(ChangeProposal, proposal_id)
    if prop is None:
        raise LookupError(f"Proposal {proposal_id} not found.")
    if prop.status != "pending":
        raise ValueError(f"Proposal {proposal_id} is already {prop.status}.")

    # A claim proposal has its own apply path — it writes into the V2 reference model
    # (claim + evidence) and resolves the verdict, not a vehicle-scoped V1 entity.
    if prop.entity == "claim":
        applied_id = _apply_claim_proposal(session, prop.patch)
        prop.status = "approved"
        prop.approved_by = approved_by.strip()
        prop.decided_at = dt.datetime.now(dt.timezone.utc)
        prop.applied_id = applied_id
        session.flush()
        return {"proposal_id": prop.id, "status": "approved", "approved_by": prop.approved_by,
                "entity": "claim", "applied_id": applied_id}

    Model = _ENTITY_MODELS[prop.entity]
    data = _coerce(prop.patch)

    if prop.op == "update":
        if prop.entity_id is None:
            raise ValueError("Update proposal missing entity_id.")
        target = session.get(Model, prop.entity_id)
        if target is None:
            raise LookupError(f"{prop.entity} #{prop.entity_id} not found.")
        # Verification guard: a weaker claim may not silently override a stronger.
        if "verification" in data and hasattr(target, "verification"):
            if not domain.can_override(data["verification"], target.verification):
                raise ValueError(
                    f"Refusing to override {target.verification} with weaker "
                    f"{data['verification']} (KB rule: lower states never override higher).")
        for k, v in data.items():
            setattr(target, k, v)
        applied_id = target.id
    else:  # insert
        obj = Model(vehicle_id=prop.vehicle_id, **data)
        session.add(obj)
        session.flush()
        applied_id = obj.id

    prop.status = "approved"
    prop.approved_by = approved_by.strip()
    prop.decided_at = dt.datetime.now(dt.timezone.utc)
    prop.applied_id = applied_id
    session.flush()
    return {"proposal_id": prop.id, "status": "approved", "approved_by": prop.approved_by,
            "entity": prop.entity, "applied_id": applied_id}


def reject_proposal(session: Session, proposal_id: int, approved_by: str,
                    reason: str | None = None) -> dict:
    prop = session.get(ChangeProposal, proposal_id)
    if prop is None:
        raise LookupError(f"Proposal {proposal_id} not found.")
    if prop.status != "pending":
        raise ValueError(f"Proposal {proposal_id} is already {prop.status}.")
    prop.status = "rejected"
    prop.approved_by = (approved_by or "").strip() or None
    prop.decided_at = dt.datetime.now(dt.timezone.utc)
    if reason:
        prop.rationale = f"{prop.rationale or ''}\n[rejected] {reason}".strip()
    session.flush()
    return {"proposal_id": prop.id, "status": "rejected"}
