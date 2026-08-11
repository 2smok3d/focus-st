from __future__ import annotations

from datetime import datetime, date
from enum import Enum
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class Authority(str, Enum):
    OEM = "oem"
    GOVERNMENT = "government"
    MANUFACTURER = "component_manufacturer"
    TECHNICAL = "technical_reference"
    COMMUNITY = "community_consensus"
    ANECDOTE = "individual_anecdote"
    USER_RECORD = "user_record"
    RAW_TELEMETRY = "raw_telemetry"


AUTHORITY_WEIGHT: dict[Authority, float] = {
    Authority.OEM: 1.00,
    Authority.GOVERNMENT: 0.98,
    Authority.MANUFACTURER: 0.92,
    Authority.TECHNICAL: 0.88,
    Authority.COMMUNITY: 0.68,
    Authority.USER_RECORD: 0.85,
    Authority.RAW_TELEMETRY: 0.95,
    Authority.ANECDOTE: 0.40,
}


class SourceRef(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    authority: Authority
    publisher: str | None = None
    url: HttpUrl | None = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: datetime | None = None
    local_reference: str | None = None
    sha256: str | None = None
    notes: str | None = None


class Claim(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    subject: str
    predicate: str
    value: Any
    unit: str | None = None
    vehicle_scope: str = "focus-st-2017"
    source_ids: list[UUID] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1, default=0.5)
    canonical: bool = False
    conflict_group: str | None = None
    verified_at: datetime | None = None
    notes: str | None = None


class EvidenceObject(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    vehicle_id: str = "focus-st-2017"
    original_name: str
    media_type: str | None = None
    source_format: str
    sha256: str
    byte_size: int
    captured_at: datetime | None = None
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    mileage_mi: int | None = Field(default=None, ge=0)
    timezone: str | None = "America/Phoenix"
    raw_path: str
    normalized_path: str | None = None
    parser: str | None = None
    parser_version: str | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DTCRecord(BaseModel):
    code: str
    module: str | None = None
    status: Literal["current", "pending", "stored", "permanent", "history", "unknown"] = "unknown"
    description: str | None = None
    occurred_at: datetime | None = None
    mileage_mi: int | None = None
    freeze_frame: dict[str, Any] = Field(default_factory=dict)
    evidence_id: UUID | None = None


class Measurement(BaseModel):
    timestamp: datetime | float | None = None
    module: str | None = None
    pid: str
    value: float | int | str | bool | None
    unit: str | None = None
    raw_value: str | None = None
    evidence_id: UUID | None = None


class CANFrame(BaseModel):
    timestamp: float | datetime | None = None
    channel: str | int | None = None
    arbitration_id: int = Field(ge=0)
    is_extended_id: bool = False
    is_fd: bool = False
    is_rx: bool | None = None
    dlc: int | None = None
    data_hex: str
    decoded_signals: dict[str, Any] = Field(default_factory=dict)
    evidence_id: UUID | None = None


class GarageEvent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    vehicle_id: str = "focus-st-2017"
    event_type: str
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    mileage_mi: int | None = Field(default=None, ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[UUID] = Field(default_factory=list)
    source_ids: list[UUID] = Field(default_factory=list)
    supersedes_event_id: UUID | None = None
    voided: bool = False


class ServiceTask(BaseModel):
    id: str
    name: str
    system: str
    interval_miles: int | None = None
    interval_months: int | None = None
    severe_interval_miles: int | None = None
    severe_interval_months: int | None = None
    oem_required: bool = False
    source_claim_ids: list[UUID] = Field(default_factory=list)
    notes: str | None = None


class ServiceRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    vehicle_id: str = "focus-st-2017"
    task_id: str | None = None
    service_date: date
    mileage_mi: int
    description: str
    parts: list[str] = Field(default_factory=list)
    fluid_spec: str | None = None
    cost_parts: float | None = None
    cost_labor: float | None = None
    vendor: str | None = None
    receipt_evidence_ids: list[UUID] = Field(default_factory=list)
    verification: str | None = None


class PartOption(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    slot: str
    category: Literal["oem", "stock_equivalent", "oem_plus", "performance", "track", "custom"]
    manufacturer: str
    part_name: str
    part_number: str | None = None
    fitment_status: Literal["verified", "probable", "unverified", "conflicting"] = "unverified"
    source_ids: list[UUID] = Field(default_factory=list)
    notes: str | None = None
    amazon_query: str | None = None
    ebay_query: str | None = None


class ApprovalIntent(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    capability: Literal[
        "clear_dtc", "actuator_test", "module_configuration", "flash", "can_transmit", "ecu_write"
    ]
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    reason: str
    target: str | None = None
    payload_digest: str | None = None
    approved: bool = False
    approved_at: datetime | None = None
    expires_at: datetime | None = None
