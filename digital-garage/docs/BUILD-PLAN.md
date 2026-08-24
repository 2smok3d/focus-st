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
  (verdict computed from evidence on approval; corroboration is monotonic). [#20]

### Post-roadmap units (fleet depth + data intelligence + UI V2)
- **F1a — fleet reference knowledge.** `seed_fleet_knowledge` normalizes the four fleet
  manuals' spec tables into graded per-variant claims. [#21]
- **F1b — live fleet cockpits.** Each fleet cockpit hydrates a Live Intelligence section
  from its own `intel.json`. [#22]
- **DI — degradation trends.** `app/trends.py` fits the observation history (drift
  detection, confounder-aware); `intel.json` `trends` block + dashboard panel. [#23]
- **PF — parts intelligence + fitment.** `app/fitment.py` resolves `PARTS.md` slots to
  reference components with a tiered fitment verdict. [#24]
- **UI V2 — modular dashboard + universal search.** `intel.html` tabbed views + one search
  box over claims + components + DTC codes (`intel.json` `search_index`). [#25]

**Fleet depth today:** Focus ST is fully populated (claims, feed, MODS, twin). The other
four now carry **normalized reference claims** (F1a) and **live cockpits** (F1b) over a
commissioned twin — real per-machine knowledge, not zeros. Still flagship-only: a
`garage.json` feed and a generated `MODS.md` (deferred as unit **FEED** in §4, low value
until a fleet machine logs mods/service).

---

## 4. Plan status — delivered, then the deferred backlog

Everything the original roadmap sequenced is built. Below the divider is the **revised
deferred backlog** — the work that remained once the roadmap was done. Each is one PR unit
with acceptance criteria; none blocks the others, so order is by value, not dependency.

**Delivered since this plan was written** — all merged, green (one line each; details are
in the §3 ledger and the PRs):
- **F1a** — fleet reference knowledge: manual specs → graded per-variant claims. [#21]
- **F1b** — live fleet cockpits: each hydrates from its own `intel.json`. [#22]
- **DI** — degradation trends over the observation history. [#23]
- **PF** — parts intelligence + fitment (catalog slots → components). [#24]
- **UI V2 (views + search)** — modular tabbed dashboard + universal search. [#25]
- (**Phase 6** — evidence-grounded MCP V2 [#20] — is in the §3 ledger.)

---

### NAV — Interactive engine-bay navigator  *(the last UI piece)*
An interactive system/component map over the graph overlays (airflow / coolant /
lubrication) that already exist in the reference graph and in `intel.json` (`overlays`).
- **Data:** extend the `intel.json` search index (or a new `graph` block) with the
  component adjacency — `ComponentRelationship` edges tagged by domain — so the client
  draws the map offline.
- **Render:** inline SVG/HTML in a new Systems sub-view; an overlay toggle
  (airflow/coolant/lube) that shows only that domain's edges; selecting a component opens
  its claims (reuse the search-result → view jump). Self-contained, CSP-safe, legible in
  light + dark.
- **Acceptance:** an overlay toggle shows only that domain's edges; clicking a component
  opens its claims; renders headless with zero errors.

### API2 — REST API V2 (parity with the MCP read surface) *(done)*
`app/main.py` gained read-only V2 endpoints mirroring the MCP tools, reusing refservice /
knowledge / trends / fitment / intel: `/v2/variant/{slug}`, `/v2/systems/{slug}`,
`/v2/component/{slug}/{comp}`, `/v2/claim`, `/v2/claims`, `/v2/conflicts`,
`/v2/knowledge/{slug}`, `/v2/trends`, `/v2/fitment/{slug}`, `/v2/intel/{slug}`. The only
write surface stays the `/proposals` queue.
- **Acceptance:** each endpoint returns the same dict the CLI/MCP does; a `TestClient`
  smoke test covers them (variant/systems/component/claim/conflicts/knowledge/intel/
  fitment) and asserts the V2 routes reject writes; no new mutation surface. ✓

### CI2 — Full DB-backed CI *(done)*
`ci.yml`'s `digital-garage tests` job now runs a **Postgres 16 service** (mapped
`5433:5432`, `DG_DB_*` = garage/garage/garage), applies the schema chain via `cli init`,
and runs the whole suite — so the ~89 DB-backed tests execute on every PR, not just the
~72 pure ones.
- **Acceptance:** the workflow spins up Postgres, `cli init` applies the schema chain, and
  the full 161-test suite runs green on every PR. ✓

### TEL — Datalog → Observation ingestion (feed trends from real logs)
Trends and the twin only light up from real measurement history; today the only series is
the `obs-seed` sample. Wire the existing datalog parser so ingesting a session also records
durable `observations` (per-pull peak boost, oil temp, …) keyed by component + condition.
- **Acceptance:** ingesting two dated logs of the same channel yields a fitted
  `component_trends` result; the sample seed is no longer the only source.

### FEED — Fleet `garage.json` feeds + `MODS.md`  *(optional)*
Deferred in F1b because a V1-style feed is near-empty for the fleet. If a fleet machine
accumulates mods/service, project a V2 `garage.json` (twin + reference summary) + `MODS.md`
from canon and wire the `fleet.json` `feed` paths.
- **Acceptance:** a fleet machine with recorded mods projects a non-empty feed its cockpit
  reads; regenerated from the DB, never hand-authored.

### MAINT5 — Five-state maintenance vocabulary  *(done)*
`maintenance_summary` now splits **DUE** (only just past the interval — within
`DUE_MARGIN_MILES` / `DUE_MARGIN_MONTHS`) from **OVERDUE** (well past), via the pure
`_past_due_state` helper (the worst dimension drives). States are now
`overdue / due / due_soon / needs_log / unknown / ok` — the V4 vocabulary, with `needs_log`
kept honest for items lacking history and `ok` = CURRENT. `attention` counts overdue + due
+ due_soon; the dashboard renders the DUE chip. `latest_odometer` gained an `id` tiebreak
so the newest reading is deterministic.
- **Acceptance:** a just-past item buckets `due`, a well-past item `overdue`, the worst
  dimension drives the split, both count toward `attention` — pure + DB tests ✓.

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
