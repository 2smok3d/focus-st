# Digital Mechanic's Garage v2.1 — Turnkey Start

## Safety boundary

This stack starts **read-only toward the vehicle**. It does not implement automatic DTC clearing, module configuration, flashing, ECU writes, risky actuator commands or arbitrary CAN transmission.

## Start the garage

From repository root:

```bash
cd digital-garage-openai/v2
cp -n /dev/null .env.local 2>/dev/null || true
# Set strong local values if the stack will be reachable by anything beyond localhost:
export GARAGE_DB_PASSWORD='change-this-local-password'
export GARAGE_APPROVAL_TOKEN='leave-empty-until-write-intent-system-is-explicitly-enabled'
docker compose -f docker-compose.v21.yml up --build -d
```

Open:

- Garage home: `http://localhost:8082/`
- Unified dashboard: `http://localhost:8082/dashboard`
- Interactive engine bay: `http://localhost:8082/visual/engine-bay`
- OpenAPI / Swagger: `http://localhost:8082/docs`
- Health check: `http://localhost:8082/health`

PostgreSQL initializes automatically from `database/001_core_schema.sql` on a fresh volume.

## Import a diagnostic file

Local Python workflow:

```bash
cd digital-garage-openai/v2
python -m garage_v2.ingest /path/to/FORScan-or-CAN-file --data-root ./garage-data
```

The importer:

1. hashes the source with SHA-256;
2. creates an immutable raw evidence copy;
3. identifies supported format;
4. extracts DTCs, CSV PID measurements or SocketCAN candump frames where recognized;
5. emits normalized JSON separately;
6. never rewrites the source file.

Supported v2.1 baseline:

- FORScan-oriented text/log DTC extraction
- FORScan/generic CSV
- wide CSV datalogs
- SocketCAN `candump` text
- JSON metadata registration
- generic text-log DTC extraction

Future parser plugins should extend this registry rather than adding one-off import scripts.

## Current vehicle-state seed

The dashboard currently derives known state from read-only existing project evidence:

- Injen cold-air intake — installed/upgraded
- ram-air intake setup — installed/upgraded
- Torque Solutions rear motor mount — installed/upgraded
- Torque Solutions passenger-side mount — installed/upgraded
- upgraded battery — exact battery metadata pending
- hood scoops — installed
- active grille shutters and recorded actuator/motor — removed

Unverified components stay explicitly `unknown`, `stock_unverified`, or `service_history_required`; the garage does not invent a factory/current state.

## Update state without destroying history

The mature workflow is event-based:

```text
FACTORY_BASELINE
  → INSPECTION
  → INSTALL / REPLACE / UPGRADE / REMOVE
  → TEST
  → VERIFIED
  → later REPLACE / REMOVE / SUPERSEDE
```

Never overwrite the historical installation event just to change the current component value.

## Parts workflow

Use `/search/parts?q=...` or the Dashboard Parts tab. Amazon/eBay links are generated as **search links only**. A listing must still be checked for:

- exact model-year fitment
- engine/transmission fitment
- manufacturer part number
- supersession
- CARB/emissions status where relevant
- current vehicle modifications that affect compatibility

## Research workflow

A new fact is accepted only with source metadata. Preferred authority:

`Ford/OEM > NHTSA/government > component manufacturer > recognized technical reference > corroborated community consensus > individual anecdote`

Forum information is intentionally valuable, but it remains labeled community evidence until independently verified.

## Google Drive relationship

Existing `/FOST` is a read-only source library. New files/copies created by this project live under:

`/FOST/DIGITAL GARAGE — OPENAI BUILD`

The visual garage has its own copies of the four existing vehicle photos. Originals remain untouched.

## GitHub relationship

Existing `master` content is treated as a legacy source. The build lives on:

`openai/digital-garage`

under:

`digital-garage-openai/`

No merge into `master` is required to run or inspect the branch.

## CI

GitHub Actions workflow:

`.github/workflows/digital-garage-openai-v21-ci.yml`

checks Python compilation, core parser/state tests, FastAPI importability, JSON validity and Docker Compose rendering.
