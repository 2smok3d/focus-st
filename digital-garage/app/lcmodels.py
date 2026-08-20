"""Physical-component lifecycle ORM (V7). Additive to models.py."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base

PC_STATUS = {"in_service", "removed", "in_inventory", "rebuilding", "scrapped"}
PC_CONDITION = {"unknown", "healthy", "degraded", "suspect", "failed"}
INSPECTION_RESULTS = {"healthy", "degraded", "suspect", "failed"}


class PhysicalComponent(Base):
    __tablename__ = "physical_components"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    component_slug: Mapped[str | None] = mapped_column(Text)
    manufacturer: Mapped[str | None] = mapped_column(Text)
    part_number: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="in_inventory")
    condition: Mapped[str] = mapped_column(Text, default="unknown")
    hours: Mapped[float] = mapped_column(Float, default=0)
    sessions: Mapped[int] = mapped_column(Integer, default=0)
    miles: Mapped[int] = mapped_column(Integer, default=0)
    cycles: Mapped[int] = mapped_column(Integer, default=0)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ComponentInstallation(Base):
    __tablename__ = "component_installations"
    id: Mapped[int] = mapped_column(primary_key=True)
    physical_component_id: Mapped[int] = mapped_column(
        ForeignKey("physical_components.id", ondelete="CASCADE"))
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    slot_slug: Mapped[str | None] = mapped_column(Text)
    installed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    removed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)


class ComponentInspection(Base):
    __tablename__ = "component_inspections"
    id: Mapped[int] = mapped_column(primary_key=True)
    physical_component_id: Mapped[int] = mapped_column(
        ForeignKey("physical_components.id", ondelete="CASCADE"))
    result: Mapped[str] = mapped_column(Text, default="healthy")
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(Text)
    method: Mapped[str | None] = mapped_column(Text)
    inspected_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    note: Mapped[str | None] = mapped_column(Text)
