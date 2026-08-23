# Digital Garage — Build Plan

> The single source of truth for **how this platform is being built**: the vision, the
> rules every unit follows, what is already merged, and what is left — sequenced.
> `V2-ARCHITECTURE.md` explains the *design*; this file tracks the *build*.

---

## 1. What we are building

An **evidence-backed, vehicle-agnostic machine-intelligence platform**. One hub, many
machines. The 2017 Ford Focus ST is the first fully-populated vehicle; a fleet of four
more (1991 ZZR600, 1985 RZ350, 1986 TZ250, 1986 Toyota 22RE pickup) rides the same
data logic. **The GitHub repo is the database's projection surface; Postgres is canon.**

Two ideas run through everything:

- **Provenance before facts.** A fact is a *claim* backed by *evidence*; its trust grade
  (`UNVERIFIED → CORROBORATED → OEM_VERIFIED → VEHICLE_VERIFIED`) is *computed* from that
  evidence, never asserted. Weaker evidence never silently overrides stronger.
- **The agent proposes, a human approves.** No agent path mutates canonical truth. The
  only write an agent can make is a *proposal* a person later approves by name.

---

## 2. Rules every build unit follows

These are invariants — a unit that breaks one is wrong, not clever.

1. **Postgres is canonical.** Markdown / JSON / dashboards (`MODS.md`, `garage.json`,
   `intel.json`) are **projections**, regenerated from the DB, never hand-authored.
2. **Migrations are additive + idempotent.** Each `db/schema_vN.sql` only adds; `cli init`
   re-applies the whole chain safely. No destructive ALTERs, no renumbering.
3. **The approval boundary is sacred.** New write surfaces record proposals; a single
   approval path (`service.approve_proposal`, human name required) is the only mutator.
4. **Verdicts are monotonic.** Adding evidence re-resolves a claim from *all* its evidence;
   a weaker source can never demote a stronger conclusion.
5. **Pure engines stay DB-free.** Core logic is unit-testable without Postgres; DB-backed
   tests are `skipif` so CI's pure suite always runs.
6. **No copyrighted manuals in the repo.** Store derived facts, citations, and permissible
   excerpts only — never bulk service-manual text.
7. **One unit, one PR.** Small, reviewable, green. The per-unit workflow (§5) is fixed.

---

## 3. Status ledger — what is merged

Everything below is on `master`. PR numbers in brackets.

### Foundation (V1, untouched and still driving `MODS.md` + `garage.json`)
- One-vehicle truth store: specs, maintenance intervals, service events, mods, issues,
  parts, diagnostic sessions, odometer, recalls. FastAPI + MCP + CLI. Approval queue.
  Receipt ingest → proposals. Datalog parser + session summarizer. CI (pytest + garage.json).

