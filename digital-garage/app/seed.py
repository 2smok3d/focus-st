"""Seed the store with the 2017 Ford Focus ST.

Values here mirror the fact-checked knowledge base (docs/VEHICLE.md and the
knowledge-base notes). Each fact carries a verification state; specs sourced from
Ford literature are OEM_VERIFIED, community-consensus items are CORROBORATED.
Nothing is VEHICLE_VERIFIED until confirmed on this actual car during work.
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .models import (
    Issue,
    MaintenanceInterval,
    Mod,
    OdometerReading,
    Spec,
    Source,
    Vehicle,
)

# --- sources ---------------------------------------------------------------
SOURCES = [
    dict(key="ford_wsm", name="Ford Workshop Manual / owner literature (MK3 Focus ST)",
         kind="oem_manual", authority=1),
    dict(key="motorcraft", name="Motorcraft / Ford fluid & part specifications",
         kind="oem_manual", authority=1),
    dict(key="ford_recall", name="Ford / NHTSA recall & TSB records",
         kind="tsb", authority=1),
    dict(key="idatalink", name="iDatalink Maestro compatibility documentation",
         kind="oem_adjacent", authority=2),
    dict(key="community", name="Focus ST community consensus (Focusfanatics / forums)",
         kind="forum", authority=4),
]

# --- specs: (category, name, value, unit, verification, source_key) ---------
SPECS = [
    ("engine", "Engine", "2.0L EcoBoost I4 (turbocharged, DI)", None, "OEM_VERIFIED", "ford_wsm"),
    ("engine", "Rated power", "252", "hp", "OEM_VERIFIED", "ford_wsm"),
    ("engine", "Rated torque", "270", "lb-ft", "OEM_VERIFIED", "ford_wsm"),
    ("engine", "Firing order", "1-3-4-2", None, "OEM_VERIFIED", "ford_wsm"),
    ("engine", "Compression ratio", "9.3:1", None, "OEM_VERIFIED", "ford_wsm"),
    ("engine", "Spark plug gap", "0.028-0.031", "in", "CORROBORATED", "community"),
    ("drivetrain", "Transmission", "MMT6 (Getrag) 6-speed manual", None, "OEM_VERIFIED", "ford_wsm"),
    ("drivetrain", "Layout", "Transverse FWD w/ eLSD (torque vectoring control)", None, "OEM_VERIFIED", "ford_wsm"),
    ("drivetrain", "Final drive", "3.82", ":1", "CORROBORATED", "community"),
    ("drivetrain", "1st gear", "3.31", ":1", "CORROBORATED", "community"),
    ("drivetrain", "2nd gear", "2.13", ":1", "CORROBORATED", "community"),
    ("drivetrain", "3rd gear", "1.48", ":1", "CORROBORATED", "community"),
    ("drivetrain", "4th gear", "1.14", ":1", "CORROBORATED", "community"),
    ("drivetrain", "5th gear", "0.95", ":1", "CORROBORATED", "community"),
    ("drivetrain", "6th gear", "0.76", ":1", "CORROBORATED", "community"),
    ("chassis", "Wheels", "18x8", "in", "OEM_VERIFIED", "ford_wsm"),
    ("chassis", "Wheel offset", "ET55", None, "OEM_VERIFIED", "ford_wsm"),
    ("chassis", "Bolt pattern", "5x108", "mm", "OEM_VERIFIED", "ford_wsm"),
    ("chassis", "Tire size", "235/40R18", None, "OEM_VERIFIED", "ford_wsm"),
    ("fluids", "Engine oil", "Motorcraft 5W-30 synthetic blend (SAE 5W-30, WSS-M2C946-B1)", None, "OEM_VERIFIED", "motorcraft"),
    ("fluids", "Engine oil capacity", "4.3", "qt", "OEM_VERIFIED", "motorcraft"),
    ("fluids", "Transmission fluid", "Motorcraft MTF (WSS-M2C200-D2 spec, MMT6)", None, "OEM_VERIFIED", "motorcraft"),
    ("fluids", "Coolant", "Motorcraft Orange (WSS-M97B44-D)", None, "OEM_VERIFIED", "motorcraft"),
    ("torque", "Wheel lug nut", "100", "lb-ft", "OEM_VERIFIED", "ford_wsm"),
    ("torque", "Spark plug", "13", "lb-ft", "CORROBORATED", "community"),
]

# --- maintenance intervals: (item, miles, months, verification, source_key, note) --
INTERVALS = [
    ("Engine oil & filter", 5000, 6, "OEM_VERIFIED", "ford_wsm", "Severe-duty / turbo interval; AZ heat favors the shorter side."),
    ("Tire rotation", 5000, 6, "OEM_VERIFIED", "ford_wsm", "Pair with oil change."),
    ("Cabin air filter", 20000, 12, "CORROBORATED", "community", None),
    ("Engine air filter", 30000, None, "CORROBORATED", "community", None),
    ("MMT6 transmission fluid", 60000, None, "CORROBORATED", "community", "Community-preferred; Ford lists as fill-for-life. Shorten under hard use."),
    ("Spark plugs", 60000, None, "CORROBORATED", "community", "Shorten to ~30-45k if tuned."),
    ("Brake fluid", None, 24, "OEM_VERIFIED", "ford_wsm", "Time-based; critical with track/spirited use."),
    ("Coolant", 100000, 60, "OEM_VERIFIED", "ford_wsm", "First change long; then shorter."),
    ("Clutch fluid (shares brake reservoir)", None, 24, "CORROBORATED", "community", "MMT6 hydraulic clutch."),
]

# --- known issues ----------------------------------------------------------
# Platform-level (CORROBORATED) + this-car observations (VEHICLE_VERIFIED where
# physically confirmed).
ISSUES = [
    dict(title="Radiator cracked → through-hole (front-left of core)",
         status="open", severity="stop", verification="VEHICLE_VERIFIED",
         note="Confirmed hole in the aluminum core. Decided fix: Mishimoto radiator. Priority 1 (Cooling bundle)."),
    dict(title="Possible oil leak after aggressive driving",
         status="monitoring", severity="warn", verification="CORROBORATED",
         note="Suspects: valve-cover gasket, turbo oil lines, filter-housing adapter, oil-pan RTV. Diagnose during the cooling/oil service."),
    dict(title="Floating / uncapped vacuum line (EVAP), no codes",
         status="monitoring", severity="warn", verification="VEHICLE_VERIFIED",
         note="Trace and cap. Check against the EVAP purge-valve recall by VIN first."),
    dict(title="0 admin keys / 3 MyKeys (ex-auction)",
         status="open", severity="warn", verification="VEHICLE_VERIFIED",
         note="Program a 2nd IA key via FORScan PATS (Add Key works with 1 existing) + reset MyKey."),
    dict(title="EVAP purge valve campaign (18S32 / 26S40) — verify status for this VIN",
         status="monitoring", severity="warn", verification="CORROBORATED",
         note="Stuck-open purge valve causes P1450/rough idle after refuel. Confirm recall completion against the VIN before chasing EVAP codes."),
    dict(title="P04DB crankcase-ventilation sensitivity — inspect PCV plumbing before parts",
         status="monitoring", severity="info", verification="CORROBORATED",
         note="Treat as a case: smoke/pressure test, confirm calibration expects installed PCV architecture. Permanent DTC can linger post-repair until monitors complete."),
]

# --- odometer baseline ------------------------------------------------------
ODOMETER_AT_PURCHASE = 86390

# --- installed mods observed on THIS car (VEHICLE_VERIFIED) ------------------
# Seeded because they are physically confirmed on the vehicle. Future installs
# still go through the propose→approve boundary.
MODS = [
    dict(slot="Intake", part_name="Injen cold-air intake", stage="P1", verification="VEHICLE_VERIFIED",
         note="Installed by prior owner. Verify MAF housing size + tune requirement."),
    dict(slot="Intake feed", part_name="Ram-air / hood-scoop feed", stage="P1", verification="VEHICLE_VERIFIED",
         note="PO addition feeding the airbox."),
    dict(slot="Intercooler", part_name="Depo 'Beast' FMIC", stage="R1", verification="VEHICLE_VERIFIED",
         note="28×8.25×5.5 core. Pressure-tested OK to ~15 psi."),
    dict(slot="Engine mounts", part_name="Torque Solution rear + passenger mounts", stage="P1", verification="VEHICLE_VERIFIED",
         note="Reduced wheel hop / engine movement; some NVH increase."),
    dict(slot="Battery", part_name="Upgraded battery (Group 96R, 590 CCA)", verification="VEHICLE_VERIFIED",
         note="AGS delete means no grille-shutter draw."),
    dict(slot="Cargo", part_name="Trunk storage box", verification="VEHICLE_VERIFIED"),
    dict(slot="Active Grille Shutters", part_name="AGS — REMOVED (delete)", verification="VEHICLE_VERIFIED",
         note="Grille shutters removed. Confirm tune/BCM tolerates the delete."),
]


def seed(session: Session, *, if_empty: bool = False) -> str:
    existing = session.scalar(select(Vehicle).where(Vehicle.vin == settings.vehicle_vin))
    if existing is not None:
        if if_empty:
            return f"Vehicle {settings.vehicle_vin} already present — seed skipped."
        vehicle = existing
    else:
        vehicle = Vehicle(
            vin=settings.vehicle_vin, year=2017, make="Ford", model="Focus",
            trim="ST", engine="2.0L EcoBoost I4", transmission="MMT6 6-speed manual",
            notes="MK3 Focus ST. Phoenix, AZ. Ex-auction acquisition.",
        )
        session.add(vehicle)
        session.flush()

    src_ids: dict[str, int] = {}
    for s in SOURCES:
        row = session.scalar(select(Source).where(Source.name == s["name"]))
        if row is None:
            row = Source(name=s["name"], kind=s["kind"], authority=s["authority"])
            session.add(row)
            session.flush()
        src_ids[s["key"]] = row.id

    def upsert_spec(category, name, value, unit, verification, source_key):
        row = session.scalar(
            select(Spec).where(Spec.vehicle_id == vehicle.id,
                               Spec.category == category, Spec.name == name)
        )
        if row is None:
            session.add(Spec(vehicle_id=vehicle.id, category=category, name=name,
                             value=value, unit=unit, verification=verification,
                             source_id=src_ids.get(source_key)))

    for row in SPECS:
        upsert_spec(*row)

    for item, miles, months, verification, source_key, note in INTERVALS:
        if session.scalar(select(MaintenanceInterval).where(
                MaintenanceInterval.vehicle_id == vehicle.id,
                MaintenanceInterval.item == item)) is None:
            session.add(MaintenanceInterval(
                vehicle_id=vehicle.id, item=item, interval_miles=miles,
                interval_months=months, verification=verification,
                source_id=src_ids.get(source_key), note=note))

    for i in ISSUES:
        if session.scalar(select(Issue).where(
                Issue.vehicle_id == vehicle.id, Issue.title == i["title"])) is None:
            session.add(Issue(vehicle_id=vehicle.id, opened_at=dt.date.today(), **i))

    for m in MODS:
        if session.scalar(select(Mod).where(
                Mod.vehicle_id == vehicle.id, Mod.slot == m["slot"],
                Mod.part_name == m["part_name"])) is None:
            session.add(Mod(vehicle_id=vehicle.id, **m))

    if session.scalar(select(OdometerReading).where(
            OdometerReading.vehicle_id == vehicle.id)) is None:
        session.add(OdometerReading(vehicle_id=vehicle.id, miles=ODOMETER_AT_PURCHASE,
                                    note="At purchase (ex-auction)."))

    from . import service  # lazy: seed the known recall baseline
    recalls_n = service.seed_known_recalls(session, vehicle.id)

    session.flush()
    return (f"Seeded vehicle {vehicle.vin}: {len(SPECS)} specs, {len(INTERVALS)} "
            f"intervals, {len(ISSUES)} issues, {len(MODS)} mods, {recalls_n} recalls, "
            f"{len(SOURCES)} sources.")
