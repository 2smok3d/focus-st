---
title: 05 Diagnostics & DTC Master
aliases: ["05 Diagnostics & DTC", DTC, Diagnostics]
tags: [focus-st, kb, diagnostics, dtc]
---

# 05 · Focus ST Diagnostics and DTC Master

> Full text (merged from the FFST vault). Reference → [[forscan-master-reference]].

## Diagnostic operating procedure
### Before touching parts
1. Verify battery condition + charging voltage (low system voltage creates unrelated module/comm faults).
2. Scan **all modules**, not only the PCM.
3. Save current, pending, permanent and history codes.
4. Save freeze-frame data before clearing anything.
5. Record mileage, ambient temp, fuel level, fuel source/octane/ethanol, tune/map, gear/RPM/load, whether the symptom followed refueling or recent work.
6. Photograph anything disturbed before disassembly.
7. Check recalls, TSBs, software level, installed modifications.
8. Prove the fault with tests before replacing a component.

### Priority levels
- **Stop and shut down:** oil-pressure warning, overheating, fuel leak, severe knock, flashing MIL with heavy misfire, uncontrolled boost, brake hydraulic failure.
- **Drive only for diagnosis/repair:** repeat misfire, fuel-pressure code, over/underboost with limp mode, clutch hydraulic leak, wheel-bearing/tire defect.
- **Monitor with case file:** isolated intermittent code with normal operation, evidence saved, safety unaffected.

## DTC quick index
| Code family | System | First checks |
|---|---|---|
| P0300–P0304 | Random/cylinder misfire | Plug condition/gap, coils, fuel, compression, charge leaks, tune |
| P0087, P0191 | Fuel-rail pressure | Low-side supply, commanded vs actual rail pressure, fuel quality, HPFP/injector data, tune demand |
| P0234 | Overboost | Wastegate/solenoid/plumbing, sensor data, tune, mechanical binding |
| P0299 | Underboost | Charge leaks, pipe retention, intercooler, bypass valve, wastegate, exhaust restriction |
| P0456, P144A, P1450 | EVAP/purge | Purge valve, recall/TSB status, tank vacuum/deformation, canister, PCM calibration |
| P0420 | Catalyst efficiency | Exhaust leak, O2 response, catalyst condition, downpipe/tune, purge/misfire contamination |
| P013x/P014x | O2 sensor/heater | Wiring, exhaust leaks, power/ground/heater test, contamination, tune/downpipe |
| P2196 | Front O2 biased/stuck rich | Purge stuck open, injector leakage, fuel pressure, O2 circuit, tune |
| P0106/P0068/P061A | Airflow/load/torque | MAP/TMAP/throttle data, vacuum/charge leaks, intake changes, calibration |
| U-codes | Network communication | Battery voltage, grounds, connectors, recent radio/FORScan work, module topology |

## Misfire (P0300–P0304)
Patterns: cold-start stumble only; idle misfire; misfire under boost; one-cylinder recurring; random after bad fuel/tune/charge-pipe work.
Test order: save freeze frame + cylinder counters → confirm correct fuel + map → inspect all plugs by cylinder (part, gap, deposits, cracking, tracking, oil/fuel) → if one cylinder implicated, swap the coil (clear only after evidence saved) and see if the fault follows → inspect coil boot/spring/well → check charge-air/vacuum integrity + fuel trims → compare low-side and high-side fuel pressure commanded vs actual → evaluate injector operation/wiring if fault stays on one cylinder → compression + leakdown when mechanical condition uncertain → borescope if oil consumption/detonation/coolant suspected.
Interpretation: fault follows coil = coil/boot/circuit; improves after correct plugs/gap = ignition demand exceeded available spark (still verify tune/fuel); one cylinder low mechanically = locate leakage; multiple cylinders at high load with rail-pressure drop = fuel supply/calibration, not all coils.
Don't: replace all four injectors without balance/electrical evidence; assume negative ignition corrections mean damage; continue WOT with a flashing MIL; tighten gap below tuner instruction to hide a fault.

