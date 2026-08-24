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

    # degradation trends — fitted over the observation history
    from . import trends as trends_mod
    trend_rows = trends_mod.component_trends(session, vehicle.id) if vehicle else []

    # parts fitment — catalog slots resolved against the reference component graph
    from . import fitment as fitment_mod
    fit = fitment_mod.catalog_fitment(session, variant_slug) if variant else None

    # knowledge quality (scoped to this machine) + research tasks
    kq = knowledge.quality_report(session, variant_slug)
    research = knowledge.list_research_tasks(session, variant_slug=variant_slug)[:8]

    # telemetry channels
    from .tmodels import TelemetryChannel
    n_channels = session.scalar(select(func.count()).select_from(TelemetryChannel)) or 0

    # universal-search index — components + this machine's claims, flat and self-contained
    search_index = _search_index(session, variant_slug, tree) if variant else {"components": [], "claims": []}

    # engine-bay navigator — component adjacency across the overlays (airflow/coolant/lube),
    # so the cockpit can draw the interactive system map offline
    graph = _graph_block(session, variant_slug, overlays, tree) if variant else {"domains": [], "nodes": [], "edges": []}

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
        "trends": {"series": trend_rows, "drifting": sum(1 for t in trend_rows if t["drift"])},
        "parts": {"slots": fit["slots"], "matched": fit["matched"], "confident": fit["confident"],
                  "unmatched": fit["unmatched"], "coverage_pct": fit["coverage_pct"],
                  "unmatched_slots": fit["unmatched_slots"][:12]} if fit else None,
        "knowledge": {"total_claims": kq["total"], "by_verification": kq["by_verification"],
                      "conflicts": kq["conflicts"], "gaps": kq["gaps"]},
        "research_tasks": research,
        "telemetry": {"channels": n_channels},
        "search_index": search_index,
        "graph": graph,
    }


def _search_index(session: Session, variant_slug: str, tree: list[dict]) -> dict:
    """A compact, self-contained index for the dashboard's universal search: the
    machine's reference components (with their system) and its graded claims. DTC codes
    are global, so the client loads those from the shared code database itself."""
    from .refmodels import Claim

    components = []
    for node in tree:
        _collect_components(node, node.get("name", ""), components)

    claims = []
    for c in session.scalars(select(Claim).where(
            Claim.applicability["variant"].astext == variant_slug)):
        claims.append({"subject_type": c.subject_type, "subject_key": c.subject_key,
                       "prop": c.prop, "value": c.value, "unit": c.unit,
                       "verification": c.verification})
    return {"components": components, "claims": claims}


def _graph_block(session: Session, variant_slug: str, overlays: list[str],
                 tree: list[dict]) -> dict:
    """The component-adjacency graph for the engine-bay navigator: every overlay's edges
    tagged by domain, plus the node set they connect (slug + name + system). The client
    draws the map and filters by domain entirely offline — no per-domain fetch."""
    from . import graphs

    # each component's system name, from the reference tree
    comps: list[dict] = []
    for node in tree:
        _collect_components(node, node.get("name", ""), comps)
    sys_of = {c["slug"]: c["system"] for c in comps if c.get("slug")}

    edges: list[dict] = []
    node_meta: dict[str, dict] = {}
    for domain in overlays:
        for e in graphs.overlay_edges(session, variant_slug, domain):
            edges.append({"from": e["from"], "to": e["to"], "domain": domain,
                          "relation": e["relation"], "medium": e["medium"],
                          "direction": e["direction"]})
            node_meta.setdefault(e["from"], {"slug": e["from"], "name": e["from_name"]})
            node_meta.setdefault(e["to"], {"slug": e["to"], "name": e["to_name"]})

    nodes = [{"slug": n["slug"], "name": n["name"], "system": sys_of.get(n["slug"])}
             for n in node_meta.values()]
    return {"domains": overlays, "nodes": nodes, "edges": edges}


def _collect_components(node: dict, system_name: str, out: list[dict]) -> None:
    for comp in node.get("components", []):
        out.append({"slug": comp.get("slug"), "name": comp.get("name"), "system": system_name})
    for child in node.get("children", []):
        _collect_components(child, child.get("name", system_name), out)


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


def write_intel_all(session: Session, *, out_dir: Path | None = None) -> list[Path]:
    """Write intel.json for every commissioned machine (a linked vehicle_variant). Pass
    `out_dir` to write under a scratch tree (`<out_dir>/<slug>/intel.json`) instead of the
    repo — tests use it so running the suite never clobbers the published projections."""
    from .models import Vehicle
    from .refmodels import VehicleVariant
    linked = {v.variant_id for v in session.scalars(select(Vehicle)) if v.variant_id}
    slugs = [vv.slug for vv in session.scalars(select(VehicleVariant)) if vv.id in linked]
    return [write_intel(session, slug,
                        out=(out_dir / slug / "intel.json") if out_dir else None)
            for slug in slugs]