### V2 — reference model + provenance
- **Phase 1 — Canonical reference model + claim/evidence provenance.** Manufacturer →
  Platform → Variant → Engine/Transmission → Systems → Components; `claims` + `evidence`
  with computed verdicts. [#7]
- **Phase 2 — Reference dataset normalization.** V1 specs → claims; maintenance, known
  issues, recalls/TSBs → graded claims. [#7, #8]

### V3 — machine state
- **Phase 3 — Temporal digital twin.** `component_states`, superseding rows, `state_at(T)`,
  reference-vs-actual deviations. Four other machines baseline-commissioned as twins. [#7]

### V4 — diagnostics + the engineering stack
- **Phase 4 — Diagnostic workbench.** Cases, hypotheses (transparent ranking), tests,
  findings. [#9]
- **Milestone A — Semantic Core.** Domain Constitution (enforced kind-promotion rules) +
  quantity/units subsystem; Observation V2 + config/env snapshots + machine-event ledger;
  ontology overlays (typed graphs), assemblies, physical-component lifecycle. [#10, #11]
- **Milestone B — Diagnostic Core.** Failure-mode library + information-gain next-test
  selection. [#12]
- **Milestone C — Workshop Engine.** Work orders, job readiness %, mandatory post-repair
  verification (`REPAIR_PERFORMED` vs `REPAIR_VERIFIED`). [#13]
- **Milestone E — Telemetry V2.** Channel registry, derived signals, event detection
  (WOT_PULL / BOOST_DEFICIT / KNOCK_EVENT / OVER_TEMP / MISFIRE_EVENT / HEAT_SOAK). [#14]
- **Milestone D — Engineering.** Constraint solver + computed build scenarios + experiment
  engine (confounder warnings). [#15]
- **Milestone F — Knowledge Operations.** Quality dashboard, research queue, entity
  resolution. [#16]

### Milestone G — the intelligence bridge (backend → web)
- **Vehicle-intelligence projection + HUD dashboard.** `intel.json` aggregates the whole
  V2 backend; `web/tools/intel.html` renders it. [#17]
- **Fleet-wide intel.** Per-machine `intel.json` + vehicle-aware dashboard, with strict
  per-variant knowledge scoping (`research_tasks.variant`). [#18]
- **Maintenance status in the intelligence layer.** Due-engine bucketed per machine,
  `needs_log` kept distinct from `overdue`. [#19]

### Phase 6 — Evidence-grounded MCP V2
- **The agent answers with provenance.** MCP read tools over the reference/provenance
  model (`get_variant`/`get_systems`/`get_component`/`get_claim`/`list_claims`/
  `list_conflicts`/`knowledge_quality`) + `propose_claim` through the approval boundary
  (verdict computed from evidence on approval; corroboration is monotonic).

**Fleet depth today:** Focus ST is fully populated (claims, feed, MODS, twin). The other
four are **scaffolded** — cockpit + manual + PARTS + `intel.json` + a commissioned twin,
but no normalized claims, no `garage.json` feed, no `MODS.md`. That gap is unit F1 below.

---

## 4. Remaining plan — sequenced

Each item is one PR unit with explicit acceptance criteria. Order is default; it can be
re-prioritized on request.

### F1 — Populate the fleet to flagship depth
Bring zzr600 / rz350 / tz250 / toyota-pickup from scaffold to fully-modeled.
- **F1a — reference knowledge.** *(done)* `seed_fleet_knowledge` normalizes each machine's
  manual spec table into graded, per-variant **claims** (`cli seed-fleet-knowledge`).
  Honest grading: web-verified → `CORROBORATED`, `⚠️ verify` → `UNVERIFIED` (feeding that
  machine's own research queue). Each machine's `intel.json` now shows real claim counts
  (zzr600 18 · rz350 14 · tz250 13 · toyota 9).
- **F1b — live fleet cockpits.** *(done)* Each fleet cockpit
  (`web/vehicles/<slug>/index.html`) gained a **Live Intelligence** section that fetches
  its `intel.json` and renders the machine's live V2 state — knowledge-quality bars,
  digital-twin deviations, open cases, and its research queue — with a `● LIVE` badge,
  themed by the page's accent, degrading silently if no feed is present. (The fleet's
  richest data lives in the V2 layer, already projected to `intel.json`; a V1-style
  `garage.json` would be near-empty, so the cockpits read the V2 projection directly.)
- **Acceptance:** claim counts populated (F1a ✓); cockpits present live per-machine state (F1b ✓).

### DI — Data intelligence: degradation trends + baselines *(done)*
Turn the observation history into **trend** intelligence.
- `app/trends.py`: a pure `fit_trend` (OLS → slope/R²/direction/drift classification, metric-
  agnostic) + `component_trends` grouping a machine's observations into per-(component,
  metric, condition) series. Confounder-aware — a series spanning a wide ambient-°C range is
  flagged. `cli trends` prints them; `intel.json` carries a `trends` block; the dashboard
  shows a Degradation Trends panel + a "drift alerts" KPI. The example `obs-seed` now lays
  down a short warm-compression series so the engine has something to fit.
- **Acceptance:** the seeded declining series is detected and drift-flagged (RZ350 cylinders
  ↘ 7% over 90d, R²=0.99 ✓); flat/noisy data yields no drift ✓; pure trend math is DB-free
  tested ✓.

### PF — Parts intelligence + fitment *(done)*
Connect the PARTS catalog to reference components and known fitment.
- `app/fitment.py`: a pure `PARTS.md` slot parser + a transparent token matcher (generic
  words demoted so a match rests on a distinctive token, not on sharing "valve"/"oil");
  `catalog_fitment` resolves every slot to a component and tiers the verdict by confidence
  — **fits** (strong overlap), **likely** (weak, confirm), **unmapped** (warn). A mapped
  slot's fitment is scoped to the variant's years/market from the reference header.
- Surfaced via `cli fitment`, the `part_fitment` MCP tool, an `intel.json` `parts` block,
  and a dashboard Parts Fitment panel + a "parts mapped" KPI.
- **Acceptance:** slots resolve to components with a fitment verdict (Spark Plugs →
  spark-plugs, Intercooler → intercooler ✓); generic false positives rejected (Oil Filter,
  Engine Oil → unmapped ✓); mismatches warn ✓.

### UI — Modular UI V2
Modularize the frontend into views (Overview / Diagnose / Maintain / Build / Parts /
Systems / Data / Knowledge); interactive engine-bay system navigator; universal search
over claims + components + codes.
- **Acceptance:** views are independent; navigator reads the overlays; search hits canon.

---

## 5. The per-unit workflow (fixed)

Every unit in §4 is built the same way:

1. **Reset** the working branch from `origin/master` (never stack on merged history).
2. **Build**: schema (additive) → models → service/engine → CLI/MCP/API → tests.
3. **Verify**: full `pytest` with a DB, the pure suite without one (`DG_DB_PORT=5999`),
   and `cli init` idempotency. Render-check any web change headless.
4. **Document**: update `V2-ARCHITECTURE.md` and this ledger.
5. **Ship**: commit → push → **draft PR** → poll CI → un-draft → merge → reset branch.

Postgres for local runs: port 5433 (`garage`/`garage`/`garage`), data at `/tmp/pgdata_dg`.
