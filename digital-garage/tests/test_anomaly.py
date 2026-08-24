"""ANOM — robust anomaly detection over the observation history.

The pure `detect_anomalies` maths runs without a DB (always). A Postgres-or-skip
integration test records a clean series with one injected outlier and checks the service
flags exactly that point, with its baseline and score.
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.anomaly import detect_anomalies
from app.db import engine, session_scope

DB = __import__("pathlib").Path(__file__).resolve().parent.parent / "db"


# ---- pure engine (no DB) --------------------------------------------------
def test_flags_a_clear_outlier_with_its_baseline():
    pts = [(i, 100.0 + (i % 3)) for i in range(10)] + [(10, 180.0)]
    r = detect_anomalies(pts)
    d = r.as_dict()
    assert d["count"] == 1 and r.method == "mad"
    a = d["anomalies"][0]
    assert a["value"] == 180.0 and a["direction"] == "high" and abs(a["score"]) >= r.threshold
    # explainable by construction: the baseline it broke is reported
    assert r.baseline == pytest.approx(101.0, abs=1.0)


def test_clean_series_flags_nothing():
    r = detect_anomalies([(i, 100.0 + (i % 3)) for i in range(12)])
    assert r.as_dict()["count"] == 0


def test_constant_series_has_no_anomalies():
    r = detect_anomalies([(i, 50.0) for i in range(6)])
    assert r.method == "none" and r.as_dict()["count"] == 0


def test_needs_enough_points():
    r = detect_anomalies([(0, 1.0), (1, 2.0), (2, 100.0)])   # below MIN_POINTS
    assert r.method == "none" and r.as_dict()["count"] == 0


def test_is_pure_and_order_independent():
    base = [(i, 10.0) for i in range(8)]
    a = detect_anomalies(base + [(8, 99.0)])
    b = detect_anomalies([(8, 99.0)] + base)
    assert a.as_dict()["count"] == b.as_dict()["count"] == 1


def test_low_outlier_reported_as_low():
    pts = [(i, 200.0 + (i % 2)) for i in range(10)] + [(10, 20.0)]
    a = detect_anomalies(pts).as_dict()["anomalies"]
    assert a and a[0]["direction"] == "low" and a[0]["deviation"] < 0


# ---- service integration (Postgres-or-skip) -------------------------------
def _db_up() -> bool:
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        return True
    except OperationalError:
        return False


dbonly = pytest.mark.skipif(not _db_up(), reason="Postgres not reachable — skipping DB integration")


@dbonly
def test_component_anomalies_flags_a_recorded_spike():
    with engine.begin() as conn:
        for f in sorted(DB.glob("schema*.sql"), key=lambda p: (len(p.stem), p.stem)):
            conn.execute(text(f.read_text()))
    from app import anomaly, service
    from app.observations import record_observation
    from app.seed import seed as seed_fn
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        veh = service.get_vehicle(s)
        now = dt.datetime.now(dt.timezone.utc)
        # a steady boost series with one spike near the end
        vals = [18.0, 18.2, 17.9, 18.1, 18.0, 18.3, 27.5, 18.1]
        for i, psi in enumerate(vals):
            record_observation(s, veh, subject_slug="anom-turbo", method="boost",
                               value=psi, unit="psi", operating_condition="wot",
                               observed_at=now - dt.timedelta(days=len(vals) - i))
    try:
        with session_scope() as s:
            veh = service.get_vehicle(s)
            rows = anomaly.component_anomalies(s, veh.id)
        mine = [r for r in rows if r["subject"] == "anom-turbo"]
        assert mine, "the spike series should be flagged"
        r = mine[0]
        assert r["count"] == 1
        worst = r["anomalies"][0]
        assert worst["value"] == pytest.approx(27.5) and worst["direction"] == "high"
        assert r["baseline"] == pytest.approx(18.1, abs=0.5)   # robust to the spike
    finally:
        from sqlalchemy import delete

        from app.obsmodels import Observation
        with session_scope() as s:
            s.execute(delete(Observation).where(Observation.subject_slug == "anom-turbo"))
