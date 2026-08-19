"""Claim-level provenance — the evidence engine (V2 Phase 1).

A *claim* is a single automotive fact ("Focus ST lug torque = 100 lb-ft") that may
be supported or contradicted by multiple pieces of *evidence*, each from a source of
some authority. This module resolves a set of evidence into a **verdict**:

    verification (UNVERIFIED..VEHICLE_VERIFIED) + confidence + conflict flag

It is pure (no DB, no I/O) so the precedence rules are unit-tested in isolation.
It reuses the existing `Verification` ladder from domain.py — V2 extends, not replaces.

Core rules:
  - Weaker evidence never silently outranks stronger (KB rule, enforced by MAX-tier).
  - A fact observed on THIS vehicle (`on_vehicle`) can reach VEHICLE_VERIFIED —
    document evidence alone tops out at OEM_VERIFIED.
  - A contradiction from an equally- or more-authoritative source caps the verdict
    and raises the conflict flag: the system surfaces disagreement, never hides it.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .domain import Verification, authority_label

# --- evidence stance -------------------------------------------------------
SUPPORTS = "supports"
CONTRADICTS = "contradicts"
SUPERSEDES = "supersedes"   # a newer revision that replaces prior evidence
STANCES = {SUPPORTS, CONTRADICTS, SUPERSEDES}

# A lone document source of authority N justifies at most this verification tier.
# (Authority 1 = OEM/factory … 6 = unknown; see domain.AUTHORITY_LABELS.)
AUTHORITY_CEILING: dict[int, Verification] = {
    1: Verification.OEM_VERIFIED,     # OEM / factory
    2: Verification.OEM_VERIFIED,     # OEM-adjacent / SAE
    3: Verification.CORROBORATED,     # professional / trade
    4: Verification.CORROBORATED,     # reputable community consensus
    5: Verification.UNVERIFIED,       # single anecdote
    6: Verification.UNVERIFIED,       # unknown / unattributed
}


@dataclass(frozen=True)
class Evidence:
    """One piece of support/contradiction for a claim."""
    authority: int                    # 1 (best) .. 6 (unknown)
    stance: str = SUPPORTS
    on_vehicle: bool = False          # observed on THIS specific car
    source_label: str = ""            # human label for rationale/UI

    def ceiling(self) -> Verification:
        if self.on_vehicle:
            return Verification.VEHICLE_VERIFIED
        return AUTHORITY_CEILING.get(self.authority, Verification.UNVERIFIED)


@dataclass(frozen=True)
class Verdict:
    verification: Verification
    confidence: float                 # 0.0 .. 1.0
    conflict: bool
    rationale: str
    supporting: int = 0
    contradicting: int = 0

    def as_dict(self) -> dict:
        return {
            "verification": self.verification.name,
            "confidence": round(self.confidence, 2),
            "conflict": self.conflict,
            "rationale": self.rationale,
            "supporting": self.supporting,
            "contradicting": self.contradicting,
        }


def _best_authority(evs: list[Evidence]) -> int:
    return min((e.authority for e in evs), default=6)


def resolve_verdict(evidence: list[Evidence]) -> Verdict:
    """Resolve a claim's evidence into a verification tier + confidence + conflict.

    Never lets weaker evidence outrank stronger; caps + flags on real conflict.
    """
    supporting = [e for e in evidence if e.stance in (SUPPORTS, SUPERSEDES)]
    contradicting = [e for e in evidence if e.stance == CONTRADICTS]

    if not supporting:
        return Verdict(Verification.UNVERIFIED, 0.15 if evidence else 0.0, bool(contradicting),
                       "No supporting evidence." if not contradicting
                       else "Only contradicting evidence on record.",
                       0, len(contradicting))

    # Strongest tier any supporting source can justify (MAX enforces precedence).
    tier = max(e.ceiling() for e in supporting)
    best_sup_auth = _best_authority(supporting)

    # Conflict: a contradicting source at least as authoritative as the best support.
    conflict = any(e.authority <= best_sup_auth for e in contradicting)
    rationale_bits = []
    if conflict:
        # Cap the verdict one tier down (don't assert OEM-verified over a peer dispute).
        tier = Verification(max(Verification.UNVERIFIED, Verification(tier - 1)))
        rationale_bits.append("Conflicting evidence of comparable authority — verdict capped.")

    # Confidence: authority strength + corroboration, penalized by conflict.
    auth_strength = (7 - best_sup_auth) / 6.0                      # 1..6 → ~1.0..0.17
    corroboration = min(1.0, 0.6 + 0.2 * (len(supporting) - 1))    # more sources → more
    conf = auth_strength * corroboration
    if any(e.on_vehicle for e in supporting):
        conf = max(conf, 0.9)                                     # measured on the car
    if conflict:
        conf *= 0.6
    conf = max(0.0, min(1.0, conf))

    top = min(supporting, key=lambda e: (0 if e.on_vehicle else 1, e.authority))
    rationale_bits.insert(0, f"Best support: {top.source_label or authority_label(top.authority)}"
                          + (" (on-vehicle)" if top.on_vehicle else "")
                          + f"; {len(supporting)} supporting.")
    return Verdict(Verification(tier), conf, conflict, " ".join(rationale_bits),
                   len(supporting), len(contradicting))


# --- applicability ---------------------------------------------------------
def applies_to(applicability: dict | None, context: dict) -> bool:
    """Does a claim's applicability match a query context?

    applicability keys are optional; a missing key means "applies to all". Supported:
      - variant: exact slug match
      - market:  exact match (or 'any')
      - years:   'YYYY-YYYY' / 'YYYY-' / 'YYYY' range vs context['year']
    """
    if not applicability:
        return True
    if "variant" in applicability and context.get("variant") not in (applicability["variant"], None):
        return False
    if "market" in applicability and applicability["market"] not in ("any", context.get("market"), None):
        return False
    yr = context.get("year")
    if "years" in applicability and yr is not None:
        lo, hi = _year_range(applicability["years"])
        if (lo is not None and yr < lo) or (hi is not None and yr > hi):
            return False
    return True


def _year_range(spec: str) -> tuple[int | None, int | None]:
    s = str(spec).strip()
    if "-" in s:
        a, _, b = s.partition("-")
        return (int(a) if a.strip() else None, int(b) if b.strip() else None)
    if s.isdigit():
        return (int(s), int(s))
    return (None, None)
