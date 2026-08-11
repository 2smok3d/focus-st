# Focus ST Community Engineering Knowledge — v2 Seed

This file records **community evidence**, not factory fact. Every claim should eventually carry thread URL, post date, vehicle year, mileage, tune/fuel, relevant parts and outcome. Community evidence never silently overrides Ford/OEM documentation.

## Confidence model

- **C1 — repeated community pattern:** appears across multiple independent build/diagnostic reports and is mechanically plausible.
- **C2 — strong individual case:** detailed build/log/history from a credible owner/vendor, but still one vehicle.
- **C3 — anecdote:** useful lead only.
- **M — manufacturer/vendor claim:** attributed to the company; not independent validation.

## 1. Intercooler as an early modification

**Observed pattern — C1:** upgraded front-mount intercoolers repeatedly appear early in modified Mk3 Focus ST builds, especially once tuning or repeated high-load operation is involved.

Supporting community/vendor observations include:

- Edge Autosport's Focus ST build history used a cp-e intercooler during increasingly aggressive turbo setups and reported charge-temperature behavior as a key performance metric.
- Multiple owner builds reference upgraded FMICs alongside Accessport/custom tune, intake/charge piping and exhaust changes.
- Garrett, Mishimoto, cp-e and CVF all maintain Focus ST-specific intercooler products, which independently confirms that this is a mature modification category, though each company's performance numbers remain manufacturer claims.

**Garage rule:** do not say an intercooler is “required” merely because forums do. Use charge-air temperature, intended duty cycle, calibration requirements and tuner instructions. For Phoenix/high-ambient use, prioritize data logging because the thermal margin is smaller.

## 2. Rear motor mount / drivetrain mounts

**Observed pattern — C1:** rear-motor-mount upgrades are extremely common in Focus ST modification lists. Owners report improved drivetrain control/shift feel/wheel-hop behavior with an NVH tradeoff.

**Current vehicle relevance:** this car's read-only build record already lists a **Torque Solutions rear motor mount** and **Torque Solutions passenger-side mount** as installed.

**Garage diagnostic rule:** vibration, false-knock concerns, harshness and drivetrain movement must be interpreted in the context of upgraded mount stiffness. Exact mount durometer/revision remains important missing metadata.

## 3. Stock-turbo vs larger-turbo build philosophy

**Observed pattern — C1:** community build discussions separate two broad approaches:

1. responsive stock-turbo / bolt-on / tune builds emphasizing early torque and daily use;
2. larger-turbo builds trading spool behavior and system simplicity for sustained airflow/top-end power.

Detailed build reports show that moving to a larger turbo can introduce additional setup work involving boost control, fuel supply, charge piping, calibration, traction, clutch and thermal management. Some owners report long periods of reliable use; others report setup-related problems or engine failures. These are not contradictory once configuration, tune quality, fuel quality, heat and duty cycle are considered.

**Garage rule:** never publish one universal “safe WHP” number as a fact. Record actual torque curve, fuel, calibration, ambient temperature, engine health, cooling, intended duty cycle and supporting sample size.

## 4. 300-WHP-class community builds

**Observed pattern — C1/C2:** ~300-WHP-class Focus ST discussions typically involve some combination of intercooler, calibration, intake/charge-air improvements and, depending on turbo/fuel strategy, additional fueling or turbo hardware. Community evidence repeatedly emphasizes tune quality and thermal control.

**Garage rule:** represent `power_target` and `power_measured` separately. A dyno value must store dyno type, correction method, fuel, tire/gearing details when available, ambient conditions and tune revision.

## 5. PCV / catch-can / crankcase ventilation

**Observed pattern — C1/M:** PCV/CCV catch-can and baffle modifications are common. Radium's Focus ST-specific hardware explicitly separates PCV and CCV paths and documents different flow behavior at low vs high load.

**Current vehicle relevance:** this car has a P04DB crankcase-ventilation diagnostic history. Therefore catch-can or PCV modifications are not treated as cosmetic upgrades; they must be mapped into hose routing and diagnostic expectations.

**Garage rule:** before recommending any catch-can configuration, document the current PCV/CCV plumbing, existing baffle/valve state, symposer-delete state, tune implications if any and local emissions considerations.

## 6. Charge pipes / bypass or blow-off valves

**Observed pattern — C1:** charge-pipe and bypass/BOV changes commonly accompany upgraded intercoolers and turbo setups. Community reports cite coupler retention, boost leaks, sound preference and valve behavior as reasons.

