"""TEL — datalog → observation ingestion.

The pure peak extractor runs without a DB. A Postgres-or-skip test drives a real datalog
ingest and confirms it lays down durable observations that the trend engine can fit.
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import delete, select, text
from sqlalchemy.exc import OperationalError

from app.db import engine, session_scope

DB = __import__("pathlib").Path(__file__).resolve().parent.parent / "db"


# ---- pure peak extractor (no DB) ------------------------------------------
def test_peak_observations_extracts_recognized_channels():
    from app.analysis import peak_observations
    meas = [{"pid": "Boost (psi)", "value": 18.0, "unit": "psi"},
            {"pid": "Boost (psi)", "value": 21.4, "unit": "psi"},   # peak
            {"pid": "Coolant Temp (F)", "value": 205, "unit": "F"},
            {"pid": "RPM", "value": 6500, "unit": "rpm"}]
    out = {o["subject_slug"]: o for o in peak_observations(meas)}
    assert out["turbocharger"]["value"] == 21.4 and out["turbocharger"]["method"] == "peak boost"
    assert out["radiator"]["value"] == 205.0
    assert "rpm" not in out                      # rpm isn't a tracked degradation channel


# ---- ingest → observations → trend (Postgres-or-skip) ---------------------
def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        return True
    except OperationalError:
        return False


@pytest.mark.skipif(not _db_up(), reason="Postgres not reachable — skipping DB integration")
def test_datalog_ingest_records_observations_that_feed_trends():
    with engine.begin() as conn:
        for f in sorted(DB.glob("schema*.sql"), key=lambda p: (len(p.stem), p.stem)):
            conn.execute(text(f.read_text()))
    import uuid

    from app import service, trends
    from app.models import DiagnosticSession, Measurement
    from app.obsmodels import Observation
    from app.parsers import ingest
    from app.seed import seed as seed_fn
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        veh = service.get_vehicle(s)
        s.execute(delete(Observation).where(Observation.subject_slug == "turbocharger"))
    # three distinct logs with a declining peak boost. A per-run nonce keeps each log's
    # SHA unique so ingest never treats them as duplicates of a prior run's sessions.
    nonce = uuid.uuid4().hex  # trailing so it can't be mistaken for the CSV header
    logs = [f"Time (s),Boost (psi)\n0,18\n0.5,20.0\n# {nonce}\n",
            f"Time (s),Boost (psi)\n0,17\n0.5,18.5\n# {nonce}\n",
            f"Time (s),Boost (psi)\n0,16\n0.5,17.0\n# {nonce}\n"]
    session_ids = []
    with session_scope() as s:
        veh = service.get_vehicle(s)
        first = ingest(s, veh.id, "datalog", logs[0].encode())
        assert first["observations_recorded"] >= 1          # ingest laid down observations
        session_ids.append(first["session_id"])
        for lg in logs[1:]:
            session_ids.append(ingest(s, veh.id, "datalog", lg.encode())["session_id"])
    # the peak-boost observations exist on the turbocharger; simulate captures over time
    with session_scope() as s:
        veh = service.get_vehicle(s)
        rows = s.scalars(select(Observation).where(
            Observation.subject_slug == "turbocharger",
            Observation.method == "peak boost").order_by(Observation.id)).all()
        assert len(rows) >= 3
        now = dt.datetime.now(dt.timezone.utc)
        for row, days_ago in zip(rows, (60, 30, 0)):
            row.observed_at = now - dt.timedelta(days=days_ago)
    with session_scope() as s:
        veh = service.get_vehicle(s)
        tr = trends.component_trends(s, veh.id)
    turbo = [t for t in tr if t["subject"] == "turbocharger"]
    assert turbo and turbo[0]["direction"] == "falling" and turbo[0]["drift"] is True
    # clean up everything this test injected so nothing leaks into other tests / projections
    with session_scope() as s:
        s.execute(delete(Observation).where(Observation.subject_slug == "turbocharger"))
        s.execute(delete(Measurement).where(Measurement.session_id.in_(session_ids)))
        s.execute(delete(DiagnosticSession).where(DiagnosticSession.id.in_(session_ids)))
