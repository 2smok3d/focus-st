---
title: 06 Powertrain Master Manual
aliases: ["06 Powertrain", Powertrain Manual]
tags: [focus-st, kb, powertrain]
---

# 06 · Powertrain Master Manual

> Full text (merged from the FFST vault). Build path → [[powertrain]].

## System map
Diagnose the 2.0L GTDI as one controlled system.
- **Air path:** filter → intake tube → compressor → hot-side charge pipe → intercooler → cold-side pipe → throttle body → intake manifold → cylinders.
- **Exhaust path:** cylinders → integrated exhaust manifold/head → turbine → downpipe/catalyst → exhaust.
- **Fuel path:** tank module/low side → high-pressure pump → rail → direct injectors.
- **Crankcase/EVAP:** PCV + fresh-air circuits manage crankcase vapors; EVAP canister + purge valve meter tank vapor into the intake. Purge failure imitates fuel, O₂ and drivability faults.
- **Torque path:** engine → dual-mass flywheel → 240 mm clutch → MMT6 → differential → axles → hubs.

A modification in one path changes the operating context of others. The tune is the control layer, not a substitute for mechanical integrity.

## Engine health
**Reliability priorities:** correct oil level/spec; no overheating/coolant loss; correct fuel for the map; healthy plugs/coils + no unresolved misfire; sealed charge + vacuum system; functional purge/PCV; no high-load low-RPM operation; controlled intake temperature + competent calibration.

**LSPI / low-speed high load:** risk rises when a turbo-DI engine is asked for high torque at low RPM. Don't floor the car in a tall gear at low RPM; downshift before requesting significant boost; use correct-quality fuel + oil; avoid excessive oil consumption + poor PCV; avoid aggressive calibration with uncontrolled low-RPM torque; keep charge temperature controlled. **No full-load pull begins below ~3,000 rpm unless the tuner specifies a different controlled procedure.** Street driving should downshift earlier rather than lug.

**Compression + leakdown:** use when tune history unknown, a cylinder-specific misfire remains, plug evidence is abnormal, oil/coolant consumption exists, or a high-power build is planned. Warm engine when safe; support battery; same procedure on all cylinders; compare cylinders rather than a generic absolute number; leakdown location matters (intake/exhaust/crankcase/cooling); repeat an anomalous test before condemning the engine.

**Oil pressure:** the factory pod is useful for trend awareness but not a substitute for a verified mechanical test when there's a warning, abnormal noise or suspect reading. Any true loss of pressure is a shutdown condition.

## Ignition
Stock: OEM gap 0.027–0.031"; Ford normal replacement ~100,000 mi. Tuned: many ST tuners specify ~0.025–0.026" gap, a one-step-colder plug for boost/E-blend where recommended, replacement/inspection ~15,000–20,000 mi. Not universal — plug selection must match calibration/use/climate; colder is not automatically better on a lightly used or stock car. Read plugs by cylinder (uniformity, cracked porcelain, electrode erosion, detonation peppering, wet fuel/oil/coolant, carbon tracking, heat range). Don't "read" a plug immediately after long idle.

## Turbocharger and boost control
Stock turbo favors fast response + strong low/midrange torque; becomes inefficient as airflow demand rises (higher charge temp + backpressure). The practical stock-turbo build favors repeatable thermal performance over a single peak pull. Components: compressor/turbine, wastegate actuator + flapper, boost-control solenoid + hoses, bypass/recirc valve, MAP/TMAP data, PCM/tune torque + boost targets. **Wastegate warning:** don't alter rod length/preload as a generic "free power" mod — incorrect preload causes under/overboost, poor control, accelerated wear; use the turbo/tuner measured procedure only after leaks + control plumbing are proven. **Charge-pipe retention:** a pipe that blew off once must not simply be pushed back on — inspect bead/retention feature, O-ring + groove, clamp type/orientation, oil contamination, pipe alignment + engine movement, intercooler outlet/inlet damage, excessive boost/mount movement; clean compatible surfaces, replace damaged seals/clamps, pressure-test after.

## Intercooler
The stock unit is widely documented as a thermal limitation, including on tuned stock-turbo cars — upgrade before an aggressive calibration. Selection: demonstrated temperature control (not just core thickness), pressure drop, end-tank design/sealing, bumper/duct fit, weight/mounting, retained crash/airflow structure, pipe compatibility, AZ heat performance. Validation: log charge-air temp before + after under similar ambient/gear/load; a good system recovers between pulls and avoids rapid heat soak; don't compare different days without noting weather.

## Intake
On the stock turbo, intake changes usually provide sound + reduced restriction at higher airflow; gains depend on complete system/tune. Before retaining the current large intake: identify brand + MAF housing dimensions; verify tune requirement; inspect filter sealing + support; isolate from hot air; ensure no rubbing/unsupported mass; inspect fuel trims + drivability. An oversized/incorrect MAF housing alters reported airflow and requires calibration.

