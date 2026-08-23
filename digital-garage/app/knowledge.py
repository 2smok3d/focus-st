"""Knowledge Operations (Milestone F) — quality dashboard, research queue, entity resolution.

The quality dashboard is a pure projection over the canonical `claims` table: how much do
we know, how well is it graded, and where are the gaps. The research queue turns those
gaps into prioritized tasks (conflicts rank highest — they can be safety-relevant). Entity
resolution normalizes messy identifiers ("22R-E" / "22RE" / "22R E") to one identity.
Nothing here mutates canonical knowledge; it measures it and proposes work.
"""
from __future__ import annotations

import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .kbmodels import EntityAlias, ResearchTask
from .refmodels import Claim

_NUMERIC = re.compile(r"^\s*-?\d+(\.\d+)?\s*$")


# ---- entity resolution (pure) --------------------------------------------
def normalize_identifier(text: str) -> str:
    """Canonical form of an identifier: uppercased, separators removed. Pure."""
    return re.sub(r"[^A-Za-z0-9]+", "", (text or "")).upper()


def resolve_alias(session: Session, alias: str) -> str:
    """Resolve an alias to its canonical identity — exact alias row, else normalized
    match against known aliases/canonicals, else the normalized input itself."""
    exact = session.scalar(select(EntityAlias).where(EntityAlias.alias == alias))
    if exact:
        return exact.canonical
    norm = normalize_identifier(alias)
    for row in session.scalars(select(EntityAlias)):
        if normalize_identifier(row.alias) == norm or normalize_identifier(row.canonical) == norm:
            return row.canonical
    return norm


def add_alias(session: Session, alias: str, canonical: str, *, kind: str | None = None) -> EntityAlias:
    row = session.scalar(select(EntityAlias).where(
        EntityAlias.alias == alias, EntityAlias.canonical == canonical))
    if row is None:
        row = EntityAlias(alias=alias, canonical=canonical, kind=kind)
        session.add(row)
        session.flush()
    return row


# ---- quality dashboard ----------------------------------------------------
def quality_report(session: Session, variant_slug: str | None = None) -> dict:
    """Counts + gaps over the canonical claims table, optionally scoped to a variant
    (claims whose applicability names that variant)."""
    scope = (Claim.applicability["variant"].astext == variant_slug,) if variant_slug else ()
    total = session.scalar(select(func.count()).select_from(Claim).where(*scope)) or 0
    by_verification = dict(session.execute(
        select(Claim.verification, func.count()).where(*scope).group_by(Claim.verification)).all())
    conflicts = session.scalar(
        select(func.count()).select_from(Claim).where(Claim.conflict.is_(True), *scope)) or 0
    missing_applicability = session.scalar(
        select(func.count()).select_from(Claim).where(Claim.applicability.is_(None), *scope)) or 0
    # numeric-valued claims lacking a unit are a real gap (firing order etc. are fine).
    missing_units = 0
    for value, unit in session.execute(select(Claim.value, Claim.unit).where(*scope)):
        if unit is None and value is not None and _NUMERIC.match(str(value)):
            missing_units += 1

    def pct(n: int) -> float:
        return round(100 * n / total, 1) if total else 0.0

    return {
        "total": total,
        "by_verification": {k: {"n": v, "pct": pct(v)} for k, v in by_verification.items()},
        "conflicts": conflicts,
        "missing_applicability": missing_applicability,
        "missing_units": missing_units,
        "gaps": conflicts + missing_units + missing_applicability
        + by_verification.get("UNVERIFIED", 0),
    }


# ---- research queue -------------------------------------------------------
def generate_research_tasks(session: Session) -> str:
    """Scan claims for gaps and enqueue prioritized research tasks (idempotent)."""
    created = 0

    def enqueue(kind, priority, subject, detail, dedupe, variant):
        nonlocal created
        row = session.scalar(select(ResearchTask).where(ResearchTask.dedupe_key == dedupe))
        if row is None:
            session.add(ResearchTask(kind=kind, priority=priority, subject=subject,
                                     detail=detail, dedupe_key=dedupe, variant=variant))
            created += 1
        elif row.variant is None and variant is not None:
            row.variant = variant  # backfill scope onto a task enqueued before it was known

    for c in session.scalars(select(Claim)):
        key = f"{c.subject_type}:{c.subject_key}:{c.prop}"
        variant = (c.applicability or {}).get("variant") if c.applicability else None
        if c.conflict:
            enqueue("conflict", "high", key,
                    f"Conflicting evidence on {c.prop} = {c.value} — resolve by VIN/OEM doc.",
                    f"conflict:{key}", variant)
        elif c.verification == "UNVERIFIED":
            enqueue("unverified", "medium", key,
                    f"Unverified: {c.prop} = {c.value}. Corroborate against a source.",
                    f"unverified:{key}", variant)
        if c.applicability is None:
            enqueue("missing_applicability", "low", key,
                    f"No applicability on {c.prop} — scope by variant/years/market.",
                    f"missing_applicability:{key}", variant)
        if c.unit is None and c.value is not None and _NUMERIC.match(str(c.value)):
            enqueue("missing_unit", "low", key,
                    f"Numeric claim {c.prop} = {c.value} has no unit.", f"missing_unit:{key}", variant)
    session.flush()
    return f"Research tasks generated: +{created} new."


def list_research_tasks(session: Session, *, status: str = "open",
                        variant_slug: str | None = None) -> list[dict]:
    """Open research tasks, newest-priority-first. When `variant_slug` is given, returns
    that machine's tasks plus fleet-wide (unscoped) ones — never another machine's gaps."""
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    q = select(ResearchTask).where(ResearchTask.status == status)
    if variant_slug is not None:
        q = q.where((ResearchTask.variant == variant_slug) | ResearchTask.variant.is_(None))
    rows = session.scalars(q).all()
    rows.sort(key=lambda t: order.get(t.priority, 9))
    return [{"id": t.id, "kind": t.kind, "priority": t.priority, "subject": t.subject,
             "detail": t.detail, "status": t.status, "variant": t.variant} for t in rows]
