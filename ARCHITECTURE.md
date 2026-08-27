# Digital Garage — Target Architecture

> This is the forward-looking blueprint for transforming the current `focus-st` repository into **Digital Garage**: a vehicle-agnostic automotive intelligence platform designed for a future mobile/web application.
>
> This document is the target architecture. Existing files remain in place until they are mapped, migrated, verified, and retired.

## 1. Product definition

**Digital Garage** is an application and data platform for deeply modeling vehicles, their systems, components, parts, history, maintenance, diagnostics, projects, documents, and telemetry.

The repository currently centers on a Focus ST, but the target system treats every vehicle as a first-class domain with the same depth of modeling. Vehicle-specific behavior is expressed through configuration, capabilities, systems, and reference data—not by creating a different architecture for each vehicle.

The product has four promises:

1. **Know the machine** — structured vehicle identity, configuration, systems, components, and history.
2. **Know the evidence** — every important fact has provenance and an explicit knowledge state.
3. **Understand what is happening** — diagnostics combine codes, symptoms, telemetry, configuration, history, and reusable failure knowledge.
4. **Keep everything connected** — parts, repairs, projects, diagnostics, documents, and observations reference the same underlying entities.

## 2. Architectural principles

### One canonical fact
A fact is stored once in the canonical model. UI pages, Markdown, JSON, reports, search indexes, and exports are projections or caches.

### Vehicle first
Every vehicle has a complete digital-twin domain. No vehicle is a second-class “lite” implementation.

### Common core, extensible systems
All vehicles share core concepts, but each vehicle can add or omit systems according to its machine type and capabilities.

### Evidence before assertion
Reference claims, vehicle observations, imported measurements, and human statements are distinguishable. Inference is never silently promoted to fact.

### Raw data is preserved
Imported diagnostic artifacts remain byte-for-byte recoverable with integrity hashes. Parsing and normalization can improve later without destroying the source.

### Diagnostics are guided reasoning
The system should rank hypotheses and recommend the next useful test. It should not jump directly from a code to a replacement part.

### Human approval for vehicle-changing actions
The platform may analyze and propose. Changes to canonical vehicle state require explicit human approval and post-change verification.

### Simple presentation, rich backend
The app should feel simple even when the underlying model is sophisticated.

## 3. Product layers

```text
                     DIGITAL GARAGE APP
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
              MOBILE                  WEB
                 │                     │
                 └──────────┬──────────┘
                            ▼
                           API
                            │
                            ▼
                 DIGITAL GARAGE CORE
                            │
      ┌─────────────────────┼─────────────────────┐
      ▼                     ▼                     ▼
   VEHICLES             KNOWLEDGE            OPERATIONS
      │                     │                     │
      ├─ state              ├─ claims             ├─ maintenance
      ├─ systems            ├─ evidence           ├─ diagnostics
      ├─ parts              ├─ procedures         ├─ work orders
      ├─ history            └─ DTC/failure modes  ├─ projects
      └─ telemetry                                └─ inventory
                            │
                            ▼
                     INGEST / INTEGRATION
                            │
        ┌───────────────────┼────────────────────┐
        ▼                   ▼                    ▼
      OBDLink            FORScan             Torque Pro
        │                   │                    │
        └───────────────────┼────────────────────┘
                            ▼
                     NORMALIZATION LAYER
                            │
                            ▼
                       CANONICAL DATA
```

## 4. Vehicle domain model

Every vehicle follows the same high-level contract:

```text
Vehicle
├── Identity
├── Configuration
├── Reference Variant
├── Capabilities
├── Systems
│   └── Components
│       └── Relationships
├── Current State
├── State History
├── Parts
├── Inventory
├── Modifications
├── Maintenance
├── Repairs / Work Orders
├── Diagnostics
├── Telemetry
├── Projects
├── Documents
├── Media
├── Measurements
└── Activity History
```

### Identity
VIN or other identifier, year, manufacturer, model, trim, market, ownership metadata, and machine type.

### Configuration
What the machine is actually equipped with: engine, transmission, control systems, major hardware, calibration, and installed components.

### Capabilities
What this machine can support. Examples: OBD, CAN, ECU telemetry, carbureted fuel system, premix, ABS, hybrid system, etc.

Capabilities drive the UI and tool availability so the app does not offer an OBD workflow to a machine that cannot provide OBD data.

## 5. Reference model vs machine state

Digital Garage separates **what a vehicle type is supposed to be** from **what this particular machine is now**.

