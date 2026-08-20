"""Failure-mode library + diagnostic-test library ORM (V8, Milestone B). Additive."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, SmallInteger, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Float

from .models import Base

SEVERITY = {"low", "moderate", "high", "critical"}
TEST_EFFECT = {"confirms", "refutes"}


class FailureMode(Base):
    __tablename__ = "failure_modes"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    system_slug: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    expected_observations: Mapped[str | None] = mapped_column(Text)
    disconfirming_evidence: Mapped[str | None] = mapped_column(Text)
    consequences: Mapped[str | None] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text, default="moderate")


class FailureModeComponent(Base):
    __tablename__ = "failure_mode_components"
    id: Mapped[int] = mapped_column(primary_key=True)
    failure_mode_id: Mapped[int] = mapped_column(ForeignKey("failure_modes.id", ondelete="CASCADE"))
    component_slug: Mapped[str] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("failure_mode_id", "component_slug"),)


class FailureModeSymptom(Base):
    __tablename__ = "failure_mode_symptoms"
    id: Mapped[int] = mapped_column(primary_key=True)
    failure_mode_id: Mapped[int] = mapped_column(ForeignKey("failure_modes.id", ondelete="CASCADE"))
    symptom: Mapped[str] = mapped_column(Text)
    keywords: Mapped[str | None] = mapped_column(Text)


class DiagnosticTest(Base):
    __tablename__ = "diagnostic_tests"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    purpose: Mapped[str | None] = mapped_column(Text)
    procedure: Mapped[str | None] = mapped_column(Text)
    discriminates: Mapped[str | None] = mapped_column(Text)
    effect: Mapped[str] = mapped_column(Text, default="confirms")
    info_gain: Mapped[float] = mapped_column(Float, default=0.5)
    cost: Mapped[int] = mapped_column(SmallInteger, default=2)
    time_min: Mapped[int | None] = mapped_column(Integer)
    difficulty: Mapped[int] = mapped_column(SmallInteger, default=2)
    risk: Mapped[int] = mapped_column(SmallInteger, default=1)
    required_tools: Mapped[str | None] = mapped_column(Text)
    required_state: Mapped[str | None] = mapped_column(Text)
