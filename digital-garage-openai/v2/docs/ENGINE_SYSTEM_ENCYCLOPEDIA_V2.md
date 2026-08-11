# 2017 Ford Focus ST — Engine & Powertrain Systems Encyclopedia v2

**Vehicle scope:** North American 2017 Focus ST / Mk3.5 / 2.0L GTDI EcoBoost / Getrag-Ford MMT6.

**Purpose:** mechanic-facing system map. This document is not a substitute for a licensed Ford Workshop Manual procedure. Torque values, one-time-use fasteners, special tools, timing procedures, restraint procedures and module programming must be resolved against the exact VIN / Ford service procedure before work begins.

## 1. Canonical factory architecture

Ford's 2017 Focus ST supplement identifies the car as a 2.0L GTDI EcoBoost inline-four with overboost, twin independent variable cam timing, coil-on-plug ignition, a 150-bar high-pressure fuel system, 57 mm throttle body, forged-steel connecting rods, cast-aluminum pistons, cast-iron crankshaft, single-scroll turbocharger and Getrag-Ford MMT6 six-speed manual transaxle.

Factory spark-plug gap: **0.027–0.031 in (0.70–0.80 mm)**. Factory compression ratio: **9.3:1**. Firing order: **1-3-4-2**. Ford describes up to **21 psi** boost under permitted overboost conditions, while SAE-certified ratings are achieved at lower boost.

### Authoritative Ford source set

- 2017 Focus ST Owner's Manual Supplement — At a Glance / ST powertrain description.
- 2017 Focus ST Owner's Manual Supplement — Engine Specifications.
- 2017 Focus ST Owner's Manual Supplement — Motorcraft Parts.
- 2017 Focus ST Owner's Manual Supplement — Capacities and Specifications.
- 2017 Focus ST Owner's Manual Supplement — Under Hood Overview.

These are indexed as OEM-authority sources in the garage provenance model.

## 2. Long block

### Block / rotating assembly

Track as separate component records:

- cylinder block
- crankshaft
- main bearings
- connecting rods
- pistons / ring lands
- wrist pins
- balance / crank trigger hardware
- oil squirters where documented by service information
- front cover / crank seal
- rear main seal

### Cylinder head / valvetrain

Track:

- aluminum cylinder head
- intake and exhaust camshafts
- Ti-VCT phasers and control solenoids
- cam position sensors
- valves, springs, retainers and guides
- timing chain, guides and tensioner
- cam cover / gasket
- direct-injection injector bores and seals

### Mechanic data to associate with every internal-engine case

- mileage
- oil level and service age
- oil pressure evidence
- compression by cylinder
- leak-down by cylinder and leakage path
- spark-plug appearance indexed by cylinder
- borescope images indexed by cylinder
- misfire counters
- knock-retard / correction history where a trustworthy source provides it
- coolant-loss evidence
- fuel-pressure actual vs commanded
- tune / calibration active during symptom

## 3. Air path and forced induction

Model the complete air path in order rather than treating the turbo as one isolated component:

`air entry → filter/intake → compressor inlet → turbo compressor → hot charge pipe → intercooler → cold charge pipe → throttle body → intake manifold → intake ports`

### Current vehicle state

The existing FFST build log is read-only evidence and currently records:

- **Injen cold-air intake — installed**
- **Ram-air intake setup — installed**

The exact Injen part number, filter model, ram-air duct geometry and installation date/mileage are still unverified and therefore remain open metadata fields.

### Turbocharger

Factory system: single-scroll exhaust-driven turbocharger. Store separately:

- compressor housing/wheel
- turbine housing/wheel
- center housing / bearing assembly
- wastegate actuator
- wastegate linkage / preload
- boost-control solenoid and hoses
- compressor bypass / recirculation valve
- oil feed / drain
- coolant feed / return
- turbine inlet / exhaust manifold interface
- downpipe interface

### Diagnostic patterns

For low boost / P0299-style complaints, compare **commanded load/boost vs actual**, not boost gauge position alone. Inspect intake restriction, compressor inlet, charge-air tract, intercooler end tanks/connections, bypass valve, wastegate mechanical movement/preload, control plumbing, exhaust restriction and tune demand.

