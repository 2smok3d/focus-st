"""Workshop Engine ORM (V9) — work orders, tasks, parts, tools, verifications. Additive."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .models import Base

WO_STATUS = {"draft", "ready", "blocked", "in_progress", "work_complete",
             "verification_required", "verified", "closed", "abandoned"}
REPAIR_STATE = {"planned", "repair_performed", "repair_verified"}
VERIFY_RESULT = {"pending", "pass", "fail"}


class WorkOrder(Base):
    __tablename__ = "work_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    code: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    component_slug: Mapped[str | None] = mapped_column(Text)
    # Soft links (real FKs enforced in schema_v9.sql) — kept as plain ints so this ORM
    # doesn't require case_findings / observations to be imported into the metadata.
    from_finding_id: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, default="draft")
    repair_state: Mapped[str] = mapped_column(Text, default="planned")
    outcome: Mapped[str | None] = mapped_column(Text)
    opened_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)

    tasks: Mapped[list["WorkOrderTask"]] = relationship(cascade="all, delete-orphan")
    parts: Mapped[list["WorkOrderPart"]] = relationship(cascade="all, delete-orphan")
    tools: Mapped[list["WorkOrderTool"]] = relationship(cascade="all, delete-orphan")
    verifications: Mapped[list["WorkOrderVerification"]] = relationship(cascade="all, delete-orphan")


class WorkOrderTask(Base):
    __tablename__ = "work_order_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str] = mapped_column(Text)
    done: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text)


class WorkOrderPart(Base):
    __tablename__ = "work_order_parts"
    id: Mapped[int] = mapped_column(primary_key=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    part_number: Mapped[str | None] = mapped_column(Text)
    qty: Mapped[int] = mapped_column(Integer, default=1)
    available: Mapped[bool] = mapped_column(Boolean, default=False)


class WorkOrderTool(Base):
    __tablename__ = "work_order_tools"
    id: Mapped[int] = mapped_column(primary_key=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    available: Mapped[bool] = mapped_column(Boolean, default=False)


class WorkOrderVerification(Base):
    __tablename__ = "work_order_verifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    work_order_id: Mapped[int] = mapped_column(ForeignKey("work_orders.id", ondelete="CASCADE"))
    test: Mapped[str] = mapped_column(Text)
    result: Mapped[str] = mapped_column(Text, default="pending")
    observation_id: Mapped[int | None] = mapped_column(Integer)   # soft link (FK in schema_v9.sql)
    verified_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    note: Mapped[str | None] = mapped_column(Text)
