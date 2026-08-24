"""API2 — REST API V2 read endpoints (parity with the MCP read surface).

Postgres-or-skip. Drives the FastAPI app through a TestClient against seeded reference
data and checks each V2 endpoint returns the same shape the CLI/MCP do, and that the
surface stays read-only.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import engine, session_scope

DB = __import__("pathlib").Path(__file__).resolve().parent.parent / "db"


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        return True
    except OperationalError:
        return False


pytestmark = pytest.mark.skipif(not _db_up(), reason="Postgres not reachable — skipping DB integration")


@pytest.fixture(scope="module")
def client():
    with engine.begin() as conn:
        for f in sorted(DB.glob("schema*.sql"), key=lambda p: (len(p.stem), p.stem)):
            conn.execute(text(f.read_text()))
    from app.commission import commission_machine
    from app.seed import seed as seed_fn
    from app.seed_ref import seed_reference
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        seed_reference(s)
        commission_machine(s, "focus-st")
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_variant_and_systems(client):
    r = client.get("/v2/variant/focus-st")
    assert r.status_code == 200 and r.json()["manufacturer"] == "Ford"
    assert client.get("/v2/variant/nope").status_code == 404
    tree = client.get("/v2/systems/focus-st").json()
    assert tree and any(n.get("components") or n.get("children") for n in tree)


def test_component_and_claim(client):
    comp = client.get("/v2/component/focus-st/intercooler")
    assert comp.status_code == 200 and comp.json()["slug"] == "intercooler"
    assert client.get("/v2/component/focus-st/nope").status_code == 404
    # the seeded oil-capacity conflict is a resolvable claim with evidence + verdict
    conflicts = client.get("/v2/conflicts").json()
    assert conflicts
    c = conflicts[0]
    got = client.get("/v2/claim", params={"subject_key": c["subject_key"], "prop": c["property"]})
    assert got.status_code == 200
    assert got.json()["evidence"] and "resolved" in got.json()


def test_knowledge_intel_fitment(client):
    kq = client.get("/v2/knowledge/focus-st").json()
    assert kq["total"] > 0 and "by_verification" in kq
    intel = client.get("/v2/intel/focus-st").json()
    assert intel["variant"] == "focus-st" and "search_index" in intel
    fit = client.get("/v2/fitment/focus-st").json()
    assert fit["slots"] >= 1 and "coverage_pct" in fit


def test_v2_surface_is_read_only(client):
    # none of the V2 routes accept a write verb
    for path in ("/v2/variant/focus-st", "/v2/systems/focus-st", "/v2/conflicts"):
        assert client.post(path).status_code in (404, 405)
