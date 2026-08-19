"""Unit tests for the claim/evidence engine — pure, no database (V2 Phase 1)."""
from app import provenance as pv
from app.domain import Verification


def E(auth, stance=pv.SUPPORTS, on_vehicle=False, label=""):
    return pv.Evidence(authority=auth, stance=stance, on_vehicle=on_vehicle, source_label=label)


# --- authority ceilings / precedence ---------------------------------------
def test_oem_source_reaches_oem_verified():
    v = pv.resolve_verdict([E(1, label="Ford WSM")])
    assert v.verification is Verification.OEM_VERIFIED
    assert not v.conflict and v.supporting == 1


def test_single_anecdote_is_unverified():
    v = pv.resolve_verdict([E(5, label="forum post")])
    assert v.verification is Verification.UNVERIFIED


def test_community_consensus_is_corroborated():
    v = pv.resolve_verdict([E(4, label="forum consensus")])
    assert v.verification is Verification.CORROBORATED


def test_weaker_never_outranks_stronger():
    # OEM + a bunch of anecdotes → still OEM-grade, not diluted.
    v = pv.resolve_verdict([E(1, label="Ford"), E(5), E(5), E(6)])
    assert v.verification is Verification.OEM_VERIFIED


def test_on_vehicle_reaches_vehicle_verified():
    v = pv.resolve_verdict([E(3, on_vehicle=True, label="measured on car")])
    assert v.verification is Verification.VEHICLE_VERIFIED
    assert v.confidence >= 0.9


def test_no_supporting_evidence_is_unverified():
    assert pv.resolve_verdict([]).verification is Verification.UNVERIFIED
    only_against = pv.resolve_verdict([E(2, stance=pv.CONTRADICTS)])
    assert only_against.verification is Verification.UNVERIFIED
    assert only_against.conflict


# --- conflict handling -----------------------------------------------------
def test_equal_authority_contradiction_flags_conflict_and_caps():
    v = pv.resolve_verdict([E(1, label="Ford A"), E(1, stance=pv.CONTRADICTS, label="Ford B")])
    assert v.conflict
    # capped one tier below OEM_VERIFIED
    assert v.verification is Verification.CORROBORATED


def test_weaker_contradiction_does_not_conflict():
    v = pv.resolve_verdict([E(1, label="Ford"), E(5, stance=pv.CONTRADICTS)])
    assert not v.conflict
    assert v.verification is Verification.OEM_VERIFIED


def test_confidence_rises_with_corroboration():
    one = pv.resolve_verdict([E(2)])
    two = pv.resolve_verdict([E(2), E(2)])
    assert two.confidence > one.confidence


def test_conflict_lowers_confidence():
    clean = pv.resolve_verdict([E(1)])
    conflicted = pv.resolve_verdict([E(1), E(1, stance=pv.CONTRADICTS)])
    assert conflicted.confidence < clean.confidence


# --- applicability ---------------------------------------------------------
def test_applicability_none_matches_all():
    assert pv.applies_to(None, {"variant": "focus-st", "year": 2017})


def test_applicability_variant_and_year_range():
    ap = {"variant": "focus-st", "years": "2015-2018", "market": "NA"}
    assert pv.applies_to(ap, {"variant": "focus-st", "year": 2017, "market": "NA"})
    assert not pv.applies_to(ap, {"variant": "focus-st", "year": 2019, "market": "NA"})
    assert not pv.applies_to(ap, {"variant": "fiesta-st", "year": 2017, "market": "NA"})


def test_applicability_open_ended_range():
    assert pv.applies_to({"years": "2015-"}, {"year": 2020})
    assert not pv.applies_to({"years": "2015-"}, {"year": 2014})
