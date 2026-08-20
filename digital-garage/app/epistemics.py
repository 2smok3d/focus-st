"""Epistemic kinds + the enforced Domain Constitution (Milestone A).

Pure module (no DB, no I/O) so the rules are unit-tested in isolation and run in CI
without a database. Encodes the entity kinds from docs/DOMAIN-CONSTITUTION.md and the
critical rule: certain promotions between kinds must never happen silently — each
requires an explicit *bridge* (a named justification), or the operation is rejected.

Application services call `promote(...)` at the moment they would turn one kind of
record into another (e.g. concluding a Finding from a Hypothesis) so the constitution
is enforced in code, not merely documented.
"""
from __future__ import annotations

from enum import Enum


class Kind(str, Enum):
    CLAIM = "claim"
    EVIDENCE = "evidence"
    OBSERVATION = "observation"
    MEASUREMENT = "measurement"
    STATE = "state"
    EVENT = "event"
    HYPOTHESIS = "hypothesis"
    FINDING = "finding"
    RECOMMENDATION = "recommendation"
    PROCEDURE = "procedure"
    TEST = "test"
    WORK_ORDER = "work_order"
    EXPERIMENT = "experiment"
    VERIFIED_REPAIR = "verified_repair"


class EpistemicError(ValueError):
    """Raised when a forbidden promotion is attempted without its required bridge."""


# Bridges — the named justification a promotion must carry.
EVIDENCE = "evidence"                       # supporting evidence + reasoning
CONFIRMING_EVIDENCE = "confirming_evidence"  # evidence that confirms a hypothesis
POST_REPAIR_VERIFICATION = "post_repair_verification"  # a verifying test/observation

# (from_kind, to_kind) -> required bridge. None means the promotion is NEVER allowed.
_RULES: dict[tuple[Kind, Kind], str | None] = {
    (Kind.CLAIM, Kind.OBSERVATION): None,                       # never — must be independently observed
    (Kind.OBSERVATION, Kind.FINDING): EVIDENCE,                 # one data point is not a conclusion
    (Kind.HYPOTHESIS, Kind.FINDING): CONFIRMING_EVIDENCE,       # a guess is not a conclusion
    (Kind.FINDING, Kind.VERIFIED_REPAIR): POST_REPAIR_VERIFICATION,  # replaced ≠ fixed
}


def required_bridge(from_kind: Kind, to_kind: Kind) -> str | None | bool:
    """Return the bridge required for a promotion:
      - a bridge string → that justification is required,
      - None            → the promotion is categorically forbidden,
      - False           → no rule constrains this promotion (allowed freely).
    """
    key = (from_kind, to_kind)
    if key not in _RULES:
        return False
    return _RULES[key]


def promote(from_kind: Kind, to_kind: Kind, bridge: str | None = None) -> None:
    """Enforce the constitution for turning one kind of record into another.

    Raises EpistemicError when the promotion is categorically forbidden, or when it
    requires a bridge that was not supplied (or the wrong bridge was supplied).
    A promotion with no governing rule is permitted.
    """
    req = required_bridge(from_kind, to_kind)
    if req is False:
        return  # unconstrained
    if req is None:
        raise EpistemicError(
            f"{from_kind.value} → {to_kind.value} is never a valid silent promotion "
            f"(see docs/DOMAIN-CONSTITUTION.md).")
    if bridge != req:
        raise EpistemicError(
            f"{from_kind.value} → {to_kind.value} requires bridge '{req}', "
            f"got {bridge!r}. A {to_kind.value} may not be asserted without it.")


def can_promote(from_kind: Kind, to_kind: Kind, bridge: str | None = None) -> bool:
    """Non-raising form of `promote` — True if the promotion is permitted."""
    try:
        promote(from_kind, to_kind, bridge)
        return True
    except EpistemicError:
        return False
