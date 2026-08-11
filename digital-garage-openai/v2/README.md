# Digital Mechanic's Garage v2

This directory is a **new-file-only** enhancement layer for the OpenAI Digital Garage build. It does not replace, rename, move, or overwrite any pre-existing `/FOST` Drive data or pre-existing `2smok3d/focus-st` repository files.

## Mission

Turn the 2017 Ford Focus ST project into a professional digital mechanic's garage that combines:

- vehicle digital twin
- maintenance and repair history
- diagnostic case management
- FORScan / OBD-II / CAN evidence ingestion
- factory service/manual indexing
- DTC, symptom and test workflows
- parts, stock replacements and performance upgrades
- community/forum intelligence with provenance
- shop tools, consumables, measurements and work orders
- API + MCP access for ChatGPT / Claude
- PostgreSQL as the durable normalized data store
- immutable raw evidence vaults
- Docker-based deployment

## Design principles

1. **Raw evidence is immutable.** Never rewrite an imported diagnostic log, photo, CAN capture, receipt, manual or configuration backup. Hash it and store a normalized derivative.
2. **Facts have provenance.** A torque value, part number, failure-mode claim or procedure must carry source metadata and confidence.
3. **Source authority matters.** Default order: Ford/OEM > government/regulatory > component manufacturer > recognized technical reference > corroborated community consensus > individual anecdote.
4. **Conflicts remain visible.** The system does not silently merge incompatible claims.
5. **State is event-derived.** Installed parts, active issues and service status are computed from historical events so the complete vehicle history remains auditable.
6. **Vehicle writes are denied by default.** Clearing DTCs, module writes, flashing, risky actuator tests and arbitrary CAN transmission require explicit human approval and separate capability enablement.
7. **Existing user data is read-only source material.** New system artifacts live only under this isolated build tree.

## v2 package

`garage_v2/` implements the enhanced core:

- `domain.py` — canonical domain records and event types
- `provenance.py` — source registry, confidence scoring and conflict handling
- `ingest.py` — immutable evidence importer / parser registry
- `diagnostics.py` — diagnostic case engine
- `maintenance.py` — due-soon/overdue and service-history engine
- `parts.py` — OEM vs stock-equivalent vs performance replacement intelligence and shopping search links
- `connectors.py` — typed integration registry
- `api.py` — FastAPI surface
- `mcp_server.py` — read-first MCP tools and approval-gated write intents

## Turnkey deployment

```bash
cd digital-garage-openai/v2
docker compose -f docker-compose.v2.yml up --build
```

Expected services:

- API: `http://localhost:8082`
- PostgreSQL: internal `garage-db:5432`
- evidence volume: `/garage-data`

The service starts with **vehicle write capabilities disabled**.

## Primary integration stack

Vehicle edge: FORScan + OBDLink EX/MX+, python-OBD, python-can, SocketCAN, CAN-utils, SavvyCAN, Wireshark.

AI / operations: GitHub, Filesystem roots, PostgreSQL/SQLite, Docker, Playwright, Terminal/Bash, Memory, REST API, Home Assistant and Google Drive through controlled connectors.

## Research assumptions

Focus ST facts are not accepted merely because they already exist in the repo. Example: legacy repository content labels the transmission as MT82; Ford documentation identifies the Focus ST manual transaxle family as **MMT6**. v2 therefore treats legacy notes as evidence to verify, not canonical truth.
