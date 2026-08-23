"""Data intelligence — degradation-trend engine.

The pure `fit_trend` maths runs without a DB (always). A Postgres-or-skip integration test
records a real observation series and checks the service groups + fits it.
"""
from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import engine, session_scope
from app.trends import fit_trend

DB = __import__("pathlib").Path(__file__).resolve().parent.parent / "db"


# ---- pure engine (no DB) --------------------------------------------------
def test_fit_trend_detects_a_steady_decline():
    t = fit_trend([(0, 152), (30, 149), (60, 146), (90, 142)])
    assert t is not None
    assert t.direction == "falling" and t.drift is True
    assert t.r2 > 0.9 and t.pct_change < 0


def test_fit_trend_ignores_flat_noise():
    t = fit_trend([(0, 145), (10, 146), (20, 144), (30, 145)])
    assert t is not None
    assert t.drift is False                         # small % change, low R²


def test_fit_trend_needs_enough_points_and_time_spread():
    assert fit_trend([(0, 1), (1, 2)]) is None          # too few
    assert fit_trend([(5, 10), (5, 11), (5, 12)]) is None  # no time axis (all same x)


def test_fit_trend_is_pure_and_order_independent():
    a = fit_trend([(0, 100), (10, 110), (20, 120)])
    b = fit_trend([(20, 120), (0, 100), (10, 110)])
    assert a.slope_per_day == pytest.approx(b.slope_per_day)
    assert a.direction == "rising" and a.drift is True


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
def test_component_trends_fits_a_recorded_series():
    with engine.begin() as conn:
        for f in sorted(DB.glob("schema*.sql"), key=lambda p: (len(p.stem), p.stem)):
            conn.execute(text(f.read_text()))
    from app import service, trends
    from app.observations import record_observation
    from app.seed import seed as seed_fn
    with session_scope() as s:
        seed_fn(s, if_empty=True)
        veh = service.get_vehicle(s)
        now = dt.datetime.now(dt.timezone.utc)
        for days_ago, psi in [(90, 150), (60, 147), (30, 144), (0, 140)]:
            record_observation(s, veh, subject_slug="trend-cyl", method="compression",
                               value=psi, unit="psi", operating_condition="warm",
                               observed_at=now - dt.timedelta(days=days_ago))
    with session_scope() as s:
        veh = service.get_vehicle(s)
        rows = trends.component_trends(s, veh.id)
    mine = [r for r in rows if r["subject"] == "trend-cyl"]
    assert mine and mine[0]["direction"] == "falling" and mine[0]["drift"] is True
    # clean up the test series so it never leaks into a projection
    from sqlalchemy import delete
    from app.obsmodels import Observation
    with session_scope() as s:
        s.execute(delete(Observation).where(Observation.subject_slug == "trend-cyl"))
