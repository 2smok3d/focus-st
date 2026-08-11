from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class ComponentState(str, Enum):
    STOCK = "stock"
    INSTALLED = "installed"
    UPGRADED = "upgraded"
    REMOVED = "removed"
    UNKNOWN = "unknown"
    NEEDS_ATTENTION = "needs_attention"
    PLANNED = "planned"


@dataclass(frozen=True)
class ComponentEvent:
    component_id: str
    event_type: str
    part_name: str | None = None
    manufacturer: str | None = None
    part_number: str | None = None
    mileage_mi: int | None = None
    notes: str | None = None


@dataclass(frozen=True)
class ComponentSnapshot:
    component_id: str
    state: ComponentState
    part_name: str | None
    manufacturer: str | None
    part_number: str | None
    notes: tuple[str, ...]


def reduce_component(component_id: str, events: Iterable[ComponentEvent]) -> ComponentSnapshot:
    """Derive present state without overwriting historical events."""
    state = ComponentState.UNKNOWN
    part_name = manufacturer = part_number = None
    notes: list[str] = []
    for event in events:
        if event.component_id != component_id:
            continue
        et = event.event_type.lower()
        if et in {"factory_baseline", "stock_confirmed"}:
            state = ComponentState.STOCK
        elif et in {"install", "replace_stock"}:
            state = ComponentState.INSTALLED
        elif et in {"upgrade", "performance_install"}:
            state = ComponentState.UPGRADED
        elif et == "remove":
            state = ComponentState.REMOVED
        elif et in {"fault", "inspection_failed", "service_due"}:
            state = ComponentState.NEEDS_ATTENTION
        elif et == "planned":
            state = ComponentState.PLANNED
        elif et == "unknown":
            state = ComponentState.UNKNOWN
        if event.part_name:
            part_name = event.part_name
        if event.manufacturer:
            manufacturer = event.manufacturer
        if event.part_number:
            part_number = event.part_number
        if event.notes:
            notes.append(event.notes)
    return ComponentSnapshot(component_id, state, part_name, manufacturer, part_number, tuple(notes))


CURRENT_SEED_EVENTS = [
    ComponentEvent("intake_airbox", "performance_install", "Cold air intake", "Injen", notes="Confirmed installed in existing FFST Mods & Build Log."),
    ComponentEvent("ram_air", "performance_install", "Ram air intake setup", notes="Confirmed installed in existing FFST Mods & Build Log."),
    ComponentEvent("rear_motor_mount", "performance_install", "Rear motor mount", "Torque Solutions", notes="Confirmed installed in existing FFST Mods & Build Log."),
    ComponentEvent("passenger_motor_mount", "performance_install", "Passenger-side motor mount", "Torque Solutions", notes="Confirmed installed in existing FFST Mods & Build Log."),
    ComponentEvent("battery", "upgrade", "Larger/upgraded battery", notes="Exact model/capacity not yet verified."),
    ComponentEvent("hood_scoops", "performance_install", "Hood scoops"),
    ComponentEvent("active_grille_shutters", "remove", "Active grille shutters", notes="Existing record states blades and motor/actuator were removed by prior owner."),
]


def current_seed_snapshot(component_ids: Iterable[str]) -> dict[str, ComponentSnapshot]:
    return {cid: reduce_component(cid, CURRENT_SEED_EVENTS) for cid in component_ids}
