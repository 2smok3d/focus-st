from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from .domain import AUTHORITY_WEIGHT, Authority, Claim, SourceRef


@dataclass(frozen=True)
class RankedClaim:
    claim: Claim
    score: float
    source_count: int
    independent_publishers: int
    rationale: tuple[str, ...]


@dataclass(frozen=True)
class ConflictResolution:
    subject: str
    predicate: str
    selected_claim_id: UUID | None
    ranked: tuple[RankedClaim, ...]
    unresolved: bool
    explanation: str


def _source_score(source: SourceRef) -> float:
    return AUTHORITY_WEIGHT[source.authority]


def rank_claim(claim: Claim, sources: Iterable[SourceRef]) -> RankedClaim:
    source_list = list(sources)
    rationale: list[str] = []
    if not source_list:
        return RankedClaim(claim, max(0.0, claim.confidence * 0.35), 0, 0, ("no linked sources",))

    weights = [_source_score(s) for s in source_list]
    authority = max(weights)
    publishers = {s.publisher or str(s.url) or s.title for s in source_list}
    corroboration = min(0.12, max(0, len(publishers) - 1) * 0.03)
    source_depth = min(0.05, max(0, len(source_list) - 1) * 0.01)
    verified_bonus = 0.04 if claim.verified_at else 0.0
    conflict_penalty = 0.04 if claim.conflict_group else 0.0

    score = (
        0.62 * authority
        + 0.26 * claim.confidence
        + corroboration
        + source_depth
        + verified_bonus
        - conflict_penalty
    )
    score = max(0.0, min(1.0, score))

    rationale.append(f"highest source authority={authority:.2f}")
    rationale.append(f"claim confidence={claim.confidence:.2f}")
    if corroboration:
        rationale.append(f"independent publisher corroboration +{corroboration:.2f}")
    if verified_bonus:
        rationale.append("explicitly verified")
    if conflict_penalty:
        rationale.append("part of unresolved conflict group")
    return RankedClaim(claim, score, len(source_list), len(publishers), tuple(rationale))


def resolve_conflict(claims: Iterable[Claim], sources_by_id: dict[UUID, SourceRef], margin: float = 0.08) -> ConflictResolution:
    claim_list = list(claims)
    if not claim_list:
        return ConflictResolution("", "", None, (), True, "no claims supplied")
    subject, predicate = claim_list[0].subject, claim_list[0].predicate
    ranked: list[RankedClaim] = []
    for claim in claim_list:
        linked = [sources_by_id[sid] for sid in claim.source_ids if sid in sources_by_id]
        ranked.append(rank_claim(claim, linked))
    ranked.sort(key=lambda x: x.score, reverse=True)

    if len(ranked) == 1:
        return ConflictResolution(subject, predicate, ranked[0].claim.id, tuple(ranked), False, "single supported claim")

    top, second = ranked[0], ranked[1]
    unresolved = (top.score - second.score) < margin
    selected = None if unresolved else top.claim.id
    explanation = (
        f"unresolved: top claims differ by only {top.score-second.score:.3f}; retain both visibly"
        if unresolved
        else f"selected higher-authority claim by margin {top.score-second.score:.3f}"
    )
    return ConflictResolution(subject, predicate, selected, tuple(ranked), unresolved, explanation)


def authority_policy() -> list[dict[str, str | float]]:
    ordered = sorted(AUTHORITY_WEIGHT.items(), key=lambda kv: kv[1], reverse=True)
    return [{"authority": authority.value, "weight": weight} for authority, weight in ordered]


KNOWN_CONFLICT_EXAMPLES = {
    "transmission_family": {
        "legacy_claim": "MT82",
        "canonical": "Getrag-Ford MMT6",
        "resolution": "Ford 2017 Focus ST documentation outranks legacy catalog text",
    },
    "engine_air_filter": {
        "legacy_claim": "Motorcraft FA-1802",
        "canonical": "Motorcraft FA-1908",
        "resolution": "Ford 2017 Focus ST Motorcraft-parts table outranks legacy catalog text",
    },
}
