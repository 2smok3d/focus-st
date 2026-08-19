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
  projections. **Next:** normalize maintenance intervals, known issues, and TSB/recall
  references into the claim model; store citations + document/page/section metadata and
  only **permissible excerpts** — never copy protected service manuals into the repo.

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

- **Phase 4 — Professional tools.** Diagnostic workbench (`diagnostic_cases` linking
  symptoms → DTCs → components → tests), telemetry PID registry + derived signals +
  event detection, maintenance status engine (`UNKNOWN`/`CURRENT`/`DUE_SOON`/`DUE`/
  `OVERDUE`), service ledger, parts intelligence + fitment, build planner.

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
