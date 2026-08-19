"""V2 reference-model seed — the Focus ST as the first deeply-modeled vehicle.

Builds Manufacturer → Platform → Variant → Engine/Transmission → System tree →
Components → typed relationships, then seeds a handful of **claims with evidence**
resolved through provenance.resolve_verdict — including a real conflict (the
documented 4.3 vs 5.7 qt oil-capacity discrepancy) and a vehicle-verified fact.

Idempotent: safe to run repeatedly. Additive to the V1 seed.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import provenance as pv
from .models import Source, Vehicle
from .refmodels import (
    Claim,
    ClaimEvidence,
    Component,
    ComponentRelationship,
    Engine,
    Manufacturer,
    SourceDocument,
    System,
    Transmission,
    VehiclePlatform,
    VehicleVariant,
)

VARIANT_SLUG = "focus-st"

# system tree: (slug, name, [child slugs]) — children created under the parent
SYSTEMS = {
    "powertrain": ("Powertrain", None),
    "engine": ("Engine", "powertrain"),
    "forced-induction": ("Forced Induction", "powertrain"),
    "fuel": ("Fuel", "powertrain"),
    "ignition": ("Ignition", "powertrain"),
    "cooling": ("Cooling", "powertrain"),
}
COMPONENTS = {
    "engine": [("block", "Engine Block"), ("head", "Cylinder Head"), ("timing", "Timing"),
               ("lubrication", "Lubrication / Oil System"), ("pcv", "PCV / Crankcase Vent"),
               ("throttle-body", "Throttle Body"), ("intake-manifold", "Intake Manifold")],
    "forced-induction": [("turbocharger", "Turbocharger"), ("wastegate", "Wastegate"),
                         ("bypass-valve", "Bypass Valve"), ("intercooler", "Intercooler"),
                         ("charge-piping", "Charge Piping")],
    "fuel": [("hpfp", "High-Pressure Fuel Pump"), ("injectors", "Injectors"), ("fuel-rail", "Fuel Rail")],
    "ignition": [("coils", "Ignition Coils"), ("spark-plugs", "Spark Plugs")],
    "cooling": [("radiator", "Radiator"), ("thermostat", "Thermostat"), ("coolant", "Coolant")],
}
# typed graph edges: (from, relation, to, note)
RELATIONSHIPS = [
    ("turbocharger", "lubricated_by", "lubrication", "Turbo bearing oil feed/return"),
    ("turbocharger", "cooled_by", "coolant", "Coolant-cooled center section"),
    ("turbocharger", "outputs_to", "intercooler", "Compressed charge to the IC"),
    ("turbocharger", "controlled_by", "wastegate", "Boost limited by the wastegate"),
    ("intercooler", "outputs_to", "charge-piping", "Cooled charge to the throttle"),
    ("charge-piping", "feeds", "throttle-body", "Cooled charge to the throttle body"),
    ("throttle-body", "feeds", "intake-manifold", "Metered air into the plenum"),
    ("intake-manifold", "feeds", "head", "Charge air into the cylinder head ports"),
    ("pcv", "affects", "turbocharger", "Crankcase vent routing affects intake/boost"),
    ("bypass-valve", "associated_with", "turbocharger", "Recirculating BPV on lift-throttle"),
]


def _source(session: Session, name: str, kind: str, authority: int) -> Source:
    row = session.scalar(select(Source).where(Source.name == name))
    if row is None:
        row = Source(name=name, kind=kind, authority=authority)
        session.add(row)
        session.flush()
    return row


def _doc(session: Session, source: Source, title: str, **kw) -> SourceDocument:
    row = session.scalar(select(SourceDocument).where(SourceDocument.title == title))
    if row is None:
        row = SourceDocument(source_id=source.id, title=title, **kw)
        session.add(row)
        session.flush()
    return row


def _add_claim(session, subject_type, subject_key, prop, value, unit, applicability, evidences):
    """evidences: list of (authority:int, stance:str, on_vehicle:bool, label:str, doc_id?)."""
    existing = session.scalar(select(Claim).where(
        Claim.subject_type == subject_type, Claim.subject_key == subject_key, Claim.prop == prop))
    if existing is not None:
        return existing
    claim = Claim(subject_type=subject_type, subject_key=subject_key, prop=prop,
                  value=value, unit=unit, applicability=applicability)
    session.add(claim)
    session.flush()
    ev_objs = []
    for auth, stance, on_veh, label, *rest in evidences:
        doc_id = rest[0] if rest else None
        session.add(ClaimEvidence(claim_id=claim.id, source_document_id=doc_id, authority=auth,
                                  stance=stance, on_vehicle=on_veh, source_label=label))
        ev_objs.append(pv.Evidence(authority=auth, stance=stance, on_vehicle=on_veh, source_label=label))
    verdict = pv.resolve_verdict(ev_objs)
    claim.verification = verdict.verification.name
    claim.confidence = verdict.confidence
    claim.conflict = verdict.conflict
    claim.notes = verdict.rationale
    session.flush()
    return claim


def seed_reference(session: Session) -> str:
    ford = session.scalar(select(Manufacturer).where(Manufacturer.name == "Ford"))
    if ford is None:
        ford = Manufacturer(name="Ford", country="USA")
        session.add(ford)
        session.flush()

    platform = session.scalar(select(VehiclePlatform).where(
        VehiclePlatform.manufacturer_id == ford.id, VehiclePlatform.name == "Focus MK3"))
    if platform is None:
        platform = VehiclePlatform(manufacturer_id=ford.id, name="Focus MK3",
                                   code="C346 / MK3", years="2011–2018")
        session.add(platform)
        session.flush()

    variant = session.scalar(select(VehicleVariant).where(VehicleVariant.slug == VARIANT_SLUG))
    if variant is None:
        variant = VehicleVariant(platform_id=platform.id, slug=VARIANT_SLUG, name="Focus ST",
                                 trim="ST (MK3.5)", market="NA", years="2015–2018")
        session.add(variant)
        session.flush()

    if session.scalar(select(Engine).where(Engine.variant_id == variant.id)) is None:
        session.add(Engine(variant_id=variant.id, code="R9DA / 2.0 EcoBoost", displacement_cc=1999,
                           config="I4 DOHC 16v", aspiration="turbo GTDI", fuel="gasoline (DI)",
                           power="252 hp @ 5,500", torque="270 lb-ft @ 2,500"))
    if session.scalar(select(Transmission).where(Transmission.variant_id == variant.id)) is None:
        session.add(Transmission(variant_id=variant.id, code="MT82", type="6-speed manual", gears=6))
    session.flush()

    # systems (parents first)
    sysmap: dict[str, System] = {}
    for slug, (name, parent_slug) in SYSTEMS.items():
        row = session.scalar(select(System).where(System.variant_id == variant.id, System.slug == slug))
        if row is None:
            row = System(variant_id=variant.id, slug=slug, name=name,
                         parent_id=sysmap[parent_slug].id if parent_slug else None)
            session.add(row)
            session.flush()
        sysmap[slug] = row

    # components
    compmap: dict[str, Component] = {}
    for sys_slug, comps in COMPONENTS.items():
        for cslug, cname in comps:
            row = session.scalar(select(Component).where(
                Component.system_id == sysmap[sys_slug].id, Component.slug == cslug))
            if row is None:
                row = Component(system_id=sysmap[sys_slug].id, slug=cslug, name=cname)
                session.add(row)
                session.flush()
            compmap[cslug] = row

    # relationships
    for a, rel, b, note in RELATIONSHIPS:
        exists = session.scalar(select(ComponentRelationship).where(
            ComponentRelationship.from_component_id == compmap[a].id,
            ComponentRelationship.to_component_id == compmap[b].id,
            ComponentRelationship.relation == rel))
        if exists is None:
            session.add(ComponentRelationship(from_component_id=compmap[a].id,
                                              to_component_id=compmap[b].id, relation=rel, note=note))
    session.flush()

    # sources + documents
    ford_wsm = _source(session, "Ford Workshop Manual (MK3 Focus ST)", "oem_manual", 1)
    ford_lit = _source(session, "Ford owner literature (MK3 Focus ST)", "oem_manual", 1)
    community = _source(session, "Focus ST community consensus (Focusfanatics / forums)", "forum", 4)
    wsm_doc = _doc(session, ford_wsm, "Ford Focus 2017 Workshop Manual", doc_id="WSM-2017", revision="A")
    lit_doc = _doc(session, ford_lit, "2017 Focus ST Owner's Manual", doc_id="OM-2017")

    ap = {"variant": VARIANT_SLUG, "years": "2015-2018", "market": "NA"}
    # 1) OEM-verified, clean
    _add_claim(session, "variant", VARIANT_SLUG, "lug_torque", "100", "lb-ft", ap,
               [(1, pv.SUPPORTS, False, "Ford WSM §204", wsm_doc.id)])
    # 2) OEM-verified firing order
    _add_claim(session, "engine", "r9da", "firing_order", "1-3-4-2", None, ap,
               [(1, pv.SUPPORTS, False, "Ford WSM §303", wsm_doc.id)])
    # 3) CONFLICT — the documented 4.3 vs 5.7 qt oil-capacity discrepancy (two OEM-grade docs)
    _add_claim(session, "component", "lubrication", "oil_capacity", "4.3", "qt", ap,
               [(1, pv.SUPPORTS, False, "Ford WSM (with filter)", wsm_doc.id),
                (1, pv.CONTRADICTS, False, "Ford literature (states 5.7)", lit_doc.id)])
    # 4) Community-corroborated
    _add_claim(session, "component", "spark-plugs", "part_and_gap", "SP-537 · 0.028–0.031 in", None, ap,
               [(4, pv.SUPPORTS, False, "community consensus")])
    # 5) Community claim about a known trait
    _add_claim(session, "component", "intercooler", "heat_soak_prone", "yes", None, ap,
               [(4, pv.SUPPORTS, False, "community consensus (AZ heat)")])
    # 6) VEHICLE-VERIFIED — observed on THIS car
    _add_claim(session, "component", "radiator", "condition", "through-hole crack (front-left)", None,
               {"variant": VARIANT_SLUG},
               [(2, pv.SUPPORTS, True, "observed on VIN …223134")])

    # link the actual vehicle to its reference variant
    veh = session.scalar(select(Vehicle))
    linked = ""
    if veh is not None and getattr(veh, "variant_id", None) != variant.id:
        veh.variant_id = variant.id
        linked = f" · linked vehicle {veh.vin} → variant"
    session.flush()

    n_sys = len(sysmap)
    n_comp = len(compmap)
    n_claims = len(session.scalars(select(Claim)).all())
    return (f"Seeded reference: Ford → Focus MK3 → Focus ST · {n_sys} systems, {n_comp} components, "
            f"{len(RELATIONSHIPS)} relationships, {n_claims} claims{linked}.")