## EVAP/purge (P1450 / P0456 / P144A)
The Focus purge-valve campaign history makes this high priority. Test order: record fuel level + whether symptom occurred after refueling → ask about rough idle/stall after fill, hard filling, gauge irregularity, tank deformation → **verify 18S32/26S40 status + PCM calibration** → observe purge command + fuel trims at idle → test purge valve sealing/flow per Ford → inspect hoses/canister/vapor lines/connector → inspect tank shape + fuel-delivery module if excessive vacuum → smoke-test at correct low pressure → confirm monitor completion, not just clear MIL.
- **P1450:** excessive vacuum unable to bleed — stuck-open valve/campaign a major lead.
- **P0456:** small leak — capless filler sealing, hoses, purge sealing, canister.
- **P144A:** purge-vapor line restriction/flow — inspect valve, plumbing, current bulletin.

## Underboost (P0299)
Divide: is the PCM commanding more boost than the engine produces? is boost actually low or a sensor/reporting problem? only in heat/high gear/one map/after pipe work? Test order: confirm tune/map + target → inspect every charge connection (esp. any that previously separated) → intercooler core/end tanks + pipe O-rings → controlled smoke/pressure test → bypass valve + control → boost-control solenoid hoses + electrical → wastegate linkage/preload per procedure (don't randomly shorten) → compare commanded/actual boost, wastegate duty, throttle closure, load, airflow → exhaust restriction + turbo condition last. Common errors: buying a turbo before finding a loose charge pipe; increasing preload to hide a leak; comparing boost across weather/gears/tunes.

## Overboost (P0234)
Stop aggressive driving → verify correct map/no tune mismatch → inspect boost-control plumbing for crossed/split/pinched/disconnected hoses → verify MAP/TMAP plausibility key-on + under load → inspect wastegate linkage for binding/improper preload → compare commanded/actual boost, throttle closure, wastegate duty → return to a known-safe calibration via tuner/Accessport recovery + stable voltage. Overboost is not free performance.

## Fuel pressure (P0087 / P0191)
Required data: low-side pressure; commanded + actual high-pressure rail pressure; sensor plausibility; fuel level/composition/temp; load/RPM at divergence; tune fueling demand. Test order: confirm blend + no contamination → battery/charging stability + sensor wiring → low-side delivery + in-tank module → commanded vs actual rail pressure under controlled operation → HPFP + rail sensor per Ford → injector leakage/balance if pressure decays or rich misfire → whether the tune exceeds stock fueling. Don't keep high-load logging when actual rail pressure falls materially below commanded.

## Catalyst (P0420)
Distinguish: actual degradation; exhaust leak near the rear sensor; O2/wiring fault; repeated misfire/rich/purge fault contaminating data; aftermarket downpipe/cat + incompatible tune; software/monitor conditions. Test: inspect for accompanying misfire/fuel-trim/purge/O2 codes → identify downpipe + cat hardware → inspect exhaust leaks + sensor install/wiring → analyze upstream/downstream sensor behavior at temperature → correct engine-control faults before condemning the cat → verify emissions legality before changing hardware/calibration.

## P2196 (O2 biased/stuck rich)
Check purge early (esp. post-refuel). Save trims + freeze frame → test purge valve sealing/command → check injector leakage + rail-pressure behavior → inspect O2 wiring + exhaust leaks → confirm fuel blend/map → verify the sensor with controlled data before replacement.

## Network / module U-codes
Triggers: weak battery/voltage drop during crank/programming; loose grounds; disconnected APIM/ACM/radio during head-unit install; incompatible Maestro firmware/config; incorrect FORScan as-built edit; water intrusion/damaged harness; a module intentionally removed without config change. Test order: save full topology scan → check battery resting/cranking/charging → identify which module stopped communicating vs which merely report losing it → inspect recent work first → restore known-good backups when a coding change caused it → check power/ground/network at the missing module. Don't replace a module because others report losing communication with it.

## Datalog minimums
RPM, accelerator + throttle angle; commanded + actual boost/MAP; load + torque request; wastegate duty; ignition timing + cylinder corrections; short- + long-term fuel trims; lambda/AFR equivalence; commanded + actual rail pressure; charge-air + coolant temps; misfire counters; vehicle speed + gear. A datalog without hardware list, map, fuel, weather, gear and symptom is incomplete evidence.

## Case closure standard
Root cause identified or evidence-supported conclusion documented; repair/adjustment + part/calibration numbers recorded; original symptom retested under safe equivalent conditions; no relevant pending/current code returns after monitor completion or appropriate drive cycle; collateral systems inspected; maintenance/mod/cost trackers updated.

## Related
[[00 Command Center]] · [[06 Powertrain]] · [[04 Recalls & TSBs]] · [[forscan-master-reference]] · [[_KB-Home|KB Home]]
