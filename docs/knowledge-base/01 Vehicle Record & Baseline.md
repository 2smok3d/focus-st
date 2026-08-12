---
title: 01 Vehicle Record & Baseline Inspection
aliases: ["01 Vehicle Record & Baseline", Baseline Inspection]
tags: [focus-st, kb, vehicle, inspection]
---

# 01 · Vehicle Record and Baseline Inspection

> Full text (merged from the FFST vault). Working spec → [[VEHICLE]].

## Identity
- Model year: 2017 · Model: Ford Focus ST · Trim: ST1
- VIN: 1FADP3L94HL223134
- Engine: 2.0L GTDI EcoBoost inline-four
- Transmission: Getrag-Ford MMT6 six-speed manual
- Known mileage when vault created: ~86,000 miles
- Ownership history reported: one prior owner, no reported accidents, documented maintenance through ~60,000 miles

## Existing equipment and modifications to verify
| Area | Known/observed | Verification required |
|---|---|---|
| Infotainment | 4" SYNC 1; Bluetooth media works | Record APIM/ACM config + firmware before replacement |
| Intake | Large aftermarket intake | Brand, filter size, MAF housing diameter, mounting, heat shielding, tune requirement |
| Mount | Torque Solutions branding observed | Exact location, part number, bushing durometer, damage, NVH |
| ECU | Unknown | Confirm factory/custom calibration and whether an Accessport is married |
| Exhaust/downpipe | Unknown | Photograph turbo outlet rearward; identify catalysts and sensors |
| Intercooler | Unknown | Measure core, identify end tanks/branding |
| Suspension | Unknown | Springs, dampers, bars, end links, spacers, ride height |
| Wheels/tires | Unknown current set | Size, offset, spacer, load/speed rating, date codes, tread depth |

## Baseline inspection procedure

### 1. Documentation
- Photograph VIN labels, emissions label, option labels, odometer.
- Save recall results from both Ford and NHTSA.
- Obtain all receipts, tune files, Accessport serial info, key count, radio security/integration docs.
- Photograph every non-stock wire splice, add-a-fuse, ground point, control box.

### 2. Full electronic scan (OBDLink MX+ + FORScan)
- Scan every module, not only the PCM.
- Save all continuous, pending, history and permanent DTCs.
- Save freeze frame for every powertrain code.
- Record battery voltage key-off, key-on, during cranking.
- Record PCM strategy/calibration identifiers.
- Do not clear codes until the report is saved.
- **Acceptance:** no unexplained current codes; battery + communication stable; stored history assigned to a case.

### 3. Engine mechanical condition
- Cold-start: crank time, timing-chain/tensioner noise, smoke, idle quality, fuel odor.
- Hot-idle: oil-pressure warning, misfire counters, vacuum behavior, cooling-fan operation.
- Inspect engine oil for level, fuel-dilution odor, coolant contamination, metallic debris.
- Inspect coolant cold for level, oil contamination, rust/deposits, mixed incompatible coolant.
- Inspect valve cover, timing cover, vacuum-pump area, turbo oil/coolant lines, oil pan, filter area for leakage.
- Inspect crankcase-ventilation hoses and fittings.
- Inspect coolant reservoir, cap, hoses, thermostat housing/water outlet, radiator end tanks.
- If tune history unknown or symptoms exist: dry compression test (battery supported); leakdown on any low/uneven cylinder; borescope if oil consumption, detonation evidence, or abnormal plug deposits. Don't judge from a single absolute compression number — cylinder consistency + leakdown location matter more.

### 4. Ignition and fuel
Remove plugs only on a suitably cool engine. Per cylinder record: brand/part number; measured gap before adjustment; electrode wear; insulator color/deposits; oil/fuel/coolant evidence; torque/removal feel + thread condition. Inspect coils for tracking, torn boots, corrosion, oil intrusion. Swap-test coils only after recording counters. Inspect injector balance via trims/misfire before condemning injectors.

### 5. EVAP and fuel-tank system
Ask/test for: rough running/stalling after refueling; difficult filling or pump shutoff; fuel-gauge irregularity; excessive vacuum when opening filler; tank deformation; P0456/P144A/P1450/P2196 or related. Check VIN campaign completion + PCM calibration before replacing components. A stuck purge valve can create multiple symptoms + secondary codes. → [[04 Recalls & TSBs]]

### 6. Turbo and charge-air system
Inspect compressor inlet, intake clamps, PCV connections. Check turbo shaft with correct technique (slight oil film ≠ failure). Inspect compressor outlet, hot-side pipe, intercooler, cold-side pipe, throttle-body connection, all O-rings/clamps. Look for witness marks. Inspect bypass valve, boost-control solenoid, wastegate linkage/plumbing. Regulated smoke/pressure test (don't exceed safe pressure). Compare commanded vs actual boost in a controlled log after mechanical integrity confirmed.

### 7. Cooling and thermal system
Pressure-test to correct cap/system spec. Confirm no coolant smell after shutdown. Verify fan stages via scan tool. Check radiator/condenser blockage, bent fins, debris between heat exchangers. Inspect undertray + ducting (missing ducting reduces thermal performance — note AGS delete).

### 8. MMT6, clutch, shifter
Clutch engagement height, slip under controlled load, chatter, dual-mass flywheel noise, release-bearing noise. Inspect shared brake/clutch reservoir. Inspect clutch master, pedal area, hydraulic line, bellhousing drain for leaks. Check every gear cold + hot, stationary + moving. Note 1–2 / 2–3 resistance, reverse engagement, whether double-clutching changes symptoms. Inspect shifter cable ends, bracket bushings, cable adjustment, mounts before blaming synchros. Check case + axle seals.

### 9. Mounts and driveline
Inspect passenger engine mount for fluid leakage/collapse, transmission mount for cracking, rear motor mount for torn/stiff bushings. Identify all aftermarket mounts. Check axles/CV boots, intermediate shaft support, wheel bearings, driveline clunk.

### 10. Brakes, suspension, steering
Measure pad thickness inner + outer. Measure rotor thickness/runout if pulsation. Check brake/clutch fluid moisture/age. Inspect hoses, calipers, slider operation, parking brake, ABS wiring. Inspect struts/shocks for leakage, springs, top mounts, ball joints, control-arm bushings, tie rods, end links, sway-bar bushings. Check steering play/noise/return-to-center. Record ride height at repeatable body points.

### 11. Wheels and tires
Record wheel size, offset, load rating, spacers. Inspect hub-centric engagement, stud/thread condition. Torque U.S. M12×1.5 nuts to **100 lb-ft / 135 N·m** on clean dry undamaged threads. Record tire size/model/date code, tread at three points, wear pattern. Use the driver's B-pillar placard as the primary cold-pressure reference.

### 12. Body and interior electrical
Inspect hatch wiring loom, water intrusion, spare well, battery tray, grounds, fuse additions. Test every light, switch, window, lock, wiper, HVAC mode, USB/12V outlet, steering control, speaker. Record any airbag/SRS warning before interior disassembly. Check under-seat connectors before seat modifications.

## Baseline approval criteria
Approved for staged modification only when: all safety-critical defects repaired; open recalls resolved or documented with a Ford plan; no active severe misfire, fuel-pressure, overboost, overheating or brake fault; fluid condition/service age established; tune + installed hardware identified; tires/brakes suitable for intended use; all unknown aftermarket wiring mapped + fused correctly.

## Related
[[VEHICLE]] · [[02 Maintenance Master]] · [[05 Diagnostics & DTC]] · [[00 Command Center]] · [[_KB-Home|KB Home]]
