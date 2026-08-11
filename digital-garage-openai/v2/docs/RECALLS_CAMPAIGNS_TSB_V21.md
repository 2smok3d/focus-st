# 2017 Focus ST — Recalls, Campaigns & Service Communications v2.1

This register separates **campaign applicability** from **campaign completion on this specific VIN**. A model/year may fall within an announced population while the individual vehicle may already have been serviced. Completion status remains `unknown` until verified by VIN through Ford/NHTSA/dealer history.

## Authority rules

1. VIN-specific Ford/NHTSA recall lookup or dealer OASIS history
2. NHTSA recall documents / official Ford recall communication
3. Ford service publication / TSB / SSM
4. community reports only as discovery leads

A TSB is not a recall, and a procedure written for another engine/model/year is not imported merely because the symptoms look similar.

## 18S32 — canister purge valve / excessive fuel-system vacuum

**Authority:** Ford safety recall announcement.

Ford announced a recall covering select 2012–2018 Focus vehicles equipped with 2.0L GDI **and 2.0L GTDI** engines for a canister purge valve that may stick open. Ford described the failure path as excessive fuel-vapor-system vacuum that may deform the plastic fuel tank; possible observations include MIL illumination, inaccurate/fluctuating fuel gauge, drivability concerns, stall, or inability to restart.

Ford's announced remedy included PCM software intended to detect the fault and inspection/replacement of the purge valve, carbon canister, fuel tank and fuel delivery module as necessary.

### Garage treatment

- campaign_id: `18S32`
- system tags: `EVAP`, `fuel_tank`, `PCM`, `purge_valve`, `drivability`
- 2017 Focus ST relevance: **model/engine population potentially applicable; VIN completion must be verified**
- current completion status: `UNKNOWN`
- diagnostic rule: do not conflate an EVAP purge-valve issue with P04DB/PCV merely because both touch vacuum/airflow diagnostics.
- evidence to retain if serviced: dealer invoice, campaign completion report, PCM calibration identifier before/after if available, purge-valve part record, tank/canister inspection outcome.

Official Ford announcement:
https://media.ford.com/content/fordmedia/fna/ca/en/news/2018/10/25/ford-motor-company-issues-recall-in-north-america-for-select-201.html

## 19S22 — incomplete 18S32 service calibration on selected previously serviced vehicles

Ford later announced a separate action after determining that some vehicles serviced under 18S32 did not receive the intended calibration. The 2019 announcement identifies select 2012 and 2017 Focus GDI vehicles and 2013–2014 Focus ST GTDI vehicles for that specific follow-up population.

### Garage treatment

For this 2017 Focus ST, do **not** infer 19S22 applicability from model year alone because Ford's announcement describes 2013–2014 Focus ST GTDI in the ST portion of the selected follow-up population. Keep this record as a historical relationship to 18S32, not as a positive applicability claim.

Official Ford announcement:
https://media.ford.com/content/fordmedia/fna/ca/en/news/2019/07/09/ford-motor-company-issues-safety-recall.html

## Manual-transmission hatchback interior-release compliance campaign

Ford announced a safety-compliance recall covering certain 2013–2017 Focus manual-transmission rear-hatchback vehicles built at Michigan Assembly Plant through August 26, 2016. The issue concerned the hatch interior release operating with a single action below approximately 4 mph rather than the required two-action behavior. Remedy was BCM software reprogramming.

### Garage treatment

- exact applicability depends on assembly/build date; do not infer only from model year.
- current completion status: `UNKNOWN`
- if build date is after the announced range, mark `NOT_APPLICABLE_BY_BUILD_DATE` with source evidence.

Official Ford announcement:
https://media.ford.com/content/fordmedia/fna/ca/en/news/2016/09/28/ford-issues-one-safety-recall-and-one-safety-compliance-recall-i.html

## TSB / SSM ingestion guardrail

Web searches can return older Ford TSBs that contain mechanically useful generic vacuum-leak methods but apply to unrelated years/engines. Example: an old Ford lean-code TSB instructs technicians to preserve DTC/freeze-frame and adaptive fuel data before clearing codes, inspect PCV/vacuum hoses, and compare fuel-trim behavior at idle vs elevated RPM. Those diagnostic concepts are reasonable, but the document is **not a 2017 Focus ST-specific procedure** and therefore must not be indexed as applicable service instruction.

Garage fields for every TSB/SSM:

- publication identifier
- title
- publication date
- superseded status
- applicable model years
- model
- engine
- transmission
- build-date range
- symptom/DTC
- VIN applicability if specified
- procedure summary
- required special tools
- software/calibration dependency
- source URL / owned-manual reference
- `applicability_confidence`

## Owner's-manual live-reference warning

Ford's web owner-manual pages state that the online view may contain newer information than the originally printed manual and may vary slightly from the vehicle's original publication. The garage therefore stores both `publication/retrieval date` and, where available, the original vehicle-era document revision rather than treating a live page as timeless.

## Recall status workflow

`DISCOVERED → APPLICABILITY_REVIEW → VIN_VERIFIED → OPEN | COMPLETED | NOT_APPLICABLE → EVIDENCE_ATTACHED`

The garage must never display `COMPLETED` based solely on a forum post, a generic model-year list, or absence of a warning light.
