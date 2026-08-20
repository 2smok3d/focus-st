"""Seed the Focus ST boost-complaint failure-mode + diagnostic-test library (Milestone B).

Authored independently of any case (roadmap #9): the low-boost failure modes with their
components, symptoms, expected observations, and the reusable tests that discriminate
them — each carrying an information-gain + cost/risk so the workbench can pick the single
best next test. Idempotent.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .fmmodels import DiagnosticTest, FailureMode, FailureModeComponent, FailureModeSymptom

# slug: dict
FAILURE_MODES = {
    "charge-air-leak": dict(
        name="Charge-air (boost) leak", system_slug="forced-induction", severity="moderate",
        description="A leak in the pressurized intake tract downstream of the turbo.",
        expected_observations="Target boost > actual; possible whistle/hiss; positive fuel-trim drift under boost.",
        disconfirming_evidence="System holds specified pressure under a smoke/pressure test.",
        consequences="Reduced performance; possible lean condition under boost.",
        components=["intercooler", "charge-piping", "throttle-body"],
        symptoms=[("Low indicated boost", "low boost pressure underboost"),
                  ("Whistle/hiss under load", "whistle hiss noise boost")]),
    "pcv-unmetered-air": dict(
        name="PCV / unmetered-air leak", system_slug="engine", severity="moderate",
        description="Crankcase-vent / post-MAF air path leak drawing unmetered air.",
        expected_observations="Idle/fuel-trim disturbance; P04DB-type crankcase-vent history; rough idle.",
        disconfirming_evidence="PCV plumbing intact and correctly routed; no vacuum leak found.",
        consequences="Idle quality + fueling errors; can mimic boost complaints.",
        components=["pcv", "intake-manifold"],
        symptoms=[("Rough idle", "rough idle stall unmetered vacuum"),
                  ("Boost-related driveability", "boost driveability crankcase pcv")]),
    "wastegate-fault": dict(
        name="Wastegate / boost-control fault", system_slug="forced-induction", severity="high",
        description="Boost-control actuator/solenoid not regulating boost to target.",
        expected_observations="Actual boost diverges from target; duty-cycle pegging; over/underboost codes.",
        disconfirming_evidence="Actual tracks target within tolerance; duty-cycle sane.",
        consequences="Under- or over-boost; risk of overboost fuel-cut or damage.",
        components=["wastegate"],
        symptoms=[("Low indicated boost", "low boost target actual wastegate"),
                  ("Overboost cut", "overboost cut fuel wastegate")]),
    "turbo-mechanical": dict(
        name="Turbo mechanical wear", system_slug="forced-induction", severity="high",
        description="Turbocharger bearing/shaft or compressor wheel wear.",
        expected_observations="Shaft play; oil in intake; noise; smoke; low boost.",
        disconfirming_evidence="No shaft play; clean compressor; boost achievable.",
        consequences="Progressive boost loss; potential catastrophic failure.",
        components=["turbocharger"],
        symptoms=[("Turbo noise", "turbo noise whine grind bearing"),
                  ("Oil consumption / smoke", "smoke oil turbo consumption")]),
}

# slug: dict — reusable tests. info_gain 0..1 discriminating power; cost/risk 1..5.
TESTS = {
    "smoke-test": dict(name="Smoke test (pressurize intake tract)",
                       purpose="Detect leaks in the pressurized intake system.",
                       discriminates="charge-air-leak", effect="confirms",
                       info_gain=0.9, cost=2, time_min=20, difficulty=2, risk=1,
                       required_tools="smoke machine", required_state="engine off"),
    "pcv-inspection": dict(name="Visual intake + PCV plumbing inspection",
                           purpose="Confirm PCV routing / find disconnected hoses.",
                           discriminates="pcv-unmetered-air", effect="confirms",
                           info_gain=0.5, cost=1, time_min=15, difficulty=1, risk=1),
    "boost-log": dict(name="Boost target vs actual (datalog)",
                      purpose="Compare requested vs actual boost across a pull.",
                      discriminates="wastegate-fault", effect="confirms",
                      info_gain=0.8, cost=2, time_min=25, difficulty=2, risk=2,
                      required_tools="FORScan/datalogger", required_state="road/dyno pull"),
    "wastegate-duty": dict(name="Wastegate duty-cycle analysis",
                           purpose="Check boost-control duty for pegging/correction.",
                           discriminates="wastegate-fault", effect="confirms",
                           info_gain=0.7, cost=2, time_min=20, difficulty=3, risk=2),
    "shaft-play": dict(name="Turbo shaft-play + compressor inspection",
                       purpose="Assess turbo mechanical condition.",
                       discriminates="turbo-mechanical", effect="confirms",
                       info_gain=0.75, cost=3, time_min=40, difficulty=3, risk=2,
                       required_state="intake removed"),
}


def seed_diaglib(session: Session) -> str:
    fm_n = t_n = 0
    for slug, d in FAILURE_MODES.items():
        fm = session.scalar(select(FailureMode).where(FailureMode.slug == slug))
        if fm is None:
            fm = FailureMode(slug=slug, name=d["name"], system_slug=d["system_slug"],
                             description=d["description"], expected_observations=d["expected_observations"],
                             disconfirming_evidence=d["disconfirming_evidence"],
                             consequences=d["consequences"], severity=d["severity"])
            session.add(fm)
            session.flush()
            fm_n += 1
            for c in d["components"]:
                session.add(FailureModeComponent(failure_mode_id=fm.id, component_slug=c))
            for label, kw in d["symptoms"]:
                session.add(FailureModeSymptom(failure_mode_id=fm.id, symptom=label, keywords=kw))
    for slug, d in TESTS.items():
        if session.scalar(select(DiagnosticTest).where(DiagnosticTest.slug == slug)) is None:
            session.add(DiagnosticTest(slug=slug, **d))
            t_n += 1
    session.flush()
    return f"Diagnostic library seeded: +{fm_n} failure modes, +{t_n} diagnostic tests."