## Exhaust and downpipe
- **Cat-back:** primarily sound/weight/packaging on a stock-turbo street car; evaluate drone, hanger alignment, ground clearance, heat shielding, leaks.
- **Downpipe:** can reduce turbine-outlet restriction but introduces tune dependency, catalyst-efficiency codes, emissions/inspection consequences, heat + O₂ wiring concerns, increased noise/odor. Don't buy before defining power target + legal requirements; a high-flow catted unit is not automatically compliant.
- **Crackle calibrations:** aggressive pops/bangs raise exhaust temperature and stress catalysts/turbine/exhaust — excluded from the reliability-first roadmap.

## Fuel system and ethanol blends
- **Pump-gas path:** start with a conservative custom calibration for consistent AZ fuel; a 91-octane tune calibrated as 91, not with 93 assumptions.
- **E30 path:** reputable tuners offer E30 on otherwise stock fuel hardware at stock-turbo airflow, but safe use requires a tuner-approved calibration, measured ethanol content of both fuels, correct blend calculation, adequate fuel level/mixing, datalogged rail pressure + trims, and no accidental full E85 fill on an E30 map. Seasonal pump ethanol varies — "three gallons of E85" is not a universal recipe.
- **Stock fueling limits:** tuner estimates vary; frequently cited stock DI limits are roughly mid-300 whp, while auxiliary/upgraded fueling becomes necessary around the 400-whp region. Planning estimates, not guaranteed thresholds. Build fueling margin before reaching the limit.

## PCV, crankcase ventilation, catch cans
Inspect first: factory PCV valve/separator function; hoses + check valves; vacuum/boost routing; oil consumption + leaks; intake-valve deposits when symptoms warrant. A catch can is an optional engineered separator — not mandatory insurance and not a cure for a failed PCV system. Requirements: correct pressure direction + check valves; no freezing concern for the climate; accessible drain schedule; secure heat-safe mounting; no vacuum leak; no vent-to-atmosphere odor/emissions issue unless deliberately designed + legal.

## Cooling (Arizona)
Keep condenser/radiator/intercooler airflow paths clean; retain proper ducting + undertray; verify fan operation; inspect reservoir/cap + hose aging; establish coolant history now; monitor charge temperature as well as coolant temperature. An intercooler doesn't replace coolant maintenance; a lower thermostat doesn't repair an inadequate radiator, fan or tune.

## MMT6 transmission
Shift-quality diagnostic order: driver technique + clutch release → correct fluid level/condition/spec → shifter cable ends + bracket bushings → cable alignment/adjustment → engine/transmission/rear mount condition → clutch hydraulic release → clutch/dual-mass flywheel → internal synchro/gear/bearing. Common practical improvements: quality cable-end/bracket bushings; correct cable alignment; weighted/shorter shift lever for feel; rear motor mount selected for acceptable NVH; fresh correct fluid. A short shifter reduces lever travel but doesn't repair clutch drag or worn synchros; excessively stiff mounts make engagement harsher + add cabin vibration. Reverse-to-first: fully depress clutch, pause in neutral, allow shafts to stop, select first without force.

## Clutch and dual-mass flywheel
Slip indicators: engine speed rises without proportional acceleration under controlled load; higher gears slip first; burning odor / worsening hot behavior; distinguish contamination/hydraulic fault from worn friction. Don't lug the engine to test slip. Shared reservoir → inspect level/condition, master/pedal area, hydraulic line, bellhousing (concentric slave), bleed correctly; a pedal problem isn't automatically the disc. Higher-power planning: choose clutch capacity with reasonable margin (not the highest advertised clamp load) considering torque curve, street drivability, pedal effort, dual- vs single-mass NVH, flywheel serviceability, hydraulic components + rear main seal while accessible.

## Mounts
Car has a Torque Solutions component — identify exact location + durometer before buying another. Rear motor mount: benefits (reduced engine roll, more consistent shift feel, less wheel hop) vs tradeoffs (idle/AC vibration, dashboard/interior buzz, more impact to drivetrain, reduced daily refinement if too stiff). Inspect all three primary mount positions as a system; a stiff rear mount can reveal a collapsed hydraulic side mount.

## Modification dependency table
| Modification | Required first | Validate after | Common conflict |
|---|---|---|---|
| Custom pump-gas tune | Healthy baseline, correct plugs/fuel | Datalog, boost/fuel pressure, misfire | Unknown intake/downpipe or poor fuel |
| E30 tune | Proven pump tune, measured ethanol | Rail pressure, trims, mixture | Wrong blend/full E85 |
| Intercooler | Fitment/duct plan | IAT recovery, leaks | Poor crash-bar/pipe fit |
| Intake | Identify MAF housing/tune need | Trims, drivability | Incorrect calibration/hot-air leak |
| Downpipe | Legal/tune plan | Leaks, O₂, boost control | Emissions/CEL/heat |
| Big turbo | Engine health, clutch, cooling, fueling plan | Full professional calibration | Stock fuel/clutch/traction limits |
| Catch can | Healthy PCV, correct routing | Vacuum, leaks, collected volume | Misrouting/freeze/neglected drain |
| RMM | Inspect other mounts | NVH, clearance, shift feel | Excessive stiffness/cabin buzz |

## Related
[[powertrain]] · [[09 Mods & Tuning]] · [[05 Diagnostics & DTC]] · [[02 Maintenance Master]] · [[_KB-Home|KB Home]]
