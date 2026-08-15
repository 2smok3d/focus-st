"""Domain logic — pure, no database I/O so it's unit-testable in isolation.

Three jobs:
  1. Evidence grading: rank sources and order verification states, and refuse to
     let weak evidence silently override strong evidence.
  2. Maintenance-due math: given intervals + last service + current odometer/date,
     say what's due, overdue, or upcoming.
  3. Parts search links: turn a query into retailer search URLs.
"""
from __future__ import annotations

import datetime as dt
import urllib.parse
from dataclasses import dataclass
from enum import IntEnum

# ---------------------------------------------------------------------------
# Source authority (rank 1 = best). Mirrors KB "12 Sources" grading.
# ---------------------------------------------------------------------------
AUTHORITY_LABELS: dict[int, str] = {
    1: "OEM / factory (Ford workshop manual, Motorcraft, VIN-specific)",
    2: "Authoritative aftermarket / OEM-adjacent (tuner docs, iDatalink, SAE)",
    3: "Professional / trade (verified indie tech, established shop TSB)",
    4: "Reputable community consensus (well-sourced forum/wiki agreement)",
    5: "Single community post / anecdote",
    6: "Unknown / unattributed",
}


def authority_label(rank: int) -> str:
    return AUTHORITY_LABELS.get(rank, "Unknown")


class Verification(IntEnum):
    """Evidence maturity — higher ordinal = stronger. Matches KB 05."""
    UNVERIFIED = 0
    CORROBORATED = 1
    OEM_VERIFIED = 2
    VEHICLE_VERIFIED = 3

    @classmethod
    def parse(cls, s: str) -> "Verification":
        return cls[s.strip().upper().replace("-", "_")]


def can_override(incoming: str | Verification, existing: str | Verification) -> bool:
    """May a claim at `incoming` maturity replace one already at `existing`?

    Rule (KB 05): "Lower states can raise hypotheses but never silently override
    a higher one." Equal or stronger evidence may replace; weaker may not.
    """
    inc = incoming if isinstance(incoming, Verification) else Verification.parse(incoming)
    exi = existing if isinstance(existing, Verification) else Verification.parse(existing)
    return inc >= exi


# ---------------------------------------------------------------------------
# Maintenance-due engine
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DueStatus:
    item: str
    status: str            # "overdue" | "due-soon" | "ok" | "unknown"
    miles_remaining: int | None
    months_remaining: float | None
    last_miles: int | None
    last_date: dt.date | None
    detail: str

    def as_dict(self) -> dict:
        return {
            "item": self.item,
            "status": self.status,
            "miles_remaining": self.miles_remaining,
            "months_remaining": (
                round(self.months_remaining, 1) if self.months_remaining is not None else None
            ),
            "last_miles": self.last_miles,
            "last_date": self.last_date.isoformat() if self.last_date else None,
            "detail": self.detail,
        }


# An item is "due soon" once within this fraction of its interval remaining,
# or within this many miles / months of the limit — whichever triggers first.
SOON_FRACTION = 0.10
SOON_MILES_FLOOR = 500
SOON_MONTHS_FLOOR = 1.0


def _months_between(a: dt.date, b: dt.date) -> float:
    return (b.year - a.year) * 12 + (b.month - a.month) + (b.day - a.day) / 30.0


