"""Unit tests for the enforced Domain Constitution (pure, no DB)."""
import pytest

from app.epistemics import (
    CONFIRMING_EVIDENCE,
    EVIDENCE,
    POST_REPAIR_VERIFICATION,
    EpistemicError,
    Kind,
    can_promote,
    promote,
    required_bridge,
)


def test_claim_to_observation_is_never_allowed():
    assert required_bridge(Kind.CLAIM, Kind.OBSERVATION) is None
    with pytest.raises(EpistemicError):
        promote(Kind.CLAIM, Kind.OBSERVATION)
    with pytest.raises(EpistemicError):
        promote(Kind.CLAIM, Kind.OBSERVATION, bridge=EVIDENCE)  # no bridge rescues it


def test_observation_to_finding_requires_evidence():
    with pytest.raises(EpistemicError):
        promote(Kind.OBSERVATION, Kind.FINDING)              # bare promotion rejected
    promote(Kind.OBSERVATION, Kind.FINDING, bridge=EVIDENCE)  # with evidence: allowed


def test_hypothesis_to_finding_requires_confirming_evidence():
    assert not can_promote(Kind.HYPOTHESIS, Kind.FINDING)
    assert not can_promote(Kind.HYPOTHESIS, Kind.FINDING, EVIDENCE)   # wrong bridge
    assert can_promote(Kind.HYPOTHESIS, Kind.FINDING, CONFIRMING_EVIDENCE)


def test_finding_to_verified_repair_requires_verification():
    with pytest.raises(EpistemicError):
        promote(Kind.FINDING, Kind.VERIFIED_REPAIR)
    promote(Kind.FINDING, Kind.VERIFIED_REPAIR, bridge=POST_REPAIR_VERIFICATION)


def test_unconstrained_promotions_are_allowed():
    # No rule governs observation → measurement; it is permitted freely.
    assert required_bridge(Kind.OBSERVATION, Kind.MEASUREMENT) is False
    promote(Kind.OBSERVATION, Kind.MEASUREMENT)  # does not raise
