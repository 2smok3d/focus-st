"""Machine State Engine ORM (V3) — the temporal digital twin.

Additive to models.py / refmodels.py. A `ComponentState` is one observation of a
component's condition + epistemic state on a real vehicle at a point in time; a newer
observation supersedes the previous one so the whole history is reconstructable.
`MachineCapability` records what a machine supports so tools adapt per machine.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base

# Physical / configuration condition of a component on a specific machine.
CONDITIONS = {"unknown", "stock", "healthy", "degraded", "suspect",
              "failed", "removed", "modified", "planned"}

# Epistemic state — WHY we believe a fact (keeps inference distinct from observation).
KNOWLEDGE_STATES = {"KNOWN", "DIRECTLY_OBSERVED", "OEM_ASSERTED", "CORROBORATED",
                    "INFERRED", "ESTIMATED", "DISPUTED", "UNKNOWN"}


class ComponentState(Base):
    __tablename__ = "component_states"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    component_id: Mapped[int | None] = mapped_column(ForeignKey("components.id", ondelete="SET NULL"))
    component_slug: Mapped[str] = mapped_column(Text)
    condition: Mapped[str] = mapped_column(Text, default="stock")
    knowledge_state: Mapped[str] = mapped_column(Text, default="UNKNOWN")
    installed_part: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    hours: Mapped[float | None] = mapped_column(Float)
    miles: Mapped[int | None] = mapped_column(Integer)
    cycles: Mapped[int | None] = mapped_column(Integer)
    observed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    superseded_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)
    source_label: Mapped[str | None] = mapped_column(Text)


class MachineCapability(Base):
    __tablename__ = "machine_capabilities"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    capability: Mapped[str] = mapped_column(Text)
    supported: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("vehicle_id", "capability"),)
