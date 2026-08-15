---
title: 02 Maintenance Master
aliases: ["02 Maintenance Master"]
tags: [focus-st, kb, maintenance]
---

# 02 · Maintenance Master

> Full text (merged from the FFST vault). Working log → [[MAINTENANCE]].

Two standards: **Ford minimum** (published NA schedule for an unmodified car) and the **FFST reliability schedule** (conservative plan for an 86k turbo car in AZ heat, possibly custom-tuned). The FFST schedule never changes the required fluid spec — it shortens intervals where heat, age, tuning or uncertain history justify it.

## Immediate age-and-history reset
Perform unless a recent dated receipt proves completion:
| Priority | Service | Acceptance |
|---|---|---|
| 1 | Engine oil + filter | correct 5W-30; inspect drained oil/filter; no fuel/coolant contamination or debris |
| 1 | Full module scan + battery/charging test | report saved; battery stable during crank/scan; no unexplained codes |
| 1 | Brake + clutch hydraulic fluid | clear fluid, acceptable moisture/boil test; flush if age unknown |
| 1 | Coolant condition + history | correct compatible coolant, no mixing/sludge, pressure integrity; service now if original/unknown |
| 1 | Spark-plug inspection | part number, gap, cylinder condition documented; replace if worn/wrong for tune |
| 1 | Tire/brake inspection | safe date codes, tread, pressure, pad/rotor, lug torque |
| 2 | MMT6 fluid | replace if history unknown; verified compatible fluid + correct fill |
| 2 | Engine + cabin air filters | replace if dirty/unknown; verify airbox/intake sealing |
| 2 | EVAP/purge + VIN campaign | no post-refuel stumble, tank deformation, hard fill, related DTC |
| 2 | Charge-air leak inspection | all pipes seated/retained; no oil-saturated loose connections or smoke-test leak |
| 3 | Alignment + suspension | wear pattern explained; no damaged bushings/bearings/leaking dampers |

## Repeating FFST reliability schedule
**Every fuel stop (until consumption characterized):** oil level (level ground, consistent method); coolant reservoir when cool; look underneath for fluid; note fuel consumption/smell/smoke/post-refuel behavior. Then monthly + before long/high-load trips.

**Every month:** tire cold pressures + damage; oil + coolant; brake-fluid reservoir; exterior lights + wipers; battery terminals/corrosion; intercooler/charge-pipe connections; review scan-tool warnings/pending codes.

**Every 5,000 mi or 6 mo:** oil + filter; tire rotation; brake pad/rotor visual; tread inner/center/outer; suspension/steering/CV-boot visual; engine/trans mount visual; leak inspection; intake-filter inspection; review consumption log. For short trips, severe heat, track use, fuel dilution, aggressive tune, or frequent high-load: shorten oil service to **~3,000–4,000 mi** (FFST strategy, not Ford-required).

**Every 10,000 mi:** the 5k inspection; plug gap/condition if tuned/ethanol/misfire; coil boots + plug wells; PCV + vacuum hoses; exhaust hangers/clamps/heat shields/O2 wiring; charge-air clamps/O-rings/witness marks; battery health before AZ summer.

### Spark plugs
- **Ford normal interval:** ~100,000 mi on an unmodified car.
- **FFST stock strategy:** inspect now (incomplete history); after baseline inspect ~20,000–30,000 mi, replace on wear/gap/symptoms/deposits.
- **Tuned:** inspect every oil service initially; many ST tuners replace ~15,000–20,000 mi and use a tighter gap ~0.025–0.026" for boost. Follow the exact tuner + plug-manufacturer instruction; never go colder just because it's marketed as an upgrade. OEM gap ~**0.027–0.031"**.

### MMT6 transmission fluid
Baseline replacement now if undocumented; repeat ~**30,000–50,000 mi**, shortened for track/contamination/shifting deterioration/heat. Verify fluid spec + fill procedure. Capacity ~**1.8 US qt / 1.7 L**; period Ford spec **WSS-M2C200-D2**, Motorcraft **XT-11-QDC**. Inspect magnetic drain material; record quantity/appearance. Final level follows procedure, not a blind pour.

### Brake and clutch hydraulic fluid
Shared reservoir. Flush every **2 years** street (or earlier by moisture/boil test); before + after demanding track use. Use fluid meeting Ford **DOT 4 LV** unless a performance fluid is deliberately chosen for the full system/climate. Never mix DOT 5 silicone. Any level loss → leak diagnosis at brakes, lines, clutch master, hydraulic line, concentric slave/bellhousing.

### Coolant
Ford period schedule: initial **100,000 mi / 6 yr**, then **50,000 mi / 3 yr**. Undocumented coolant is due by time even below 100k. Original fill Motorcraft Orange **WSS-M97B44-D2**; Motorcraft Yellow **WSS-M97B57-A2** is Ford-identified compatible for service. Don't add generic universal coolant/chemical flush without documented compatibility. Record exactly what is installed.

### Air/cabin filters, battery, tires, wheels, brakes
- Engine air filter: inspect every 10k, more in dust; don't over-oil aftermarket filters; allow full cure; verify no collapse/rub/hot-air ingestion; verify no contact with brake/clutch lines or wiring.
- Cabin filter: at least annually; AZ dust may justify 6–12 mo; confirm airflow direction + clear cowl/drain.
- Battery: load/conductance test before AZ summer + on undervoltage; record date; clean/tighten terminals to verified values; regulated support during programming.
- Tires: B-pillar placard authority; check monthly + before high speed; rotate 5,000–7,500 mi; record inner/center/outer tread; replace on condition/heat cycles/age; re-align after suspension changes/impacts/uneven wear.
- Wheel nuts: M12×1.5, **100 lb-ft / 135 N·m**, clean dry threads; don't lubricate + reuse damaged fasteners.
- Brakes at every tire service: inner/outer pad; slider + dust boots; rotor cracking/lip/heat-check/rust + thickness; hose flex + ABS wiring; clean hub mating.

### Direct-injection intake-valve deposits
Don't clean by mileage alone. Verify ignition/fueling/compression/vacuum-boost leaks/purge first; borescope if symptoms remain; mechanically controlled cleaning by a competent shop when confirmed; prevent debris entering cylinders. A catch can is not a substitute for diagnosis.

## Post-modification service rules
- **After intake/charge-pipe/intercooler:** inspect at install, after first heat cycle, after 100–250 mi; review fuel trims + commanded/actual boost; check rubbing/clamp migration/oil mist.
- **After a tune revision:** verify fuel before flashing; maintain battery voltage; complete tuner-prescribed idle/cruise/WOT logs safely; inspect plugs/fluids more often; stop high-load testing for misfire, knock outside guidance, fuel-pressure drop, boost-control error, overheating, or mechanical noise.
- **After suspension/wheel changes:** verify clearance at full lock + compression; align; inspect tire-to-strut/fender/liner; verify hub engagement + fasteners.
- **After brake work:** bedding per manufacturer; check pedal before moving; inspect leaks; verify fastener torque; recheck fluid + rotor/caliper temperature balance after testing.

## Prohibited shortcuts
No universal coolant by color; no additive as a repair substitute; no plug gap adjusted by striking the electrode; no pressure-washing connectors/coil wells/intake; no clearing DTCs before freeze-frame; no high-load low-RPM "test" of a tune; no repeated limiter/launch/flat-shift abuse as diagnostic; no unverified torque values from other Focus generations or European manuals.

## Related
[[01 Vehicle Record & Baseline]] · [[06 Powertrain]] · [[03 OEM Specifications]] · [[MAINTENANCE]] · [[_KB-Home|KB Home]]
