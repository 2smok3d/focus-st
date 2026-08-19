"""SQLAlchemy 2.0 ORM — mirrors db/schema.sql."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    authority: Mapped[int] = mapped_column(SmallInteger)
    url: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (CheckConstraint("authority BETWEEN 1 AND 6", name="ck_source_authority"),)


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    vin: Mapped[str] = mapped_column(Text, unique=True)
    year: Mapped[int | None] = mapped_column(SmallInteger)
    make: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    trim: Mapped[str | None] = mapped_column(Text)
    engine: Mapped[str | None] = mapped_column(Text)
    transmission: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    # V2 digital-twin link → the reference variant this actual car is configured as.
    variant_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    specs: Mapped[list["Spec"]] = relationship(back_populates="vehicle", cascade="all, delete-orphan")
    intervals: Mapped[list["MaintenanceInterval"]] = relationship(cascade="all, delete-orphan")
    services: Mapped[list["ServiceEvent"]] = relationship(cascade="all, delete-orphan")
    mods: Mapped[list["Mod"]] = relationship(cascade="all, delete-orphan")
    issues: Mapped[list["Issue"]] = relationship(cascade="all, delete-orphan")
    odometer: Mapped[list["OdometerReading"]] = relationship(cascade="all, delete-orphan")


class Spec(Base):
    __tablename__ = "specs"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    value: Mapped[str] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(Text)
    verification: Mapped[str] = mapped_column(String(20), default="UNVERIFIED")
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    vehicle: Mapped[Vehicle] = relationship(back_populates="specs")
    __table_args__ = (UniqueConstraint("vehicle_id", "category", "name"),)


class OdometerReading(Base):
    __tablename__ = "odometer_readings"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    miles: Mapped[int] = mapped_column(Integer)
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(Text)


class MaintenanceInterval(Base):
    __tablename__ = "maintenance_intervals"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    item: Mapped[str] = mapped_column(Text)
    interval_miles: Mapped[int | None] = mapped_column(Integer)
    interval_months: Mapped[int | None] = mapped_column(Integer)
    verification: Mapped[str] = mapped_column(String(20), default="UNVERIFIED")
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("vehicle_id", "item"),)


class ServiceEvent(Base):
    __tablename__ = "service_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    interval_id: Mapped[int | None] = mapped_column(ForeignKey("maintenance_intervals.id", ondelete="SET NULL"))
    item: Mapped[str] = mapped_column(Text)
    performed_at: Mapped[dt.date] = mapped_column(Date)
    miles: Mapped[int | None] = mapped_column(Integer)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    vendor: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Mod(Base):
    __tablename__ = "mods"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    slot: Mapped[str] = mapped_column(Text)
    part_name: Mapped[str] = mapped_column(Text)
    part_number: Mapped[str | None] = mapped_column(Text)
    installed_on: Mapped[dt.date | None] = mapped_column(Date)
    installed_miles: Mapped[int | None] = mapped_column(Integer)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    url: Mapped[str | None] = mapped_column(Text)
    stage: Mapped[str | None] = mapped_column(Text)
    verification: Mapped[str] = mapped_column(String(20), default="UNVERIFIED")
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Issue(Base):
    __tablename__ = "issues"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="open")
    severity: Mapped[str | None] = mapped_column(Text)
    opened_at: Mapped[dt.date] = mapped_column(Date, server_default=func.current_date())
    resolved_at: Mapped[dt.date | None] = mapped_column(Date)
    root_cause: Mapped[str | None] = mapped_column(Text)
    verification: Mapped[str] = mapped_column(String(20), default="UNVERIFIED")
    note: Mapped[str | None] = mapped_column(Text)


class Part(Base):
    __tablename__ = "parts"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    part_number: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    oem: Mapped[bool] = mapped_column(Boolean, default=False)
    approx_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    url: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(Text)


class DiagnosticSession(Base):
    __tablename__ = "diagnostic_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(Text)
    captured_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    ingested_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    miles: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    raw_path: Mapped[str] = mapped_column(Text)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    note: Mapped[str | None] = mapped_column(Text)

    dtcs: Mapped[list["Dtc"]] = relationship(cascade="all, delete-orphan")
    measurements: Mapped[list["Measurement"]] = relationship(cascade="all, delete-orphan")
    can_frames: Mapped[list["CanFrame"]] = relationship(cascade="all, delete-orphan")


class Dtc(Base):
    __tablename__ = "dtcs"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(Text)
    module: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)


class Measurement(Base):
    __tablename__ = "measurements"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"))
    pid: Mapped[str] = mapped_column(Text)
    value: Mapped[float | None] = mapped_column(Double)
    unit: Mapped[str | None] = mapped_column(Text)
    t_offset_s: Mapped[float | None] = mapped_column(Double)


class CanFrame(Base):
    __tablename__ = "can_frames"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"))
    t_offset_s: Mapped[float | None] = mapped_column(Double)
    can_id: Mapped[str] = mapped_column(Text)
    dlc: Mapped[int | None] = mapped_column(SmallInteger)
    data_hex: Mapped[str | None] = mapped_column(Text)


class Recall(Base):
    __tablename__ = "recalls"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    campaign_number: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(Text, default="nhtsa")
    component: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    consequence: Mapped[str | None] = mapped_column(Text)
    remedy: Mapped[str | None] = mapped_column(Text)
    report_date: Mapped[dt.date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(Text, default="unknown")
    verification: Mapped[str] = mapped_column(String(20), default="CORROBORATED")
    fetched_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("vehicle_id", "campaign_number"),)


class ChangeProposal(Base):
    __tablename__ = "change_proposals"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    entity: Mapped[str] = mapped_column(Text)
    op: Mapped[str] = mapped_column(Text, default="insert")
    entity_id: Mapped[int | None] = mapped_column(Integer)
    patch: Mapped[dict] = mapped_column(JSONB)
    rationale: Mapped[str | None] = mapped_column(Text)
    proposed_by: Mapped[str] = mapped_column(Text, default="agent")
    status: Mapped[str] = mapped_column(String(12), default="pending")
    approved_by: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    applied_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
