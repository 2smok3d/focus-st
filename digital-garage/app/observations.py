"""Observation V2 + configuration/environment snapshots + event ledger service (V5).

Ties the semantic core into real records:
  * environment values are normalized to canonical units via `quantities`;
  * a configuration snapshot materializes the twin's component state (+ adjustable
    settings folded from the event ledger) at a point in time — so `config_at(T)`
    answers "what configuration was the machine running at time T?";
  * observations are directly-measured facts (never findings); two measurements are
    compared unit-aware (145 psi vs 1000 kPa are the same reading);
  * machine_events is append-only — state is a projection of it.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import quantities as q
from . import twin
from .models import Vehicle
from .obsmodels import (
    EVENT_KINDS,
    OBS_TYPES,
    SETTING_EVENT_KINDS,
    SUBJECT_KINDS,
    ConfigurationSnapshot,
    EnvironmentSnapshot,
    Instrument,
    MachineEvent,
    Observation,
)


def upsert_instrument(session: Session, code: str, name: str, kind: str | None = None) -> Instrument:
    row = session.scalar(select(Instrument).where(Instrument.code == code))
    if row is None:
        row = Instrument(code=code, name=name, kind=kind)
        session.add(row)
        session.flush()
    return row


def record_environment(session: Session, vehicle: Vehicle, *, ambient=None, ambient_unit="°C",
                       humidity_pct: float | None = None, baro=None, baro_unit="kPa",
                       elevation_m: float | None = None, weather: str | None = None,
                       taken_at: dt.datetime | None = None, note: str | None = None) -> EnvironmentSnapshot:
    """Store an environment snapshot, normalizing to canonical units (°C, kPa)."""
    amb_c = q.convert(ambient, ambient_unit, "°C") if ambient is not None else None
    baro_kpa = q.convert(baro, baro_unit, "kPa") if baro is not None else None
    row = EnvironmentSnapshot(vehicle_id=vehicle.id, ambient_c=amb_c, humidity_pct=humidity_pct,
                              baro_kpa=baro_kpa, elevation_m=elevation_m, weather=weather,
                              taken_at=taken_at or dt.datetime.now(dt.timezone.utc), note=note)
    session.add(row)
    session.flush()
    return row


def record_event(session: Session, vehicle: Vehicle, kind: str, *, component_slug: str | None = None,
                 detail: str | None = None, data: dict | None = None,
                 occurred_at: dt.datetime | None = None, source_label: str | None = None) -> MachineEvent:
    if kind not in EVENT_KINDS:
        raise ValueError(f"unknown event kind '{kind}'")
    row = MachineEvent(vehicle_id=vehicle.id, kind=kind, component_slug=component_slug,
                       detail=detail, data=data, source_label=source_label,
                       occurred_at=occurred_at or dt.datetime.now(dt.timezone.utc))
    session.add(row)
    session.flush()
    return row


def events_for(session: Session, vehicle_id: int, *, kind: str | None = None) -> list[dict]:
    stmt = select(MachineEvent).where(MachineEvent.vehicle_id == vehicle_id).order_by(
        MachineEvent.occurred_at, MachineEvent.id)
    if kind:
        stmt = stmt.where(MachineEvent.kind == kind)
    return [{"id": e.id, "kind": e.kind, "component": e.component_slug, "detail": e.detail,
             "data": e.data, "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None}
            for e in session.scalars(stmt)]


def _settings_at(session: Session, vehicle_id: int, when: dt.datetime) -> dict:
    """Fold adjustable-setting events (jetting/tune/gearing) up to `when`: latest wins."""
    settings: dict[str, dict] = {}
    for e in session.scalars(select(MachineEvent).where(
            MachineEvent.vehicle_id == vehicle_id,
            MachineEvent.kind.in_(SETTING_EVENT_KINDS),
            MachineEvent.occurred_at <= when).order_by(MachineEvent.occurred_at, MachineEvent.id)):
        settings[e.kind] = {"detail": e.detail, "data": e.data,
                            "at": e.occurred_at.isoformat() if e.occurred_at else None}
    return settings


def config_at(session: Session, vehicle: Vehicle, when: dt.datetime | None = None) -> dict:
    """The machine's configuration as of `when` — a projection over the temporal twin
    (component conditions) and the event ledger (adjustable settings)."""
    when = when or dt.datetime.now(dt.timezone.utc)
    states = twin.state_at(session, vehicle.id, when)
    components = {slug: {"condition": s.condition, "knowledge_state": s.knowledge_state,
                         "installed_part": s.installed_part} for slug, s in states.items()}
    return {"as_of": when.isoformat(), "components": components,
            "settings": _settings_at(session, vehicle.id, when)}


def snapshot_config(session: Session, vehicle: Vehicle, *, code: str | None = None,
                    at: dt.datetime | None = None, note: str | None = None) -> ConfigurationSnapshot:
    """Materialize the configuration at `at` (default now) into a stored snapshot."""
    at = at or dt.datetime.now(dt.timezone.utc)
    row = ConfigurationSnapshot(vehicle_id=vehicle.id, code=code,
                                config=config_at(session, vehicle, at), taken_at=at, note=note)
    session.add(row)
    session.flush()
    return row


def record_observation(session: Session, vehicle: Vehicle, *, subject_slug: str,
                       subject_kind: str = "component", obs_type: str = "mechanical",
                       method: str | None = None, instrument_code: str | None = None,
                       value: float | None = None, unit: str | None = None,
                       result_text: str | None = None, operating_condition: str | None = None,
                       confidence: float | None = None, config_snapshot_id: int | None = None,
                       environment_id: int | None = None, observed_at: dt.datetime | None = None,
                       note: str | None = None) -> Observation:
    """Record a directly-measured/observed fact (an Observation, never a Finding).

    A value+unit makes it a Measurement; the unit is validated so it can be compared
    unit-aware later. Also appends a MEASUREMENT_RECORDED event to the ledger.
    """
    if subject_kind not in SUBJECT_KINDS:
        raise ValueError(f"invalid subject_kind '{subject_kind}'")
    if obs_type not in OBS_TYPES:
        raise ValueError(f"invalid obs_type '{obs_type}'")
    if value is not None and unit is not None:
        q.to_canonical(value, unit)  # validates the unit is known/normalizable
    instrument_id = None
    if instrument_code:
        inst = session.scalar(select(Instrument).where(Instrument.code == instrument_code))
        instrument_id = inst.id if inst else None
    row = Observation(vehicle_id=vehicle.id, subject_kind=subject_kind, subject_slug=subject_slug,
                      obs_type=obs_type, operating_condition=operating_condition, method=method,
                      instrument_id=instrument_id, value=value, unit=unit, result_text=result_text,
                      confidence=confidence, config_snapshot_id=config_snapshot_id,
                      environment_id=environment_id,
                      observed_at=observed_at or dt.datetime.now(dt.timezone.utc), note=note)
    session.add(row)
    session.flush()
    if value is not None:
        record_event(session, vehicle, "MEASUREMENT_RECORDED", component_slug=subject_slug,
                     detail=f"{method or 'measurement'}: {value} {unit or ''}".strip(),
                     source_label="observation")
    return row


def observations_for(session: Session, vehicle_id: int, *, subject_slug: str | None = None) -> list[dict]:
    stmt = select(Observation).where(Observation.vehicle_id == vehicle_id).order_by(
        Observation.observed_at, Observation.id)
    if subject_slug:
        stmt = stmt.where(Observation.subject_slug == subject_slug)
    return [{"id": o.id, "subject": o.subject_slug, "type": o.obs_type, "method": o.method,
             "value": o.value, "unit": o.unit, "result": o.result_text,
             "operating_condition": o.operating_condition, "config_snapshot_id": o.config_snapshot_id,
             "environment_id": o.environment_id,
             "observed_at": o.observed_at.isoformat() if o.observed_at else None}
            for o in session.scalars(stmt)]


def measurements_agree(a: Observation, b: Observation, rel_tol: float = 0.02) -> bool:
    """Do two measurements represent the same reading, unit-aware? (145 psi == 1000 kPa)."""
    if a.value is None or b.value is None or not a.unit or not b.unit:
        raise ValueError("both observations must carry a value + unit")
    return q.agree(a.value, a.unit, b.value, b.unit, rel_tol=rel_tol)
