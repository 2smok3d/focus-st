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

- **Phase 2 — Reference dataset.** Normalize the Focus ST knowledge base (specs,
  torques, fluids, intervals, known traits) into claims with citations. Migrate
  existing Markdown *facts* into structured claims; keep the Markdown as a
  projection. Store citations + document/page/section metadata and only
  **permissible excerpts** — never copy protected service manuals into the repo.

- **Phase 3 — Digital Twin.** Component *state* on the actual car (`STOCK` /
  `MODIFIED` / `REMOVED` / `PLANNED` / `FAILED`), reference-vs-actual diff, and mods
  attached to the components they change.

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
