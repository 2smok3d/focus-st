"""Observation V2 + configuration/environment snapshots + machine-event ledger (V5).

Additive to models.py. An Observation is a directly-measured/observed fact (never a
Finding); with a value+unit+method+instrument it is a Measurement. Observations point
at the configuration and environment snapshots in effect when taken. `machine_events`
is an append-only ledger — current state is a projection of it.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base

SUBJECT_KINDS = {"component", "system", "assembly", "machine"}
OBS_TYPES = {"electronic", "mechanical", "visual", "auditory", "human"}

# Machine-event ledger kinds (extend freely — data-driven, no schema change).
EVENT_KINDS = {
    "PART_INSTALLED", "PART_REMOVED", "COMPONENT_FAILED", "COMPONENT_REPAIRED",
    "FLUID_CHANGED", "ADJUSTMENT_CHANGED", "JET_CHANGED", "TUNE_CHANGED",
    "GEARING_CHANGED", "INSPECTION_COMPLETED", "MEASUREMENT_RECORDED",
    "ENGINE_REBUILT", "WORK_ORDER_COMPLETED",
}
# Events that change adjustable configuration (folded into config_at settings).
SETTING_EVENT_KINDS = {"JET_CHANGED", "TUNE_CHANGED", "GEARING_CHANGED", "ADJUSTMENT_CHANGED"}


class Instrument(Base):
    __tablename__ = "instruments"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    kind: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)


class EnvironmentSnapshot(Base):
    __tablename__ = "environment_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    ambient_c: Mapped[float | None] = mapped_column(Float)
    humidity_pct: Mapped[float | None] = mapped_column(Float)
    baro_kpa: Mapped[float | None] = mapped_column(Float)
    elevation_m: Mapped[float | None] = mapped_column(Float)
    weather: Mapped[str | None] = mapped_column(Text)
    taken_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    note: Mapped[str | None] = mapped_column(Text)


class ConfigurationSnapshot(Base):
    __tablename__ = "configuration_snapshots"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    code: Mapped[str | None] = mapped_column(Text)
    config: Mapped[dict] = mapped_column(JSONB)
    taken_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    note: Mapped[str | None] = mapped_column(Text)


class Observation(Base):
    __tablename__ = "observations"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    subject_kind: Mapped[str] = mapped_column(Text, default="component")
    subject_slug: Mapped[str | None] = mapped_column(Text)
    obs_type: Mapped[str] = mapped_column(Text, default="mechanical")
    operating_condition: Mapped[str | None] = mapped_column(Text)
    method: Mapped[str | None] = mapped_column(Text)
    instrument_id: Mapped[int | None] = mapped_column(ForeignKey("instruments.id", ondelete="SET NULL"))
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(Text)
    result_text: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column(Float)
    config_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("configuration_snapshots.id", ondelete="SET NULL"))
    environment_id: Mapped[int | None] = mapped_column(
        ForeignKey("environment_snapshots.id", ondelete="SET NULL"))
    observed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    note: Mapped[str | None] = mapped_column(Text)


class MachineEvent(Base):
    __tablename__ = "machine_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(Text)
    component_slug: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    data: Mapped[dict | None] = mapped_column(JSONB)
    occurred_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_label: Mapped[str | None] = mapped_column(Text)
