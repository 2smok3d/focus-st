# Digital Garage — Domain Constitution

> The non-negotiable semantics of the platform. These definitions and rules are
> **enforced in application services and tests** (`app/epistemics.py`,
> `app/quantities.py`), not merely documented. A change here is a change to the
> meaning of the whole system.

## 1. Entities

| Entity | Meaning |
|---|---|
| **Claim** | An assertion originating from a *source* (OEM doc, forum, person). Truth not yet established. |
| **Evidence** | Material that supports or contradicts a claim or hypothesis. |
| **Observation** | Something directly measured or observed on a machine. |
| **Measurement** | A quantified observation, with units, method, and instrument. |
| **State** | A condition/configuration valid over a span of time. |
| **Event** | Something that changes state. |
| **Hypothesis** | A possible causal explanation under test. |
| **Finding** | A conclusion supported by evidence. |
| **Recommendation** | A proposed action. |
| **Procedure** | A prescribed sequence of operations. |
| **Test** | A procedure intended to discriminate between / verify possibilities. |
| **Work Order** | A planned or performed workshop operation. |
| **Experiment** | A controlled comparison intended to answer a question. |

Each entity is a distinct *epistemic kind*. The kind of a record is part of its
identity — you cannot relabel a record from one kind to another for free.

## 2. The critical rule — forbidden silent transformations

These promotions must **never happen silently**. Each requires an explicit *bridge*
(named justification); without it, the operation is rejected in code.

| Forbidden silent promotion | Why | Required bridge |
|---|---|---|
| **CLAIM → OBSERVATION** | A source saying it is not the same as seeing it. | *(never allowed — an observation must be independently recorded)* |
| **OBSERVATION → FINDING** | One data point is not a conclusion. | supporting **evidence** + reasoning |
| **HYPOTHESIS → FINDING** | A guess is not a conclusion. | **confirming evidence** |
| **FINDING → VERIFIED_REPAIR** | "Part replaced" ≠ "problem fixed." | a **post-repair verification** test/observation |

Enforcement lives in `app/epistemics.py::promote(...)`, which raises
`EpistemicError` on a forbidden transition lacking its bridge. Services that produce
findings or verified repairs route through it; `tests/test_epistemics.py` proves the
rejections hold.

### States of a repair
A repair is never "done" — it is one of:
- `REPAIR_PERFORMED · OUTCOME_UNKNOWN` — work happened, effect unconfirmed.
- `REPAIR_VERIFIED` — a post-repair test/observation confirmed the fix.

## 3. Quantities & units

Every numeric engineering value carries a **quantity_type** and a **unit**; the system
normalizes to a canonical unit internally while preserving the original for display
(`app/quantities.py`). The consequence that matters:

> A contradiction checker must understand that **100 lb·ft** and **135.6 N·m** do
> **not** conflict — they are the same torque in different units.

Comparisons and conflict detection operate on canonical values within a tolerance;
comparing across incompatible quantity types (torque vs pressure) is itself a category
error and is rejected, not silently coerced.

## 4. Provenance ladder (unchanged, referenced here)

`UNVERIFIED → CORROBORATED → OEM_VERIFIED → VEHICLE_VERIFIED`. Weaker evidence never
silently outranks stronger (`app/provenance.py`). A finding cites the evidence it
rests on; a verified repair cites the verification that confirmed it.

## 5. Enforcement summary

| Rule | Enforced by |
|---|---|
| Epistemic kinds are distinct; forbidden promotions rejected | `app/epistemics.py` + `tests/test_epistemics.py` |
| Units normalized; cross-unit values compared correctly | `app/quantities.py` + `tests/test_quantities.py` |
| Evidence precedence / conflict | `app/provenance.py` + `tests/test_provenance.py` |
| Human approval boundary (agent proposes → human approves) | `app/service.py` change-proposal queue |
| Observations are directly-measured facts, never Findings | `app/observations.py` (Observation V2) |
| Configuration at time T is a projection of history | `app/observations.py::config_at` (twin state + event ledger) |
| Measurements compared unit-aware | `app/observations.py::measurements_agree` (via `quantities`) |

## 6. Records that realize these entities

| Entity | Realized by |
|---|---|
| Observation / Measurement | `observations` (+ `instruments`) — value normalized via `quantities` |
| State (over time) | `component_states` (temporal twin) |
| Event | `machine_events` (append-only ledger; state is a projection of it) |
| Configuration snapshot | `configuration_snapshots` — materialized twin state + settings |
| Environment | `environment_snapshots` — canonical °C / kPa |
| Claim / Evidence | `claims` / `claim_evidence` |
| Hypothesis / Finding / Test | `case_hypotheses` / `case_findings` / `case_tests` (workbench) |
