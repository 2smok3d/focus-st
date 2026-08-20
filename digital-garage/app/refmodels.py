"""Canonical automotive reference model + claim/evidence provenance (V2 Phase 1).

Additive to models.py — reuses the same declarative Base. This is the vehicle-agnostic
reference layer:

    Manufacturer → Platform → Variant → {Engine, Transmission, Systems → Components}

plus a source-document registry and the claim/claim_evidence provenance tables. The
user's actual `vehicles` row links to a `vehicle_variants` row (its reference config)
instead of duplicating reference data.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .models import Base


class Manufacturer(Base):
    __tablename__ = "manufacturers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    country: Mapped[str | None] = mapped_column(Text)


class VehiclePlatform(Base):
    __tablename__ = "vehicle_platforms"
    id: Mapped[int] = mapped_column(primary_key=True)
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturers.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    code: Mapped[str | None] = mapped_column(Text)         # e.g. "MK3 / C346"
    years: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("manufacturer_id", "name"),)


class VehicleVariant(Base):
    __tablename__ = "vehicle_variants"
    id: Mapped[int] = mapped_column(primary_key=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("vehicle_platforms.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(Text, unique=True)   # e.g. "focus-st"
    name: Mapped[str] = mapped_column(Text)
    trim: Mapped[str | None] = mapped_column(Text)
    market: Mapped[str | None] = mapped_column(Text)       # NA, EU, JDM…
    years: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class Engine(Base):
    __tablename__ = "engines"
    id: Mapped[int] = mapped_column(primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("vehicle_variants.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(Text)                # "R9DA / 2.0 EcoBoost"
    displacement_cc: Mapped[int | None] = mapped_column(Integer)
    config: Mapped[str | None] = mapped_column(Text)       # "I4 DOHC 16v"
    aspiration: Mapped[str | None] = mapped_column(Text)   # "turbo GTDI"
    fuel: Mapped[str | None] = mapped_column(Text)
    power: Mapped[str | None] = mapped_column(Text)
    torque: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class Transmission(Base):
    __tablename__ = "transmissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("vehicle_variants.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(Text)                # "MT82"
    type: Mapped[str | None] = mapped_column(Text)         # "6-speed manual"
    gears: Mapped[int | None] = mapped_column(SmallInteger)
    notes: Mapped[str | None] = mapped_column(Text)


class System(Base):
    """Hierarchical system/subsystem tree (parent_id = NULL for top level)."""
    __tablename__ = "systems"
    id: Mapped[int] = mapped_column(primary_key=True)
    variant_id: Mapped[int] = mapped_column(ForeignKey("vehicle_variants.id", ondelete="CASCADE"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("systems.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint("variant_id", "slug"),)


class Assembly(Base):
    """An Assembly groups Components within a System (Machine → System → Assembly → Component)."""
    __tablename__ = "assemblies"
    id: Mapped[int] = mapped_column(primary_key=True)
    system_id: Mapped[int] = mapped_column(ForeignKey("systems.id", ondelete="CASCADE"))
    slug: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("system_id", "slug"),)


class Component(Base):
    __tablename__ = "components"
    id: Mapped[int] = mapped_column(primary_key=True)
    system_id: Mapped[int] = mapped_column(ForeignKey("systems.id", ondelete="CASCADE"))
    assembly_id: Mapped[int | None] = mapped_column(ForeignKey("assemblies.id", ondelete="SET NULL"))
    slug: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    oem_hint: Mapped[str | None] = mapped_column(Text)     # OEM part hint / number
    __table_args__ = (UniqueConstraint("system_id", "slug"),)


# Typed relationships between components (the knowledge graph edges).
RELATIONS = {
    "contains", "connects_to", "feeds", "returns_to", "controls", "monitors",
    "requires", "affects", "replaces", "supersedes", "compatible_with",
    "conflicts_with", "diagnosed_by", "associated_with", "lubricated_by",
    "cooled_by", "outputs_to", "controlled_by", "monitored_by",
}


# Graph overlays — the domain a relationship belongs to (the same components can be
# traversed as several overlaid graphs).
DOMAINS = {"function", "mechanical", "airflow", "coolant", "lubrication", "fuel",
           "electrical", "vacuum", "boost", "exhaust"}


class ComponentRelationship(Base):
    __tablename__ = "component_relationships"
    id: Mapped[int] = mapped_column(primary_key=True)
    from_component_id: Mapped[int] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"))
    to_component_id: Mapped[int] = mapped_column(ForeignKey("components.id", ondelete="CASCADE"))
    relation: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(Text, default="function")   # which overlay
    medium: Mapped[str | None] = mapped_column(Text)                # air | coolant | oil | ...
    direction: Mapped[str] = mapped_column(Text, default="forward")  # forward | bidirectional
    note: Mapped[str | None] = mapped_column(Text)


class SourceDocument(Base):
    """A specific document/revision under a graded source (extends `sources`)."""
    __tablename__ = "source_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(Text)
    doc_id: Mapped[str | None] = mapped_column(Text)       # publication / doc number
    revision: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[dt.date | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class Claim(Base):
    """A single automotive fact, with a resolved verdict recomputed from its evidence."""
    __tablename__ = "claims"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_type: Mapped[str] = mapped_column(Text)        # component | variant | engine | system | spec
    subject_key: Mapped[str] = mapped_column(Text)         # slug/identifier of the subject
    prop: Mapped[str] = mapped_column("property", Text)    # e.g. "lug_torque"
    value: Mapped[str] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(Text)
    applicability: Mapped[dict | None] = mapped_column(JSONB)   # {variant, years, market}
    verification: Mapped[str] = mapped_column(Text, default="UNVERIFIED")   # resolved verdict
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    conflict: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    evidence: Mapped[list["ClaimEvidence"]] = relationship(cascade="all, delete-orphan")


class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"))
    source_document_id: Mapped[int | None] = mapped_column(ForeignKey("source_documents.id", ondelete="SET NULL"))
    authority: Mapped[int] = mapped_column(SmallInteger)   # 1..6 (copied for fast resolve)
    stance: Mapped[str] = mapped_column(Text, default="supports")
    on_vehicle: Mapped[bool] = mapped_column(Boolean, default=False)
    page: Mapped[str | None] = mapped_column(Text)
    section: Mapped[str | None] = mapped_column(Text)
    excerpt: Mapped[str | None] = mapped_column(Text)
    source_label: Mapped[str | None] = mapped_column(Text)
    retrieved_at: Mapped[dt.date | None] = mapped_column(DateTime(timezone=True))
