"""Parts intelligence + fitment.

Pure parser + matcher run without a DB; a Postgres-or-skip test resolves the real
focus-st catalog against the seeded reference components.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import engine, session_scope
from app.fitment import match_component, parse_catalog_slots

DB = __import__("pathlib").Path(__file__).resolve().parent.parent / "db"

_COMPONENTS = [
    {"slug": "air-filter", "name": "Air Filter / Intake"},
    {"slug": "spark-plugs", "name": "Spark Plugs"},
    {"slug": "coils", "name": "Ignition Coils"},
    {"slug": "intercooler", "name": "Intercooler"},
    {"slug": "charge-piping", "name": "Charge Piping"},
    {"slug": "pcv", "name": "PCV / Crankcase Vent"},
    {"slug": "oil-pump", "name": "Oil Pump"},
    {"slug": "block", "name": "Engine Block"},
]


# ---- pure matcher ----------------------------------------------------------
def test_matcher_hits_distinctive_slots():
    for slot, want in [("Spark Plugs", "spark-plugs"), ("Intercooler", "intercooler"),
                       ("Charge Pipes", "charge-piping"), ("Coil Packs", "coils"),
                       ("PCV Valve", "pcv")]:
        comp, score = match_component(slot, _COMPONENTS)
        assert comp is not None and comp["slug"] == want, f"{slot} → {comp}"
        assert score >= 0.33


def test_matcher_rejects_generic_false_positives():
    # "Oil Filter" must NOT map to oil-pump, "Engine Oil" must NOT map to block —
    # generic tokens are demoted so only distinctive overlap counts.
    assert match_component("Oil Filter", _COMPONENTS)[0] is None
    assert match_component("Engine Oil", _COMPONENTS)[0] is None
    assert match_component("Cruise Control", _COMPONENTS)[0] is None


# ---- pure parser -----------------------------------------------------------
def test_parse_catalog_slots():
    md = (
        "<details>\n<summary><b>ENGINE</b></summary>\n\n"
        "#### Air Filter\n"
        "**Installed:** [Motorcraft FA-1802](https://x) — OEM · BM5Z · ⚠️ unknown\n\n"
        "#### Spark Plugs *(4 required — gap 0.028\")*\n"
        "**Installed:** OEM SP-537 — OEM\n"
    )
    slots = parse_catalog_slots(md)
    assert {"section": "ENGINE", "slot": "Air Filter", "installed": "Motorcraft FA-1802"} in slots
    spark = [s for s in slots if s["slot"] == "Spark Plugs"][0]
    assert spark["slot"] == "Spark Plugs"                    # italic spec note stripped
    assert spark["installed"].startswith("OEM SP-537")


# ---- service integration (Postgres-or-skip) --------------------------------
def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        return True
    except OperationalError:
        return False


@pytest.mark.skipif(not _db_up(), reason="Postgres not reachable — skipping DB integration")
def test_catalog_fitment_resolves_focus_st():
    with engine.begin() as conn:
        for f in sorted(DB.glob("schema*.sql"), key=lambda p: (len(p.stem), p.stem)):
            conn.execute(text(f.read_text()))
    from app.commission import commission_machine
    from app.fitment import catalog_fitment
    from app.seed import seed as seed_fn
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        commission_machine(s, "focus-st")
    with session_scope() as s:
        r = catalog_fitment(s, "focus-st")
    assert r["slots"] > 0 and r["matched"] >= 1
    got = {row["slot"]: row["component"] for row in r["rows"] if row["component"]}
    assert got.get("Spark Plugs") == "spark-plugs"
    assert got.get("Intercooler") == "intercooler"
    # every mapped row carries a fitment note scoped to the variant
    for row in r["rows"]:
        if row["component"]:
            assert row["applies_to"] and row["verdict"] in ("fits", "likely")