def maintenance_due(
    item: str,
    interval_miles: int | None,
    interval_months: int | None,
    last_miles: int | None,
    last_date: dt.date | None,
    current_miles: int | None,
    today: dt.date | None = None,
) -> DueStatus:
    """Evaluate one maintenance item. Mileage and time are checked independently;
    the *worse* of the two drives the verdict (whichever comes due first)."""
    today = today or dt.date.today()

    # Never serviced but we have an interval → treat as due now (best-effort).
    if last_miles is None and last_date is None:
        if interval_miles or interval_months:
            return DueStatus(item, "overdue", None, None, None, None,
                             "No service on record for an item with a defined interval.")
        return DueStatus(item, "unknown", None, None, None, None, "No interval and no history.")

    miles_remaining: int | None = None
    if interval_miles and last_miles is not None and current_miles is not None:
        miles_remaining = (last_miles + interval_miles) - current_miles

    months_remaining: float | None = None
    if interval_months and last_date is not None:
        elapsed = _months_between(last_date, today)
        months_remaining = interval_months - elapsed

    # Verdict per dimension.
    verdicts: list[str] = []
    if miles_remaining is not None:
        soon_m = max(SOON_MILES_FLOOR, interval_miles * SOON_FRACTION)  # type: ignore[operator]
        verdicts.append(
            "overdue" if miles_remaining < 0
            else "due-soon" if miles_remaining <= soon_m
            else "ok"
        )
    if months_remaining is not None:
        soon_t = max(SOON_MONTHS_FLOOR, interval_months * SOON_FRACTION)  # type: ignore[operator]
        verdicts.append(
            "overdue" if months_remaining < 0
            else "due-soon" if months_remaining <= soon_t
            else "ok"
        )

    if not verdicts:
        status = "unknown"
    elif "overdue" in verdicts:
        status = "overdue"
    elif "due-soon" in verdicts:
        status = "due-soon"
    else:
        status = "ok"

    bits = []
    if miles_remaining is not None:
        bits.append(f"{miles_remaining:+,} mi")
    if months_remaining is not None:
        bits.append(f"{months_remaining:+.1f} mo")
    detail = " / ".join(bits) if bits else "insufficient data"

    return DueStatus(item, status, miles_remaining, months_remaining,
                     last_miles, last_date, detail)


# ---------------------------------------------------------------------------
# Parts search-link generator
# ---------------------------------------------------------------------------
VEHICLE_TAG = "2017 Ford Focus ST"

_RETAILERS: dict[str, str] = {
    "amazon": "https://www.amazon.com/s?k={q}",
    "ebay": "https://www.ebay.com/sch/i.html?_nkw={q}",
    "rockauto": "https://www.rockauto.com/en/partsearch/?partsearch={q}",
    "summit": "https://www.summitracing.com/search?SearchTerm={q}",
    "google": "https://www.google.com/search?q={q}",
}


def parts_search_links(
    query: str,
    *,
    part_number: str | None = None,
    include_vehicle: bool = True,
    retailers: list[str] | None = None,
) -> dict[str, str]:
    """Build retailer search URLs for a part. Part number, when present, is the
    strongest search term, so it leads; the vehicle tag disambiguates generic
    names ("intercooler" → "2017 Ford Focus ST intercooler")."""
    terms: list[str] = []
    if part_number:
        terms.append(part_number)
    if include_vehicle and not part_number:
        terms.append(VEHICLE_TAG)
    terms.append(query)
    q = urllib.parse.quote_plus(" ".join(t for t in terms if t))

    chosen = retailers or list(_RETAILERS)
    return {r: _RETAILERS[r].format(q=q) for r in chosen if r in _RETAILERS}


# ---------------------------------------------------------------------------
# Proposal → target mapping. Which columns a proposal may set per entity.
# The approval path (cli/main) uses this allow-list so a proposal can't write
# arbitrary columns.
# ---------------------------------------------------------------------------
PROPOSABLE_ENTITIES: dict[str, set[str]] = {
    "mod": {"slot", "part_name", "part_number", "installed_on", "installed_miles",
            "cost", "url", "stage", "verification", "note"},
    "issue": {"title", "status", "severity", "opened_at", "resolved_at",
              "root_cause", "verification", "note"},
    "spec": {"category", "name", "value", "unit", "verification"},
    "service_event": {"item", "performed_at", "miles", "cost", "vendor", "note"},
}


def validate_patch(entity: str, patch: dict) -> tuple[bool, str]:
    """Return (ok, message). Rejects unknown entities and stray columns."""
    allowed = PROPOSABLE_ENTITIES.get(entity)
    if allowed is None:
        return False, f"Unknown proposable entity '{entity}'. Allowed: {sorted(PROPOSABLE_ENTITIES)}"
    stray = set(patch) - allowed
    if stray:
        return False, f"Fields not allowed on '{entity}': {sorted(stray)}"
    if not patch:
        return False, "Empty patch."
    return True, "ok"
