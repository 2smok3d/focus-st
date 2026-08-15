"""Recall / safety-campaign lookup.

Two data paths, one table:
  - KNOWN[] — the Focus ST campaigns the knowledge base already documents, seeded
    so the store is useful even with no network. Graded CORROBORATED and clearly
    flagged "verify against the VIN".
  - fetch_nhtsa() — the free NHTSA recallsByVehicle API (by make/model/year).
    parse_nhtsa() maps its JSON to recall rows; it's pure and unit-tested.

Per-VIN completion status is NOT in the free API, so `status` stays 'unknown'
until a human confirms it at a dealer — the honest default.
"""
from __future__ import annotations

import datetime as dt

NHTSA_URL = "https://api.nhtsa.gov/recalls/recallsByVehicle"

# Known campaigns for the MK3 Focus ST, from KB "04 Recalls & TSBs". Seeded as a
# baseline; the live fetch augments/updates these by campaign number.
KNOWN: list[dict] = [
    dict(campaign_number="18S32", origin="ford-known", component="Fuel system — EVAP purge valve",
         summary="EVAP purge valve can stick open, drawing excess vacuum on the tank "
                 "(rough idle/stall after refueling, possible P1450). Ford customer program.",
         remedy="Purge valve inspection/replacement + PCM calibration per program.",
         note="Verify completion against THIS VIN at nhtsa.gov/recalls or a Ford dealer."),
    dict(campaign_number="26S40", origin="ford-known", component="Fuel system — EVAP purge (follow-up)",
         summary="Related EVAP purge-valve campaign referenced alongside 18S32.",
         remedy="Per Ford program — inspection/replacement + calibration as specified.",
         note="Confirm applicability and completion for this VIN; numbers vary by market/year."),
    dict(campaign_number="ST-SEATBACK", origin="ford-known", component="Seats — seatback frame",
         summary="Seatback-related campaign noted for the platform in the KB.",
         remedy="Per applicable Ford bulletin/recall.",
         note="Community/KB-noted — verify the exact campaign and applicability by VIN."),
    dict(campaign_number="ST-HATCH-LATCH", origin="ford-known", component="Latches — hatch/liftgate",
         summary="Hatch-latch campaign noted for the platform in the KB.",
         remedy="Per applicable Ford bulletin/recall.",
         note="Community/KB-noted — verify the exact campaign and applicability by VIN."),
]


def _to_date(v) -> dt.date | None:
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_nhtsa(results: list[dict]) -> list[dict]:
    """Map NHTSA recallsByVehicle `results` entries to recall rows. Pure."""
    out: list[dict] = []
    for r in results or []:
        camp = (r.get("NHTSACampaignNumber") or r.get("Campaign") or "").strip()
        if not camp:
            continue
        out.append({
            "campaign_number": camp,
            "origin": "nhtsa",
            "component": (r.get("Component") or "").strip() or None,
            "summary": (r.get("Summary") or "").strip() or None,
            "consequence": (r.get("Consequence") or "").strip() or None,
            "remedy": (r.get("Remedy") or "").strip() or None,
            "report_date": _to_date(r.get("ReportReceivedDate")),
            "verification": "OEM_VERIFIED",  # sourced from the federal database
            "note": (r.get("Notes") or "").strip() or None,
        })
    return out


def fetch_nhtsa(make: str, model: str, model_year: int, *, timeout: float = 25.0) -> list[dict]:
    """Query NHTSA and return parsed recall rows. Network — raises on failure so
    callers can fall back to the seeded baseline. Uses env proxies if present."""
    import httpx  # local import: only needed when a live refresh is requested

    resp = httpx.get(NHTSA_URL, params={"make": make, "model": model,
                                        "modelYear": str(model_year)},
                     timeout=timeout, trust_env=True)
    resp.raise_for_status()
    return parse_nhtsa(resp.json().get("results", []))
