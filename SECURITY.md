# Security & Safety

This file consolidates rules that already exist elsewhere in this repository
and its governing project — it does not introduce new policy. See the linked
sources for full detail; this page is a map, not a duplicate.

## The automotive safety boundary

INFORMATION → ANALYSIS → RECOMMENDATION → SIMULATION → ACTION

This platform enforces the boundary structurally, not by convention:

- **No agent path mutates canonical truth.** The only write an agent can make
  is a *proposal*; a single approval path (`service.approve_proposal`, a human
  name required) is the only mutator. See
  [`digital-garage/docs/BUILD-PLAN.md`](digital-garage/docs/BUILD-PLAN.md) §2.
- **No ECU write, flash, or actuator-command code exists anywhere in this
  repository.** Confirmed by direct source audit (2026-08-25) — this isn't a
  policy statement alone, it's the observed state of the codebase.
- **Verdicts are monotonic and computed, never asserted.** A claim's trust
  grade (`UNVERIFIED → CORROBORATED → OEM_VERIFIED → VEHICLE_VERIFIED`) is
  derived from its evidence; weaker evidence never overrides stronger.
- Full governing rules: [`CLAUDE.md`](CLAUDE.md) and the parent project's
  `SAFETY-BOUNDARIES.md`.

## Data handling

- Raw diagnostic/telemetry artifacts are hashed (SHA-256) and stored
  byte-for-byte before any parsing — see `digital-garage/app/parsers.py`.
  Re-ingesting identical bytes is detected and is a no-op (idempotent).
- No copyrighted service-manual bulk text is stored in this repo — only
  derived facts, citations, and permissible excerpts (`BUILD-PLAN.md` §2
  rule 6).
- Personal data footprint is minimal: one VIN per backend instance
  (`.env.example`), no location/driver-behavior tracking, no cloud telemetry
  upload — the whole platform is local-first by design.

## Secrets

- The parts-tracker PWA (`web/tools/parts.html`) requires a GitHub PAT with
  **Contents: read & write** scope on this repo, entered by the user and
  stored only in their own browser's `localStorage` (`fst_tok`) — never
  committed, never sent anywhere but the GitHub API.
- `.env.example` contains only local Docker-Compose defaults
  (`garage`/`garage`/`garage`), not real credentials.
- No hardcoded secrets were found in a working-tree scan as of 2026-08-25.
  That scan was shallow (tree only, not full git history) — a full-history
  scan (`gitleaks` or equivalent) is a recommended future CI addition, not
  yet implemented.

## Known gaps (tracked, not hidden)

Recorded in [`digital-garage/docs/BUILD-PLAN.md`](digital-garage/docs/BUILD-PLAN.md) §7:

- No dedicated tool/action risk-registry (deferred — no current consumer).
- No mock-vehicle/simulation environment (deferred — no real vehicle-write
  path exists yet to gate).
- No full-history secret scan in CI yet.

## Reporting

This is a personal project with a single maintainer/owner. There is no
formal disclosure process — open an issue or contact the repository owner
directly.
