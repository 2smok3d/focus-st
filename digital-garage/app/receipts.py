"""Receipt ingest — turn a Gmail receipt into a change proposal.

Two entry shapes, one output:
  - a structured dict (what the Gmail Apps Script / a webhook posts), or
  - raw email text (paste-in),
→ a `Receipt` (vendor, date, total, items, order id) → a *proposal* for a
`parts` purchase or a `service_event`. It never writes the target row: like
everything else that touches the car's record, it lands in the approval queue.

The classifier is deliberately conservative — when unsure it proposes a `parts`
row with a note rather than guessing a service item, so a human tightens it at
approval time.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

# --- vendor knowledge ------------------------------------------------------
# Retailers/brands whose receipts are parts purchases…
_PARTS_VENDORS = {
    "amazon", "ebay", "rockauto", "summit", "summitracing", "mishimoto",
    "mountune", "cobb", "cobbtuning", "steeda", "cp-e", "cpe", "tasca",
    "levittownfordparts", "fordparts", "turbosmart", "gfb", "whoosh",
    "pumaspeed", "corksport", "boomba", "damond", "ptp", "revohealth",
    "gorilla", "michelin", "tirerack", "discounttiredirect",
}
# …and vendors whose receipts are service/labor events.
_SERVICE_VENDORS = {
    "ford", "fordservice", "jiffylube", "valvoline", "firestone", "midas",
    "pepboys", "discounttire", "bigotires", "meineke", "mavis", "brakemasters",
}

# item keyword → canonical maintenance interval item (matches seed.INTERVALS)
_SERVICE_ITEM_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\boil\b.*\bfilter\b|\boil change\b|\bmotorcraft.*oil\b", re.I), "Engine oil & filter"),
    (re.compile(r"\btire rotation|rotate.*tires?\b", re.I), "Tire rotation"),
    (re.compile(r"\bcabin (air )?filter\b", re.I), "Cabin air filter"),
    (re.compile(r"\b(engine )?air filter\b", re.I), "Engine air filter"),
    (re.compile(r"\btransmission fluid|mtf|mmt6\b", re.I), "MMT6 transmission fluid"),
    (re.compile(r"\bspark plugs?\b", re.I), "Spark plugs"),
    (re.compile(r"\bbrake fluid\b", re.I), "Brake fluid"),
    (re.compile(r"\bcoolant|antifreeze\b", re.I), "Coolant"),
    (re.compile(r"\bclutch fluid\b", re.I), "Clutch fluid (shares brake reservoir)"),
]

# part keyword → catalog category (for a parts proposal)
_PART_CATEGORY_MAP: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"accessport|access port|\btune\b|ecu flash|cobb.*stage|calibration", re.I), "Tuning"),
    (re.compile(r"intercooler|fmic", re.I), "Cooling"),
    (re.compile(r"downpipe|cat[- ]?back|exhaust|muffler", re.I), "Exhaust"),
    (re.compile(r"intake|filter|maf", re.I), "Intake"),
    (re.compile(r"turbo|wastegate|bpv|bov|charge pipe", re.I), "Boost"),
    (re.compile(r"motor mount|rmm|bushing", re.I), "Drivetrain"),
    (re.compile(r"coilover|spring|sway bar|shock|strut", re.I), "Suspension"),
    (re.compile(r"pad|rotor|caliper|brake", re.I), "Brakes"),
    (re.compile(r"tire|tyre|wheel", re.I), "Wheels/Tires"),
    (re.compile(r"clutch|flywheel", re.I), "Clutch"),
    (re.compile(r"plug|coil|injector|hpfp|pump", re.I), "Engine"),
]

_TOTAL_RE = re.compile(r"(?:order\s+total|grand\s+total|total|amount\s+(?:paid|charged))\D{0,12}\$?\s*([0-9][0-9,]*\.\d{2})", re.I)
_ANY_MONEY_RE = re.compile(r"\$\s*([0-9][0-9,]*\.\d{2})")
_ORDER_RE = re.compile(r"order\s*(?:#|number|no\.?|id)?\s*[:#]?\s*([A-Z0-9][A-Z0-9\-]{4,})", re.I)
_DATE_PATTERNS = [
    re.compile(r"\b(\d{4}-\d{2}-\d{2})\b"),
    re.compile(r"\b(\d{1,2}/\d{1,2}/\d{2,4})\b"),
    re.compile(r"\b([A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4})\b"),
]


@dataclass
class Receipt:
    vendor: str
    date: dt.date | None = None
    total: float | None = None
    currency: str = "USD"
    items: list[str] = field(default_factory=list)
    order_id: str | None = None
    url: str | None = None
    source_email_id: str | None = None
    raw: str | None = None

    def as_dict(self) -> dict:
        return {"vendor": self.vendor,
                "date": self.date.isoformat() if self.date else None,
                "total": self.total, "currency": self.currency, "items": self.items,
                "order_id": self.order_id, "url": self.url,
                "source_email_id": self.source_email_id}


def _norm_vendor(v: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (v or "").lower())


def _parse_date(text: str) -> dt.date | None:
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        raw = m.group(1)
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%B %d %Y", "%b %d, %Y", "%b %d %Y"):
            try:
                return dt.datetime.strptime(raw, fmt).date()
            except ValueError:
                continue
    return None


def parse_receipt(payload: dict | str) -> Receipt:
    """Normalize a structured payload or raw email text into a Receipt."""
    if isinstance(payload, dict):
        d = payload
        date = None
        if d.get("date"):
            try:
                date = dt.date.fromisoformat(str(d["date"])[:10])
            except ValueError:
                date = _parse_date(str(d["date"]))
        total = d.get("total")
        try:
            total = float(total) if total is not None else None
        except (TypeError, ValueError):
            total = None
        items = d.get("items") or []
        if isinstance(items, str):
            items = [items]
        return Receipt(
            vendor=str(d.get("vendor") or d.get("from") or "unknown"),
            date=date, total=total, currency=str(d.get("currency") or "USD"),
            items=[str(i) for i in items], order_id=d.get("order_id") or d.get("order"),
            url=d.get("url"), source_email_id=d.get("email_id") or d.get("message_id"),
            raw=d.get("body"),
        )

    text = str(payload)
    # vendor: prefer a From: line domain, else first known brand mention.
    vendor = "unknown"
    mfrom = re.search(r"^from:.*?@([a-z0-9.-]+)", text, re.I | re.M)
    if mfrom:
        vendor = mfrom.group(1).split(".")[0]
    else:
        for known in _PARTS_VENDORS | _SERVICE_VENDORS:
            if known in _norm_vendor(text):
                vendor = known
                break
    mtot = _TOTAL_RE.search(text) or _ANY_MONEY_RE.search(text)
    total = float(mtot.group(1).replace(",", "")) if mtot else None
    morder = _ORDER_RE.search(text)
    murl = re.search(r"https?://\S+", text)
    # crude line-items: lines that carry a price
    items = []
    for line in text.splitlines():
        if _ANY_MONEY_RE.search(line) and not _TOTAL_RE.search(line):
            cleaned = _ANY_MONEY_RE.sub("", line).strip(" -\t·|")
            if 3 <= len(cleaned) <= 80:
                items.append(cleaned)
    return Receipt(vendor=vendor, date=_parse_date(text), total=total,
                   items=items[:12], order_id=morder.group(1) if morder else None,
                   url=murl.group(0) if murl else None, raw=text)


# --- classification --------------------------------------------------------
@dataclass
class Classification:
    entity: str          # 'service_event' | 'parts'
    patch: dict
    rationale: str


def classify(r: Receipt) -> Classification:
    """Decide whether a receipt is a service event or a parts purchase, and
    build the proposal patch. Conservative: unknown vendors default to parts."""
    vkey = _norm_vendor(r.vendor)
    blob = " ".join(r.items) + " " + (r.raw or "")

    is_service_vendor = any(v in vkey for v in _SERVICE_VENDORS)
    service_item = next((canon for pat, canon in _SERVICE_ITEM_MAP if pat.search(blob)), None)

    # Service if a known service vendor OR the items clearly name a service item.
    if is_service_vendor or (service_item and not any(v in vkey for v in _PARTS_VENDORS)):
        patch = {
            "item": service_item or "Service (uncategorized)",
            "performed_at": (r.date or dt.date.today()).isoformat(),
            "vendor": r.vendor,
            "cost": r.total,
            "note": f"Auto-classified from receipt{' ' + r.order_id if r.order_id else ''}. "
                    f"Items: {'; '.join(r.items) if r.items else '—'}",
        }
        why = (f"Receipt from {r.vendor} "
               f"{'(known service vendor)' if is_service_vendor else 'names a service item'}"
               f" → service_event '{patch['item']}'. Review before approving.")
        return Classification("service_event", patch, why)

    # Otherwise a parts purchase.
    category = next((cat for pat, cat in _PART_CATEGORY_MAP if pat.search(blob)), None)
    name = r.items[0] if r.items else f"Part from {r.vendor}"
    patch = {
        "name": name[:120],
        "category": category,
        "approx_price": r.total,
        "url": r.url,
        "oem": vkey in {"fordparts", "tasca", "levittownfordparts", "motorcraft"},
        "note": f"Auto-classified from receipt{' ' + r.order_id if r.order_id else ''}. "
                f"Vendor: {r.vendor}. Items: {'; '.join(r.items) if r.items else '—'}",
    }
    why = (f"Receipt from {r.vendor} → parts purchase"
           f"{f' (category {category})' if category else ''}. "
           f"Install it as a mod separately once fitted. Review before approving.")
    return Classification("parts", patch, why)