```text
REFERENCE
Manufacturer
   ↓
Platform
   ↓
Variant
   ↓
Engine / Transmission
   ↓
Systems / Components

ACTUAL MACHINE
Vehicle
   ↓
Current component state
   ↓
Installed parts / modifications
   ↓
Measurements / observations
   ↓
History over time
```

The existing backend already contains this separation through the vehicle-variant reference model, provenance claims, component states, and capability profiles. The redesign should preserve and generalize it rather than recreate it. `digital-garage/db/schema_v2.sql` and `schema_v3.sql` are the existing foundations.

## 6. Diagnostic intelligence

Diagnostics are a first-class domain, not merely a DTC lookup page.

```text
Input
├── DTCs
├── Symptoms
├── Freeze-frame data
├── Telemetry
├── Visual observations
├── Vehicle configuration
├── Modifications
├── Previous repairs
└── Historical cases
        │
        ▼
Evidence normalization
        │
        ▼
Failure-mode candidates
        │
        ▼
Hypothesis ranking
        │
        ▼
Best next test
        │
        ▼
Test result
        │
        ├── supports
        ├── refutes
        └── inconclusive
        │
        ▼
Updated ranking
        │
        ▼
Finding / repair proposal
        │
        ▼
Human approval
        │
        ▼
Repair + verification
        │
        ▼
Historical case
```

A DTC record should connect to reusable knowledge:

```text
DTC
├── meaning
├── affected systems
├── symptoms
├── known failure modes
├── diagnostic tests
├── expected observations
├── disconfirming observations
├── applicable variants
├── related components
└── historical cases
```

The diagnosis engine should distinguish between:

- **Known** — supported by authoritative evidence.
- **Observed** — directly measured or seen on the vehicle.
- **Inferred** — reasoned from evidence but not directly observed.
- **Recommended** — an action suggested by the system.
- **Unknown** — insufficient evidence.

The existing workbench, failure-mode library, test library, provenance engine, anomaly detection, integrity checks, and telemetry pipeline are the starting point for this model.

## 7. Data acquisition and integrations

All external tools feed a common ingestion pipeline.

```text
External tool
   ↓
Adapter
   ↓
Raw artifact store
   ↓
Parser
   ↓
Normalization
   ↓
Canonical channels / events / DTCs / observations
   ↓
Vehicle history + diagnostics
```

Initial adapter targets:

| Source | Typical data | Target canonical domain |
|---|---|---|
| OBDLink | DTCs, PIDs, reports, CSV logs | diagnostics + telemetry |
| FORScan | module reports, DTCs, PID logs, CAN/scan artifacts | diagnostics + telemetry + evidence |
| Torque Pro | PID logs / CSV exports | telemetry |
| Generic CSV | time-series data | telemetry |
| CAN logs | raw frames | telemetry / CAN |
| Manual entry | observations, service, repairs | vehicle history |

Every import records at least:

```text
source_tool
source_format
vehicle
captured_at
ingested_at
sha256
raw_artifact
parser_version
normalization_version
```

## 8. Canonical telemetry model

External names are normalized into stable Digital Garage channels.

Example:

```text
Torque Pro       ─┐
OBDLink          ─┼──→ engine_speed
FORScan          ─┘
```

A canonical channel can be:

```text
canonical_name
unit
source_aliases
description
normal_range
warning_range
vehicle applicability
derived formula
```

Raw measurements remain immutable. Derived signals and detected events reference raw inputs.

The current repo already has this pattern in `telemetry_channels`, `telemetry_events`, and the datalog parser.

## 9. Parts and fitment

A part should be a reusable entity rather than a line of Markdown duplicated across multiple views.

```text
Part
├── identity
├── manufacturer
├── part number(s)
├── category
├── specifications
├── source links
├── fitment
├── compatibility notes
└── evidence
```

Vehicle relationship:

```text
Part
   ├── fits → Vehicle Variant
   ├── installed on → Vehicle
   ├── replaces → Stock Component
   ├── required by → Project
   └── referenced by → Repair
```

Installed parts are part of machine state. Catalog/research data should not be confused with installed configuration.

## 10. Maintenance and workshop model

Maintenance is a timeline, not a checklist.

```text
Maintenance Rule
       ↓
Due calculation
       ↓
Work item / recommendation
       ↓
Parts + tools + procedure
       ↓
Work order
       ↓
Repair performed
       ↓
Post-repair verification
       ↓
Service history
```

The system should support mileage-based, time-based, usage-based, and condition-based maintenance as the data becomes available.

The existing maintenance engine, work-order lifecycle, job-readiness logic, and mandatory verification are retained as core building blocks.

