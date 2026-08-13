---
title: 09 Modifications & Tuning Master Plan
aliases: ["09 Mods & Tuning", Mods, Tuning]
tags: [focus-st, kb, tuning, mods]
---

# 09 · Modifications and Tuning Master Plan

> Full text (merged from the FFST vault). Build → [[powertrain]].

## Build philosophy
A long-term daily-driven 2017 ST. Improve repeatability, response, comfort + integration before chasing a peak dyno figure. Every modification answers: (1) what measured problem does it solve? (2) what supporting parts/calibration does it require? (3) what reliability/NVH/emissions/service tradeoff does it introduce? (4) how will success be validated? (5) how is it reversed/serviced later?

## Performance stages (project categories, not universal standards)
- **R0 — health + evidence** (required before performance tuning): VIN recall status documented; complete module scan; current calibration/tune identified; fluids established (oil, coolant, brake/clutch, MMT6); plugs/coils inspected; charge-air sealed; purge/EVAP healthy; brakes/tires/mounts safe; no unresolved misfire/fuel-pressure/boost-control/overheating fault. Gain: none. Value: prevents expensive misdiagnosis + tune-related failure.
- **R1 — reliability + thermal:** quality high-capacity intercooler; correct fresh plugs for the intended tune; charge-pipe clamp/O-ring inspection/upgrade where justified; clean radiator/condenser/intercooler airflow; conservative custom 91-octane calibration; tires + brake service appropriate to power. Intercooler prioritized (stock heat-soaks even tuned).
- **P1 — stock-turbo pump-gas street:** healthy/calibrated intake; upgraded intercooler; optional cat-back; optional RMM; custom 91/93 tune. Responsible planning range ~mid-250s to high-270s whp; torque often substantially higher. Not a guarantee. Control low-RPM torque + charge temperature over the first dyno pull.
- **P2 — stock-turbo E30:** measured E30 blend; tuner-specific E30 calibration; fuel-pressure + mixture logging; repeatable blending. Published examples ~upper-200-whp, some ~290–300 whp. Don't load E30 on gasoline, fill full E85 on stock fueling, assume pump E85 = 85%, or use a fixed gallon recipe without measuring.
- **P3 — stock-turbo full bolt-on:** intercooler; intake; downpipe where legal; cat-back; charge pipes/BPV; custom pump/E30 calibration. Stock turbo generally most useful below ~300 whp; ~280 whp a strong repeatable target. Don't expect linear gains from every bolt-on.
- **BT1 — responsive big-turbo street:** define target first; plan compression/leakdown + engine health; turbo sizing + response; exhaust manifold/head outlet compatibility; intercooler + charge pipes; intake/MAF strategy; downpipe/catalyst; wastegate + boost control; clutch/flywheel torque capacity; tire/traction + differential; fuel-system capacity; professional custom calibration; emissions/legal status. A responsive ~330–380 whp may fit stock fueling depending on fuel/calibration; maintain pressure margin.
- **BT2 — ~400+ whp:** a system build, not a turbo swap. Upgraded HPFP/auxiliary port fuel; clutch/flywheel; traction/differential; engine-health verification + realistic stock-internal risk acceptance; cooling + oil monitoring; stronger charge/exhaust hardware; professional calibration + fail-safes. ~400 whp is a practical stock-engine planning ceiling; failures can occur below it, some survive above. Not an engineering guarantee.

## Calibration paths
- **Factory:** baseline diagnosis, emissions/dealer work, unknown-hardware verification, max OEM behavior. Don't flash stock software blindly if incompatible hardware (altered MAF housing, downpipe) needs calibration.
- **Off-the-shelf:** only when hardware exactly matches map requirements, fuel meets the minimum, the map is current for the model year/strategy, logs show normal operation. COBB Stage 2 requires an upgraded intercooler; a stage label is not interchangeable across tuners.
- **Custom pump-gas (preferred first):** AZ-safe 91-octane map unless reliable 93 is consistently available; conservative low-RPM torque; stock-turbo thermal awareness; optional lower-torque/valet map slots; datalog revision process.
- **E30:** only after the pump-gas tune is mechanically proven; maintain a blend calculator + fuel log; verify ethanol content where practical.
- **Flex-fuel warning:** a true flex-fuel system adjusts to measured ethanol via appropriate hardware/software. Many ST "E30" tunes are fixed-blend maps, not automatic flex fuel — don't use the terms interchangeably.

## Tuner-selection criteria
Platform history + technical transparency; hardware/fuel questionnaire quality; datalog review process; response to knock/fuel-pressure/boost-control concerns; emissions/legal policy; revision + support terms; whether torque is shaped for the stock engine/clutch + intended use; whether the tuner explains limits rather than only advertising peak power. Commonly researched: Stratified Automotive Controls, Edge Autosport, JST Performance, Mountune, Panda Motorworks, COBB-supported calibrators — verify current service, policies, support before purchase (not an endorsement ranking).

