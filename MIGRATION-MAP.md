# Digital Garage — Migration Map

> Working map for consolidating the current `focus-st` repository into the Digital Garage architecture in `ARCHITECTURE.md`. This file is intentionally operational and will be retired or merged once migration is complete.

## Current reality

The repository already contains the main building blocks of Digital Garage:

- Fleet registry: `data/fleet.json`
- Per-vehicle data: `data/vehicles/<slug>/`
- Shared DTC reference: `data/dtc-codes.json`
- PostgreSQL schema chain: `digital-garage/db/schema.sql` + `schema_v2.sql` … `schema_v13.sql`
- Reference/provenance model: `vehicle_variants`, `systems`, `components`, `claims`, `claim_evidence`
- Temporal machine state: `component_states` + capabilities
- Diagnostic workbench: cases, hypotheses, tests, findings
- Failure-mode and diagnostic-test library
- Telemetry channels and event detection
- Datalog ingestion with raw SHA-256 preservation
- Trends, anomalies, RUL, integrity, fitment, corroboration, and research queue
- Vehicle intelligence projection: `intel.json`
- Web/PWA interfaces
- GitHub Actions CI
- Human-facing Obsidian/project documentation

## Disposition rules

| Current area | Target role | Disposition |
|---|---|---|
| `digital-garage/db/*` | Canonical structured data model | KEEP + evolve |
| `digital-garage/app/*` | Core platform/services | KEEP + reorganize by domain when stable |
| `digital-garage/tests/*` | Platform validation | KEEP |
| `data/fleet.json` | Fleet configuration / seed/projection input | KEEP temporarily; reduce authority over time |
| `data/vehicles/*` | Vehicle projections / migration sources | KEEP during migration; gradually make generated |
| `data/dtc-codes.json` | Shared diagnostic reference projection/seed | KEEP, move toward canonical diagnostic knowledge |
| `web/vehicles/*` | Vehicle UI projections | KEEP; rebuild around universal vehicle shell |
| `web/tools/*` | Shared UI/tools | KEEP selectively; fold into app navigation |
| `docs/VEHICLE.md` | Focus ST legacy master note | KEEP during migration; split state vs reference |
| `docs/PROJECTS.md` | Project index/projection | KEEP but shrink |
| `docs/MAINTENANCE.md` | Human-facing service history | KEEP during migration; canonical state moves to DB |
| `docs/SETUP.md` | Cross-system setup notes | MERGE into platform/app setup documentation |
| `docs/FOST-COMPLETE.md` | Generated compendium | GENERATED / ARCHIVE |
| `docs/FOST-CLEANUP-MAP.md` | External Drive cleanup history | ARCHIVE / RETIRE |
| `TESTING.md` | Test discoverability | KEEP if useful; source policy remains build plan |
| `SECURITY.md` | Safety/security discoverability | KEEP if useful; source policy remains governing docs |
| `CLAUDE.md` | AI operating rules | KEEP |
| `DECISIONS.md` | Durable decisions | KEEP, but future decisions should describe Digital Garage architecture rather than session archaeology |
| `digital-garage/docs/V2-ARCHITECTURE.md` | Previous architecture generation | HISTORICAL; merge durable principles into `ARCHITECTURE.md` and later archive |
| `digital-garage/docs/BUILD-PLAN.md` | Implementation history / backlog | KEEP as history until a cleaner project-management model replaces it |

## Target authority model

```text
Canonical Digital Garage model
        │
        ├── reference knowledge
        ├── vehicle state
        ├── parts / fitment
        ├── maintenance / work
        ├── diagnostics
        ├── telemetry
        ├── projects
        └── source provenance
                 │
                 ▼
          generated projections
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
      Web       JSON      Docs
```

## Vehicle migration contract

Every vehicle must ultimately expose the same application contract:

```text
identity
configuration
capabilities
systems
components
state
parts
maintenance
repairs
modifications
projects
diagnostics
telemetry
documents
media
history
```

The contents inside those domains can differ by machine type.

## Immediate consolidation targets

### 1. Stop competing truth stores

Current documentation describes both `PARTS.md` and PostgreSQL as authoritative in different places. The target is one canonical structured owner, with `PARTS.md` becoming a generated or transitional view.

### 2. Separate reference knowledge from vehicle state

`VEHICLE.md` currently mixes stable specifications, current configuration, open issues, maintenance, and research corrections. Migrate those concepts into the appropriate canonical domains.

### 3. Turn project documents into instructions, not databases

Project docs should explain how to perform work. Status, cost, parts relationships, diagnostics, and history should reference canonical entities rather than maintaining parallel state tables.

### 4. Normalize diagnostic inputs

All supported tools feed one ingestion contract:

```text
OBDLink / FORScan / Torque Pro / CSV / CAN / manual
                    ↓
                 adapter
                    ↓
                raw store
                    ↓
                 parser
                    ↓
               canonical data
```

### 5. Replace vehicle-specific UI duplication

The current web pattern uses per-vehicle HTML modules. The target is one reusable vehicle shell populated by vehicle-specific data, capabilities, systems, and theme configuration.

### 6. Reduce documentation sprawl

Use the fewest documents that give clear navigation. Do not create a new index simply because an existing document is hard to find. Prefer links and generated views.

## Next migration sequence

1. Inventory every current source and consumer.
2. Define canonical owner for each entity.
3. Build/verify the universal vehicle model.
4. Migrate the five current vehicles to that contract.
5. Convert legacy Markdown/JSON to projections.
6. Consolidate diagnostic knowledge and code relationships.
7. Build integration adapters and a common import API.
8. Replace duplicated web pages with a universal application shell.
9. Retire obsolete documentation and generated duplicates.
10. Package the core into the future mobile/web application.

## Guardrail

No deletion is considered safe until the content has a canonical destination, its consumers are identified, and the replacement projection passes validation.
