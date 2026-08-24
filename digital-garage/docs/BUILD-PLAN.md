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

### Deferred backlog — now fully built
The §4 backlog was revised into concrete, sequenced units [#26] and then all six were
built, each as its own green PR:
- **CI2 — full DB-backed CI.** The PR test job stands up a Postgres 16 service and runs
  `cli init` before pytest, so the whole DB-backed suite (not just the pure engines) runs
  on every PR. [#27]
- **MAINT5 — five-/six-state maintenance.** `due` split from `overdue`; the vocabulary is
  `overdue · due · due_soon · needs_log · unknown · ok`, `attention` = overdue+due+due_soon,
  and `needs_log` is never reported as a false `overdue`. [#28]
- **API2 — REST API V2.** Read-only `/v2/*` endpoints (variant, systems, component, claim,
  claims, conflicts, knowledge, trends, fitment, intel) at parity with the MCP read surface,
  reusing the same services. [#29]
- **TEL — durable observations from datalogs.** `parsers.ingest` records `electronic`
  observations for the peak of each mapped channel (boost→turbo, IAT→intercooler,
  coolant→radiator, rail→HPFP, knock→block), best-effort and idempotent. [#30]
- **FEED — fleet `garage.json` + `MODS.md`.** `app/fleetfeed.py` projects each commissioned
  fleet machine's twin deviations into `web/vehicles/<slug>/garage.json` and
  `data/vehicles/<slug>/MODS.md`; `cli fleet-feed [--all]`; `fleet.json` `feed` paths wired. [#31]
- **NAV — interactive engine-bay navigator.** `intel.json` gains a `graph` block
  (`ComponentRelationship` edges tagged by overlay domain + their node set); `intel.html`
  gains a Navigator view that draws the map, isolates one overlay at a time, and opens a
  component's claims on selection. [#32]

**Fleet depth today:** Focus ST is fully populated (claims, feed, MODS, twin). The other
four carry **normalized reference claims** (F1a), **live cockpits** (F1b) over a
commissioned twin, and now a **twin-projected `garage.json` feed + `MODS.md`** (FEED) —
real per-machine knowledge, not zeros. What stays flagship-only is genuinely-logged mod and
service history (the fleet machines have none yet); their feeds honestly show the twin's
deviations-from-stock instead. Overlay graphs are seeded for the Focus ST only, so the
fleet's Navigator honestly reads "No graph overlays recorded yet."

---

## 4. Plan status — everything delivered

Everything the original roadmap sequenced **and** the revised deferred backlog is built and
merged — the §3 ledger is the complete record. The unit write-ups below are kept as the
design/acceptance notes for each deferred unit (all now marked *(done)*); they are history,
not a to-do list. Each was one PR with its own acceptance criteria; none blocked the others.

**Delivered since this plan was written** — all merged, green (one line each; details are
in the §3 ledger and the PRs):
- **F1a** — fleet reference knowledge: manual specs → graded per-variant claims. [#21]
- **F1b** — live fleet cockpits: each hydrates from its own `intel.json`. [#22]
- **DI** — degradation trends over the observation history. [#23]
- **PF** — parts intelligence + fitment (catalog slots → components). [#24]
- **UI V2 (views + search)** — modular tabbed dashboard + universal search. [#25]
- (**Phase 6** — evidence-grounded MCP V2 [#20] — is in the §3 ledger.)

---

### NAV — Interactive engine-bay navigator  *(the last UI piece)* *(done)*
An interactive system/component map over the graph overlays (airflow / coolant /
lubrication) that already exist in the reference graph and in `intel.json` (`overlays`).
- **Data:** `intel.py` now emits a `graph` block — `_graph_block` walks every overlay's
  `ComponentRelationship` edges (via `graphs.overlay_edges`), tags each by domain, and
  carries the node set (slug + name + system) they connect, so the client draws and
  filters the map entirely offline.
- **Render:** a new **Navigator** view in `web/tools/intel.html` draws an inline-SVG
  circular map (nodes grouped by system); a radio-style overlay legend isolates one
  domain's edges (`All` restores every overlay); selecting a component highlights its
  incident edges and opens its claims + connections in the side panel; a component search
  hit jumps into the Navigator and selects it. Self-contained, CSP-safe, theme-aware.
- **Acceptance (met):** isolating the airflow overlay shows exactly its 6 edges and no
  others; clicking a component opens its claims; the page renders headless with zero
  console/page errors (17 nodes / 19 edges for the Focus ST). `test_intel_carries_navigator_graph`
  guards the projection. Fleet machines have no seeded overlay edges yet, so their
  Navigator honestly reads "No graph overlays recorded for this machine yet."

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

### TEL — Datalog → Observation ingestion (feed trends from real logs) *(done)*
`parsers.ingest` now records durable `observations` from each datalog's per-channel peaks
(via the pure `analysis.peak_observations`): boost → turbocharger, charge-air temp →
intercooler, coolant → radiator, rail pressure → hpfp, knock → block — each a distinct
component so the series never collide, timestamped at the log's capture time, `electronic`
obs_type. Best-effort and isolated (a bad unit retries unitless, then skips — never fails
the ingest). So `component_trends` now fits real logged history, not just the `obs-seed`
sample.
- **Acceptance:** ingesting datalogs records observations keyed by component/condition, and
  a series of declining logs yields a fitted, drift-flagged `component_trends` result ✓;
  the pure peak extractor is DB-free tested ✓.

### FEED — Fleet `garage.json` feeds + `MODS.md`  *(done)*
`app/fleetfeed.py` (`cli fleet-feed [--all]`) projects, for each of the four fleet
machines, a **`MODS.md`** and a compact **`garage.json`** feed from the digital twin's
reference-vs-actual **deviations** — the honest "changes / unknowns vs stock" for machines
with no logged V1 mods (zzr600/rz350 2 each, toyota 4, tz250 0). This fills the
`fleet.json` `mods` paths that were dangling and adds a `feed` path per machine. `intel.json`
stays the full projection; this is the lightweight sibling.
- **Acceptance:** each fleet machine gets a MODS.md + garage.json regenerated from canon
  (never hand-authored); `fleet.json` feeds are wired; pure renderer + DB build tested. ✓

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
