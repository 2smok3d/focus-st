"""FEED — fleet garage.json + MODS.md from the digital twin.

Pure MODS renderer runs without a DB; a Postgres-or-skip test builds a real feed for a
commissioned fleet machine.
"""
from __future__ import annotations

import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import engine, session_scope
from app.fleetfeed import render_fleet_mods

DB = __import__("pathlib").Path(__file__).resolve().parent.parent / "db"


# ---- pure MODS renderer (no DB) -------------------------------------------
def test_render_mods_lists_deviations():
    md = render_fleet_mods({"name": "ZZR600"}, "zzr600",
                           [{"slug": "carburetors", "condition": "suspect",
                             "installed_part": None, "knowledge_state": "INFERRED"}])
    assert "# MODS — ZZR600" in md
    assert "carburetors" in md and "suspect" in md and "do not hand-edit" in md


def test_render_mods_empty_is_honest():
    md = render_fleet_mods({"name": "TZ250"}, "tz250", [])
    assert "No recorded deviations from stock" in md
    assert "|" not in md                       # no table when there's nothing to show


# ---- DB build (Postgres-or-skip) ------------------------------------------
def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        return True
    except OperationalError:
        return False


@pytest.mark.skipif(not _db_up(), reason="Postgres not reachable — skipping DB integration")
def test_build_and_write_fleet_feed(tmp_path, monkeypatch):
    with engine.begin() as conn:
        for f in sorted(DB.glob("schema*.sql"), key=lambda p: (len(p.stem), p.stem)):
            conn.execute(text(f.read_text()))
    from app import fleetfeed
    from app.commission import commission_machine
    from app.twin import seed_twin
    from app.seed import seed as seed_fn
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        commission_machine(s, "zzr600")
        seed_twin(s)
    with session_scope() as s:
        feed = fleetfeed.build_fleet_feed(s, "zzr600")
    assert feed["variant"] == "zzr600" and feed["reference"]
    assert "changes_from_stock" in feed and feed["full_intelligence"] == "intel.json"

    # write under a scratch tree so the test never clobbers the repo's published feeds
    monkeypatch.setattr(fleetfeed, "REPO", tmp_path)
    with session_scope() as s:
        res = fleetfeed.write_fleet_feed(s, "zzr600")
    mods = (tmp_path / "data" / "vehicles" / "zzr600" / "MODS.md").read_text()
    garage = json.loads((tmp_path / "web" / "vehicles" / "zzr600" / "garage.json").read_text())
    assert mods.startswith("# MODS — ") and garage["variant"] == "zzr600"
    assert res["changes"] == len(garage["changes_from_stock"])
