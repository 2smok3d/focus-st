# Digital Garage — OpenAI Build

Professional read-first mechanic's garage for a 2017 Ford Focus ST, designed to scale to multiple vehicles.

## Goals
- Preserve raw diagnostic evidence unchanged.
- Normalize FORScan, OBD-II, OBDLink and SocketCAN/candump data.
- Separate OEM, regulatory, manufacturer, technical-reference, community-consensus and anecdotal evidence.
- Track maintenance, repairs, OEM replacements, performance replacements, costs, warranties and verification.
- Expose safe read tools through FastAPI and MCP.
- Keep destructive vehicle operations disabled by default.

## Quick start
1. Copy `.env.example` to `.env`.
2. Run `docker compose up --build`.
3. Open `http://localhost:8080/docs`.
4. Put diagnostic files in `runtime-data/inbox/`.
5. Import with `docker compose exec garage python -m garage.cli ingest /data/inbox/<file>`.
6. Run MCP over stdio with `docker compose exec -i garage python -m garage.mcp_server`.

Existing Drive `/FOST` content and all pre-existing repository paths are treated as read-only sources. New implementation lives only under `digital-garage-openai/`.