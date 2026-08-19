"""Operator CLI — the human side of the garage.

    python -m app.cli init                 # create schema (V1 + V2 additive)
    python -m app.cli seed [--if-empty]    # load the Focus ST
    python -m app.cli seed-ref             # load the V2 reference model
    python -m app.cli ref [--variant S]    # reference system → component tree
    python -m app.cli component <slug>     # a component: relationships + claims
    python -m app.cli claim <subj> <prop>  # a claim: evidence + resolved verdict
    python -m app.cli conflicts            # claims flagged as conflicting
    python -m app.cli vehicle              # show the tracked car
    python -m app.cli specs [--category X] # list graded specs
    python -m app.cli due --miles 62000    # maintenance-due report
    python -m app.cli ingest forscan scan.txt [--miles 61000]
    python -m app.cli dtc P0299            # find a code across sessions
    python -m app.cli parts "intercooler"  # retailer search links
    python -m app.cli receipt email.txt    # file a receipt as a proposal
    python -m app.cli export --miles 62000 # DB → MODS.md + garage.json
    python -m app.cli proposals            # review the approval queue
    python -m app.cli approve <id> --by "Brandon"
    python -m app.cli reject  <id> --by "Brandon" --reason "duplicate"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import select, text

from . import domain, service
from .db import engine, session_scope
from .models import Base, Dtc
from .parsers import ingest
from .seed import seed as seed_fn


def _print_rows(rows: list[dict]) -> None:
    if not rows:
        print("(none)")
        return
    for r in rows:
        print("  " + "  ".join(f"{k}={v}" for k, v in r.items() if v is not None))


def cmd_init(_: argparse.Namespace) -> int:
    # Prefer the canonical DDL (enums, checks) if present; fall back to ORM.
    db = Path(__file__).resolve().parent.parent / "db"
    schema = db / "schema.sql"
    if schema.exists():
        with engine.begin() as conn:
            conn.execute(text(schema.read_text()))
        print(f"Schema applied from {schema}")
        # V2 additive layer (reference model + provenance). Idempotent.
        schema_v2 = db / "schema_v2.sql"
        if schema_v2.exists():
            with engine.begin() as conn:
                conn.execute(text(schema_v2.read_text()))
            print(f"V2 schema applied from {schema_v2}")
    else:
        import app.refmodels  # noqa: F401 — register V2 tables on the Base
        Base.metadata.create_all(engine)
        print("Schema created from ORM metadata.")
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    with session_scope() as s:
        print(seed_fn(s, if_empty=args.if_empty))
    return 0


def cmd_seed_ref(_: argparse.Namespace) -> int:
    from .seed_ref import seed_reference
    with session_scope() as s:
        print(seed_reference(s))
    return 0


def _verdict_icon(verification: str, conflict: bool) -> str:
    if conflict:
        return "⚠️"
    return {"VEHICLE_VERIFIED": "🟢", "OEM_VERIFIED": "🔵",
            "CORROBORATED": "🟡", "UNVERIFIED": "⚪"}.get(verification, "·")


def cmd_ref(args: argparse.Namespace) -> int:
    from . import refservice as rs
    with session_scope() as s:
        hdr = rs.variant_header(s, args.variant)
        if hdr is None:
            print(f"No reference variant '{args.variant}'. Run: python -m app.cli seed-ref",
                  file=sys.stderr)
            return 1
        print(f"{hdr['manufacturer']} {hdr['platform']} "
              f"[{hdr['platform_code']}] → {hdr['name']} · {hdr['trim'] or ''} "
              f"· {hdr['market'] or ''} {hdr['years'] or ''}")
        if hdr["engine"]:
            e = hdr["engine"]
            print(f"  engine: {e['code']} · {e['displacement_cc']}cc {e['config']} · "
                  f"{e['aspiration']} · {e['power']} / {e['torque']}")
        if hdr["transmission"]:
            t = hdr["transmission"]
            print(f"  trans:  {t['code']} · {t['type']}")
        print()

        def walk(nodes: list[dict], depth: int = 0) -> None:
            for n in nodes:
                print("  " * depth + f"▸ {n['name']}")
                for c in n["components"]:
                    hint = f"  ({c['oem_hint']})" if c["oem_hint"] else ""
                    print("  " * (depth + 1) + f"· {c['name']}  [{c['slug']}]{hint}")
                walk(n["children"], depth + 1)

        walk(rs.system_tree(s, args.variant))
    return 0


def cmd_component(args: argparse.Namespace) -> int:
    from . import refservice as rs
    with session_scope() as s:
        c = rs.get_component(s, args.variant, args.slug)
        if c is None:
            print(f"No component '{args.slug}' on variant '{args.variant}'.", file=sys.stderr)
            return 1
        print(f"{c['name']}  [{c['slug']}] · system: {c['system']}")
        if c["description"]:
            print(f"  {c['description']}")
        if c["relationships"]:
            print("  relationships:")
            for r in c["relationships"]:
                note = f" — {r['note']}" if r["note"] else ""
                print(f"    {r['dir']} {r['relation']} {r['other']}{note}")
        if c["claims"]:
            print("  claims:")
            for cl in c["claims"]:
                u = f" {cl['unit']}" if cl["unit"] else ""
                icon = _verdict_icon(cl["verification"], cl["conflict"])
                print(f"    {icon} {cl['property']}: {cl['value']}{u}  "
                      f"({cl['verification']}, conf {cl['confidence']:.2f})")
    return 0


def cmd_claim(args: argparse.Namespace) -> int:
    from . import refservice as rs
    with session_scope() as s:
        c = rs.get_claim(s, args.subject, args.property)
        if c is None:
            print(f"No claim '{args.subject}/{args.property}'.", file=sys.stderr)
            return 1
        u = f" {c['unit']}" if c["unit"] else ""
        icon = _verdict_icon(c["verification"], c["conflict"])
        print(f"{icon} {c['subject_type']}:{c['subject_key']} · {c['property']} = {c['value']}{u}")
        r = c["resolved"]
        print(f"  verdict:  {r['verification']} · confidence {r['confidence']} "
              f"· {'CONFLICT' if r['conflict'] else 'no conflict'}")
        print(f"  {r['rationale']}")
        if c["applicability"]:
            print(f"  applies:  {c['applicability']}")
        print("  evidence:")
        for e in c["evidence"]:
            stance = {"supports": "＋", "contradicts": "－", "supersedes": "↻"}.get(e["stance"], "?")
            veh = " [on-vehicle]" if e["on_vehicle"] else ""
            print(f"    {stance} auth {e['authority']} · {e['label']}{veh}")
    return 0


def cmd_conflicts(_: argparse.Namespace) -> int:
    from . import refservice as rs
    with session_scope() as s:
        rows = rs.list_conflicts(s)
        if not rows:
            print("No conflicting claims on record. 🟢")
            return 0
        print(f"{len(rows)} conflicting claim(s):")
        for c in rows:
            u = f" {c['unit']}" if c["unit"] else ""
            print(f"  ⚠️ {c['subject_type']}:{c['subject_key']} · {c['property']} = "
                  f"{c['value']}{u}  ({c['verification']})")
            if c["notes"]:
                print(f"      {c['notes']}")
    return 0


def cmd_vehicle(_: argparse.Namespace) -> int:
    with session_scope() as s:
        v = service.get_vehicle(s)
        print(f"{v.year} {v.make} {v.model} {v.trim}  VIN {v.vin}")
        print(f"  {v.engine} · {v.transmission}")
        if v.notes:
            print(f"  {v.notes}")
    return 0


def cmd_specs(args: argparse.Namespace) -> int:
    from .models import Spec
    with session_scope() as s:
        v = service.get_vehicle(s)
        stmt = select(Spec).where(Spec.vehicle_id == v.id)
        if args.category:
            stmt = stmt.where(Spec.category == args.category)
        for r in s.scalars(stmt.order_by(Spec.category, Spec.name)):
            u = f" {r.unit}" if r.unit else ""
            print(f"  [{r.category}] {r.name}: {r.value}{u}  ({r.verification})")
    return 0


def cmd_due(args: argparse.Namespace) -> int:
    icon = {"overdue": "🔴", "due-soon": "🟡", "ok": "🟢", "unknown": "⚪"}
    with session_scope() as s:
        v = service.get_vehicle(s)
        rows = service.due_list(s, v.id, current_miles=args.miles)
        for r in rows:
            print(f"  {icon.get(r['status'], '·')} {r['item']:<40} {r['status']:<9} {r['detail']}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    content = Path(args.file).read_bytes()
    with session_scope() as s:
        v = service.get_vehicle(s)
        res = ingest(s, v.id, args.kind, content, miles=args.miles, note=args.note)
    print(res)
    return 0


def cmd_sessions(args: argparse.Namespace) -> int:
    with session_scope() as s:
        v = service.get_vehicle(s)
        for r in service.list_sessions(s, v.id):
            print(f"  #{r['id']} {r['kind']:<8} dtcs={r['dtcs']} meas={r['measurements']} "
                  f"can={r['can_frames']}  {r['ingested_at'] or ''}")
    return 0


def cmd_summary(args: argparse.Namespace) -> int:
    icon = {"warn": "🟡", "info": "·"}
    with session_scope() as s:
        try:
            summ = service.session_summary(s, args.id)
        except LookupError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    print(f"Session #{summ['session_id']} ({summ['kind']}) · {summ['samples']} samples · "
          f"{summ['channels_recorded']} channels · {summ['duration_s']}s")
    for f in summ["findings"]:
        print(f"  {icon.get(f['level'], '·')} {f['text']}")
    if not summ["findings"]:
        print("  (no measurements to analyze — is this a datalog session?)")
    return 0


def cmd_dtc(args: argparse.Namespace) -> int:
    with session_scope() as s:
        rows = s.scalars(select(Dtc).where(Dtc.code == args.code.upper())).all()
        if not rows:
            print(f"No occurrences of {args.code.upper()} on record.")
            return 0
        for r in rows:
            print(f"  session {r.session_id}: {r.code}  module={r.module}  "
                  f"status={r.status}  {r.description or ''}")
    return 0


def cmd_parts(args: argparse.Namespace) -> int:
    for retailer, url in domain.parts_search_links(args.query, part_number=args.part_number).items():
        print(f"  {retailer:<10} {url}")
    return 0


def cmd_receipt(args: argparse.Namespace) -> int:
    import json
    raw = Path(args.file).read_text()
    payload: dict | str
    if args.file.endswith(".json"):
        payload = json.loads(raw)
    else:
        payload = raw
    with session_scope() as s:
        v = service.get_vehicle(s)
        res = service.propose_from_receipt(s, v.id, payload, proposed_by="cli")
    print(f"Filed proposal #{res['proposal_id']} as {res['classified_as']} "
          f"(vendor {res['receipt']['vendor']}, total {res['receipt']['total']}).")
    print(f"  patch: {res['patch']}")
    print("  Approve with:  python -m app.cli approve "
          f"{res['proposal_id']} --by \"<name>\"")
    return 0


def cmd_recalls(args: argparse.Namespace) -> int:
    icon = {"completed": "✅", "open": "🔴", "unknown": "⚪"}
    with session_scope() as s:
        v = service.get_vehicle(s)
        if args.refresh:
            res = service.refresh_recalls(s, v, live=not args.offline)
            print(f"Refreshed: known={res['known_seeded']} nhtsa={res['nhtsa_fetched']}"
                  + (f" (NHTSA: {res['error']})" if res["error"] else ""))
        for r in service.list_recalls(s, v.id):
            print(f"  {icon.get(r['status'], '·')} [{r['campaign_number']}] "
                  f"{r['component'] or ''} — {r['status']} ({r['origin']})")
            if r["summary"]:
                print(f"      {r['summary'][:110]}")
    return 0


def cmd_recall_status(args: argparse.Namespace) -> int:
    with session_scope() as s:
        v = service.get_vehicle(s)
        try:
            service.set_recall_status(s, v.id, args.campaign, args.status)
        except (LookupError, ValueError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    print(f"{args.campaign} → {args.status}")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    from pathlib import Path as _P

    from .export import write_export
    with session_scope() as s:
        v = service.get_vehicle(s)
        out = _P(args.out) if args.out else None
        res = write_export(s, v.id, current_miles=args.miles,
                           repo_root=out, json_dir=out)
    print(f"Wrote {res['mods_md']}")
    print(f"Wrote {res['garage_json']}")
    print(f"  {res['mods']} mods · total spend ${res['total_cost']:,.2f}")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    """Export, then git add/commit/push the two published artifacts so the Pages
    dashboard updates. Only stages garage.json + MODS.md."""
    import subprocess
    from pathlib import Path as _P

    from .export import write_export
    repo = _P(__file__).resolve().parent.parent.parent  # focus-st/
    with session_scope() as s:
        v = service.get_vehicle(s)
        res = write_export(s, v.id, current_miles=args.miles)
    files = [res["mods_md"], res["garage_json"]]

    def git(*a):
        return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)

    git("add", *files)
    status = git("status", "--porcelain", *files).stdout.strip()
    if not status:
        print("Nothing changed — dashboard already current.")
        return 0
    msg = args.message or "chore(garage): refresh published snapshot"
    c = git("commit", "-m", msg, *files)
    if c.returncode != 0:
        print(f"commit failed:\n{c.stderr or c.stdout}", file=sys.stderr)
        return 1
    print("Committed:", msg)
    if args.push:
        p = git("push")
        if p.returncode != 0:
            print(f"push failed:\n{p.stderr or p.stdout}", file=sys.stderr)
            return 1
        print("Pushed.")
    else:
        print("Skipped push (--push to publish to Pages).")
    return 0


def cmd_proposals(args: argparse.Namespace) -> int:
    with session_scope() as s:
        rows = service.list_proposals(s, status=args.status)
        if not rows:
            print("(no proposals)")
            return 0
        for p in rows:
            print(f"  #{p['id']} [{p['status']}] {p['op']} {p['entity']} "
                  f"by {p['proposed_by']}")
            print(f"      patch: {p['patch']}")
            if p["rationale"]:
                print(f"      why:   {p['rationale']}")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    with session_scope() as s:
        try:
            res = service.approve_proposal(s, args.id, args.by)
            export = service.maybe_autoexport(s, service.get_vehicle(s).id)
        except (LookupError, ValueError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    print(f"Approved #{res['proposal_id']} → {res['entity']} #{res['applied_id']} "
          f"(by {res['approved_by']})")
    if export and not export.get("error"):
        print(f"  ↳ auto-exported {export['garage_json']} + MODS.md")
    elif export and export.get("error"):
        print(f"  ↳ auto-export skipped: {export['error']}")
    return 0


def cmd_reject(args: argparse.Namespace) -> int:
    with session_scope() as s:
        try:
            service.reject_proposal(s, args.id, args.by, args.reason)
        except (LookupError, ValueError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    print(f"Rejected #{args.id}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="app.cli", description="Digital Garage operator CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create the schema").set_defaults(fn=cmd_init)

    sp = sub.add_parser("seed", help="load the Focus ST")
    sp.add_argument("--if-empty", action="store_true", help="skip if the vehicle already exists")
    sp.set_defaults(fn=cmd_seed)

    sub.add_parser("seed-ref", help="seed the V2 reference model (Focus ST)").set_defaults(fn=cmd_seed_ref)

    sp = sub.add_parser("ref", help="show a variant's reference system tree")
    sp.add_argument("--variant", default="focus-st")
    sp.set_defaults(fn=cmd_ref)

    sp = sub.add_parser("component", help="show a component: relationships + claims")
    sp.add_argument("slug")
    sp.add_argument("--variant", default="focus-st")
    sp.set_defaults(fn=cmd_component)

    sp = sub.add_parser("claim", help="show a claim with evidence + resolved verdict")
    sp.add_argument("subject", help="subject_key (e.g. 'lubrication', 'focus-st')")
    sp.add_argument("property", help="property (e.g. 'oil_capacity')")
    sp.set_defaults(fn=cmd_claim)

    sub.add_parser("conflicts", help="list claims flagged as conflicting").set_defaults(fn=cmd_conflicts)

    sub.add_parser("vehicle", help="show the tracked vehicle").set_defaults(fn=cmd_vehicle)

    sp = sub.add_parser("specs", help="list graded specs")
    sp.add_argument("--category")
    sp.set_defaults(fn=cmd_specs)

    sp = sub.add_parser("due", help="maintenance-due report")
    sp.add_argument("--miles", type=int, default=None)
    sp.set_defaults(fn=cmd_due)

    sp = sub.add_parser("ingest", help="ingest a diagnostic artifact")
    sp.add_argument("kind", choices=["forscan", "candump", "datalog"])
    sp.add_argument("file")
    sp.add_argument("--miles", type=int, default=None)
    sp.add_argument("--note", default=None)
    sp.set_defaults(fn=cmd_ingest)

    sp = sub.add_parser("dtc", help="find a DTC across sessions")
    sp.add_argument("code")
    sp.set_defaults(fn=cmd_dtc)

    sub.add_parser("sessions", help="list ingested diagnostic sessions").set_defaults(fn=cmd_sessions)

    sp = sub.add_parser("summary", help="summarize a datalog session")
    sp.add_argument("id", type=int)
    sp.set_defaults(fn=cmd_summary)

    sp = sub.add_parser("parts", help="retailer search links")
    sp.add_argument("query")
    sp.add_argument("--part-number", default=None)
    sp.set_defaults(fn=cmd_parts)

    sp = sub.add_parser("receipt", help="file a receipt (.txt/.json) as a proposal")
    sp.add_argument("file")
    sp.set_defaults(fn=cmd_receipt)

    sp = sub.add_parser("recalls", help="list/refresh recall campaigns")
    sp.add_argument("--refresh", action="store_true", help="re-seed known + fetch NHTSA")
    sp.add_argument("--offline", action="store_true", help="with --refresh, skip the NHTSA fetch")
    sp.set_defaults(fn=cmd_recalls)

    sp = sub.add_parser("recall-status", help="mark a recall completed/open/unknown")
    sp.add_argument("campaign")
    sp.add_argument("status", choices=["unknown", "open", "completed"])
    sp.set_defaults(fn=cmd_recall_status)

    sp = sub.add_parser("export", help="export DB → MODS.md + garage.json")
    sp.add_argument("--miles", type=int, default=None)
    sp.add_argument("--out", default=None, help="output dir (default: repo root for MODS.md, data/export for json)")
    sp.set_defaults(fn=cmd_export)

    sp = sub.add_parser("publish", help="export + git commit/push the snapshot")
    sp.add_argument("--miles", type=int, default=None)
    sp.add_argument("--message", default=None)
    sp.add_argument("--push", action="store_true", help="also push to origin")
    sp.set_defaults(fn=cmd_publish)

    sp = sub.add_parser("proposals", help="review the approval queue")
    sp.add_argument("--status", default="pending")
    sp.set_defaults(fn=cmd_proposals)

    sp = sub.add_parser("approve", help="approve a proposal (human)")
    sp.add_argument("id", type=int)
    sp.add_argument("--by", required=True, help="approver name")
    sp.set_defaults(fn=cmd_approve)

    sp = sub.add_parser("reject", help="reject a proposal")
    sp.add_argument("id", type=int)
    sp.add_argument("--by", default="")
    sp.add_argument("--reason", default=None)
    sp.set_defaults(fn=cmd_reject)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
