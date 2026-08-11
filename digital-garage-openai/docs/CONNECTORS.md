# Connector Architecture

## Claude / MCP
Use the dedicated `digital-automotive-garage` MCP server for semantic garage tools. Keep general GitHub/filesystem/Drive MCP connections separate. The automotive MCP is the policy boundary that exposes vehicle concepts rather than raw unrestricted shell/CAN writes.

## Google Drive
Role: durable documents, research reports, manual/source index artifacts, receipts and human-readable evidence. Legacy `/FOST` remains read-only. New content belongs under `DIGITAL GARAGE — OPENAI BUILD`.

## GitHub
Role: executable source, schemas, tests and documentation. Existing root application remains read-only for this build; OpenAI work is isolated under `digital-garage-openai/` on `openai/digital-garage`.

## NHTSA
Use public datasets/APIs for model-level recall discovery. Mark candidate campaigns; confirm active vehicle status through a VIN-specific Ford/NHTSA lookup before asserting applicability.

## FORScan / OBDLink
FORScan remains the authoritative Ford-specific diagnostic/configuration application. Garage imports are derivatives for correlation/history; do not replace FORScan’s supported service functions with homegrown write logic.

## SocketCAN / python-can / CAN-utils
Use Linux SocketCAN for read/capture/replay only in controlled development. Use `vcan` for parser/UI development. Arbitrary transmission on a live vehicle network is outside default garage capability.

## PostgreSQL
Canonical structured store for vehicle observations, diagnostic sessions, maintenance, parts, source records and derived measurements. Large raw logs/manuals remain files with hashes/pointers rather than BLOB-heavy Git history.
