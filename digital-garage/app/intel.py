"""Vehicle-intelligence projection (Milestone G bridge).

Aggregates the whole V2 backend — reference model, digital twin, diagnostics,
workshop, telemetry, and knowledge quality — into a single static `intel.json` the
GitHub-Pages cockpit can fetch. Postgres stays canonical; this is a projection, like
`garage.json`. Read-only: it never mutates anything.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Vehicle


def build_intel(session: Session, variant_slug: str = "focus-st") -> dict:
    from . import graphs, knowledge, refservice, twin, workbench, workshop
    from .refmodels import VehicleVariant

    variant = session.scalar(select(VehicleVariant).where(VehicleVariant.slug == variant_slug))
    header = refservice.variant_header(session, variant_slug) if variant else None
    vehicle = session.scalar(select(Vehicle).where(Vehicle.variant_id == variant.id)) if variant else None

    # systems + overlays
    tree = refservice.system_tree(session, variant_slug) if variant else []
    overlays = graphs.domains(session, variant_slug) if variant else []

    # digital twin deviations
    rva = twin.reference_vs_actual(session, variant_slug) if variant else None
    deviations = rva["deviations"] if rva else []

    # diagnostics — open cases with leading hypothesis + recommended test
    cases = []
    if vehicle:
        for c in workbench.list_cases(session, vehicle.id):
            v = workbench.case_view(session, c["id"])
            cases.append({"code": c["code"] or f"#{c['id']}", "title": c["title"],
                          "status": c["status"], "leading": c.get("leading"),
                          "recommended_test": v.get("recommended_test") if v else None})

    # workshop — work orders + readiness
    work_orders = workshop.list_work_orders(session, vehicle.id) if vehicle else []

    # maintenance — due-engine projected into status buckets (against latest odometer)
    from . import service
    maintenance = service.maintenance_summary(session, vehicle.id) if vehicle else None

    # knowledge quality (scoped to this machine) + research tasks
    kq = knowledge.quality_report(session, variant_slug)
    research = knowledge.list_research_tasks(session, variant_slug=variant_slug)[:8]

    # telemetry channels
    from .tmodels import TelemetryChannel
    n_channels = session.scalar(select(func.count()).select_from(TelemetryChannel)) or 0

    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "variant": variant_slug,
        "vehicle": {"vin": vehicle.vin, "name": f"{vehicle.year} {vehicle.make} {vehicle.model}"}
        if vehicle else None,
        "reference": header,
        "systems": [{"slug": n["slug"], "name": n["name"],
                     "components": sum(_count_components(n))} for n in tree],
        "overlays": overlays,
        "twin": {"deviations": deviations, "count": len(deviations)},
        "diagnostics": {"open_cases": [c for c in cases if c["status"] in ("open", "investigating")],
                        "total_cases": len(cases)},
        "workshop": {"work_orders": work_orders,
                     "open": sum(1 for w in work_orders if w["status"] not in ("closed", "abandoned"))},
        "maintenance": maintenance,
        "knowledge": {"total_claims": kq["total"], "by_verification": kq["by_verification"],
                      "conflicts": kq["conflicts"], "gaps": kq["gaps"]},
        "research_tasks": research,
        "telemetry": {"channels": n_channels},
    }


def _count_components(node: dict) -> list[int]:
    yield len(node.get("components", []))
    for child in node.get("children", []):
        yield from _count_components(child)


def write_intel(session: Session, variant_slug: str = "focus-st", *, out: Path | None = None) -> Path:
    repo_root = Path(__file__).resolve().parent.parent.parent  # focus-st/
    out = out or (repo_root / "web" / "vehicles" / variant_slug / "intel.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_intel(session, variant_slug), indent=2))
    return out


def write_intel_all(session: Session) -> list[Path]:
    """Write intel.json for every commissioned machine (a linked vehicle_variant)."""
    from .models import Vehicle
    from .refmodels import VehicleVariant
    linked = {v.variant_id for v in session.scalars(select(Vehicle)) if v.variant_id}
    slugs = [vv.slug for vv in session.scalars(select(VehicleVariant)) if vv.id in linked]
    return [write_intel(session, slug) for slug in slugs]
