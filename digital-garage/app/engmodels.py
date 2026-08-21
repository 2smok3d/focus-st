"""Engineering ORM (V11, Milestone D) — build scenarios + constraints + experiments."""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .models import Base

RELATIONS = {"requires", "recommends", "conflicts", "incompatible", "supersedes", "alternative"}
ARMS = {"baseline", "changed"}


class BuildScenario(Base):
    __tablename__ = "build_scenarios"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    code: Mapped[str | None] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    goal: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    items: Mapped[list["BuildItem"]] = relationship(cascade="all, delete-orphan")


class BuildItem(Base):
    __tablename__ = "build_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("build_scenarios.id", ondelete="CASCADE"))
    tag: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    component_slug: Mapped[str | None] = mapped_column(Text)
    est_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    note: Mapped[str | None] = mapped_column(Text)


class ConstraintRule(Base):
    __tablename__ = "constraint_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_tag: Mapped[str] = mapped_column(Text)
    relation: Mapped[str] = mapped_column(Text)
    object_tag: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("subject_tag", "relation", "object_tag"),)


class Experiment(Base):
    __tablename__ = "experiments"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    code: Mapped[str | None] = mapped_column(Text)
    question: Mapped[str] = mapped_column(Text)
    metric: Mapped[str | None] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    runs: Mapped[list["ExperimentRun"]] = relationship(cascade="all, delete-orphan")


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    experiment_id: Mapped[int] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"))
    arm: Mapped[str] = mapped_column(Text)
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(Text)
    environment_id: Mapped[int | None] = mapped_column(Integer)   # soft link (FK in schema_v11.sql)
    session_id: Mapped[int | None] = mapped_column(Integer)       # soft link
    note: Mapped[str | None] = mapped_column(Text)
