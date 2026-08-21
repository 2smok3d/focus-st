"""Operator CLI — the human side of the garage.

    python -m app.cli init                 # create schema (V1 + V2 additive)
    python -m app.cli seed [--if-empty]    # load the Focus ST
    python -m app.cli seed-ref             # load the V2 reference model
    python -m app.cli migrate-specs        # migrate V1 specs → V2 claims (non-destructive)
    python -m app.cli migrate-knowledge    # migrate V1 maintenance + issues + recalls → claims
    python -m app.cli commission [machine] # baseline-commission a machine (or 'all')
    python -m app.cli fleet                # fleet overview across all machines
    python -m app.cli seed-twin            # seed the digital twin from on-vehicle facts
    python -m app.cli twin [--variant S]   # reference-vs-actual component state
    python -m app.cli dx-seed              # seed the worked diagnostic case (low boost)
    python -m app.cli cases                # list diagnostic cases
    python -m app.cli case <id>            # the diagnostic workbench view
    python -m app.cli dx-test <id> <result> # record a test result → re-ranks hypotheses
    python -m app.cli obs-seed             # seed an example Observation V2 (compression)
    python -m app.cli observations         # list observations (rich, unit-aware)
    python -m app.cli config-at            # the machine's configuration now (a projection)
    python -m app.cli events               # the append-only machine-event ledger
    python -m app.cli seed-graph           # seed typed graph overlays (airflow/coolant/…)
    python -m app.cli overlay [domain]     # show a graph overlay (--trace <slug> to follow flow)
    python -m app.cli pc-seed / pc <code>  # physical-component lifecycle
    python -m app.cli seed-diaglib         # seed the failure-mode + diagnostic-test library
    python -m app.cli symptom "<text>"     # symptom → candidate failure modes + best next test
    python -m app.cli dx-open "<symptom>"  # open a case from a symptom (auto-seeds candidates)
    python -m app.cli failure-mode <slug>  # a failure mode + its discriminating tests
    python -m app.cli next-test <fm>… [--done …] # rank next tests by info-gain utility
    python -m app.cli wo-seed              # seed an example work order (job readiness)
    python -m app.cli work-orders / wo <id> # list / show work orders
    python -m app.cli wo-verify <id> <test> pass|fail  # post-repair verification
    python -m app.cli seed-channels        # seed the telemetry channel registry
    python -m app.cli telemetry <sid> [--case N] # detect datalog events → case evidence
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
        for extra in ("schema_v2.sql", "schema_v3.sql", "schema_v4.sql", "schema_v5.sql",
                      "schema_v6.sql", "schema_v7.sql", "schema_v8.sql", "schema_v9.sql",
                      "schema_v10.sql"):
            path = db / extra
            if path.exists():
                with engine.begin() as conn:
                    conn.execute(text(path.read_text()))
                print(f"Additive schema applied from {path}")
    else:
        import app.refmodels  # noqa: F401 — register V2 tables on the Base
        import app.twinmodels  # noqa: F401 — register V3 tables on the Base
        import app.dxmodels  # noqa: F401 — register V4 tables on the Base
        import app.obsmodels  # noqa: F401 — register V5 tables on the Base
        import app.lcmodels  # noqa: F401 — register V7 tables on the Base
        import app.fmmodels  # noqa: F401 — register V8 tables on the Base
        import app.womodels  # noqa: F401 — register V9 tables on the Base
        import app.tmodels  # noqa: F401 — register V10 tables on the Base
        Base.metadata.create_all(engine)  # V6 columns/tables live in refmodels (already imported)
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


def cmd_migrate_specs(args: argparse.Namespace) -> int:
    from .migrate_specs import migrate_specs_to_claims
    with session_scope() as s:
        print(migrate_specs_to_claims(s, args.variant))
    return 0


def cmd_migrate_knowledge(args: argparse.Namespace) -> int:
    from .migrate_knowledge import migrate_knowledge
    with session_scope() as s:
        print(migrate_knowledge(s, args.variant))
    return 0


def cmd_seed_graph(args: argparse.Namespace) -> int:
    from .seed_graph import seed_graph
    with session_scope() as s:
        print(seed_graph(s, args.variant))
    return 0


def cmd_seed_diaglib(_: argparse.Namespace) -> int:
    from .seed_diaglib import seed_diaglib
    with session_scope() as s:
        print(seed_diaglib(s))
    return 0


def cmd_seed_channels(_: argparse.Namespace) -> int:
    from . import telemetry
    with session_scope() as s:
        print(telemetry.seed_channels(s))
    return 0


def cmd_telemetry(args: argparse.Namespace) -> int:
    from . import telemetry
    sev = {"info": "·", "warn": "🟠", "critical": "🔴"}
    with session_scope() as s:
        events = telemetry.run_pipeline(s, args.session_id)
        if not events:
            print(f"No telemetry events detected on session #{args.session_id}.")
            return 0
        print(f"Telemetry events · session #{args.session_id}:")
        for e in events:
            span = f"{e['t_start']:g}–{e['t_end']:g}s" if e["t_start"] is not None else ""
            print(f"  {sev.get(e['severity'], '·')} {e['kind']} {span}  {e['detail']}")
        if args.case:
            from .workbench import case_view
            from .dxmodels import DiagnosticCase
            case = s.get(DiagnosticCase, args.case)
            if case is not None:
                n = telemetry.events_to_case(s, case, events)
                print(f"  ↳ attached {n} event(s) to case #{args.case} as evidence.")
    return 0


def cmd_failure_mode(args: argparse.Namespace) -> int:
    from . import diaglib
    with session_scope() as s:
        fm = diaglib.failure_mode(s, args.slug)
        if fm is None:
            print(f"No failure mode '{args.slug}'.", file=sys.stderr)
            return 1
        print(f"{fm['name']}  [{fm['slug']}] · {fm['system']} · severity {fm['severity']}")
        if fm["description"]:
            print(f"  {fm['description']}")
        print(f"  components: {', '.join(fm['components'])}")
        print(f"  expect:     {fm['expected_observations']}")
        print(f"  rules out:  {fm['disconfirming_evidence']}")
        print(f"  consequence: {fm['consequences']}")
        if fm["tests"]:
            print("  discriminating tests:")
            for t in fm["tests"]:
                print(f"    · {t['name']}  (info {t['info_gain']}, cost {t['cost']}, risk {t['risk']})")
    return 0


def cmd_symptom(args: argparse.Namespace) -> int:
    from . import diaglib
    with session_scope() as s:
        cands = diaglib.candidates_for_symptom(s, args.text)
        if not cands:
            print("No candidate failure modes matched.")
            return 0
        slugs = [c["slug"] for c in cands]
        print(f"Candidate failure modes for “{args.text}”:")
        for c in cands:
            print(f"  · {c['name']}  [{c['slug']}] · {c['system']}  (match {c['match']})")
        rec = diaglib.recommend_next_test(s, slugs)
        if rec:
            best = rec[0]
            print(f"\n  ▸ best next test: {best['name']}  "
                  f"(utility {best['utility']} · info {best['info_gain']}, cost {best['cost']}, risk {best['risk']})")
            if best["purpose"]:
                print(f"      {best['purpose']}")
            if len(rec) > 1:
                print("    then: " + "; ".join(f"{r['name']} ({r['utility']})" for r in rec[1:4]))
    return 0


def cmd_next_test(args: argparse.Namespace) -> int:
    from . import diaglib
    with session_scope() as s:
        rec = diaglib.recommend_next_test(s, args.candidates, args.done)
        if not rec:
            print("(no pending tests for those candidates)")
            return 0
        print("Next-test ranking (highest information-gain utility first):")
        for r in rec:
            print(f"  {r['utility']:>5}  {r['name']}  → {r['discriminates']}  "
                  f"(info {r['info_gain']}, cost {r['cost']}, risk {r['risk']})")
    return 0


def cmd_pc_seed(_: argparse.Namespace) -> int:
    """Seed a physical-component lifecycle example: a TZ250 piston through a race weekend."""
    from sqlalchemy import select as _select
    from . import lifecycle as lc
    from .models import Vehicle
    with session_scope() as s:
        tz = s.scalar(_select(Vehicle).where(Vehicle.vin == "YAM-TZ250-1986"))
        if tz is None:
            print("Commission the TZ250 first (`commission tz250`).", file=sys.stderr)
            return 1
        pc = lc.register(s, "P-0042", "TZ250 right piston", component_slug="pistons",
                         manufacturer="Yamaha", part_number="—")
        lc.install(s, pc, tz, "pistons", note="Fresh top-end")
        lc.add_usage(s, pc, hours=4.7, sessions=3)
        lc.inspect(s, pc, "healthy", value=0.05, unit="mm", method="ring end-gap", note="within spec")
        print(f"Seeded physical component {pc.code} on TZ250 · {pc.hours}h / {pc.sessions} sessions.")
    return 0


def cmd_pc(args: argparse.Namespace) -> int:
    from . import lifecycle as lc
    with session_scope() as s:
        d = lc.lifecycle(s, args.code)
        if d is None:
            print(f"No physical component '{args.code}'.", file=sys.stderr)
            return 1
        u = d["usage"]
        print(f"{d['code']} · {d['name']}  [{d['status']} · {d['condition']}]")
        print(f"  usage: {u['hours']}h · {u['sessions']} sessions · {u['miles']} mi · {u['cycles']} cycles")
        print("  installations:")
        for i in d["installations"]:
            span = f"{i['installed_at']}" + (f" → {i['removed_at']}" if i["removed_at"] else " → (current)")
            print(f"    · {i['vehicle']} / {i['slot']}  {span}")
        if d["inspections"]:
            print("  inspections:")
            for ins in d["inspections"]:
                val = f" {ins['value']} {ins['unit']}" if ins["value"] is not None else ""
                print(f"    · {ins['result']}{val}  ({ins['method'] or ''})  {ins['at']}")
    return 0


def cmd_overlay(args: argparse.Namespace) -> int:
    from . import graphs
    with session_scope() as s:
        if not args.domain:
            print("overlays present: " + ", ".join(graphs.domains(s, args.variant)))
            return 0
        edges = graphs.overlay_edges(s, args.variant, args.domain)
        if not edges:
            print(f"No '{args.domain}' overlay for {args.variant}. "
                  f"Present: {', '.join(graphs.domains(s, args.variant))}", file=sys.stderr)
            return 1
        arrow = {"forward": "→", "bidirectional": "↔"}
        print(f"{args.domain} overlay · {args.variant}:")
        for e in edges:
            med = f" [{e['medium']}]" if e["medium"] else ""
            print(f"    {e['from_name']} {arrow.get(e['direction'], '→')} {e['to_name']}"
                  f"  ({e['relation']}{med})")
        if args.trace:
            path = graphs.trace(s, args.variant, args.domain, args.trace)
            print(f"  trace from {args.trace}: " + " → ".join(path))
    return 0


def cmd_commission(args: argparse.Namespace) -> int:
    from .commission import MACHINES, commission_all, commission_machine
    with session_scope() as s:
        if args.machine in (None, "all"):
            for line in commission_all(s):
                print(line)
        elif args.machine in MACHINES:
            print(commission_machine(s, args.machine))
        else:
            print(f"Unknown machine '{args.machine}'. Known: {', '.join(MACHINES)}, all",
                  file=sys.stderr)
            return 1
    return 0


def cmd_fleet(_: argparse.Namespace) -> int:
    from .models import Vehicle
    from .refmodels import VehicleVariant
    from . import twin
    with session_scope() as s:
        vehicles = s.scalars(select(Vehicle).order_by(Vehicle.id)).all()
        print(f"Fleet · {len(vehicles)} machine(s)")
        for v in vehicles:
            variant = s.get(VehicleVariant, v.variant_id) if v.variant_id else None
            states = twin.current_states(s, v.id)
            devs = sum(1 for st in states.values() if st.condition in twin.NOTABLE_CONDITIONS)
            link = f"→ {variant.slug}" if variant else "(unlinked)"
            print(f"  {v.year} {v.make} {v.model} · {v.vin}  {link}")
            print(f"      states tracked={len(states)} · deviations={devs} · {v.notes or ''}")
    return 0


def cmd_dx_seed(args: argparse.Namespace) -> int:
    from .workbench import seed_example_case
    with session_scope() as s:
        print(seed_example_case(s, args.variant))
    return 0


def cmd_wo_seed(_: argparse.Namespace) -> int:
    """Seed a water-pump work order that is READY 80% (a crush washer missing)."""
    from . import service, workshop
    with session_scope() as s:
        v = service.get_vehicle(s)
        wo = workshop.open_work_order(s, v, "Water pump replacement", code="WO-0001",
                                      component_slug="water-pump")
        for i, t in enumerate(["Drain coolant", "Remove belt + pulley", "Remove old pump",
                               "Install new pump + gasket", "Refill + bleed"]):
            workshop.add_task(s, wo, t, seq=i)
        workshop.add_part(s, wo, "Water pump", part_number="MC-WP-2.0", available=True)
        workshop.add_part(s, wo, "Coolant (Motorcraft Orange)", available=True)
        workshop.add_part(s, wo, "Pump gasket", available=True)
        workshop.add_part(s, wo, "Crush washer", available=False)   # the blocker
        workshop.add_tool(s, wo, "Socket set", available=True)
        workshop.add_tool(s, wo, "Torque wrench", available=True)
        workshop.mark_ready(s, wo)
        r = workshop.job_readiness(s, wo.id)
        print(f"Seeded {wo.code} '{wo.title}' → status {wo.status.upper()} · READY {r['ready_pct']}%")
        if r["blockers"]:
            print("  blockers: " + "; ".join(r["blockers"]))
    return 0


def cmd_work_orders(_: argparse.Namespace) -> int:
    from . import service, workshop
    icon = {"draft": "○", "ready": "🟢", "blocked": "🔴", "in_progress": "🟡",
            "verification_required": "🟠", "verified": "🔵", "closed": "✅", "abandoned": "⚫"}
    with session_scope() as s:
        v = service.get_vehicle(s)
        rows = workshop.list_work_orders(s, v.id)
        if not rows:
            print("(no work orders — try `wo-seed`)")
            return 0
        for w in rows:
            handle = w["code"] or f"#{w['id']}"
            print(f"  {icon.get(w['status'], '·')} {handle}  {w['title']}  "
                  f"[{w['status']} · {w['repair_state']}]  READY {w['ready_pct']}%")
    return 0


def cmd_wo(args: argparse.Namespace) -> int:
    from . import workshop
    with session_scope() as s:
        w = workshop.work_order_view(s, args.id)
        if w is None:
            print(f"No work order #{args.id}.", file=sys.stderr)
            return 1
        print(f"{w['code'] or '#'+str(w['id'])} · {w['title']}  [{w['status']} · {w['repair_state']}]")
        r = w["readiness"]
        print(f"  READY {r['ready_pct']}%  ({r['satisfied']}/{r['items']})")
        if r["blockers"]:
            for b in r["blockers"]:
                print(f"    ✕ {b}")
        print("  tasks:")
        for t in w["tasks"]:
            print(f"    {'☑' if t['done'] else '☐'} {t['description']}")
        if w["verifications"]:
            print("  verifications:")
            for vf in w["verifications"]:
                print(f"    · {vf['test']}: {vf['result']}")
    return 0


def cmd_wo_verify(args: argparse.Namespace) -> int:
    from . import workshop
    from .womodels import WorkOrder
    with session_scope() as s:
        wo = s.get(WorkOrder, args.id)
        if wo is None:
            print(f"No work order #{args.id}.", file=sys.stderr)
            return 1
        try:
            workshop.verify(s, wo, args.test, args.result, note=args.note)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        print(f"Recorded verification '{args.test}' → {args.result}. "
              f"Work order now {wo.status.upper()} ({wo.repair_state}).")
    return 0


def cmd_dx_open(args: argparse.Namespace) -> int:
    from . import service, workbench
    with session_scope() as s:
        v = service.get_vehicle(s)
        case = workbench.open_case_from_symptom(s, v, args.symptom)
        view = workbench.case_view(s, case.id)
        print(f"Opened case #{case.id} · “{args.symptom}”")
        print("  candidate failure modes (hypotheses):")
        for h in view["hypotheses"]:
            print(f"    · {h['description']}  [{h['key']}]  support {h['support']:.0%}")
        if view["recommended_test"]:
            print(f"  ▸ best next test: {view['recommended_test']}")
    return 0


def cmd_cases(_: argparse.Namespace) -> int:
    from . import workbench
    icon = {"open": "🔵", "investigating": "🟡", "resolved": "🟢", "abandoned": "⚫"}
    with session_scope() as s:
        rows = workbench.list_cases(s)
        if not rows:
            print("(no diagnostic cases — try `dx-seed`)")
            return 0
        for c in rows:
            handle = c["code"] or f"#{c['id']}"
            sup = f" · leading {c['leading']} ({c['support']:.0%})" if c["leading"] else ""
            print(f"  {icon.get(c['status'], '·')} {handle}  {c['title']}  [{c['status']}]{sup}")
    return 0


def cmd_case(args: argparse.Namespace) -> int:
    from . import workbench
    ricon = {"pass": "✅", "fail": "🔴", "pending": "○", "inconclusive": "◐"}
    with session_scope() as s:
        v = workbench.case_view(s, args.id)
        if v is None:
            print(f"No case #{args.id}.", file=sys.stderr)
            return 1
        print(f"{v['code'] or '#'+str(v['id'])} · {v['title']}  [{v['status']}]")
        if v["symptoms"]:
            print("  symptoms: " + "; ".join(v["symptoms"]))
        if v["known_data"]:
            print("  known data:")
            for e in v["known_data"]:
                comp = f" → {e['component']}" if e["component"] else ""
                print(f"    · [{e['kind']}] {e['ref'] or ''} {e['detail'] or ''}{comp}")
        print("  hypotheses (heuristic ranking — not a probability):")
        for h in v["hypotheses"]:
            bar = "█" * int(round(h["support"] * 20))
            print(f"    {h['support']:>5.0%} {bar:<20} {h['description']}  "
                  f"(score {h['score']}, {h['tests_applied']} test(s) applied)")
        print("  tests:")
        for t in v["tests"]:
            line = f"    {ricon.get(t['result'], '·')} #{t['id']} {t['name']}  [{t['result']}] → {t['bears_on'] or ''}"
            print(line)
            if t["interpretation"]:
                print(f"        {t['interpretation']}")
        if v["next_test"]:
            print(f"  ▸ next test: {v['next_test']}")
        if v["findings"]:
            print("  findings (evidence ledger):")
            for f in v["findings"]:
                print(f"    • {f['text']}")
                if f["supporting"]:
                    print(f"        + {f['supporting']}")
                if f["contradicting"]:
                    print(f"        − {f['contradicting']}")
    return 0


def cmd_dx_test(args: argparse.Namespace) -> int:
    from . import workbench
    with session_scope() as s:
        try:
            t = workbench.record_result(s, args.test_id, args.result,
                                        actual=args.actual, interpretation=args.interpretation)
        except (LookupError, ValueError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        ranked = workbench.rank_hypotheses(s, t.case_id)
        print(f"Recorded test #{t.id} '{t.name}' → {t.result}.")
        if ranked:
            lead = ranked[0]
            print(f"  ↳ leading hypothesis now: {lead['description']} "
                  f"(support {lead['support']:.0%}, score {lead['score']})")
    return 0


def cmd_obs_seed(args: argparse.Namespace) -> int:
    from . import observations as ob, service
    from .refmodels import VehicleVariant
    from .models import Vehicle
    from sqlalchemy import select as _select
    with session_scope() as s:
        # A cross-machine example (RZ350 compression) proves Observation V2 is not
        # Focus-specific; falls back to the tracked vehicle if the RZ isn't commissioned.
        variant = s.scalar(_select(VehicleVariant).where(VehicleVariant.slug == args.variant))
        veh = s.scalar(_select(Vehicle).where(Vehicle.variant_id == variant.id)) if variant else None
        if veh is None:
            veh = service.get_vehicle(s)
        ob.upsert_instrument(s, "DG-TOOL-41", "Compression gauge", "gauge")
        env = ob.record_environment(s, veh, ambient=72, ambient_unit="°F", weather="shop")
        snap = ob.snapshot_config(s, veh, code="baseline")
        o = ob.record_observation(s, veh, subject_slug="cylinders", method="compression test",
                                  instrument_code="DG-TOOL-41", value=145, unit="psi",
                                  operating_condition="warm", config_snapshot_id=snap.id,
                                  environment_id=env.id, note="left cylinder")
        print(f"Recorded observation #{o.id} on {veh.make} {veh.model}: "
              f"compression 145 psi (warm) · config snapshot {snap.code} · env #{env.id}.")
    return 0


def cmd_config_at(args: argparse.Namespace) -> int:
    from . import observations as ob, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        cfg = ob.config_at(s, v)
        print(f"Configuration of {v.make} {v.model} as of {cfg['as_of']}:")
        print("  components:")
        for slug, c in sorted(cfg["components"].items()):
            part = f" → {c['installed_part']}" if c.get("installed_part") else ""
            print(f"    · {slug}: {c['condition']} [{c['knowledge_state']}]{part}")
        if cfg["settings"]:
            print("  settings:")
            for k, val in cfg["settings"].items():
                print(f"    · {k}: {val.get('detail') or val.get('data')}")
    return 0


def cmd_events(_: argparse.Namespace) -> int:
    from . import observations as ob, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        rows = ob.events_for(s, v.id)
        if not rows:
            print("(no machine events)")
            return 0
        for e in rows:
            comp = f" [{e['component']}]" if e["component"] else ""
            print(f"  {e['occurred_at'] or ''}  {e['kind']}{comp}  {e['detail'] or ''}")
    return 0


def cmd_observations(args: argparse.Namespace) -> int:
    from . import observations as ob, service
    with session_scope() as s:
        v = service.get_vehicle(s)
        rows = ob.observations_for(s, v.id, subject_slug=args.subject)
        if not rows:
            print("(no observations)")
            return 0
        for o in rows:
            val = f"{o['value']} {o['unit']}" if o["value"] is not None else (o["result"] or "")
            cond = f" @ {o['operating_condition']}" if o["operating_condition"] else ""
            print(f"  #{o['id']} {o['subject']}: {val}{cond}  ({o['method'] or o['type']}) "
                  f"· cfg={o['config_snapshot_id']} env={o['environment_id']}")
    return 0


def cmd_seed_twin(args: argparse.Namespace) -> int:
    from .twin import seed_twin
    with session_scope() as s:
        print(seed_twin(s, args.variant))
    return 0


def cmd_twin(args: argparse.Namespace) -> int:
    from . import twin
    cond_icon = {"stock": "·", "modified": "🟣", "removed": "⚫", "failed": "🔴",
                 "suspect": "🟠", "degraded": "🟡", "healthy": "🟢",
                 "planned": "🔵", "unknown": "⚪"}
    with session_scope() as s:
        rva = twin.reference_vs_actual(s, args.variant)
        if rva is None:
            print(f"No reference variant '{args.variant}'.", file=sys.stderr)
            return 1
        print(f"Digital twin · {args.variant} · VIN {rva['vin'] or '(unlinked)'}")
        print(f"  deviations from stock: {len(rva['deviations'])}")

        def walk(nodes, depth=0):
            for n in nodes:
                print("  " * depth + f"▸ {n['name']}")
                for c in n["components"]:
                    a = c["actual"]
                    icon = cond_icon.get(a["condition"], "·")
                    extra = ""
                    if a["observed"]:
                        extra = f"  [{a['condition']} · {a['knowledge_state']}]"
                        if a["installed_part"]:
                            extra += f" → {a['installed_part']}"
                    print("  " * (depth + 1) + f"{icon} {c['name']}{extra}")
                walk(n["children"], depth + 1)

        walk(rva["tree"])
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

    sp = sub.add_parser("migrate-specs", help="migrate V1 specs → V2 claims (non-destructive)")
    sp.add_argument("--variant", default="focus-st")
    sp.set_defaults(fn=cmd_migrate_specs)

    sp = sub.add_parser("migrate-knowledge", help="migrate V1 maintenance + issues → V2 claims")
    sp.add_argument("--variant", default="focus-st")
    sp.set_defaults(fn=cmd_migrate_knowledge)

    sp = sub.add_parser("seed-graph", help="seed typed graph overlays (airflow/coolant/lubrication)")
    sp.add_argument("--variant", default="focus-st")
    sp.set_defaults(fn=cmd_seed_graph)

    sub.add_parser("seed-diaglib", help="seed the failure-mode + diagnostic-test library").set_defaults(fn=cmd_seed_diaglib)

    sub.add_parser("seed-channels", help="seed the telemetry channel registry").set_defaults(fn=cmd_seed_channels)

    sp = sub.add_parser("telemetry", help="detect telemetry events on a datalog session")
    sp.add_argument("session_id", type=int)
    sp.add_argument("--case", type=int, default=None, help="also attach events to this case as evidence")
    sp.set_defaults(fn=cmd_telemetry)

    sp = sub.add_parser("failure-mode", help="show a failure mode + its discriminating tests")
    sp.add_argument("slug")
    sp.set_defaults(fn=cmd_failure_mode)

    sp = sub.add_parser("symptom", help="symptom → candidate failure modes + best next test")
    sp.add_argument("text")
    sp.set_defaults(fn=cmd_symptom)

    sp = sub.add_parser("next-test", help="rank next tests by info-gain utility for candidates")
    sp.add_argument("candidates", nargs="+", help="failure-mode slugs under consideration")
    sp.add_argument("--done", nargs="*", default=[], help="test slugs already performed")
    sp.set_defaults(fn=cmd_next_test)

    sp = sub.add_parser("overlay", help="show a graph overlay (omit domain to list them)")
    sp.add_argument("domain", nargs="?", default=None, help="airflow | coolant | lubrication | ...")
    sp.add_argument("--variant", default="focus-st")
    sp.add_argument("--trace", default=None, help="trace flow downstream from a component slug")
    sp.set_defaults(fn=cmd_overlay)

    sub.add_parser("pc-seed", help="seed a physical-component lifecycle example (TZ250 piston)").set_defaults(fn=cmd_pc_seed)

    sp = sub.add_parser("pc", help="show a physical component's lifecycle")
    sp.add_argument("code")
    sp.set_defaults(fn=cmd_pc)

    sp = sub.add_parser("commission", help="baseline-commission a machine (or 'all') as a twin")
    sp.add_argument("machine", nargs="?", default="all",
                    help="machine slug (zzr600/rz350/tz250/toyota-pickup) or 'all'")
    sp.set_defaults(fn=cmd_commission)

    sub.add_parser("fleet", help="fleet overview across all machines").set_defaults(fn=cmd_fleet)

    sp = sub.add_parser("dx-seed", help="seed the worked diagnostic case (low boost)")
    sp.add_argument("--variant", default="focus-st")
    sp.set_defaults(fn=cmd_dx_seed)

    sp = sub.add_parser("dx-open", help="open a case from a symptom (auto-seeds candidate failure modes)")
    sp.add_argument("symptom")
    sp.set_defaults(fn=cmd_dx_open)

    sub.add_parser("wo-seed", help="seed an example work order (water pump, READY 80%)").set_defaults(fn=cmd_wo_seed)
    sub.add_parser("work-orders", help="list work orders").set_defaults(fn=cmd_work_orders)

    sp = sub.add_parser("wo", help="show a work order (readiness + tasks + verification)")
    sp.add_argument("id", type=int)
    sp.set_defaults(fn=cmd_wo)

    sp = sub.add_parser("wo-verify", help="record a post-repair verification (pass → VERIFIED)")
    sp.add_argument("id", type=int)
    sp.add_argument("test")
    sp.add_argument("result", choices=["pass", "fail", "pending"])
    sp.add_argument("--note", default=None)
    sp.set_defaults(fn=cmd_wo_verify)

    sub.add_parser("cases", help="list diagnostic cases").set_defaults(fn=cmd_cases)

    sp = sub.add_parser("case", help="show a diagnostic case (the workbench view)")
    sp.add_argument("id", type=int)
    sp.set_defaults(fn=cmd_case)

    sp = sub.add_parser("dx-test", help="record a test result (re-ranks hypotheses)")
    sp.add_argument("test_id", type=int)
    sp.add_argument("result", choices=["pass", "fail", "inconclusive", "pending"])
    sp.add_argument("--actual", default=None)
    sp.add_argument("--interpretation", default=None)
    sp.set_defaults(fn=cmd_dx_test)

    sp = sub.add_parser("obs-seed", help="seed an example Observation V2 (compression)")
    sp.add_argument("--variant", default="rz350")
    sp.set_defaults(fn=cmd_obs_seed)

    sub.add_parser("config-at", help="show the machine's configuration now (a projection)").set_defaults(fn=cmd_config_at)
    sub.add_parser("events", help="list the machine-event ledger").set_defaults(fn=cmd_events)

    sp = sub.add_parser("observations", help="list observations")
    sp.add_argument("--subject", default=None)
    sp.set_defaults(fn=cmd_observations)

    sp = sub.add_parser("seed-twin", help="seed the digital twin from on-vehicle observations")
    sp.add_argument("--variant", default="focus-st")
    sp.set_defaults(fn=cmd_seed_twin)

    sp = sub.add_parser("twin", help="reference-vs-actual component state (the digital twin)")
    sp.add_argument("--variant", default="focus-st")
    sp.set_defaults(fn=cmd_twin)

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
