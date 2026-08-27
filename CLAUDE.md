# DIGITAL GARAGE — CLAUDE PROJECT INSTRUCTIONS

Read `DIGITAL-GARAGE-FINAL-FINAL-CLAUDE-PROMPT.md` before substantial work.

## Mission
Transform the repository into **Digital Garage**, a premium personal automotive intelligence platform.

## Non-negotiable rules
1. Inspect before modifying.
2. Never invent repository state or test results.
3. Never silently delete valuable vehicle information.
4. Preserve provenance for vehicle-specific facts.
5. Distinguish verified, observed, inferred, recommended, speculative, and unknown.
6. Generated artifacts are projections, not sources of truth.
7. Use the simplest architecture capable of satisfying requirements.
8. Keep AI authority below platform/tool/policy authority.
9. Vehicle-changing capabilities require explicit human approval and validation.
10. Prefer simulation/mock hardware before real vehicle interaction.
11. Make changes in coherent, reviewable stages.
12. Run relevant validation after meaningful changes.

## Execution loop
DISCOVER → PLAN → IMPLEMENT → TEST → REVIEW → DOCUMENT → COMMIT

## Required living documents
Maintain, as appropriate:
- `REPO_INDEX.md`
- `ARCHITECTURE_CURRENT.md`
- `DATA_SOURCES.md`
- `AUDIT_REGISTER.md`
- `MIGRATION_PLAN.md`
- `DECISIONS.md`
- `VALIDATION_STATUS.md`
- `CURRENT_STATUS.md`

## Automotive boundary
Separate:
INFORMATION → ANALYSIS → RECOMMENDATION → SIMULATION → ACTION

The platform—not the AI—enforces permissions and safety boundaries.

## Session continuity
If work cannot finish in one session, update `CURRENT_STATUS.md` with the current phase, completed work, files changed, validation, unresolved issues, and exact next actions.

## Completion standard
Do not declare completion merely because the project builds. Include appropriate correctness, security, data/provenance, architecture, UX, performance, AI/tool safety, migration, and documentation reviews.

---

> **Note on this file's history:** this `CLAUDE.md` was replaced on 2026-08-25 with
> the parent project's governance version (see `DECISIONS.md`, Decision 2). The
> previous version of this file contained repository-specific operational detail
> (the parts-tracker PWA's parsing contract, GitHub Contents API sync internals,
> service-worker cache mechanics, deployment specifics, design-system tokens) that
> has no other canonical home in this governance file. That detail was migrated to
> the "Operational reference" section of the root `README.md` before this file was
> replaced, so nothing was lost — read `README.md` for those specifics.
