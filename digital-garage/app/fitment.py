"""Parts intelligence + fitment.

Bridges the hand-authored `PARTS.md` catalog to the canonical reference component graph:
each catalog slot ("Air Filter", "Coil Packs", "Charge Pipes") is resolved to a reference
component ("air-filter", "coils", "charge-piping") by a transparent token match, and the
match answers *fitment* — a slot that resolves to a component in this machine's graph fits
the variant the reference model scopes (its years/market); a slot that resolves to nothing
is flagged to confirm, never silently assumed to fit.

The parser and matcher are pure (no DB); `catalog_fitment` is the service that reads a
variant's `PARTS.md`, resolves every slot, and reports coverage. Nothing here mutates
canon — it measures how well the catalog lines up with the reference model.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent

# Light synonym/stem map so catalog wording lines up with component slugs. Transparent on
# purpose — every mapping is inspectable, none inferred at runtime.
_SYNONYMS = {
    "pipes": "piping", "pipe": "piping", "packs": "coil", "pack": "coil",
    "plugs": "spark", "plug": "spark", "airbox": "air", "bov": "bypass",
    "recirculation": "bypass", "diverter": "bypass", "hpfp": "fuel", "pcv": "pcv",
    "downpipe": "exhaust", "catback": "exhaust", "cat": "exhaust",
}
# Generic words are dropped so a match rests on a *distinctive* token, not on sharing
# "valve" or "oil" with an unrelated component (which otherwise mismatched Oil Filter →
# oil-pump and PCV Valve → bypass-valve).
_STOP = {"the", "a", "an", "of", "and", "or", "with", "kit", "assembly", "oem", "set",
         "valve", "oil", "filter", "fluid", "engine", "front", "rear", "pressure",
         "high", "low", "hand", "system"}


def _tokens(text: str) -> set[str]:
    raw = re.split(r"[^a-z0-9]+", (text or "").lower())
    out: set[str] = set()
    for w in raw:
        if not w or w in _STOP:
            continue
        w = _SYNONYMS.get(w, w)
        if w.endswith("s") and len(w) > 3:      # cheap singularization
            w = w[:-1]
        out.add(w)
    return out


def match_component(query: str, components: list[dict]) -> tuple[dict | None, float]:
    """Best reference component for a catalog slot name. Returns (component, score) where
    score is token overlap in [0,1]; (None, 0.0) if nothing clears the bar. Pure."""
    q = _tokens(query)
    if not q:
        return None, 0.0
    best, best_score = None, 0.0
    for c in components:
        ct = _tokens(c.get("name", "")) | _tokens(c.get("slug", ""))
        if not ct:
            continue
        inter = len(q & ct)
        if not inter:
            continue
        score = inter / len(q | ct)             # Jaccard over the token sets
        if score > best_score:
            best, best_score = c, score
    # Require a real overlap: at least one shared token and a third of the union.
    return (best, round(best_score, 3)) if best_score >= 0.33 else (None, round(best_score, 3))


_SECTION = re.compile(r"<summary><b>(.+?)</b></summary>", re.I)
_SLOT = re.compile(r"^####\s+(.+?)\s*$")
_INSTALLED = re.compile(r"^\*\*Installed:\*\*\s*(.+?)\s*$")
_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")


def parse_catalog_slots(md: str) -> list[dict]:
    """Parse a PARTS.md catalog into slots: {section, slot, installed}. Pure. Follows the
    documented format — sections are `<summary><b>…</b>`, slots are `#### ` headings, and
    the `**Installed:**` line names the fitted part."""
    section = None
    slots: list[dict] = []
    lines = md.splitlines()
    for i, ln in enumerate(lines):
        m = _SECTION.search(ln)
        if m:
            section = m.group(1).strip()
            continue
        ms = _SLOT.match(ln)
        if ms:
            name = ms.group(1).split(" *(")[0].strip()      # drop the italic spec note
            installed = None
            for look in lines[i + 1:i + 6]:                 # installed line is right below
                mi = _INSTALLED.match(look.strip())
                if mi:
                    txt = mi.group(1)
                    lk = _LINK.search(txt)
                    installed = (lk.group(1) if lk else txt.split(" — ")[0]).strip()
                    break
            slots.append({"section": section, "slot": name, "installed": installed})
    return slots


def catalog_fitment(session, variant_slug: str = "focus-st") -> dict:
    """Resolve every catalog slot for a machine to a reference component and report
    fitment coverage. Read-only."""
    from . import refservice

    header = refservice.variant_header(session, variant_slug)
    parts_md = REPO / "data" / "vehicles" / variant_slug / "PARTS.md"
    if header is None or not parts_md.exists():
        return {"variant": variant_slug, "slots": 0, "matched": 0, "unmatched": 0,
                "coverage_pct": 0.0, "rows": [], "unmatched_slots": []}

    components = _flatten_components(refservice.system_tree(session, variant_slug))
    fits_note = _fits_note(header)
    rows, unmatched = [], []
    for s in parse_catalog_slots(parts_md.read_text()):
        comp, score = match_component(s["slot"], components)
        if comp is not None:
            # A strong token overlap asserts fitment; a weak one is a lead to confirm,
            # not a claim — the score is always shown so the confidence is legible.
            verdict = "fits" if score >= 0.5 else "likely"
            rows.append({"section": s["section"], "slot": s["slot"], "installed": s["installed"],
                         "component": comp["slug"], "component_name": comp["name"],
                         "score": score, "verdict": verdict, "applies_to": fits_note})
        else:
            unmatched.append(s["slot"])
            rows.append({"section": s["section"], "slot": s["slot"], "installed": s["installed"],
                         "component": None, "component_name": None, "score": score,
                         "verdict": "unmapped", "applies_to": None})
    matched = sum(1 for r in rows if r["component"])
    confident = sum(1 for r in rows if r["verdict"] == "fits")
    total = len(rows)
    return {"variant": variant_slug, "slots": total, "matched": matched,
            "confident": confident, "unmatched": total - matched,
            "coverage_pct": round(100 * matched / total, 1) if total else 0.0,
            "rows": rows, "unmatched_slots": unmatched}


def _flatten_components(tree: list[dict]) -> list[dict]:
    out: list[dict] = []

    def walk(n: dict):
        out.extend(n.get("components", []))
        for ch in n.get("children", []):
            walk(ch)

    for n in tree:
        walk(n)
    return out


def _fits_note(header: dict) -> str:
    bits = [header.get("name") or header.get("slug", "")]
    if header.get("years"):
        bits.append(str(header["years"]))
    if header.get("market"):
        bits.append(str(header["market"]))
    return " · ".join(b for b in bits if b)
