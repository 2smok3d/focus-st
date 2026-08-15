# Digital Garage

A local-first **truth store** for one vehicle — a 2017 Ford Focus ST (VIN
`1FADP3L94HL223134`). It turns scattered receipts, FORScan scans, CAN dumps,
and forum lore into a single queryable database with **evidence grading** and a
**human-approval boundary** on every write that touches the car's record.

This is the backend companion to the [`garage.html`](../garage.html) dashboard
and the [Obsidian knowledge base](../docs). Where those are *read* surfaces,
this is the *system of record*: Postgres for structured facts, FastAPI for local
HTTP, and an MCP server so Claude (or any MCP client) can query the car without
being able to silently rewrite its history.

## Why it exists

The knowledge base has a rule: every claim carries a **verification state**
(`UNVERIFIED → CORROBORATED → OEM-VERIFIED → VEHICLE-VERIFIED`) and every source
carries an **authority rank** (1 OEM … 6 unknown). Markdown can't enforce that.
A database can. The domain layer here refuses to let a rank-5 forum post
overwrite an OEM-verified spec, and refuses to mutate the vehicle record without
an explicit `approved_by` — so an agent can *propose* but a human *commits*.

## Architecture

```
                    ┌─────────────────────────────┐
   FORScan / CSV ──▶│  parsers.py                 │
   candump / CAN ──▶│  raw-preserving + SHA-256   │──┐
   receipts ───────▶│  normalizer                 │  │
                    └─────────────────────────────┘  │
                                                      ▼
   ┌──────────┐   read      ┌──────────────┐   ┌──────────────┐
   │ MCP      │────────────▶│ domain.py    │──▶│  Postgres    │
   │ (Claude) │◀── propose ─│ authority +  │   │  truth store │
   └──────────┘   only      │ verification │   └──────────────┘
                            │ maint-due    │          ▲
   ┌──────────┐   read/     │ parts-links  │          │
   │ FastAPI  │◀───write────│              │──────────┘
   │ (local)  │  (approved) └──────────────┘
   └──────────┘
```

- **Postgres** — the store. Schema in [`db/schema.sql`](db/schema.sql); the ORM
  mirror in [`app/models.py`](app/models.py).
- **`app/domain.py`** — the rules: source-authority resolution, verification-state
  ordering, maintenance-due math, and parts search-link generation. No I/O.
- **`app/parsers.py`** — ingest. Every raw artifact is stored byte-for-byte with
  its SHA-256 before anything is normalized, so a parse can always be re-run.
- **`app/main.py`** — FastAPI. Reads are open; writes to the vehicle record
  require an approval token.
- **`app/mcp_server.py`** — FastMCP tools. **Read-first**: query tools are free;
  the only write tool *proposes* a change for human approval, it never commits.
- **`app/cli.py`** — operator console (seed, ingest, list due, approve proposals).

## Quick start

```bash
cd digital-garage
cp .env.example .env                 # defaults work for local Docker
docker compose up -d db              # Postgres on :5433
pip install -r requirements.txt
python -m app.cli init               # create schema
python -m app.cli seed               # load the Focus ST
python -m app.cli due --miles 62000  # what's overdue at 62k?
uvicorn app.main:app --reload        # http://localhost:8000/docs
```

Or run the whole thing in Docker:

```bash
docker compose up --build            # db + api together
```

## Receipts in, dashboard out

The store is wired to both sides of the vision:

**Gmail receipts → proposals.** A purchase or service receipt (posted by the
Gmail Apps Script to `POST /receipts`, or filed with `python -m app.cli receipt
email.txt`, or pasted to Claude via the `log_receipt` MCP tool) is parsed,
classified as a **parts purchase** or a **service event**, and filed as a
*pending proposal*. Nothing lands on the car's record until you approve it — the
receipt path honors the same boundary as everything else.

**Truth store → markdown/JSON.** `python -m app.cli export` regenerates
`MODS.md` (the file the PWA references) and `data/export/garage.json` (a single
feed the dashboard can read instead of inline data) from the database. Postgres
becomes the source; the markdown surfaces become build artifacts, so they never
drift. `GET /export/snapshot` returns the same JSON live.

```bash
python -m app.cli receipt receipt.txt      # → pending proposal
python -m app.cli approve 1 --by "Brandon" # → lands as parts/service_event
python -m app.cli export --miles 62000     # → MODS.md + garage.json
```

## Datalog analysis

Ingest a FORScan/CSV datalog and get a session summary instead of a wall of rows:

```bash
python -m app.cli ingest datalog pull.csv --miles 86500
python -m app.cli sessions          # list ingested sessions
python -m app.cli summary 1         # channel stats + findings
```

The summarizer recognizes turbo-relevant channels by name (boost vs. target,
knock, misfire, fuel-trim drift, coolant/charge-air temps, rail pressure) and
emits plain-language findings — "Knock activity … correlate with fuel/octane
before another WOT pull", "Charge/intake air peak 61 C — heat-soak territory".
Also at `GET /sessions/{id}/summary` and the `session_summary` MCP tool.

## Publishing (auto-export)

After any approval the store re-generates `MODS.md` + `garage.json` so the
served dashboard stays current (set `DG_AUTO_EXPORT=0` to disable). To push the
refreshed snapshot to GitHub Pages in one step:

```bash
python -m app.cli publish --push     # export → git commit → push
```

## Recall checker

The store seeds the Focus ST's known safety campaigns (EVAP purge 18S32 / 26S40,
seatback, hatch-latch) as a baseline and can refresh against the free **NHTSA**
recallsByVehicle API:

```bash
python -m app.cli recalls --refresh          # re-seed known + fetch NHTSA
python -m app.cli recall-status 18S32 completed   # once confirmed at a dealer
```

Per-VIN completion isn't in the free API, so campaigns stay `unknown` until you
confirm them — the dashboard shows them as ⚪ "verify by VIN". Also at
`GET /recalls`, `POST /recalls/refresh`, and the `check_recalls` MCP tool.

## The approval boundary

Reads never require approval. Writes that change the vehicle's record — a new
mod, a resolved DTC, a corrected spec — go through `propose_change()`, which
writes a row to `change_proposals` with status `pending`. A human runs:

```bash
python -m app.cli proposals          # review the queue
python -m app.cli approve <id> --by "Brandon"
```

Only then does the change land, stamped with who approved it. The MCP server
exposes *only* the propose side to Claude; the approve side is CLI/human-only.
That's the whole safety model: **an agent can see everything and change nothing
without a name on it.**

## Layout

| Path | What |
|------|------|
| `docker-compose.yml` | Postgres + API services |
| `db/schema.sql` | Canonical DDL (source of truth for the schema) |
| `app/config.py` | Settings from env |
| `app/db.py` | Engine + session |
| `app/models.py` | SQLAlchemy 2.0 ORM |
| `app/domain.py` | Authority, verification, maintenance-due, parts links |
| `app/parsers.py` | FORScan / CSV / candump normalizers, SHA-256 raw store |
| `app/seed.py` | Focus ST seed data (specs, intervals, known issues, sources) |
| `app/main.py` | FastAPI app |
| `app/mcp_server.py` | FastMCP read-first server |
| `app/cli.py` | Operator CLI |
| `tests/` | Domain-logic unit tests (no DB needed) |

## Scope

One car, local use, no auth beyond the approval boundary. It is deliberately
small: a durable place to keep *true* things about *this* vehicle, with the
grading discipline the knowledge base already assumes. Not a fleet system, not a
cloud service, not a tuning platform.
