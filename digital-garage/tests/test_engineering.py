"""Integration tests for Milestone D — constraint solver + experiment engine.

Postgres-or-skip. Covers: builds computed from constraint rules (unmet requires,
recommends, conflicts), and controlled vs confounded experiment comparisons.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
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
        for f in ("schema.sql", "schema_v2.sql", "schema_v3.sql", "schema_v4.sql", "schema_v5.sql",
                  "schema_v6.sql", "schema_v7.sql", "schema_v8.sql", "schema_v9.sql", "schema_v10.sql",
                  "schema_v11.sql"):
            conn.execute(text((DB / f).read_text()))
    from app.seed import seed as seed_fn
    from app.builds import seed_constraints
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        seed_constraints(s)
    yield


@pytest.fixture(autouse=True)
def _clean():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE build_scenarios, experiments, environment_snapshots "
                          "RESTART IDENTITY CASCADE"))
    yield


def test_build_is_computed_unmet_requires_and_recommends():
    from app import builds, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        sc = builds.new_scenario(s, v, "Big turbo", goal="350 whp")
        builds.add_item(s, sc, "big-turbo", "Larger turbo", est_cost=1800)
        builds.add_item(s, sc, "intercooler", "FMIC", est_cost=450)
        builds.add_item(s, sc, "tune", "Custom tune", est_cost=600)
        r = builds.solve(s, sc.id)
    assert r["valid"] is False                                   # a REQUIRE is unmet
    unmet = {u["object"] for u in r["requires_unmet"]}
    assert "fueling" in unmet                                    # big-turbo requires fueling
    met = {m["object"] for m in r["requires_met"]}
    assert {"intercooler", "tune"} <= met                        # these are present
    rec = {x["object"] for x in r["recommends"]}
    assert "oil-cooler" in rec and "colder-plugs" in rec
    assert r["est_cost"] == 2850.0


def test_build_becomes_valid_when_requires_satisfied():
    from app import builds, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        sc = builds.new_scenario(s, v, "Stage 2", goal="reliable")
        builds.add_item(s, sc, "stage-2", "Stage-2 kit")
        builds.add_item(s, sc, "tune", "Tune")            # stage-2 requires tune
        r = builds.solve(s, sc.id)
    assert r["valid"] is True and not r["requires_unmet"]


def test_build_detects_conflict():
    from app import builds, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        sc = builds.new_scenario(s, v, "Turbo w/ stock pipe")
        builds.add_item(s, sc, "big-turbo", "Turbo")
        builds.add_item(s, sc, "tune", "Tune")
        builds.add_item(s, sc, "fueling", "Injectors")
        builds.add_item(s, sc, "intercooler", "FMIC")
        builds.add_item(s, sc, "stock-charge-pipe", "Stock charge pipe")   # conflicts
        r = builds.solve(s, sc.id)
    assert any(c["object"] == "stock-charge-pipe" for c in r["conflicts"])
    assert r["valid"] is False                                   # a conflict invalidates it


def test_experiment_controlled_comparison():
    from app import experiments as ex, observations as ob, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        e = ex.open_experiment(s, v, "FMIC vs OEM charge temps", metric="peak_iat", unit="°C")
        a = ob.record_environment(s, v, ambient=90, ambient_unit="°F")
        b = ob.record_environment(s, v, ambient=92, ambient_unit="°F")   # ~1°C apart
        ex.add_run(s, e, "baseline", 61, unit="°C", environment_id=a.id)
        ex.add_run(s, e, "changed", 52, unit="°C", environment_id=b.id)
        r = ex.compare(s, e.id)
    assert r["delta"] == -9.0
    assert r["controlled"] is True and r["warnings"] == []


def test_experiment_flags_confounded_comparison():
    from app import experiments as ex, observations as ob, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        e = ex.open_experiment(s, v, "same test, hotter day", metric="peak_iat", unit="°C")
        a = ob.record_environment(s, v, ambient=90, ambient_unit="°F")
        hot = ob.record_environment(s, v, ambient=115, ambient_unit="°F")   # ~14°C apart
        ex.add_run(s, e, "baseline", 61, unit="°C", environment_id=a.id)
        ex.add_run(s, e, "changed", 58, unit="°C", environment_id=hot.id)
        r = ex.compare(s, e.id)
    assert r["controlled"] is False
    assert any("Poorly controlled" in w for w in r["warnings"])


def test_experiment_invalid_arm_rejected():
    from app import experiments as ex, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        e = ex.open_experiment(s, v, "q")
        with pytest.raises(ValueError):
            ex.add_run(s, e, "sideways", 1.0)
