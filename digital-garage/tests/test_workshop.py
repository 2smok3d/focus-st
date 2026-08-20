"""Integration tests for the Workshop Engine (Milestone C). Postgres-or-skip.

Covers job-readiness computation, the status lifecycle, mandatory post-repair
verification (part replaced ≠ problem fixed), and the automatic service record on close.
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
        for f in ("schema.sql", "schema_v2.sql", "schema_v3.sql", "schema_v4.sql", "schema_v5.sql",
                  "schema_v6.sql", "schema_v7.sql", "schema_v8.sql", "schema_v9.sql"):
            conn.execute(text((DB / f).read_text()))
    from app.seed import seed as seed_fn
    with session_scope() as s:
        seed_fn(s, if_empty=True)
    yield


@pytest.fixture(autouse=True)
def _clean():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE work_orders, service_events RESTART IDENTITY CASCADE"))
    yield


def _job(s):
    from app import service, workshop
    v = service.get_vehicle(s)
    wo = workshop.open_work_order(s, v, "Water pump replacement", code="WO-T", component_slug="water-pump")
    workshop.add_task(s, wo, "Remove old pump")
    workshop.add_task(s, wo, "Install new pump")
    workshop.add_part(s, wo, "Water pump", available=True)
    workshop.add_part(s, wo, "Gasket", available=True)
    workshop.add_part(s, wo, "Crush washer", available=False)   # 1 of 3 parts missing
    workshop.add_tool(s, wo, "Sockets", available=True)
    return v, wo


def test_job_readiness_and_blockers():
    from app import workshop
    with session_scope() as s:
        _v, wo = _job(s)
        r = workshop.job_readiness(s, wo.id)
    # items = 3 parts + 1 tool + 1 procedure = 5; satisfied = 2 parts + 1 tool + procedure = 4
    assert r["ready_pct"] == 80
    assert r["ready"] is False
    assert any("Crush washer" in b for b in r["blockers"])


def test_mark_ready_transitions_on_completeness():
    from app import workshop
    from app.womodels import WorkOrderPart
    with session_scope() as s:
        _v, wo = _job(s)
        workshop.mark_ready(s, wo)
        assert wo.status == "blocked"                       # missing part
        # supply the missing part → now fully ready
        for p in s.scalars(select(WorkOrderPart).where(WorkOrderPart.work_order_id == wo.id)):
            p.available = True
        s.flush()
        workshop.mark_ready(s, wo)
        assert wo.status == "ready"


def test_completion_requires_verification_not_auto_fixed():
    from app import workshop
    with session_scope() as s:
        _v, wo = _job(s)
        workshop.start(s, wo)
        workshop.complete_work(s, wo)
    assert wo.status == "verification_required"
    assert wo.repair_state == "repair_performed"           # performed, NOT verified


def test_failed_verification_does_not_verify_passing_one_does():
    from app import workshop
    with session_scope() as s:
        _v, wo = _job(s)
        workshop.start(s, wo)
        workshop.complete_work(s, wo)
        workshop.verify(s, wo, "leak-down + temp", "fail")
        assert wo.status == "verification_required" and wo.repair_state == "repair_performed"
        workshop.verify(s, wo, "leak-down + temp", "pass")
        assert wo.status == "verified" and wo.repair_state == "repair_verified"


def test_close_requires_verified_and_writes_service_event():
    from app import workshop
    from app.models import ServiceEvent
    with session_scope() as s:
        _v, wo = _job(s)
        workshop.start(s, wo)
        workshop.complete_work(s, wo)
        with pytest.raises(ValueError):
            workshop.close(s, wo)                            # not verified yet
        workshop.verify(s, wo, "leak-down + temp", "pass")
        ev = workshop.close(s, wo, miles=86900)
        assert wo.status == "closed"
        assert ev.item == "Water pump replacement" and ev.miles == 86900
        # the service ledger now carries the record
        found = s.scalar(select(ServiceEvent).where(ServiceEvent.id == ev.id))
    assert found is not None


def test_invalid_transitions_rejected():
    from app import workshop
    with session_scope() as s:
        _v, wo = _job(s)
        # cannot complete work before starting
        with pytest.raises(ValueError):
            workshop.complete_work(s, wo)
        # cannot verify before work is complete
        with pytest.raises(ValueError):
            workshop.verify(s, wo, "x", "pass")
