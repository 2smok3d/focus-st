"""Unit tests for the pure domain logic — no database required."""
import datetime as dt

import pytest

from app import domain
from app.domain import Verification


# --- verification ordering -------------------------------------------------
def test_verification_ordering():
    assert Verification.UNVERIFIED < Verification.CORROBORATED
    assert Verification.OEM_VERIFIED < Verification.VEHICLE_VERIFIED


def test_can_override_equal_or_stronger():
    assert domain.can_override("OEM_VERIFIED", "CORROBORATED")
    assert domain.can_override("VEHICLE_VERIFIED", "VEHICLE_VERIFIED")


def test_can_override_refuses_weaker():
    # A forum-grade CORROBORATED claim may not overwrite an OEM_VERIFIED one.
    assert not domain.can_override("CORROBORATED", "OEM_VERIFIED")
    assert not domain.can_override("UNVERIFIED", "CORROBORATED")


def test_verification_parse_hyphen():
    assert Verification.parse("oem-verified") is Verification.OEM_VERIFIED


# --- maintenance-due -------------------------------------------------------
def test_due_overdue_by_miles():
    st = domain.maintenance_due(
        "Oil", interval_miles=5000, interval_months=6,
        last_miles=50000, last_date=dt.date(2025, 1, 1),
        current_miles=56000, today=dt.date(2025, 3, 1))
    assert st.status == "overdue"
    assert st.miles_remaining == -1000


def test_due_soon_by_miles():
    st = domain.maintenance_due(
        "Oil", interval_miles=5000, interval_months=None,
        last_miles=50000, last_date=None,
        current_miles=54800, today=dt.date(2025, 3, 1))
    assert st.status == "due-soon"  # 200 mi left, floor is 500


def test_due_ok():
    st = domain.maintenance_due(
        "Oil", interval_miles=5000, interval_months=6,
        last_miles=50000, last_date=dt.date(2025, 1, 1),
        current_miles=51000, today=dt.date(2025, 2, 1))
    assert st.status == "ok"


def test_due_worse_dimension_wins():
    # Fine on miles, but 8 months since a 6-month item → overdue.
    st = domain.maintenance_due(
        "Brake fluid", interval_miles=None, interval_months=6,
        last_miles=50000, last_date=dt.date(2024, 1, 1),
        current_miles=50100, today=dt.date(2024, 9, 1))
    assert st.status == "overdue"


def test_due_never_serviced_with_interval_is_overdue():
    st = domain.maintenance_due(
        "Coolant", interval_miles=100000, interval_months=60,
        last_miles=None, last_date=None,
        current_miles=40000, today=dt.date(2025, 1, 1))
    assert st.status == "overdue"


# --- parts links -----------------------------------------------------------
def test_parts_links_include_vehicle_when_no_part_number():
    links = domain.parts_search_links("intercooler")
    assert "amazon" in links and "ebay" in links
    assert "Focus" in links["amazon"]  # vehicle tag encoded in the query


def test_parts_links_prefer_part_number():
    links = domain.parts_search_links("intercooler", part_number="MMINT-MK3")
    assert "MMINT-MK3" in links["amazon"]
    assert "Focus" not in links["amazon"]  # part number replaces the vehicle tag


def test_parts_links_retailer_subset():
    links = domain.parts_search_links("plugs", retailers=["rockauto"])
    assert set(links) == {"rockauto"}


# --- patch validation ------------------------------------------------------
def test_validate_patch_rejects_unknown_entity():
    ok, _ = domain.validate_patch("engine_swap", {"x": 1})
    assert not ok


def test_validate_patch_rejects_stray_field():
    ok, msg = domain.validate_patch("mod", {"slot": "IC", "hacker": True})
    assert not ok and "hacker" in msg


def test_validate_patch_accepts_good_mod():
    ok, _ = domain.validate_patch("mod", {"slot": "Intercooler", "part_name": "Mishimoto"})
    assert ok


def test_authority_label():
    assert "OEM" in domain.authority_label(1)
    assert domain.authority_label(99) == "Unknown"