**Garage rule:** a “boost leak” diagnostic must show the current pipe material, couplers, clamps, BOV/recirc configuration and vacuum source. Do not troubleshoot a modified charge tract using a stock routing diagram without overlaying the modifications.

## 7. Active grille shutter removal

**Observed pattern — C1/M:** several large Focus ST intercoolers require or encourage removal of active grille shutter hardware because of packaging. cp-e's development description explicitly notes removing shutters while maximizing core size; CVF lists AGS removal for its Street intercooler.

**Current vehicle relevance:** this car's existing record states the AGS blades **and motor/actuator** were removed by the prior owner.

**Garage rule:** any intercooler recommendation must score fitment with the car's already-removed AGS state. Any AGS-related DTC or aerodynamic/cooling reasoning must use the actual removed configuration rather than a factory-complete assumption.

## 8. Thermal-management escalation

**Observed pattern — C1/M:** radiator and oil-cooler upgrades are most frequently discussed for sustained high-load/track usage rather than as the first street-power modification. Mishimoto markets both a larger radiator and thermostatic oil cooler for 2013–2018 Focus ST; community track/big-turbo discussions repeatedly surface oil/coolant temperature management.

**Garage rule:** separate three temperatures:

- engine coolant temperature
- engine oil temperature
- charge-air temperature

Do not call “overheating” from one gauge without identifying which system is actually hot.

## 9. Intake modifications

**Observed pattern — C1:** aftermarket intakes are common but owner goals vary: sound, filter serviceability, turbo inlet flow, engine-bay appearance or package requirements. They should not automatically be credited with a specific horsepower gain.

**Current vehicle relevance:** Injen cold-air intake + ram-air setup are recorded installed.

**Garage rule:** the interactive bay defaults to the Injen/ram-air configuration. The OEM Motorcraft FA-1908 air-filter reference remains in the factory-parts knowledge base but is not shown as the currently installed filter until the exact Injen filter is identified.

## 10. Sound symposer delete

**Observed pattern — C1:** symposer-delete kits are common, partly for cabin sound preference and partly because certain PCV/catch-can layouts use that packaging space or vacuum location. Radium explicitly requires a compatible symposer-delete arrangement for some Focus ST catch-can kits.

**Current state:** unverified. Do not infer it solely from intake/mount modifications.

## 11. Clutch / differential / traction as power rises

**Observed pattern — C1:** higher-power FWD builds increasingly discuss clutch capacity, limited-slip differentials, tires and wheel-hop/traction control. Community examples show these often matter to usable performance more than another small engine bolt-on.

**Garage rule:** modification planning should score **usable traction and thermal margin**, not only estimated crank/whp gain.

## 12. Failure-case handling

Community build failures are valuable only when the garage records the full context. Example categories to capture:

- ring-land/piston failure
- injector/fueling problem
- turbo/wastegate failure
- clutch slip
- synchro/shift problems
- charge-pipe/coupler failure
- coolant leak/overheat
- oil contamination in charge-air system
- false knock / mount-induced noise
- calibration/boost-control setup problems

For each case, preserve:

`year → mileage → installed parts → turbo → fuel → tune → target boost/torque → ambient/duty cycle → symptoms → evidence → root cause certainty → repair → post-repair outcome`.

A dramatic failure story without those fields remains **C3 anecdote**.

## Initial community/source leads already identified

- Edge Autosport Focus ST build history (originally mirrored/referenced from FocusST.org; detailed multi-stage turbo/intercooler build).
- FocusST.org-linked owner intercooler reviews referenced by current Focus ST vendors.
- Classic Motorsports Focus ST build thread with turbo/catch-can/datalog discussion.
- Focus ST Forum (Germany) turbo/power/reliability threads — useful as historical community evidence, translated and cross-checked before canonical summaries.
- Stratified Automotive Focus ST big-turbo technical guide — tuner/vendor technical evidence, not OEM authority.
- Radium Engineering Focus EcoBoost PCV/CCV documentation — manufacturer technical evidence.

## Community ingestion target

The mature forum crawler/index should extract only publicly accessible material and store:

- canonical thread URL
- site
- thread title
- post ID / author handle
- date
- build configuration entities
- claim text summary (not wholesale copied post text)
- mileage/power/fuel/tune if stated
- outcome/failure/repair
- corroborating and contradicting posts
- confidence class
- system/component tags

Long copyrighted posts should be summarized, not mirrored wholesale.
