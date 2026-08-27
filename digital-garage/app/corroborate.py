"""CORR — corroboration suggester (extends Phase-6 provenance + knowledge ops).

The compendium wants "automated evidence verification". Rebuilt *in this platform's grain*
without breaking the sacred rule that **the agent proposes, a human approves, and verdicts are
computed from evidence, never asserted**.

A claim is keyed uniquely by (subject, property), so corroboration here is not "find an agreeing
duplicate" — it is **adding an independent supporting source to an existing `UNVERIFIED` claim**,
which `_apply_claim_proposal` re-resolves monotonically (a weak claim is promoted, a strong one
is never demoted). CORR does two honest things:

  • *Suggest*: for every `UNVERIFIED` claim, compute — with the same `resolve_verdict` the
    approval path uses — the verdict it *would* reach if one more supporting source were linked,
    and the **weakest source authority that would actually promote it** ("a trade source suffices"
    vs "needs an OEM source"). It invents no evidence; it quantifies the leverage of finding one.
  • *Propose*: file the source a human actually found as a **pending proposal** through the
    ordinary approval boundary. Nothing is corroborated until a person approves it.
"""
from __future__ import annotations

from .domain import Verification, authority_label
from .provenance import SUPPORTS, Evidence, resolve_verdict

# The realistic "next source" a person is likely to find first (3 = professional/trade). Lifts
# an UNVERIFIED claim to CORROBORATED — the common, achievable corroboration.
TRADE_AUTHORITY = 3


def project_verdict(existing: list[Evidence], added: Evidence) -> dict:
    """Verdict the claim would resolve to if `added` evidence were linked. Pure."""
    return resolve_verdict(list(existing) + [added]).as_dict()


def min_authority_to_promote(existing: list[Evidence], current: str) -> int | None:
    """The weakest supporting-source authority (1 best … 6) that would lift this claim above its
    current tier, or None if even an OEM source wouldn't (already at ceiling / blocked by
    conflict). Pure — probes the real verdict engine, never asserts."""
    cur = Verification[current]
    for auth in range(6, 0, -1):                      # weakest first — report the easiest that works
        v = project_verdict(existing, Evidence(authority=auth, stance=SUPPORTS))
        if Verification[v["verification"]] > cur:
            return auth
    return None


# ---- service ------------------------------------------------------------------
def _claim_evidence(claim) -> list[Evidence]:
    return [Evidence(authority=e.authority, stance=e.stance, on_vehicle=e.on_vehicle,
                     source_label=e.source_label or "") for e in claim.evidence]


def _variant_claims(session, variant_slug: str):
    from sqlalchemy import select

    from .refmodels import Claim
    return session.scalars(select(Claim).where(
        Claim.applicability["variant"].astext == variant_slug)).all()


def corroboration_candidates(session, variant_slug: str = "focus-st") -> dict:
    """Every `UNVERIFIED` claim for one machine, with the verdict one more source would earn and
    the weakest authority that would promote it. Read-only — proposing a source is a separate,
    approval-gated step."""
    claims = [c for c in _variant_claims(session, variant_slug) if c.verification == "UNVERIFIED"]
    candidates = []
    for c in claims:
        evs = _claim_evidence(c)
        need = min_authority_to_promote(evs, c.verification)
        at_trade = project_verdict(evs, Evidence(authority=TRADE_AUTHORITY, stance=SUPPORTS))["verification"]
        candidates.append({
            "claim_id": c.id, "subject_type": c.subject_type, "subject_key": c.subject_key,
            "prop": c.prop, "value": c.value, "unit": c.unit,
            "current_verification": c.verification,
            "projected_with_trade_source": at_trade,
            "min_authority_to_promote": need,
            "min_source": authority_label(need) if need else None,
            "promotable": need is not None,
            "suggestion": (
                f"{c.subject_key}·{c.prop} is UNVERIFIED — "
                + (f"one {authority_label(need)} source would promote it to "
                   f"{project_verdict(evs, Evidence(authority=need, stance=SUPPORTS))['verification']}."
                   if need else "even an OEM source wouldn't lift it (already capped or in conflict).")),
        })
    # easiest wins first: promotable, then the weakest authority that suffices
    candidates.sort(key=lambda x: (not x["promotable"], x["min_authority_to_promote"] or 99))
    return {"variant": variant_slug, "unverified": len(claims),
            "promotable": sum(1 for c in candidates if c["promotable"]),
            "candidates": candidates}


def propose_corroboration(session, vehicle_id: int, claim_id: int, *, authority: int,
                          source_label: str, on_vehicle: bool = False,
                          proposed_by: str = "corr-agent") -> dict:
    """File a *pending proposal* linking a real source a person found (its `authority` 1..6 and a
    `source_label`) to an UNVERIFIED claim, through the ordinary approval boundary. Never mutates
    the claim — a human approves it and the verdict is recomputed from the merged evidence on
    approval. Invents no evidence: the caller must name the source."""
    from . import service
    from .refmodels import Claim

    if not (1 <= authority <= 6):
        raise ValueError("authority must be 1 (OEM/best) .. 6 (unknown).")
    if not source_label or not source_label.strip():
        raise ValueError("a source_label is required — corroboration must name its source.")
    claim = session.get(Claim, claim_id)
    if claim is None:
        raise ValueError(f"claim #{claim_id} not found.")
    if claim.verification != "UNVERIFIED":
        raise ValueError(f"claim #{claim_id} is already {claim.verification}; nothing to corroborate.")

    projected = project_verdict(_claim_evidence(claim),
                                Evidence(authority=authority, stance=SUPPORTS, on_vehicle=on_vehicle))
    return service.propose_claim(
        session, vehicle_id, subject_type=claim.subject_type, subject_key=claim.subject_key,
        prop=claim.prop, value=claim.value, unit=claim.unit, applicability=claim.applicability,
        evidence=[{"authority": authority, "stance": SUPPORTS, "on_vehicle": on_vehicle,
                   "label": source_label}],
        rationale=(f"CORR: corroborate claim #{claim_id} ({claim.subject_key}·{claim.prop}) with "
                   f"{authority_label(authority)} source '{source_label}' → projects to "
                   f"{projected['verification']}."),
        proposed_by=proposed_by)
