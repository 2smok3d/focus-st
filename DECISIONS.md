# DECISIONS.md — Digital Garage / focus-st

Format per `DECISION-RECORD.md`. All six decisions below were made in the same
session, 2026-08-25, in response to the Phase 0 reconciliation.

---

## Decision 1 — Mission mode

- **Date:** 2026-08-25
- **Decision:** Re-run the full 67-section `DIGITAL-GARAGE-FINAL-FINAL-CLAUDE-PROMPT.md`
  against the repository regardless of what `BUILD-PLAN.md` already claims is done —
  do not shortcut to "audit/harden/extend" mode.
- **Context:** `BUILD-PLAN.md` §4 states the original roadmap and revised backlog
  are fully built and merged. Claude's Phase 0 pass recommended trusting that
  self-report and shifting to a narrower audit/harden/extend posture.
- **Options considered:** (A) shift to audit/harden/extend mode, (B) re-run the
  full spec regardless of self-reported completion, (C) discard current
  implementation and re-architect from scratch.
- **Selected option:** B.
- **Why:** The repo's own status claims should not be taken as ground truth
  without independent verification against the full spec — a self-authored
  "done" ledger can miss gaps its author didn't think to check for.
- **Consequences:** This is a large body of work (67 sections). It will be
  sequenced into groups rather than attempted in one pass (see Execution note
  below). Some sections will likely confirm `BUILD-PLAN.md`'s claims; the value
  is in finding the sections that don't.
- **Revisit conditions:** If several consecutive section-groups turn up nothing
  but confirmation of existing work, it's reasonable to revisit whether full
  re-verification of every remaining section is still the best use of effort.

## Decision 2 — Which `CLAUDE.md` governs

- **Date:** 2026-08-25
- **Decision:** Replace the repository's `CLAUDE.md` with the project's version.
- **Context:** The repo's `CLAUDE.md` contains operational detail with no
  duplicate anywhere else in the repo (PARTS.md parser rules, GitHub Contents
  API sync mechanics, localStorage key names, service-worker cache-bump
  procedure, deployment specifics, design-system tokens). Replacing it outright
  would delete that content, which conflicts with the project's own rule 3
  ("never silently delete valuable information").
- **Options considered:** (A) layer the two files, repo's stays authoritative
  for implementation detail, (B) replace wholesale, (C) leave both unreconciled.
- **Selected option:** B.
- **Why:** [decision made; rationale not elaborated by the user beyond
  selecting B]
- **Consequences / mitigation:** To avoid violating rule 3 while still executing
  B, the operational content unique to the old `CLAUDE.md` is being migrated
  into the root `README.md` (an existing file, consistent with Decision 3's
  "no new top-level files") before the replacement takes effect. See the
  prepared migration diff below. **This migration has not yet been confirmed —
  flagging once before proceeding, since it affects content with no other
  home.**
- **Revisit conditions:** If the parts-tracker PWA (`web/tools/parts.html`)
  breaks or is edited incorrectly because its parsing contract is no longer
  documented in `CLAUDE.md`, restore the migrated detail's visibility.

## Decision 3 — Disposition of the four Phase 0 documents

- **Date:** 2026-08-25
- **Decision:** Merge Phase 0 findings directly into existing repository docs;
  do not add `REPO_INDEX.md` / `ARCHITECTURE_CURRENT.md` / `DATA_SOURCES.md` /
  `AUDIT_REGISTER.md` as new standalone top-level files.
- **Options considered:** (A) keep as thin cross-referencing indexes, (B) merge
  content into existing docs, no new files, (C) keep all four fully standalone.
- **Selected option:** B.
- **Consequences:** `AUDIT_REGISTER.md` findings fold into `BUILD-PLAN.md` (its
  natural home — it already carries a "done" ledger and rule set).
  `REPO_INDEX.md`/`ARCHITECTURE_CURRENT.md`/`DATA_SOURCES.md` content folds into
  `README.md` / `V2-ARCHITECTURE.md` / `DOMAIN-CONSTITUTION.md` as topically
  appropriate. `DECISIONS.md` (this file) and `CURRENT_STATUS.md` remain
  separate — they're on the project's required-living-documents list
  independent of the four Phase 0 documents this decision governs.

## Decision 4 — `CORR` (corroboration suggester)

- **Date:** 2026-08-25
- **Decision:** Build `CORR` next, following the repo's established per-unit
  workflow (`BUILD-PLAN.md` §5).
- **Options considered:** (A) build next, (B) deprioritize behind audit findings,
  (C) drop it.
- **Selected option:** A.
- **Consequences:** Sequenced after the branch/CLAUDE.md/doc-merge housekeeping
  below, and interleaved with the Decision 1 full-spec pass — if the spec
  re-read surfaces something higher-priority or something that changes `CORR`'s
  design, that takes precedence before `CORR`'s schema is written (additive
  migrations are cheap to sequence, not cheap to redo).

## Decision 5 — Vehicle scope

- **Date:** 2026-08-25
- **Decision:** Respect the repo's fleet architecture. "FFST" in conversation
  means the Focus ST slice of the platform, not a mandate to strip the other
  four vehicles out.
- **Options considered:** (A) respect fleet architecture, scope conversation
  not repo, (B) propose a Focus-ST-only fork/export, (C) remove the other four
  vehicles from the live repo.
- **Selected option:** A.
- **Consequences:** None of the fleet-wide code (`fleetfeed.py`, `fitment.py`,
  fleet-scoped tests) is in scope for removal under any future request framed
  around "FFST" unless explicitly and separately requested.

## Decision 6 — Stale/diverged branches

- **Date:** 2026-08-25
- **Decision:** Diff `origin/openai/digital-garage` against `master`
  module-by-module before archiving/deleting it; delete the fully-merged,
  zero-divergence `origin/claude/car-project-docs-system-lhlhp6` outright.
- **Options considered:** (A) diff first then decide, (B) delete both without
  review, (C) leave both for now.
- **Selected option:** A.
- **Consequences:** See the diff results below — this is executed in the same
  session as this record.

---

## Execution log (applies to Decisions 2, 3, 6)

This session initially cloned the repository read-only over HTTPS with no
push credentials, and prepared exact file content, diffs, and branch-deletion
commands for the user to apply. The user then connected GitHub via a Zapier
connector (authenticated as `2smok3d`, matching the repo owner), after which
all four items below were executed directly, in this order:

1. This file (`DECISIONS.md`) was created at repo root.
2. The migration content (parts-tracker parser rules, GitHub sync internals,
   service worker, deployment) was appended to `README.md` **before**
   `CLAUDE.md` was replaced, per the mitigation above — nothing was lost.
3. `digital-garage/docs/BUILD-PLAN.md` received the audit-findings appendix
   (§7), including the AUD-001 correction recorded in full rather than
   silently dropped.
4. `CLAUDE.md` was replaced with the project's version.
5. `origin/claude/car-project-docs-system-lhlhp6` (zero divergence),
   `origin/claude/claude-md-docs-58eozc`, and `origin/openai/digital-garage`
   were deleted — content-level comparison (not just staleness) confirmed no
   unique material was lost; see BUILD-PLAN.md §7.2 (AUD-002) for the
   comparison.

Each commit's SHA is recorded in the session's tool-call history; this
document doesn't restate them to avoid drift if any are later amended.
