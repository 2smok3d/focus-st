"""Operator CLI — the human side of the garage.

    python -m app.cli init                 # create schema
    python -m app.cli seed [--if-empty]    # load the Focus ST
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
    schema = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
    if schema.exists():
        with engine.begin() as conn:
            conn.execute(text(schema.read_text()))
        print(f"Schema applied from {schema}")
    else:
        Base.metadata.create_all(engine)
        print("Schema created from ORM metadata.")
    return 0


def cmd_seed(args: argparse.Namespace) -> int:
    with session_scope() as s:
        print(seed_fn(s, if_empty=args.if_empty))
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
        except (LookupError, ValueError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
    print(f"Approved #{res['proposal_id']} → {res['entity']} #{res['applied_id']} "
          f"(by {res['approved_by']})")
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

    sub.add_parser("vehicle", help="show the tracked vehicle").set_defaults(fn=cmd_vehicle)

    sp = sub.add_parser("specs", help="list graded specs")
    sp.add_argument("--category")
    sp.set_defaults(fn=cmd_specs)

    sp = sub.add_parser("due", help="maintenance-due report")
    sp.add_argument("--miles", type=int, default=None)
    sp.set_defaults(fn=cmd_due)

    sp = sub.add_parser("ingest", help="ingest a diagnostic artifact")
    sp.add_argument("kind", choices=["forscan", "candump"])
    sp.add_argument("file")
    sp.add_argument("--miles", type=int, default=None)
    sp.add_argument("--note", default=None)
    sp.set_defaults(fn=cmd_ingest)

    sp = sub.add_parser("dtc", help="find a DTC across sessions")
    sp.add_argument("code")
    sp.set_defaults(fn=cmd_dtc)

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