## 11. Projects

Projects organize work without becoming a second database.

A project references canonical parts, procedures, work orders, costs, diagnostics, and vehicle state.

```text
Project
├── objective
├── scope
├── dependencies
├── parts → Part
├── work orders → WorkOrder
├── diagnostics → DiagnosticCase
├── costs
├── documents
├── measurements
└── outcome
```

`PROJECTS.md` should eventually be a navigation/projection layer, not a parallel source of project state.

## 12. Documents and knowledge

Knowledge is organized by purpose:

```text
Reference knowledge
    = reusable facts, procedures, failure modes, specifications

Vehicle knowledge
    = observations, configuration, history, vehicle-specific findings

Project documentation
    = how to perform a planned piece of work

Source artifacts
    = original receipts, logs, scans, documents, images
```

These categories should not be mixed just because all of them are “notes.”

## 13. User experience

The application should hide the complexity until it is useful.

Primary navigation:

```text
HOME
├── Vehicles
├── Diagnostics
├── Maintenance
├── Projects
├── Parts
├── Knowledge
├── Data / Imports
└── Search
```

Vehicle view:

```text
VEHICLE
├── Overview
├── Systems
├── Configuration
├── Maintenance
├── Diagnostics
├── Telemetry
├── Parts
├── Modifications
├── Projects
├── Documents
├── Media
└── History
```

Universal search should return entities, not just matching text:

```text
Search: “P0299”

DTC
Failure modes
Diagnostic tests
Vehicle cases
Relevant components
Telemetry events
Repairs
Reference documents
```

## 14. Repository target

The current repository is not immediately renamed or flattened. The target direction is:

```text
focus-st/
├── README.md
├── ARCHITECTURE.md
├── CLAUDE.md
├── DECISIONS.md
│
├── .github/
│   ├── workflows/
│   └── scripts/
│
├── digital-garage/
│   ├── app/
│   ├── db/
│   └── tests/
│
├── web/
│   ├── app/
│   ├── tools/
│   └── vehicles/
│
├── data/
│   ├── reference/
│   └── vehicles/
│       ├── focus-st/
│       ├── zzr600/
│       ├── rz350/
│       ├── tz250/
│       └── toyota-pickup/
│
└── docs/
    ├── knowledge/
    ├── projects/
    ├── procedures/
    └── vehicle-guides/
```

This is a **target state**, not an instruction to move everything immediately. The existing structure must first be mapped against this model.

## 15. Redundancy rules

The redesign explicitly prohibits duplicate authoritative representations.

### Never maintain independently

```text
same vehicle fact in multiple canonical files
same part in multiple catalogs
same project status in multiple trackers
same DTC meaning in multiple databases
same telemetry channel under several internal names
```

### Allowed projections

```text
Database → JSON feed
Database → dashboard
Database → Markdown report
Database → search index
Database → generated compendium
```

Generated outputs must identify themselves as generated and must never become a second source of truth.

## 16. Migration strategy

No destructive “big bang” rewrite.

### Stage 1 — Inventory
Map every file, table, data source, workflow, and generated artifact.

### Stage 2 — Ownership
Assign each piece of information a canonical owner.

### Stage 3 — Normalize
Create shared entities for vehicles, systems, components, parts, diagnostics, telemetry, projects, and sources.

### Stage 4 — Migrate
Move existing data into the canonical model with provenance preserved.

### Stage 5 — Rebuild projections
Generate web views, JSON, Markdown, search indexes, and reports from canonical data.

### Stage 6 — UX
Replace repository-oriented navigation with application-oriented navigation.

### Stage 7 — Integrations
Add import adapters for OBDLink, FORScan, Torque Pro, and other tools.

### Stage 8 — Intelligence
Layer diagnostic reasoning, maintenance intelligence, anomaly detection, research assistance, and AI explanations over the structured model.

### Stage 9 — App extraction
Reuse the same core and API in a mobile/web application.

## 17. Definition of success

Digital Garage is successful when:

- Every vehicle is equally deep and first-class.
- FoST information exists under the FoST vehicle domain rather than scattered globally.
- Facts have one canonical owner.
- External tool data can be imported without bespoke database silos.
- DTCs connect to systems, components, tests, causes, fixes, and historical cases.
- The diagnostic engine can recommend a useful next test and explain why.
- Repairs can be verified and become historical evidence.
- The UI is simpler than the underlying model.
- Generated artifacts can be deleted and recreated without losing information.
- The data model can support a future mobile/web app without another rewrite.
