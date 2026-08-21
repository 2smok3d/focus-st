"""Knowledge-Operations ORM (V12) — research queue + entity aliases. Additive."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .models import Base

TASK_KINDS = {"conflict", "unverified", "missing_unit", "missing_applicability"}
PRIORITIES = {"low", "medium", "high", "critical"}
TASK_STATUS = {"open", "in_progress", "resolved", "wont_fix"}


class ResearchTask(Base):
    __tablename__ = "research_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(Text, default="medium")
    subject: Mapped[str] = mapped_column(Text)
    detail: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="open")
    dedupe_key: Mapped[str | None] = mapped_column(Text, unique=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EntityAlias(Base):
    __tablename__ = "entity_aliases"
    id: Mapped[int] = mapped_column(primary_key=True)
    alias: Mapped[str] = mapped_column(Text)
    canonical: Mapped[str] = mapped_column(Text)
    kind: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("alias", "canonical"),)
