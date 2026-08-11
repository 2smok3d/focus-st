# Supported Integration Stack — FFST Digital Garage

Date: 2026-08-11

This file is additive. It does not replace or modify any pre-existing project file.

## 1. Vehicle diagnostic edge

### FORScan
Primary Ford-specific scan/configuration application. Use it as the authoritative operator-facing Ford diagnostic tool for module discovery, Ford-specific DTCs, service functions, configuration backups, PID logging and supported module procedures.

Garage policy:
- import FORScan reports/logs/configuration backups as immutable evidence;
- normalize DTC/PID/session metadata into PostgreSQL;
- never silently clear DTCs or overwrite module configuration;
- module writes, programming and service functions remain explicit human actions.

### OBDLink EX
Preferred wired shop interface for Windows/FORScan work where a stable physical connection matters.

### OBDLink MX+
Preferred wireless/mobile interface for road logging and app-based diagnostics where Bluetooth convenience is useful. OBDLink documents OEM diagnostics support and its app can expose DTC, freeze-frame, PID and monitor-test information for supported vehicles.

## 2. Programmable OBD layer

### python-OBD
Role:
- generic SAE OBD-II acquisition;
- portable PID scripts;
- quick health checks;
- normalized JSON/CSV output feeding the garage importer.

Do not treat generic OBD-II as a replacement for FORScan's Ford-specific module coverage.

## 3. CAN engineering layer

### python-can
Canonical Python CAN abstraction for capture, replay in a safe test environment, log conversion, filtering, and integration with DBC decoding tools.

### SocketCAN
Canonical Linux CAN transport. Linux exposes CAN controllers as network interfaces through the PF_CAN socket family. Use SocketCAN as the underlying Linux interface for CAN capture and analysis tooling.

### can-utils
Use for:
- `candump` capture;
- `cansniffer` exploratory analysis;
- format conversion/replay only in bench/vcan environments unless an explicit vehicle-TX approval exists;
- basic interface testing.

### SavvyCAN
Use as an interactive reverse-engineering and visualization workbench for recorded captures, signal exploration and DBC-assisted analysis.

### Wireshark
Use for packet-level analysis when CAN/ISO-TP captures are available in a supported format. Treat it as analysis tooling, not as the vehicle control layer.

### DBC/cantools strategy
Decoded signals must retain:
- raw arbitration ID;
- raw payload;
- capture timestamp;
- bus/interface;
- DBC file/hash/version;
- decoded signal/value/unit;
- decode warning/confidence.

A DBC definition is evidence, not unquestioned truth. Unknown/community-derived signal definitions require provenance.

## 4. Safety boundary

Default state:

```text
vehicle.read = allowed
vehicle.capture = allowed
vehicle.clear_dtc = blocked
vehicle.module_write = blocked
vehicle.flash = blocked
vehicle.can_tx = blocked
vehicle.risky_actuator_test = approval-required
```

The garage may analyze and recommend. It may not autonomously perform destructive or state-changing vehicle operations.

## 5. Claude / MCP integration layer

The garage MCP server should expose automotive concepts while delegating infrastructure operations to dedicated MCP servers.

### Automotive Garage MCP
Primary semantic interface:

```text
garage.get_vehicle
garage.get_current_build
garage.get_maintenance_history
garage.get_due_service
garage.get_parts
garage.get_costs

diagnostics.get_cases
diagnostics.get_dtcs
diagnostics.get_session
diagnostics.compare_sessions
diagnostics.lookup_dtc

telemetry.list_sessions
telemetry.get_pid_series
telemetry.get_can_capture
telemetry.decode_capture

manual.search
manual.lookup_procedure
manual.lookup_torque_spec
manual.lookup_fluid_spec

community.search_claims
community.get_consensus
community.get_conflicts

parts.search_replacements
parts.search_upgrades
parts.generate_marketplace_links
```

### GitHub MCP
Use for source code, issues, pull requests, release history and the garage's versioned schemas/docs. Existing `/ffst` files are read-only inputs; new OpenAI build work remains isolated under `digital-garage-openai/`.

### Filesystem MCP
Use for the local synchronized garage filesystem and raw evidence vault. Raw evidence paths should be immutable after ingestion except for administrative relocation/copy outside the canonical evidence store.

### SQLite / PostgreSQL MCP
PostgreSQL is the production normalized data store. SQLite is useful for portable/offline snapshots and tooling tests.

Recommended separation:
- PostgreSQL: canonical structured vehicle data;
- SQLite: export/portable/test database;
- filesystem: large/raw binary artifacts and logs;
- Git: schemas, source code, documentation and small curated datasets.

### Docker MCP
Use for container lifecycle, logs, health checks and controlled development/deployment tasks.

### Playwright MCP
Use for UI verification and browser automation against the garage dashboard and public technical sources when legally and technically appropriate. Do not use it to bypass site controls.

### Terminal/Bash MCP
Use for trusted local commands, import pipelines, Git operations, database tooling, SocketCAN utilities and test execution. Vehicle-state-changing commands require the same safety gates as API/MCP vehicle tools.

### Memory MCP
Use for durable assistant context such as project conventions, diagnostic preferences and workflow defaults. Do not make Memory the authoritative store for mechanical facts; mechanical truth must remain evidence-backed in the garage database/knowledge registry.

### REST API MCP
Use the FastAPI garage service as the stable integration boundary for external clients. MCP tools should call typed service methods rather than duplicating business logic.

### Home Assistant MCP
Optional automation layer for garage/shop environment:
- ambient/shop temperature and humidity;
- battery maintainer smart-plug state;
- garage-door state;
- tool/charger energy monitoring;
- maintenance reminders and presence-aware notifications.

Home Assistant must not be used as an autonomous ECU/CAN control path.

### Google Drive MCP
Use for the durable user-facing knowledge/evidence vault. Existing `/FOST` material is read-only source material; all OpenAI-created material lives inside `DIGITAL GARAGE — OPENAI BUILD`.

## 6. Recommended data flow

```text
2017 Focus ST
   │
   ├─ FORScan ───────┐
   ├─ OBDLink ───────┤
   ├─ python-OBD ────┤
   └─ SocketCAN ─────┤
                     ▼
              RAW EVIDENCE VAULT
                     │
             Diagnostic Normalizer
                     │
                     ▼
                 PostgreSQL
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       FastAPI    Dashboard   MCP Server
          │                     │
          │              Claude / ChatGPT
          │                     │
          └──── GitHub / Drive / Filesystem
```

## 7. Provenance requirements

Every imported or researched fact should support these fields where practical:

- `source_id`
- `source_class`
- `source_uri`
- `title`
- `publisher/author`
- `retrieved_at`
- `vehicle_scope`
- `model_year_scope`
- `claim_text`
- `confidence`
- `corroboration_count`
- `conflicts_with`
- `raw_evidence_hash`
- `review_status`

## 8. Current primary-source validation

Independent research confirmed from Ford's 2017 Focus ST supplement that the platform uses the Getrag-Ford MMT6 6-speed manual transaxle, 2.0L GTDI EcoBoost, coil-on-plug ignition, twin independent variable cam timing, and a single-scroll turbo. Ford publishes a 0.027–0.031 in spark-plug gap and Motorcraft references including FA-1908 air filter, FL-910-S oil filter, SP-537/CYFS12Y2 plugs and FP-70 cabin filter.

The build should prefer those Ford-published values over conflicting community or legacy notes unless later vehicle-specific evidence proves a supersession or configuration difference.
