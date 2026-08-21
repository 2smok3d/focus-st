# Digital Garage V2 — Architecture & Migration Roadmap

> **Not a rewrite.** V2 is an *incremental, additive* evolution of the working V1
> truth store. Every V2 change lands alongside V1, keeps the existing exports and
> dashboards functional, and is migrated in small, testable stages. Postgres and the
> structured reference datasets are canonical; Markdown, JSON, and dashboards are
> **projections** of that canon, never the source.

---

## 1. What V2 adds to V1

V1 modeled **one vehicle**: a `vehicles` row with graded `specs`, maintenance
intervals, service events, mods, issues, parts, diagnostic sessions, and a
human-approval queue (`change_proposals`). That machinery is untouched and still
drives `MODS.md` + `garage.json`.

V2 introduces the **vehicle-agnostic reference layer** and **claim-level
provenance** underneath it, so the platform can hold reference truth for *any*
machine and reason about *why* each fact is trusted:

```
                       ┌──────────────────────────────────────────────┐
   REFERENCE TRUTH     │  Manufacturer → Platform → Variant            │
   (V2, vehicle-       │      → { Engine, Transmission }               │
    agnostic)          │      → Systems → Components → (typed edges)   │
                       └───────────────────────┬──────────────────────┘
                                               │ variant_id
   VEHICLE TRUTH       ┌───────────────────────┴──────────────────────┐
   (V1, this car)      │  vehicles → specs / mods / issues / service   │
                       │            / diagnostic sessions / parts      │
                       └──────────────────────────────────────────────┘

   PROVENANCE          claims ── claim_evidence ── source_documents ── sources
   (spans both)        every fact resolves to a verdict + confidence + conflict
```

The actual car (`vehicles`) now carries a `variant_id` pointing at its reference
configuration (`vehicle_variants`), instead of duplicating reference data. The
Focus ST is the first deeply-modeled variant.

---

## 2. The evidence model (the defining characteristic)

A **claim** is one automotive fact ("Focus ST lug torque = 100 lb-ft"). Each claim
gathers **evidence**, each piece from a graded **source** (authority `1`=OEM/factory
… `6`=unknown) with a **stance** (`supports` / `contradicts` / `supersedes`) and an
`on_vehicle` flag. `app/provenance.py` resolves the evidence set into a **verdict**:

| Verification ladder | Reached by |
|---|---|
| `UNVERIFIED` | no support, or a single anecdote |
| `CORROBORATED` | reputable community / trade consensus |
| `OEM_VERIFIED` | OEM / factory document |
| `VEHICLE_VERIFIED` | observed on **this** car (`on_vehicle`) |

Rules enforced (and unit-tested in `tests/test_provenance.py`):

- **Weaker evidence never silently outranks stronger** — the tier is the MAX
  ceiling any *supporting* source can justify.
- A document tops out at `OEM_VERIFIED`; only an on-vehicle observation reaches
  `VEHICLE_VERIFIED`.
- A **contradiction from an equal-or-higher authority** caps the verdict one tier
  and raises the `conflict` flag — disagreement is surfaced, never hidden.
- Confidence blends authority strength × corroboration, penalized by conflict,
  floored high for on-vehicle facts.

The canonical worked example, seeded live: the **oil-capacity discrepancy** — the
Ford WSM (with filter) states **4.3 qt** while other Ford literature states **5.7
qt**. Two authority-1 sources disagree, so the verdict is capped to `CORROBORATED`,
flagged `conflict=true`, and confidence dropped (~0.36). The system records both,
picks the WSM value, and *shows the disagreement* rather than pretending certainty.

---

## 3. Phase 1 — Data Foundation ✅ (this stage)

**Delivered, additive, tested:**

