"""Integration tests for baseline commissioning of the four other machines.

Postgres-or-skip. Verifies each machine becomes a real twin: reference variant +
systems/components, a linked vehicle, a capability profile, and honestly-graded
baseline states. Also checks idempotency and vehicle-agnosticism (the same core
handles a carbureted two-stroke and an EFI truck without special-casing).
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, select, text
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
        for f in ("schema.sql", "schema_v2.sql", "schema_v3.sql"):
            conn.execute(text((DB / f).read_text()))
    from app.seed import seed as seed_fn
    with session_scope() as s:
        seed_fn(s, if_empty=True)
    yield


def test_commission_all_creates_linked_twins():
    from app.commission import MACHINES, commission_all
    from app.models import Vehicle
    from app.refmodels import VehicleVariant
    with session_scope() as s:
        commission_all(s)
    with session_scope() as s:
        for slug, spec in MACHINES.items():
            variant = s.scalar(select(VehicleVariant).where(VehicleVariant.slug == slug))
            assert variant is not None, slug
            vin = spec["vehicle"]["vin"]
            veh = s.scalar(select(Vehicle).where(Vehicle.vin == vin))
            assert veh is not None and veh.variant_id == variant.id, slug


def test_reference_trees_built_per_machine():
    from app import refservice as rs
    from app.commission import commission_all
    with session_scope() as s:
        commission_all(s)
    with session_scope() as s:
        # ZZR600: carbureted inline-4 → has a fuel/carburetion system with carburetors
        zzr = rs.get_component(s, "zzr600", "carburetors")
        assert zzr is not None and "Keihin" in zzr["name"]
        # Toyota: EFI truck → EFI component exists, and an engine block
        efi = rs.get_component(s, "toyota-pickup", "efi")
        assert efi is not None


def test_baseline_states_graded_honestly():
    from app import twin
    from app.commission import commission_all
    with session_scope() as s:
        commission_all(s)
    with session_scope() as s:
        toyota = twin.reference_vs_actual(s, "toyota-pickup")
        devs = {d["slug"]: d for d in toyota["deviations"]}
        # Owner-stated facts → removed + DIRECTLY_OBSERVED
        assert devs["block"]["condition"] == "removed"
        assert devs["block"]["knowledge_state"] == "DIRECTLY_OBSERVED"
        assert devs["seats"]["condition"] == "removed"
        # TZ250 baseline is un-inspected → "unknown", NOT counted as a deviation
        tz = twin.reference_vs_actual(s, "tz250")
        assert tz["deviations"] == []


def test_capability_profiles_differ_by_machine():
    from app import service, twin
    from app.commission import commission_all
    from app.models import Vehicle
    with session_scope() as s:
        commission_all(s)
    with session_scope() as s:
        toyota = s.scalar(select(Vehicle).where(Vehicle.vin == "TOY-22RE-1986"))
        tz = s.scalar(select(Vehicle).where(Vehicle.vin == "YAM-TZ250-1986"))
        toy_caps = {c["capability"]: c["supported"] for c in twin.capabilities(s, toyota.id)}
        tz_caps = {c["capability"]: c["supported"] for c in twin.capabilities(s, tz.id)}
    # EFI truck supports OBD/DTC; the carbureted race two-stroke does not.
    assert toy_caps.get("obd") is True and toy_caps.get("dtc") is True
    assert tz_caps.get("obd") is False and tz_caps.get("premix") is True


def test_commission_is_idempotent():
    from app.commission import MACHINES, commission_all
    from app.models import Vehicle
    from app.refmodels import VehicleVariant

    def _counts(s):
        # count only the commissioned machines (robust to other seeds / bench vehicles)
        slugs = list(MACHINES)
        vins = [MACHINES[k]["vehicle"]["vin"] for k in slugs]
        variants = s.scalar(select(func.count()).select_from(VehicleVariant)
                            .where(VehicleVariant.slug.in_(slugs)))
        vehicles = s.scalar(select(func.count()).select_from(Vehicle)
                            .where(Vehicle.vin.in_(vins)))
        return variants, vehicles

    with session_scope() as s:
        commission_all(s)
    with session_scope() as s:
        before = _counts(s)
        commission_all(s)         # second run must not duplicate anything
    with session_scope() as s:
        after = _counts(s)
    assert before == after == (len(MACHINES), len(MACHINES))
