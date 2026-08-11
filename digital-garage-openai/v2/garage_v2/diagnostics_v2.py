from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class CaseStatus(str, Enum):
    OPEN = "open"
    TESTING = "testing"
    REPAIR_PLANNED = "repair_planned"
    VERIFYING = "verifying"
    CLOSED = "closed"
    DEFERRED = "deferred"


@dataclass
class Hypothesis:
    id: UUID = field(default_factory=uuid4)
    text: str = ""
    system: str = "unknown"
    probability: float = 0.5
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)
    status: str = "untested"


@dataclass
class DiagnosticTest:
    id: UUID = field(default_factory=uuid4)
    name: str = ""
    purpose: str = ""
    invasiveness: int = 1
    safety_notes: str | None = None
    expected_if_true: str | None = None
    expected_if_false: str | None = None
    result: str | None = None
    evidence_ids: list[str] = field(default_factory=list)
    performed_at: str | None = None


@dataclass
class DiagnosticCase:
    id: UUID = field(default_factory=uuid4)
    vehicle_id: str = "focus-st-2017"
    title: str = ""
    symptom: str = ""
    status: CaseStatus = CaseStatus.OPEN
    severity: str = "normal"
    opened_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    mileage_mi: int | None = None
    dtcs: list[str] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    tests: list[DiagnosticTest] = field(default_factory=list)
    resolution: str | None = None
    verification: str | None = None

    def ranked_hypotheses(self) -> list[dict[str, Any]]:
        ranked = sorted(self.hypotheses, key=lambda h: h.probability, reverse=True)
        return [asdict(h) for h in ranked]

    def next_tests(self) -> list[dict[str, Any]]:
        """Prefer high-information, low-invasiveness tests before parts replacement."""
        pending = [t for t in self.tests if t.result is None]
        pending.sort(key=lambda t: (t.invasiveness, t.name))
        return [asdict(t) for t in pending]


def p04db_seed_case() -> DiagnosticCase:
    case = DiagnosticCase(
        title="P04DB — crankcase ventilation disconnected / system performance history",
        symptom="Existing vehicle records include P04DB while MIL behavior has not always matched stored/pending/permanent code state.",
        severity="important",
        dtcs=["P04DB"],
    )
    case.hypotheses = [
        Hypothesis(text="PCV/CCV hose or quick-connect leak/disconnection", system="pcv", probability=.72),
        Hypothesis(text="PCV valve / baffle assembly fault or restriction", system="pcv", probability=.62),
        Hypothesis(text="Aftermarket intake / crankcase hose routing interaction", system="intake_pcv", probability=.48, supporting_evidence=["Injen intake is recorded installed"]),
        Hypothesis(text="Residual/history code after prior repair with no current fault", system="diagnostic_state", probability=.38),
        Hypothesis(text="Electrical/sensor rationality issue rather than physical disconnection", system="controls", probability=.24),
    ]
    case.tests = [
        DiagnosticTest(name="Preserve full DTC scan + status", purpose="Differentiate current/pending/stored/permanent state before clearing anything", invasiveness=0, expected_if_true="Current/pending evidence remains present"),
        DiagnosticTest(name="Photograph and trace PCV/CCV routing", purpose="Compare actual hose routing to exact engine configuration", invasiveness=0, expected_if_true="Visible loose, damaged, altered or missing connection"),
        DiagnosticTest(name="Inspect Injen-related crankcase connection points", purpose="Identify aftermarket intake routing/interface issue", invasiveness=1),
        DiagnosticTest(name="Smoke test intake/crankcase ventilation paths", purpose="Find leakage without blind parts replacement", invasiveness=2, safety_notes="Use low regulated pressure suitable for intake/EVAP diagnostic work; avoid pressurizing systems beyond service-tool guidance."),
        DiagnosticTest(name="Compare idle trims / airflow observations", purpose="Look for air-path behavior consistent with a leak", invasiveness=1),
        DiagnosticTest(name="Verify repair with drive cycle and rescans", purpose="Prove current fault is gone without relying only on MIL state", invasiveness=0),
    ]
    return case


def generic_boost_case(code: str | None = None) -> DiagnosticCase:
    title = f"Boost-control case {code}" if code else "Boost / spool / charge-air complaint"
    case = DiagnosticCase(title=title, symptom="Low, high, inconsistent or subjectively absent boost/spool behavior", dtcs=[code] if code else [])
    case.hypotheses = [
        Hypothesis(text="Charge-air leak / coupler or pipe issue", system="charge_air", probability=.65),
        Hypothesis(text="Wastegate / boost-control mechanical or plumbing issue", system="turbo_control", probability=.58),
        Hypothesis(text="Bypass/recirculation valve leakage or control issue", system="turbo_control", probability=.42),
        Hypothesis(text="Tune/load/ambient conditions explain perceived behavior", system="calibration", probability=.38),
        Hypothesis(text="Turbocharger mechanical degradation", system="turbo", probability=.28),
    ]
    case.tests = [
        DiagnosticTest(name="Full scan + freeze-frame capture", purpose="Preserve control-module evidence", invasiveness=0),
        DiagnosticTest(name="Datalog commanded vs actual boost/load", purpose="Separate control request from airflow delivery", invasiveness=0),
        DiagnosticTest(name="Visual/tactile charge-air inspection", purpose="Find loose clamps, oil tracks, cracked pipes or disconnected couplers", invasiveness=1),
        DiagnosticTest(name="Charge-air smoke/pressure leak test", purpose="Objectively test tract integrity", invasiveness=2),
        DiagnosticTest(name="Wastegate linkage/control inspection", purpose="Check mechanical travel and control plumbing", invasiveness=2),
    ]
    return case