For overboost / P0234-style complaints, inspect wastegate movement/preload, boost-control plumbing/solenoid, calibration demand and mechanically restricted wastegate travel before assuming a turbocharger replacement is required.

### Intercooler engineering

An intercooler replacement should be evaluated as a thermal-control modification, not merely a peak-power part. Record:

- core dimensions and volume
- frontal area
- end-tank design
- pressure drop
- charge-air temperature entering/leaving if measured
- ambient temperature
- heat-soak recovery time
- fitment effects on radiator/condenser airflow
- crash-bar / shutter / ducting changes

Phoenix use materially increases the value of collecting ambient and charge-air-temperature data. Do not convert that observation into a fixed service requirement without data.

## 4. Fuel system

The garage models low-pressure and high-pressure fuel sides separately.

### Low-pressure side

- fuel tank
- in-tank pump/module
- supply line
- pressure control where applicable
- fuel quality / ethanol content record

### High-pressure direct injection

- mechanically driven HPFP
- rail
- rail pressure sensor
- high-pressure lines
- four direct injectors
- injector seals

Ford identifies a 150-bar fuel pump in the ST supplement. Diagnostic records should retain actual and commanded fuel pressure, RPM, load, throttle, lambda/AFR representation, ethanol content when known, tune identifier and ambient conditions.

Any auxiliary-fueling or upgraded-HPFP setup is represented as a **new fuel-system configuration**, not simply an installed part, because it changes diagnostic expectations and failure modes.

## 5. Ignition / combustion monitoring

Factory ignition is coil-on-plug.

### Ford scheduled-service references

- spark plugs: Motorcraft **SP-537 / CYFS12Y2**
- factory gap: **0.027–0.031 in**

The existing legacy parts catalog contains plug and gap claims that are not automatically canonical. v2 stores OEM gap, tuner-requested gap and measured installed gap as separate values.

For tuned configurations, a smaller gap or different heat range can be a tuner requirement, but it is never labeled Ford factory specification unless Ford documents it.

Track per cylinder:

- plug manufacturer/number
- heat range
- measured gap
- installation mileage
- coil identifier
- misfire history
- compression/leak-down
- injector-related evidence

## 6. PCV / crankcase ventilation

This vehicle has an existing history involving **P04DB / crankcase ventilation**. The visual garage therefore marks PCV as diagnostically relevant even when the MIL is not currently illuminated.

Model:

- crankcase pressure source
- PCV valve / baffle assembly
- manifold-vacuum path
- fresh-air / turbo-inlet path
- hoses and quick-connect fittings
- seals/gaskets affected by excessive crankcase pressure
- aftermarket catch-can/baffle hardware if later installed

A P04DB case should preserve DTC status (current/pending/stored/permanent), freeze-frame data if available, smoke-test setup, hose routing photos, idle trims/airflow observations and final verification after repair.

## 7. EVAP

Keep EVAP separate from PCV despite shared vacuum/intake plumbing.

Track purge valve, vapor lines, canister, fuel-tank pressure data where supported and PCM-commanded purge behavior. Ford Focus-platform purge-related field history should be researched through exact-year TSB/recall/manufacturer-communication records rather than generalized from unrelated model years.

## 8. Lubrication

Ford's 2017 ST material specifies SAE 5W-30 meeting the then-current Ford specification **WSS-M2C946-A** and an engine oil fill including filter of approximately **5.4 L / 1.4 gal**. The garage stores specification, viscosity and actual fill quantity separately so future superseding Ford specifications can be tracked without rewriting historical service records.

Service part:

- Motorcraft oil filter **FL-910-S**

Track:

- oil brand/product
- viscosity
- certification / Ford specification
- filter part
- quantity added
- mileage/date
- track / severe-heat exposure
- oil consumption between changes
- oil-pressure observations
- oil-temperature observations
- laboratory analysis report when available

## 9. Cooling system

Model cooling as a complete heat-rejection system:

