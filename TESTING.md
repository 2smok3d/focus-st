# Testing

This file consolidates testing conventions that already exist in
[`digital-garage/docs/BUILD-PLAN.md`](digital-garage/docs/BUILD-PLAN.md) §5 —
it does not introduce new policy. That file is the source of truth; this page
makes it discoverable from the repo root.

## Running the suite

```bash
cd digital-garage
docker compose up -d          # Postgres 16
python -m app.cli init        # applies the full schema chain (v1 → latest)
pytest tests/ -q              # full suite, DB-backed tests included
```

Without a reachable Postgres, DB-backed tests `skipif` — the pure-engine
suite still runs on its own:

```bash
DG_DB_PORT=5999 pytest tests/ -q   # pure suite only, no DB needed
```

CI runs the full DB-backed suite automatically on every PR/push
(`.github/workflows/ci.yml`) by standing up a real Postgres 16 service
container — this is not simulated or mocked.

## What's covered

As of 2026-08-25: 33 test files under `digital-garage/tests/`, covering every
domain module (diagnostics, telemetry, anomaly detection, RUL, fitment,
corroboration, integrity checks, the reference/provenance model, etc.) plus a
`garage.json` schema validator (`.github/scripts/validate_garage_json.py`)
run as its own CI job.

## What's not covered (tracked, not hidden)

Per the Phase 0 external audit recorded in `BUILD-PLAN.md` §7:

- No property-based or fuzz testing.
- No lint/type-check step in CI (`ruff`/`mypy` are candidates, not yet added).
- No dependency/secret-scanning step in CI (`pip-audit`/`gitleaks` are
  candidates, not yet added).
- No hardware-in-the-loop or mock-vehicle simulation testing — there's no
  real vehicle-write path yet to test against.

## The per-unit workflow (for any new feature)

Every build unit in this repo follows the same fixed cycle
(`BUILD-PLAN.md` §5):

1. **Reset** the working branch from `origin/master`.
2. **Build**: schema (additive) → models → service/engine → CLI/MCP/API → tests.
3. **Verify**: full `pytest` with a DB, the pure suite without one, and
   `cli init` idempotency. Render-check any web change headless.
4. **Document**: update `V2-ARCHITECTURE.md` and the `BUILD-PLAN.md` ledger.
5. **Ship**: commit → push → draft PR → poll CI → un-draft → merge → reset branch.

Small, reviewable, green — one unit, one PR.
