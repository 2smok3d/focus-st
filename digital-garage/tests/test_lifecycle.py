"""Integration tests for physical-component lifecycle tracking (V7). Postgres-or-skip.

The core roadmap property: a physical component persists through removal and can move
between machines, keeping its whole history and usage accumulators.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from app.db import engine, session_scope

DB = Path(__file__).resolve().parent.parent / "db"


def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        return True
    except OperationalError:
        return False


pytestmark = pytest.mark.skipif(not _db_up(), reason="Postgres not reachable — skipping DB integration")


@pytest.fixture(scope="module", autouse=True)
def _schema():
    with engine.begin() as conn:
        for f in ("schema.sql", "schema_v2.sql", "schema_v3.sql", "schema_v4.sql",
                  "schema_v5.sql", "schema_v6.sql", "schema_v7.sql"):
            conn.execute(text((DB / f).read_text()))
    from app.seed import seed as seed_fn
    with session_scope() as s:
        seed_fn(s, if_empty=True)
    yield


@pytest.fixture(autouse=True)
def _clean():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE physical_components RESTART IDENTITY CASCADE"))
    yield


def test_usage_accumulates_and_inspection_sets_condition():
    from app import lifecycle as lc, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        pc = lc.register(s, "P-0042", "TZ250 right piston", component_slug="pistons")
        lc.install(s, pc, v, "pistons")
        lc.add_usage(s, pc, hours=2.5, sessions=2)
        lc.add_usage(s, pc, hours=2.2, sessions=1)
        lc.inspect(s, pc, "healthy", value=0.05, unit="mm", method="ring end-gap")
        d = lc.lifecycle(s, "P-0042")
    assert d["usage"]["hours"] == pytest.approx(4.7)
    assert d["usage"]["sessions"] == 3
    assert d["condition"] == "healthy"
    assert d["status"] == "in_service"


def _bench(s, vin):
    """Get-or-create a throwaway machine (the DB persists across runs)."""
    from app.models import Vehicle
    v = s.scalar(select(Vehicle).where(Vehicle.vin == vin))
    if v is None:
        v = Vehicle(vin=vin, make="Test", model="Bench")
        s.add(v)
        s.flush()
    return v


def test_component_survives_removal_and_moves_between_machines():
    from app import lifecycle as lc, service
    with session_scope() as s:
        v1 = service.get_vehicle(s)
        v2 = _bench(s, "TEST-BENCH-1")   # a second machine to move the part to
        pc = lc.register(s, "P-0042", "piston", component_slug="pistons")
        lc.install(s, pc, v1, "pistons")
        lc.remove(s, pc)                       # off the machine → still exists
        d_removed = lc.lifecycle(s, "P-0042")
        lc.install(s, pc, v2, "pistons")       # installed on a different machine
        d_moved = lc.lifecycle(s, "P-0042")
    assert d_removed is not None and d_removed["status"] == "in_inventory"
    # history preserved: two installations, the second current
    assert len(d_moved["installations"]) == 2
    assert d_moved["installations"][0]["current"] is False
    assert d_moved["installations"][1]["current"] is True
    assert d_moved["status"] == "in_service"


def test_only_one_open_installation_at_a_time():
    from app import lifecycle as lc, service
    with session_scope() as s:
        v1 = service.get_vehicle(s)
        v2 = _bench(s, "TEST-BENCH-2")
        pc = lc.register(s, "P-0099", "coil")
        lc.install(s, pc, v1, "coils")
        lc.install(s, pc, v2, "coils")   # installing elsewhere auto-closes the prior
        from app.lcmodels import ComponentInstallation
        open_installs = s.scalars(select(ComponentInstallation).where(
            ComponentInstallation.physical_component_id == pc.id,
            ComponentInstallation.removed_at.is_(None))).all()
    assert len(open_installs) == 1
    assert open_installs[0].vehicle_id == v2.id


def test_invalid_inspection_result_rejected():
    from app import lifecycle as lc
    with session_scope() as s:
        pc = lc.register(s, "P-0001", "thing")
        with pytest.raises(ValueError):
            lc.inspect(s, pc, "vaporized")
