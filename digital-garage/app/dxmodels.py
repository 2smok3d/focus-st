"""Diagnostic Workbench ORM (V4) — cases, symptoms, evidence, tests, hypotheses, findings.

Additive to models.py. A `DiagnosticCase` is a professional diagnostic record: it pulls
in symptoms and known data, walks a tree of tests, ranks hypotheses through a
transparent scoring model (see app/workbench.py), and records auditable findings.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .models import Base

CASE_STATUS = {"open", "investigating", "resolved", "abandoned"}
TEST_RESULTS = {"pending", "pass", "fail", "inconclusive"}
HYP_STATUS = {"open", "supported", "refuted", "confirmed"}
EVIDENCE_KINDS = {"dtc", "mod", "known_issue", "telemetry", "measurement", "observation"}
POLARITY = {"confirms", "refutes"}


class DiagnosticCase(Base):
    __tablename__ = "diagnostic_cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id", ondelete="CASCADE"))
    code: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="open")
    outcome: Mapped[str | None] = mapped_column(Text)
    opened_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    closed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)

    symptoms: Mapped[list["CaseSymptom"]] = relationship(cascade="all, delete-orphan")
    evidence: Mapped[list["CaseEvidence"]] = relationship(cascade="all, delete-orphan")
    hypotheses: Mapped[list["CaseHypothesis"]] = relationship(cascade="all, delete-orphan")
    tests: Mapped[list["CaseTest"]] = relationship(cascade="all, delete-orphan")
    findings: Mapped[list["CaseFinding"]] = relationship(cascade="all, delete-orphan")


class CaseSymptom(Base):
    __tablename__ = "case_symptoms"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_cases.id", ondelete="CASCADE"))
    description: Mapped[str] = mapped_column(Text)
    observed_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseEvidence(Base):
    __tablename__ = "case_evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_cases.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(Text)
    ref: Mapped[str | None] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    component_slug: Mapped[str | None] = mapped_column(Text)


class CaseHypothesis(Base):
    __tablename__ = "case_hypotheses"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_cases.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    component_slug: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="open")
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("case_id", "key"),)


class CaseTest(Base):
    __tablename__ = "case_tests"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_cases.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    expected: Mapped[str | None] = mapped_column(Text)
    actual: Mapped[str | None] = mapped_column(Text)
    interpretation: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str] = mapped_column(Text, default="pending")
    bears_on: Mapped[str | None] = mapped_column(Text)
    polarity: Mapped[str] = mapped_column(Text, default="confirms")
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    component_slug: Mapped[str | None] = mapped_column(Text)
    source_label: Mapped[str | None] = mapped_column(Text)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    performed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))


class CaseFinding(Base):
    __tablename__ = "case_findings"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("diagnostic_cases.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    supporting: Mapped[str | None] = mapped_column(Text)
    contradicting: Mapped[str | None] = mapped_column(Text)
    derived_by: Mapped[str | None] = mapped_column(Text)
    superseded_by: Mapped[int | None] = mapped_column(ForeignKey("case_findings.id", ondelete="SET NULL"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