## Datalogging protocol
**Pre-log:** no active safety-critical DTC; correct fuel + map confirmed twice; oil/coolant correct; tires/brakes/road safe; engine fully warmed; no passenger distraction; tuner-prescribed gear/RPM range only. **Record with every log:** date/time; ambient temp + elevation; fuel brand/octane + measured ethanol; map revision; hardware list; gear + start/end RPM; recent maintenance; symptom/tuning purpose. **Channels:** RPM/throttle/accelerator; commanded/actual boost or manifold pressure; load/torque request; wastegate duty; lambda/equivalence + fuel trims; commanded/actual rail pressure; ignition timing + cylinder corrections; coolant + charge-air temperature; misfire counters. **Abort:** flashing MIL/misfire; actual fuel pressure materially below target; uncontrolled overboost; severe/repeated abnormal knock outside tuner instruction; overheating; mechanical noise/smoke/fluid warning; unsafe traffic. Don't repeatedly WOT-log "to see if it clears up."

## Modification ranking
- **Highest value:** baseline service + recall verification → tires → intercooler → conservative custom tune → correct plugs + inspection interval → brake fluid/pads matched to use → alignment.
- **High-value feel/quality:** shifter cable-end/bracket bushings after inspection; correct cable alignment; targeted rear motor mount if wheel hop/engine movement justifies NVH; sound treatment; modern head unit/RR2 integration; wireless charging + audio improvements.
- **Conditional:** intake (sound/airflow at higher power — verify MAF/tune); cat-back (sound, little stock-turbo power alone); downpipe (power/response but legal/heat/tune consequences); catch can (optional vapor management); BOV (sound — preserve metering/control); larger rear sway bar (balance, not automatically safer); coilovers (only with a clear geometry/ride objective).
- **Low-priority/avoid:** aggressive crackle tune; repeated launch-control/flat-foot-shift abuse; unverified eBay charge/fuel/suspension parts; vent-to-atmosphere systems causing poor drivability/legal issues; quick-release steering wheel without airbag on a street car; rigid emblem on the airbag cover; extreme lowering without a travel/geometry plan; parts bought solely because a forum calls them "stage required."

## Compatibility matrix
| Component | Stock tune | Custom pump | E30 | Big turbo | Cautions |
|---|---|---|---|---|---|
| Large intercooler | Yes | Strongly recommended | Strongly recommended | Required | Fit, pressure drop, ducting |
| Aftermarket intake | Often | Yes if calibrated | Yes | Usually required | MAF housing + hot-air sealing |
| Cat-back | Yes | Yes | Yes | Yes | Drone, leaks, hanger fit |
| Downpipe | Not without a plan | Tune/legal dependent | Tune/legal dependent | Usually part of system | Catalyst/CEL/emissions/heat |
| Colder plugs | Not automatically | Tuner dependent | Common recommendation | Tuner dependent | Fouling/incorrect heat range |
| RMM | Yes | Yes | Yes | Yes | NVH + other mount condition |
| Catch can | Optional | Optional | Optional | Optional/engine-build dependent | Routing, drain, vacuum leak |
| Stock clutch | Yes | Torque dependent | Often limiting | Commonly limiting | Slip + DMF condition |
| Stock fueling | Yes | Yes | Common at stock-turbo E30 | Limited by target/fuel | Pressure margin |
| Aux/HPFP fueling | No | No | Target dependent | Required near higher power | Calibration, failsafe, install |

## Parts-purchase gate
Before ordering any performance part, enter into the project database: exact part number + year fitment; problem/objective; required tune/supporting hardware; installation instructions + torque source; emissions/warranty implications; expected measurable result; competing options; total installed cost; return/service policy; validation test. A part without a validation plan is not approved.

## Final recommended roadmap
1. Complete R0 baseline + recalls. 2. Identify current intake, mount, intercooler, exhaust, ECU tune. 3. Service fluids/plugs + repair any EVAP/charge fault. 4. Install tires/brake service/alignment as needed. 5. Install a proven intercooler. 6. Obtain a conservative custom 91 tune + validate logs. 7. Complete RR2/head-unit, wireless charger, sound treatment, spare-well audio. 8. Evaluate E30 only after the pump tune + blending process are proven. 9. Decide whether stock-turbo response is sufficient before buying a downpipe or big turbo. 10. If higher power is desired, set a wheel-horsepower/response budget and design fueling, clutch, cooling, traction together.

## Related
[[powertrain]] · [[06 Powertrain]] · [[10 Forum Consensus]] · [[12 Sources]] · [[11 Build Roadmap]] · [[_KB-Home|KB Home]]
