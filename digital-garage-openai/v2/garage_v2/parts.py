from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote_plus

BASE = Path(__file__).resolve().parents[1]
PARTS_FILE = BASE / "data" / "focus_st_2017_parts_seed.json"


def load_parts() -> dict:
    return json.loads(PARTS_FILE.read_text(encoding="utf-8"))


def shopping_links(query: str) -> dict[str, str]:
    """Discovery links only. Search results are not fitment verification."""
    q = quote_plus(query.strip())
    return {
        "amazon": f"https://www.amazon.com/s?k={q}",
        "ebay": f"https://www.ebay.com/sch/i.html?_nkw={q}",
        "google": f"https://www.google.com/search?q={q}",
    }


def slot_by_id(slot: str) -> dict | None:
    for item in load_parts().get("slots", []):
        if item.get("slot") == slot:
            result = dict(item)
            search = result.get("search", {})
            result["generated_links"] = {
                key: shopping_links(query) for key, query in search.items() if query
            }
            return result
    return None


def search_catalog(text: str) -> list[dict]:
    needle = text.strip().lower()
    if not needle:
        return []
    out: list[dict] = []
    for item in load_parts().get("slots", []):
        haystack = json.dumps(item, ensure_ascii=False).lower()
        if needle in haystack:
            out.append(item)
    return out
