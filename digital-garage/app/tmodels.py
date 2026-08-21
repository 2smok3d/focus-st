"""Telemetry V2 ORM (V10) — channel registry + detected-event ledger. Additive."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base

EVENT_SEVERITY = {"info", "warn", "critical"}


class TelemetryChannel(Base):
    __tablename__ = "telemetry_channels"
    id: Mapped[int] = mapped_column(primary_key=True)
    canonical_name: Mapped[str] = mapped_column(Text, unique=True)
    unit: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    normal_min: Mapped[float | None] = mapped_column(Float)
    normal_max: Mapped[float | None] = mapped_column(Float)
    warn_min: Mapped[float | None] = mapped_column(Float)
    warn_max: Mapped[float | None] = mapped_column(Float)
    derived: Mapped[bool] = mapped_column(Boolean, default=False)
    formula: Mapped[str | None] = mapped_column(Text)


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(Text)
    t_start: Mapped[float | None] = mapped_column(Float)
    t_end: Mapped[float | None] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(Text, default="info")
    channel: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