| Piece | File |
|---|---|
| Provenance engine (pure, no DB) | `app/provenance.py` |
| Reference ORM (manufacturer→…→component + claims) | `app/refmodels.py` |
| Additive DDL (idempotent, `CREATE … IF NOT EXISTS`) | `db/schema_v2.sql` |
| Digital-twin link `vehicles.variant_id` | `db/schema_v2.sql`, `app/models.py` |
| Focus ST reference seed (6 systems, 20 components, 10 edges, 6 graded claims) | `app/seed_ref.py` |
| Read/query projection layer | `app/refservice.py` |
| CLI surface (`seed-ref`, `ref`, `component`, `claim`, `conflicts`) | `app/cli.py` |
| Unit tests (evidence precedence, conflict, applicability) | `tests/test_provenance.py` |
| DB integration tests (Postgres-or-skip) | `tests/test_refmodel.py` |

**Migration integrity:** `db/schema.sql` domains are now created idempotently
(`DO $$ … duplicate_object … $$`), and `schema_v2.sql` is fully `IF NOT EXISTS`, so
`python -m app.cli init` re-runs cleanly on an existing V1 database. The V1 vehicle,
its specs, and the export path are unchanged — proven by
`test_export_compatibility_vehicle_linked_not_mutated`.

**Try it:**

```bash
python -m app.cli init          # V1 schema + V2 additive layer
python -m app.cli seed --if-empty
python -m app.cli seed-ref      # build the reference model + graded claims
python -m app.cli ref           # the system → component tree
python -m app.cli component turbocharger
python -m app.cli claim lubrication oil_capacity   # see the conflict resolved
python -m app.cli conflicts
```

---

## 4. Later phases (planned, not yet started)

Each phase is additive and independently shippable. **Do not start a later phase
before the previous one is complete and tested.**

- **Phase 2 — Reference dataset.** *(in progress)* Normalize the Focus ST knowledge
  base (specs, torques, fluids, intervals, known traits) into claims with citations.
  **Done:** the V1-spec → claim migrator (`app/migrate_specs.py`, `cli migrate-specs`)
  moves 19 fact-checked specs onto the reference model — engine/transmission/component
  claims — deriving each verdict from the spec's source authority (OEM→`OEM_VERIFIED`,
  community→`CORROBORATED`). It is idempotent, never overwrites a seeded claim (the
  oil-capacity conflict survives), reports unmapped specs instead of guessing, and
  leaves the V1 `specs` rows (and their exports) intact — the Markdown/JSON stay
  projections. **Maintenance + known issues *(done)*:** `app/migrate_knowledge.py`
  (`cli migrate-knowledge`) lifts the V1 `maintenance_intervals` and `issues` tables
  into claims too — maintenance intervals become `maintenance:<item> · interval_miles|
  interval_months` graded from the interval's source (OEM→`OEM_VERIFIED`,
  community→`CORROBORATED`); known issues become `issue:<title> · known_issue`, where a
  VEHICLE_VERIFIED issue is on-vehicle evidence (→`VEHICLE_VERIFIED`, scoped to this car)
  and a platform issue is community/OEM knowledge (→`CORROBORATED`, scoped to the
  variant/years). **Recalls / TSBs *(done)*:** `migrate_recalls_to_claims` folds the
  `recalls` table into `recall:<campaign> · campaign` claims — NHTSA-origin campaigns are
  government-authoritative (→`OEM_VERIFIED`), KB-noted Ford campaigns keep their
  conservative recorded grade (→`CORROBORATED`) until confirmed for this VIN. Only
  *derived structured facts* are stored (campaign number, affected component, remedy
  summary, status, the "verify by VIN" citation) — never protected manual content.
  Idempotent, non-destructive; the `due` calculations still read the V1 rows.
  **Phase 2 complete** — specs, maintenance, issues, and recalls are all claims now.

