"""Quantity & units subsystem (Milestone A) — normalize engineering values so
comparisons and contradiction checks are unit-aware.

Pure module (no DB). Every value carries a quantity_type and a unit; internally we
normalize to a canonical unit (affine: canonical = value*factor + offset) while
preserving the original for display. The consequence that matters (the achievement
test from the roadmap):

    100 lb·ft  and  135.6 N·m  do NOT conflict — same torque, different units.

Comparing across incompatible quantity types (torque vs pressure) is a category error
and raises, rather than silently coercing.
"""
from __future__ import annotations

from dataclasses import dataclass

QUANTITY_TYPES = {
    "torque", "temperature", "pressure", "length", "distance", "volume", "mass",
    "speed", "power", "energy", "time", "angle", "ratio", "frequency", "voltage",
    "current", "resistance", "flow",
}


class IncompatibleUnits(ValueError):
    """Raised when values of different quantity types are compared."""


# unit -> (quantity_type, factor, offset): canonical = value*factor + offset
# Canonical units: torque N·m, temperature °C, pressure kPa, length mm, distance km,
# volume L, mass kg, speed km/h, power kW, energy kJ, time s, angle deg, frequency Hz,
# voltage V, current A, resistance ohm, flow L/min.
_UNITS: dict[str, tuple[str, float, float]] = {
    # torque
    "n·m": ("torque", 1.0, 0.0), "nm": ("torque", 1.0, 0.0), "n-m": ("torque", 1.0, 0.0),
    "lb-ft": ("torque", 1.3558179, 0.0), "lbft": ("torque", 1.3558179, 0.0),
    "ft-lb": ("torque", 1.3558179, 0.0), "ft·lb": ("torque", 1.3558179, 0.0),
    "lb-in": ("torque", 0.11298482, 0.0), "in-lb": ("torque", 0.11298482, 0.0),
    # temperature (affine)
    "°c": ("temperature", 1.0, 0.0), "c": ("temperature", 1.0, 0.0), "degc": ("temperature", 1.0, 0.0),
    "°f": ("temperature", 5.0 / 9.0, -160.0 / 9.0), "f": ("temperature", 5.0 / 9.0, -160.0 / 9.0),
    "k": ("temperature", 1.0, -273.15),
    # pressure
    "kpa": ("pressure", 1.0, 0.0), "psi": ("pressure", 6.8947573, 0.0),
    "bar": ("pressure", 100.0, 0.0), "mbar": ("pressure", 0.1, 0.0),
    "inhg": ("pressure", 3.3863886, 0.0), "atm": ("pressure", 101.325, 0.0),
    # length
    "mm": ("length", 1.0, 0.0), "cm": ("length", 10.0, 0.0), "m": ("length", 1000.0, 0.0),
    "in": ("length", 25.4, 0.0), '"': ("length", 25.4, 0.0), "thou": ("length", 0.0254, 0.0),
    # distance
    "km": ("distance", 1.0, 0.0), "mi": ("distance", 1.6093440, 0.0), "mile": ("distance", 1.6093440, 0.0),
    # volume
    "l": ("volume", 1.0, 0.0), "ml": ("volume", 0.001, 0.0),
    "qt": ("volume", 0.94635295, 0.0), "gal": ("volume", 3.7854118, 0.0),
    # mass
    "kg": ("mass", 1.0, 0.0), "g": ("mass", 0.001, 0.0), "lb": ("mass", 0.45359237, 0.0),
    # speed
    "km/h": ("speed", 1.0, 0.0), "kph": ("speed", 1.0, 0.0), "mph": ("speed", 1.6093440, 0.0),
    # power
    "kw": ("power", 1.0, 0.0), "hp": ("power", 0.74569987, 0.0), "ps": ("power", 0.73549875, 0.0),
    # frequency
    "hz": ("frequency", 1.0, 0.0), "rpm": ("frequency", 1.0 / 60.0, 0.0),
    # electrical
    "v": ("voltage", 1.0, 0.0), "mv": ("voltage", 0.001, 0.0),
    "a": ("current", 1.0, 0.0), "ma": ("current", 0.001, 0.0),
    "ohm": ("resistance", 1.0, 0.0), "ω": ("resistance", 1.0, 0.0),
    # angle / ratio / time
    "deg": ("angle", 1.0, 0.0), "°": ("angle", 1.0, 0.0),
    "s": ("time", 1.0, 0.0), "ms": ("time", 0.001, 0.0), "min": ("time", 60.0, 0.0),
}


def _norm(unit: str) -> str:
    return unit.strip().lower().replace("·", "·")


def unit_info(unit: str) -> tuple[str, float, float]:
    key = _norm(unit)
    if key not in _UNITS:
        raise IncompatibleUnits(f"unknown unit {unit!r}")
    return _UNITS[key]


def quantity_type(unit: str) -> str:
    return unit_info(unit)[0]


def to_canonical(value: float, unit: str) -> tuple[float, str]:
    """Return (canonical_value, quantity_type)."""
    qtype, factor, offset = unit_info(unit)
    return value * factor + offset, qtype


def convert(value: float, from_unit: str, to_unit: str) -> float:
    q_from = quantity_type(from_unit)
    q_to = quantity_type(to_unit)
    if q_from != q_to:
        raise IncompatibleUnits(f"cannot convert {q_from} to {q_to}")
    canonical, _ = to_canonical(value, from_unit)
    _, factor, offset = unit_info(to_unit)
    return (canonical - offset) / factor


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str

    @property
    def quantity_type(self) -> str:
        return quantity_type(self.unit)

    @property
    def canonical(self) -> float:
        return to_canonical(self.value, self.unit)[0]

    def to(self, unit: str) -> "Quantity":
        return Quantity(convert(self.value, self.unit, unit), unit)


def agree(a_value: float, a_unit: str, b_value: float, b_unit: str,
          rel_tol: float = 0.01, abs_tol: float = 1e-9) -> bool:
    """True if two quantities represent the same physical value within tolerance.

    Raises IncompatibleUnits if the quantity types differ (a category error, not a
    numeric disagreement). rel_tol is relative to the larger canonical magnitude.
    """
    a_can, qa = to_canonical(a_value, a_unit)
    b_can, qb = to_canonical(b_value, b_unit)
    if qa != qb:
        raise IncompatibleUnits(f"{qa} vs {qb} are not comparable")
    diff = abs(a_can - b_can)
    return diff <= max(abs_tol, rel_tol * max(abs(a_can), abs(b_can)))


def conflict(a_value: float, a_unit: str, b_value: float, b_unit: str,
             rel_tol: float = 0.01) -> bool:
    """True if two same-type quantities numerically disagree beyond tolerance.

    The achievement test: conflict(100, 'lb-ft', 135.6, 'N·m') is False.
    """
    return not agree(a_value, a_unit, b_value, b_unit, rel_tol=rel_tol)
