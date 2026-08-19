"""Baseline commissioning — onboard a machine as a real digital twin, not a DB row.

For each machine this builds the vehicle-agnostic reference graph
(Manufacturer → Platform → Variant → Engine/Transmission → Systems → Components),
creates the actual `vehicles` row, links it to its reference variant, sets a
capability profile, and records a **structured baseline** of component states —
graded honestly: documented/owner-stated facts get a real condition + knowledge
state; everything else is left unrecorded (assumed stock, *not* claimed verified).

Specs here are the web-verified figures from each machine's manual (see
data/vehicles/<slug>/manual.md). ⚠️-flagged manual items are NOT asserted as fact.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import twin
from .models import Vehicle
from .refmodels import (
    Component,
    Engine,
    Manufacturer,
    System,
    Transmission,
    VehiclePlatform,
    VehicleVariant,
)

# Each machine's reference model + vehicle identity + commissioning baseline.
# systems: {slug: (name, parent_slug|None)}   components: {system_slug: [(slug, name)]}
# capabilities: [(name, supported)]           baseline: [(comp_slug, condition, knowledge, note)]
MACHINES: dict[str, dict] = {
    "zzr600": {
        "manufacturer": ("Kawasaki", "Japan"),
        "platform": ("ZZR600 (ZX600-D)", "ZX600-D", "1990–1993"),
        "variant": ("zzr600", "ZZR600", "ZX600-D (1st gen, ram-air)", "US", "1991"),
        "engine": dict(code="ZX600D I4", displacement_cc=599, config="I4 DOHC 16v liquid-cooled",
                       aspiration="carbureted (ram-air)", fuel="gasoline",
                       power="~98 hp (crank)", torque="~46 lb-ft @ 9,500",
                       notes="Bore×stroke 66.0×43.8 mm. 4× Keihin CVKD36 carbs."),
        "transmission": dict(code="6-speed", type="6-speed manual", gears=6),
        "systems": {
            "engine": ("Engine", None), "fuel": ("Fuel / Carburetion", None),
            "cooling": ("Cooling", None), "ignition": ("Ignition", None),
            "driveline": ("Driveline", None), "electrical": ("Electrical / Charging", None),
        },
        "components": {
            "engine": [("cylinder-head", "Cylinder Head"), ("valvetrain", "Valvetrain (shim-under-bucket)"),
                       ("crankshaft", "Crankshaft"), ("clutch", "Clutch")],
            "fuel": [("carburetors", "Carburetors (4× Keihin CVKD36)"), ("petcock", "Petcock"),
                     ("float-bowls", "Float Bowls")],
            "cooling": [("radiator", "Radiator"), ("water-pump", "Water Pump"), ("thermostat", "Thermostat")],
            "ignition": [("coils", "Ignition Coils"), ("spark-plugs", "Spark Plugs (NGK CR9E)"), ("cdi", "CDI / Igniter")],
            "driveline": [("chain", "Drive Chain (525)"), ("sprockets", "Sprockets")],
            "electrical": [("stator", "Stator"), ("regulator-rectifier", "Regulator/Rectifier"), ("battery", "Battery")],
        },
        "capabilities": [("carburetor", True), ("obd", False), ("dtc", False),
                         ("ecu_telemetry", False), ("compression_test", True), ("manual_measurement", True)],
        "vehicle": dict(vin="KAW-ZX600D-1991", year=1991, make="Kawasaki", model="ZZR600",
                        trim="ZX600-D", engine="599cc I4 DOHC 16v (carbureted)",
                        transmission="6-speed", notes="First-gen ZZR. Recommission from a long sit."),
        "baseline": [
            ("carburetors", "suspect", "INFERRED", "Long sit — bench service / ultrasonic clean due before running."),
            ("regulator-rectifier", "suspect", "INFERRED", "Verify charging (R/R is a known weak point) before road use."),
        ],
    },
    "rz350": {
        "manufacturer": ("Yamaha", "Japan"),
        "platform": ("RZ350 / RD350 YPVS", "31K", "1983–1985"),
        "variant": ("rz350", "RZ350 Kenny Roberts", "31K (final US year, catalyzed)", "US", "1985"),
        "engine": dict(code="RZ350 2T twin", displacement_cc=347, config="2-stroke reed-valve parallel twin · YPVS",
                       aspiration="carbureted (2× Mikuni VM26)", fuel="gasoline + 2-stroke oil",
                       power="~46 hp (US catted) / ~59 hp (RD)", torque="~30 lb-ft @ 8,000",
                       notes="Bore×stroke 64×54 mm. Autolube injection; gearbox oil separate."),
        "transmission": dict(code="6-speed", type="6-speed manual", gears=6),
        "systems": {
            "engine": ("Engine (2-stroke)", None), "fuel": ("Fuel / Carburetion", None),
            "cooling": ("Cooling", None), "ignition": ("Ignition", None),
            "lubrication": ("Lubrication (Autolube)", None), "driveline": ("Driveline", None),
            "electrical": ("Electrical / Charging", None),
        },
        "components": {
            "engine": [("cylinders", "Cylinders / Barrels"), ("pistons", "Pistons & Rings"),
                       ("crank-seals", "Crank Seals"), ("ypvs-powervalve", "YPVS Power Valve"),
                       ("reed-valves", "Reed Valves"), ("clutch", "Clutch")],
            "fuel": [("carburetors", "Carburetors (2× Mikuni VM26)")],
            "cooling": [("radiator", "Radiator"), ("water-pump", "Water Pump")],
            "ignition": [("cdi", "CDI"), ("spark-plugs", "Spark Plugs (NGK B8ES/BR8ES)")],
            "lubrication": [("autolube-pump", "Autolube Oil Pump"), ("oil-tank", "Injection Oil Tank")],
            "driveline": [("chain", "Drive Chain")],
            "electrical": [("stator", "Stator"), ("regulator-rectifier", "Regulator/Rectifier"), ("battery", "Battery")],
        },
        "capabilities": [("carburetor", True), ("two_stroke", True), ("autolube", True),
                         ("obd", False), ("dtc", False), ("manual_measurement", True)],
        "vehicle": dict(vin="YAM-RZ350-1985", year=1985, make="Yamaha", model="RZ350",
                        trim="Kenny Roberts (31K)", engine="347cc 2-stroke twin · YPVS",
                        transmission="6-speed", notes="Last US year. KR livery. Restoration project."),
        "baseline": [
            ("ypvs-powervalve", "suspect", "INFERRED", "Power-valve service due — carbon/seizure common; clean & verify actuation."),
            ("crank-seals", "suspect", "INFERRED", "Verify crank seals (air-leak = lean seizure on a 2-stroke). Pressure-test."),
        ],
    },
    "tz250": {
        "manufacturer": ("Yamaha", "Japan"),
        "platform": ("TZ250 (production racer)", "TZ250", "1986–1987"),
        "variant": ("tz250", "TZ250", "Over-the-counter GP racer (premix)", "JDM/race", "1986"),
        "engine": dict(code="TZ250 2T twin", displacement_cc=249, config="2-stroke reed-valve parallel twin · liquid-cooled",
                       aspiration="carbureted (2× Mikuni flat-slide, powerjet)", fuel="premix (race 2-stroke oil)",
                       power="~55–65 hp", torque="—",
                       notes="Bore×stroke 56×50.7 mm. Premix only — NO oil injection. Race-only."),
        "transmission": dict(code="6-speed close-ratio", type="6-speed manual (dry clutch)", gears=6),
        "systems": {
            "engine": ("Engine (2-stroke race)", None), "fuel": ("Fuel / Carburetion", None),
            "cooling": ("Cooling", None), "ignition": ("Ignition", None), "driveline": ("Driveline", None),
        },
        "components": {
            "engine": [("cylinders", "Cylinders / Barrels"), ("pistons", "Pistons & Rings"),
                       ("crankshaft", "Crankshaft"), ("reed-valves", "Reed Valves"), ("dry-clutch", "Dry Clutch")],
            "fuel": [("carburetors", "Carburetors (2× Mikuni flat-slide powerjet)")],
            "cooling": [("radiator", "Radiator"), ("water-pump", "Water Pump")],
            "ignition": [("cdi", "CDI / Ignition"), ("spark-plugs", "Spark Plugs")],
            "driveline": [("chain", "Drive Chain"), ("sprockets", "Sprockets (per circuit)")],
        },
        "capabilities": [("carburetor", True), ("two_stroke", True), ("premix", True),
                         ("race_sessions", True), ("engine_hours", True), ("jetting", True),
                         ("obd", False), ("dtc", False), ("telemetry", True)],
        "vehicle": dict(vin="YAM-TZ250-1986", year=1986, make="Yamaha", model="TZ250",
                        trim="production racer", engine="249cc 2-stroke twin (premix)",
                        transmission="6-speed close-ratio · dry clutch",
                        notes="GP roadracer. No lights, premix only — track/GP only. Service by race-hour."),
        "baseline": [
            ("pistons", "unknown", "UNKNOWN", "Top-end life is measured in race-hours — baseline bore + ring end-gap before running."),
            ("carburetors", "unknown", "UNKNOWN", "Jetting is per-day (air density). Establish a baseline jetting sheet."),
        ],
    },
    "toyota-pickup": {
        "manufacturer": ("Toyota", "Japan"),
        "platform": ("Pickup (N50, single cab)", "N50", "1984–1988"),
        "variant": ("toyota-pickup", "Pickup 22RE", "Single cab, RWD", "US", "1986"),
        "engine": dict(code="22RE", displacement_cc=2366, config="SOHC 8v EFI I4 · iron block, alloy head",
                       aspiration="naturally aspirated (EFI)", fuel="gasoline (EFI)",
                       power="~105 hp", torque="136–140 lb-ft @ 2,800–3,600",
                       notes="Bore×stroke 92.0×89.0 mm. CR 9.0:1. Swap pending — shell is engine-out."),
        "transmission": dict(code="W56", type="5-speed manual", gears=5),
        "systems": {
            "engine": ("Engine (22RE)", None), "fuel": ("Fuel (EFI)", None),
            "cooling": ("Cooling", None), "ignition": ("Ignition", None),
            "driveline": ("Driveline", None), "electrical": ("Electrical", None),
            "interior": ("Interior", None), "body": ("Body", None),
        },
        "components": {
            "engine": [("block", "Engine Block (22RE)"), ("cylinder-head", "Cylinder Head"),
                       ("valvetrain", "Valvetrain (adjustable)"), ("timing-chain", "Timing Chain"),
                       ("water-pump", "Water Pump")],
            "fuel": [("efi", "EFI System"), ("fuel-pump", "Fuel Pump"), ("injectors", "Injectors")],
            "cooling": [("radiator", "Radiator"), ("thermostat", "Thermostat")],
            "ignition": [("distributor", "Distributor"), ("spark-plugs", "Spark Plugs (NGK BPR5EY)"), ("coil", "Ignition Coil")],
            "driveline": [("transmission", "W56 Transmission"), ("clutch", "Clutch"), ("rear-diff", "Rear Differential")],
            "electrical": [("alternator", "Alternator"), ("battery", "Battery"), ("harness", "Wiring Harness")],
            "interior": [("seats", "Seats"), ("dash", "Dash"), ("interior-trim", "Interior Trim")],
            "body": [("cab", "Cab"), ("bed", "Bed")],
        },
        "capabilities": [("efi", True), ("obd", True), ("dtc", True), ("can_bus", False),
                         ("ecu_telemetry", False), ("manual_measurement", True)],
        "vehicle": dict(vin="TOY-22RE-1986", year=1986, make="Toyota", model="Pickup",
                        trim="22RE single cab", engine="2.4L 22RE SOHC EFI I4 (swap pending)",
                        transmission="W56 5-speed manual",
                        notes="Empty-shell single cab — full interior rebuild + engine swap. Ground-up."),
        "baseline": [
            ("block", "removed", "DIRECTLY_OBSERVED", "Engine-out shell — 22RE swap pending (owner-stated)."),
            ("seats", "removed", "DIRECTLY_OBSERVED", "Bare shell — interior 100% stripped (owner-stated)."),
            ("dash", "removed", "DIRECTLY_OBSERVED", "Bare shell — interior 100% stripped (owner-stated)."),
            ("interior-trim", "removed", "DIRECTLY_OBSERVED", "Bare shell — interior 100% stripped (owner-stated)."),
        ],
    },
}


def _get_or_create(session, model, where, **create):
    row = session.scalar(select(model).where(*where))
    if row is None:
        row = model(**create)
        session.add(row)
        session.flush()
    return row


def commission_machine(session: Session, slug: str) -> str:
    spec = MACHINES.get(slug)
    if spec is None:
        return f"Unknown machine '{slug}'. Known: {', '.join(MACHINES)}."

    mk_name, country = spec["manufacturer"]
    maker = _get_or_create(session, Manufacturer, (Manufacturer.name == mk_name,),
                           name=mk_name, country=country)
    p_name, p_code, p_years = spec["platform"]
    platform = _get_or_create(session, VehiclePlatform,
                              (VehiclePlatform.manufacturer_id == maker.id, VehiclePlatform.name == p_name),
                              manufacturer_id=maker.id, name=p_name, code=p_code, years=p_years)
    v_slug, v_name, v_trim, v_market, v_years = spec["variant"]
    variant = _get_or_create(session, VehicleVariant, (VehicleVariant.slug == v_slug,),
                             platform_id=platform.id, slug=v_slug, name=v_name,
                             trim=v_trim, market=v_market, years=v_years)

    if session.scalar(select(Engine).where(Engine.variant_id == variant.id)) is None:
        session.add(Engine(variant_id=variant.id, **spec["engine"]))
    if session.scalar(select(Transmission).where(Transmission.variant_id == variant.id)) is None:
        session.add(Transmission(variant_id=variant.id, **spec["transmission"]))
    session.flush()

    sysmap = {}
    for s_slug, (s_name, parent) in spec["systems"].items():
        row = _get_or_create(session, System,
                             (System.variant_id == variant.id, System.slug == s_slug),
                             variant_id=variant.id, slug=s_slug, name=s_name,
                             parent_id=sysmap[parent].id if parent else None)
        sysmap[s_slug] = row
    for s_slug, comps in spec["components"].items():
        for c_slug, c_name in comps:
            _get_or_create(session, Component,
                           (Component.system_id == sysmap[s_slug].id, Component.slug == c_slug),
                           system_id=sysmap[s_slug].id, slug=c_slug, name=c_name)
    session.flush()

    vspec = spec["vehicle"]
    vehicle = session.scalar(select(Vehicle).where(Vehicle.vin == vspec["vin"]))
    if vehicle is None:
        vehicle = Vehicle(**vspec)
        session.add(vehicle)
        session.flush()
    if vehicle.variant_id != variant.id:
        vehicle.variant_id = variant.id
    session.flush()

    for cap, supported in spec["capabilities"]:
        twin.set_capability(session, vehicle, cap, supported)

    existing = twin.current_states(session, vehicle.id)
    recorded = 0
    for c_slug, cond, know, note in spec["baseline"]:
        if c_slug in existing:
            continue
        twin.record_state(session, vehicle, c_slug, condition=cond, knowledge_state=know,
                          confidence=0.8 if know == "DIRECTLY_OBSERVED" else 0.4,
                          note=note, source_label="baseline commissioning")
        recorded += 1

    n_sys = len(sysmap)
    n_comp = sum(len(c) for c in spec["components"].values())
    return (f"Commissioned {v_name} [{v_slug}] · VIN {vspec['vin']} · {n_sys} systems, "
            f"{n_comp} components, {len(spec['capabilities'])} capabilities, "
            f"{recorded} baseline state(s).")


def commission_all(session: Session) -> list[str]:
    return [commission_machine(session, slug) for slug in MACHINES]
