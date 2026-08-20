"""Integration tests for typed graph overlays (Milestone A ontology). Postgres-or-skip."""
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
        for f in ("schema.sql", "schema_v2.sql", "schema_v3.sql", "schema_v4.sql",
                  "schema_v5.sql", "schema_v6.sql"):
            conn.execute(text((DB / f).read_text()))
    from app.seed import seed as seed_fn
    from app.seed_graph import seed_graph
    from app.seed_ref import seed_reference
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        seed_reference(s)
        seed_graph(s)
    yield


def test_overlays_are_distinct_graphs_over_shared_components():
    from app import graphs
    with session_scope() as s:
        present = graphs.domains(s, "focus-st")
        airflow = {(e["from"], e["to"]) for e in graphs.overlay_edges(s, "focus-st", "airflow")}
        coolant = {(e["from"], e["to"]) for e in graphs.overlay_edges(s, "focus-st", "coolant")}
    assert {"airflow", "coolant", "lubrication"} <= set(present)
    # the cylinder head participates in BOTH airflow and coolant overlays
    assert ("intake-manifold", "head") in airflow
    assert ("head", "thermostat") in coolant
    # but the overlays are different edge sets
    assert airflow != coolant


def test_airflow_trace_follows_the_charge_path():
    from app import graphs
    with session_scope() as s:
        path = graphs.trace(s, "focus-st", "airflow", "air-filter")
    assert path == ["air-filter", "turbocharger", "intercooler", "charge-piping",
                    "throttle-body", "intake-manifold", "head"]


def test_coolant_loop_is_cycle_safe():
    from app import graphs
    with session_scope() as s:
        path = graphs.trace(s, "focus-st", "coolant", "water-pump")
    # radiator → water-pump closes the loop; traversal must terminate, no dup pump
    assert path[:5] == ["water-pump", "block", "head", "thermostat", "radiator"]
    assert path.count("water-pump") == 1


def test_edges_carry_medium_and_direction():
    from app import graphs
    with session_scope() as s:
        coolant = graphs.overlay_edges(s, "focus-st", "coolant")
    assert all(e["medium"] == "coolant" for e in coolant)
    assert any(e["direction"] == "bidirectional" for e in coolant)  # turbo cooled_by coolant


def test_assembly_groups_components():
    from sqlalchemy import select
    from app.refmodels import Assembly, Component, System, VehicleVariant
    with session_scope() as s:
        variant = s.scalar(select(VehicleVariant).where(VehicleVariant.slug == "focus-st"))
        asm = s.scalar(select(Assembly).join(System).where(
            System.variant_id == variant.id, Assembly.slug == "charge-air-path"))
        assert asm is not None
        members = s.scalars(select(Component.slug).where(Component.assembly_id == asm.id)).all()
    assert set(members) == {"intercooler", "charge-piping", "throttle-body"}
