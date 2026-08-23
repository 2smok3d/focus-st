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

**Fleet depth today:** Focus ST is fully populated (claims, feed, MODS, twin). The other
four are **scaffolded** — cockpit + manual + PARTS + `intel.json` + a commissioned twin,
but no normalized claims, no `garage.json` feed, no `MODS.md`. That gap is unit F1 below.

---

## 4. Remaining plan — sequenced

Each item is one PR unit with explicit acceptance criteria. Order is default; it can be
re-prioritized on request.

### P6 — Evidence-grounded MCP V2 *(in progress — current unit)*
Expose the V2 reference/provenance model to the agent so it answers **with provenance**,
and let it propose claims through the approval boundary.
- **Read tools:** `get_variant`, `get_systems`, `get_component` (claims + typed edges),
  `get_claim` (evidence + freshly re-resolved verdict), `list_claims`, `list_conflicts`,
  `knowledge_quality`.
- **Write tool:** `propose_claim` — records a pending proposal; **no mutation**. On human
  approval, the claim + evidence are created and the verdict resolved via provenance.
- **Acceptance:** read tools return graded, provenance-carrying dicts; `propose_claim`
  never mutates canon; approving a claim proposal creates it with a computed verdict;
  corroborating evidence strengthens monotonically; pure + DB tests green; docs updated.

### F1 — Populate the fleet to flagship depth
Bring zzr600 / rz350 / tz250 / toyota-pickup from scaffold to fully-modeled.
- Normalize each machine's manual/PARTS into graded **claims** (scoped by variant).
- Generate each a `garage.json` feed + `MODS.md` from the DB; wire `fleet.json` feeds.
- **Acceptance:** each machine's `intel.json` shows real claim counts; cockpits hydrate
  from their own feed; projections regenerate from canon.

### DI — Data intelligence: degradation trends + baselines
Turn the observation/telemetry history into **trend** intelligence.
- Per-channel/per-component baselines; drift detection over time; surface in `intel.json`
  + a dashboard panel. Confounder-aware (reuse the experiment engine's ambient-gap logic).
- **Acceptance:** a seeded declining trend is detected and flagged; no false trend on flat
  data; pure trend math is DB-free tested.

### PF — Parts intelligence + fitment
Connect the PARTS catalog / mods to reference components and known fitment.
- Map catalog slots → components; carry fitment applicability (variant/years/market);
  flag mods against the twin. Surface fitment confidence on the dashboard.
- **Acceptance:** a part resolves to a component with a fitment verdict; mismatches warn.

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