- block/head coolant passages
- water pump
- thermostat/housing
- radiator
- degas/expansion reservoir
- hoses / quick-connects
- cabin heater circuit
- turbo coolant circuit
- cooling fan/module
- radiator ducting
- condenser interaction
- intercooler frontal interaction
- active grille shutter state

### Current vehicle state

The existing build log records the **active grille shutters and their motor/actuator as removed by a previous owner**. That is modeled explicitly because airflow, diagnostics and front-end packaging differ from a factory-complete car.

Ford's 2017 ST specification source lists approximately **6.45 L (1.7 gal)** engine-coolant capacity and the then-specified Motorcraft Orange coolant meeting **WSS-M97B44-D2**. Because Ford coolant recommendations have evolved, any present-day service plan must check Ford's current compatibility/supersession information rather than selecting by color alone.

## 10. Mounts / driveline support

Current build-log evidence records:

- **Torque Solutions rear motor mount — installed**
- **Torque Solutions passenger-side motor mount — installed**

The visual garage presents these as upgrades. Exact durometer, revision and installation mileage remain open fields.

Mount changes can influence NVH and can complicate interpretation of vibration or noise complaints, so every diagnostic case involving knock-like noise, vibration, wheel hop or drivetrain movement should include current mount configuration.

## 11. Transmission / clutch

Canonical transmission family: **Getrag-Ford MMT6 six-speed manual**.

Ford's ST supplement lists:

| Gear | Ratio | Final drive |
|---|---:|---:|
| 1 | 3.23 | 4.063 |
| 2 | 1.95 | 4.063 |
| 3 | 1.32 | 4.063 |
| 4 | 1.03 | 4.063 |
| 5 | 1.13 | 2.955 |
| 6 | 0.94 | 2.955 |
| Reverse | 4.60 | 2.955 |

The split final-drive arrangement is important for gear/RPM calculators.

The garage tracks:

- clutch disc
- pressure plate
- dual-mass or alternate flywheel
- release bearing / slave cylinder
- master-cylinder/hydraulic circuit
- shifter cables/bushings
- synchronizer symptoms by gear
- fluid specification and service record
- axle seals
- differential bearings
- left/right halfshafts and CV joints

## 12. Factory service parts corrected from Ford source

For the 2017 Focus ST supplement Ford lists:

| Service item | Motorcraft reference |
|---|---|
| Air filter element | **FA-1908** |
| Oil filter | **FL-910-S** |
| Battery | **BXT-96R-590** |
| Spark plugs | **SP-537 / CYFS12Y2** |
| Cabin air filter | **FP-70** |
| Fuel filter | Lifetime-filter designation |

This specifically supersedes the legacy garage's unsupported `FA-1802` air-filter entry for canonical factory reference purposes. The legacy file remains untouched as evidence of what was previously recorded.

## 13. Mod-aware mechanic rules

Every procedure and diagnostic query should resolve the current configuration first.

Examples:

- **Intake complaint:** do not assume stock airbox; show Injen + ram-air state.
- **Drivetrain vibration:** show Torque Solutions mount state before suggesting factory-mount diagnosis.
- **Cooling/front airflow:** show AGS removed before reasoning about factory shutter behavior.
- **Battery/charging:** show upgraded-battery state but demand exact battery chemistry/capacity before charging recommendations.
- **P04DB:** surface PCV history automatically.
- **Boost/charge-air:** flag intercooler status as unverified until visually or documentarily confirmed.

## 14. Knowledge expansion targets

Each subsystem record should eventually contain:

1. factory function
2. physical location
3. interactive-bay hotspot
4. OEM part numbers / supersessions
5. connector / hose / fastener relationships
6. torque-spec references
7. removal/installation procedure links into legitimately owned manuals
8. service interval
9. common symptoms
10. DTC relationships
11. diagnostic tests and expected observations
12. stock-equivalent replacements
13. OEM+ alternatives
14. performance alternatives
15. modification interactions
16. track/severe-use implications
17. photos / diagrams
18. forum claims and corroboration count
19. installed vehicle state
20. event history and evidence links

This twenty-field pattern is the minimum completeness target for the mature component knowledge graph.
