"""Unit tests for the quantity/units subsystem (pure, no DB)."""
import pytest

from app import quantities as q
from app.quantities import IncompatibleUnits, Quantity


def test_torque_conversion_lbft_to_nm():
    assert q.convert(100, "lb-ft", "N·m") == pytest.approx(135.58, abs=0.01)
    assert q.convert(135.58, "N·m", "lb-ft") == pytest.approx(100, abs=0.01)


def test_temperature_affine_conversion():
    assert q.convert(212, "°F", "°C") == pytest.approx(100.0, abs=1e-6)
    assert q.convert(0, "°C", "°F") == pytest.approx(32.0, abs=1e-6)
    assert q.convert(0, "K", "°C") == pytest.approx(-273.15, abs=1e-6)


def test_achievement_test_lbft_and_nm_do_not_conflict():
    # The roadmap's stated achievement test.
    assert q.conflict(100, "lb-ft", 135.6, "N·m") is False
    assert q.agree(100, "lb-ft", 135.6, "N·m") is True


def test_real_disagreement_is_a_conflict():
    assert q.conflict(100, "lb-ft", 90, "lb-ft") is True
    # the documented Focus oil-capacity discrepancy, in mixed units, still conflicts
    assert q.conflict(4.3, "qt", 5.7, "qt") is True


def test_cross_type_comparison_raises():
    with pytest.raises(IncompatibleUnits):
        q.agree(100, "lb-ft", 100, "psi")   # torque vs pressure is a category error


def test_quantity_dataclass_canonical_and_to():
    boost = Quantity(20, "psi")
    assert boost.quantity_type == "pressure"
    assert boost.canonical == pytest.approx(137.9, abs=0.1)  # kPa
    assert boost.to("bar").value == pytest.approx(1.379, abs=0.01)


def test_rpm_is_frequency():
    assert q.quantity_type("rpm") == "frequency"
    assert q.convert(3600, "rpm", "Hz") == pytest.approx(60.0, abs=1e-6)


def test_unknown_unit_raises():
    with pytest.raises(IncompatibleUnits):
        q.to_canonical(1, "smoots")