- **Phase 3 — Digital Twin / Machine State Engine.** *(started)* A machine is a
  **state over time**, not a bag of current records. **Done:** `db/schema_v3.sql` +
  `app/twinmodels.py` + `app/twin.py` add `component_states` — each row an observation
  of a component's **condition** (`stock`/`modified`/`removed`/`failed`/`suspect`/
  `degraded`/`healthy`/`planned`/`unknown`) *and* its **epistemic knowledge_state**
  (`DIRECTLY_OBSERVED`/`OEM_ASSERTED`/`INFERRED`/`ESTIMATED`/`DISPUTED`/… — keeping
  inference distinct from fact). A new observation **supersedes** the prior one, so
  `MachineState(T)` is reconstructable for any T (`state_at`). `reference_vs_actual`
  overlays recorded states on the reference tree (unobserved → assumed stock, *not
  claimed verified*); `machine_capabilities` records what a machine supports so tools
  adapt per machine (no "Scan DTC" on a carbureted two-stroke). CLI: `seed-twin`,
  `twin`. Usage accumulators (`hours`/`miles`/`cycles`) are in place to feed later
  condition-based maintenance + degradation models. **Next:** usage-driven degradation
  / remaining-life estimates, and attaching mods/service events to component states.

  **Fleet commissioning *(done)*:** `app/commission.py` + `cli commission [machine|all]`
  onboards the four other machines — **ZZR600** (carbureted inline-4), **RZ350** (YPVS
  two-stroke twin), **TZ250** (premix race two-stroke), **Toyota 22RE** (EFI truck) — as
  real twins rather than DB rows. Each gets its own reference graph (manufacturer →
  platform → variant → engine/transmission → systems → components, from the web-verified
  manual specs), a linked `vehicles` row, a **capability profile** (the EFI truck has
  OBD/DTC; the carbureted two-strokes don't), and an honestly-graded **baseline**:
  owner-stated facts (Toyota engine-out + stripped interior → `removed`/`DIRECTLY_OBSERVED`)
  vs un-inspected items (TZ top-end → `unknown`, *not* a claimed deviation). `cli fleet`
  gives the five-machine overview. The core is vehicle-agnostic — a 6th machine is a new
  entry in the `MACHINES` map, no schema or engine change.

- **Phase 4 — Professional tools.** *(started — diagnostic workbench done)* The
  **diagnostic workbench** ships: `db/schema_v4.sql` + `app/dxmodels.py` +
  `app/workbench.py` add `diagnostic_cases` with symptoms, known-data evidence
  (DTCs/mods/issues/telemetry), a tree of tests (TEST → EXPECTED → ACTUAL →
  INTERPRETATION → RESULT), ranked hypotheses, and an evidence-ledger of findings. A
  case combines the vehicle's data (a DTC, a mod, the component graph) and **ranks
  hypotheses through a transparent, documented heuristic** — `score = prior + Σ test
  contributions`, where a completed test raises or lowers the hypothesis it bears on by
  its weight and polarity. Rankings are **relative support, never a calibrated
  probability**; recording a test result **re-ranks live**. The seeded worked case
  (`DG-0004` low/intermittent boost) leads with the PCV/unmetered-air hypothesis from
  the P04DB history + post-MAF intake mod, then promotes the boost-leak hypothesis when
  the smoke test fails. CLI: `dx-seed`, `cases`, `case <id>`, `dx-test <id> <result>`.

- **Milestone B — Diagnostic Core.** *(started)* A reusable **failure-mode library** and
  **diagnostic-test library** (`db/schema_v8.sql`, `app/fmmodels.py`, `app/diaglib.py`).
  Failure modes are authored once (components, symptoms, expected observations,
  disconfirming evidence, consequences) independent of any case; a **symptom maps to
  candidate failure modes**; each reusable test carries an **information-gain + cost +
  risk** so `recommend_next_test` picks the *single best next test* by a transparent
  utility (discriminating power per unit cost/risk) — not a list of ten. Confidence is
  reported in **bands** (LOW/MODERATE/HIGH/VERY_HIGH), never invented percentages. The
  workbench consumes it: `workbench.recommend_next_test(case)` maps the case's
  hypotheses → candidate failure modes → the best next test, surfaced in the case view.
  CLI: `seed-diaglib`, `symptom "<text>"`, `failure-mode <slug>`, `next-test <fm>…`.
  The loop is closed: `open_case_from_symptom` auto-seeds candidate failure modes as
  hypotheses, and `confirm_failure_mode` promotes one to a finding **only with confirming
  evidence** (constitution-enforced), citing the mode's consequence.

- **Milestone C — Workshop Engine.** *(started)* Work orders with the full status
  lifecycle (`draft → ready/blocked → in_progress → verification_required → verified →
  closed`) and repair state (`planned → repair_performed → repair_verified`).
  `db/schema_v9.sql`, `app/womodels.py`, `app/workshop.py`. **Job readiness** (#13)
  computes what fraction of the required parts/tools/procedure is in hand ("READY 86% —
  missing: Crush washer"). **Mandatory verification** (#16): completing the work yields
  `verification_required`/`repair_performed` — never "fixed"; only a **passing post-repair
  verification** promotes it to `verified`/`repair_verified` (through the constitution's
  `FINDING → VERIFIED_REPAIR` bridge), and **closing writes an automatic `ServiceEvent`**
  to the ledger. CLI: `wo-seed`, `work-orders`, `wo <id>`, `wo-verify`.
  **Next:** procedure-execution mode (step → measurement → abnormal observation) and
  garage inventory to source the readiness check.

- **Milestone C — Workshop Engine.** *(done)* Work orders with the full status
  lifecycle (`draft`→`ready`/`blocked`→`in_progress`→`verification_required`→`verified`
  →`closed`), **job-readiness analysis** ("READY 86% — missing the crush washer"), and
  **mandatory post-repair verification**: completing the work yields
  `REPAIR_PERFORMED`, and only a passing verification reaches `REPAIR_VERIFIED` (the
  constitution's FINDING→VERIFIED_REPAIR bridge). Closing a verified order writes an
  automatic **service-ledger** event. `db/schema_v9.sql`, `app/workshop.py`; CLI
  `wo-seed`, `work-orders`, `wo <id>`, `wo-verify`.

- **Milestone E — Telemetry V2.** *(done)* A canonical **channel registry** + a pure
  **derive → detect** engine (`db/schema_v10.sql`, `app/telemetry.py`): normalized
  frames → derived signals (`boost_error`, `charge_temp_delta`) → **event detection**
  (`WOT_PULL`, `BOOST_DEFICIT`, `KNOCK_EVENT`, `OVER_TEMP`, `MISFIRE_EVENT`, `HEAT_SOAK`).
  Raw measurements are never mutated. `run_pipeline` persists events per diagnostic
  session (idempotent); `events_to_case` attaches them to a case as telemetry evidence —
  closing the loop from a datalog to a diagnosis. The pure engine runs in CI without a
  DB. Also fixed the channel recognizer to read commanded/desired boost as `boost_cmd`.
  CLI: `seed-channels`, `telemetry <sid> [--case N]`.

  **Remaining later:** maintenance status engine (`UNKNOWN`/`CURRENT`/`DUE_SOON`/`DUE`/
  `OVERDUE`), parts intelligence + fitment, build planner (Milestone D), machine
  baselines + degradation trends.

- **Phase 5 — UI V2.** Modularize the frontend into app/components/views (Overview,
  Diagnose, Maintain, Build, Parts, Systems, Data, Knowledge); interactive engine
  bay as a system navigator; universal search over claims + components + codes.

- **Phase 6 — Intelligence.** Evidence-grounded MCP V2 (`get_system`,
  `get_component`, `get_claim`, `get_evidence`) so the agent answers *with*
  provenance and proposes claims through the same human-approval boundary.

---

## 5. Invariants (hold across every phase)

1. **Human approval boundary** — agent proposes → human reviews → human approves →
   canonical record changes. Reference claims flow through the same queue.
2. **Provenance or it didn't happen** — a fact without evidence is `UNVERIFIED`.
3. **Never overwrite stronger with weaker.** Enforced in code, not convention.
4. **Canon is Postgres.** Markdown/JSON/dashboards regenerate from it.
5. **Raw artifacts are preserved** byte-for-byte with SHA-256 before normalization.
6. **Protected content stays out of the repo** — structured facts, citations, and
   limited permissible excerpts only.
