---
title: 08 Electronics, Infotainment & Interior
aliases: ["08 Electronics & Interior", Electronics, Interior]
tags: [focus-st, kb, electronics, interior]
---

# 08 · Electronics, Infotainment and Interior Modernization Manual

> Full text (merged from the FFST vault). Build → [[cockpit-electronics]].

## Objective
Modernize the ST1 cabin to a reversible, serviceable 2030-style system while retaining vehicle functions, preventing network faults and avoiding aftermarket clutter. Start: 4" SYNC 1 display, factory steering-wheel controls, factory center gauge pod, OBDLink MX+. Planned: aftermarket head unit, iDatalink Maestro RR2 + Focus integration hardware, wireless Android Auto, blue accent lighting, wireless charging, spare-well subwoofer.

## Electrical rules
1. Disconnect power only after recording codes/radio-module state/required procedures. 2. Use a regulated support supply for programming/long sessions. 3. Never probe an airbag/SRS circuit with a test light/ordinary meter. 4. Fuse every added circuit as close to its source as practical. 5. Size wire for current/length/temperature/voltage-drop, not connector appearance. 6. Proper crimp tooling, sealed connectors where exposed, strain relief, abrasion protection. 7. Never use strand-cutting taps as the permanent standard. 8. Keep audio power wiring separated from signal/CAN where practical. 9. Preserve service loops + access to factory connectors. 10. Document every fuse/splice/ground/module.

## Baseline module inventory (before removing SYNC)
Run a full FORScan scan; save every module DTC; record APIM, ACM, IPC, BCM, FCIM + steering-control configuration; save as-built data by module; photograph every connector + pin-lock position; record factory functions (chimes, steering controls, clock, Bluetooth, USB, backup camera if present, vehicle settings, display behavior). Don't assume all ST1 cars share identical harnesses/options.

## Head-unit + Maestro RR2 architecture
Depending on the final radio, Maestro firmware + vehicle compatibility, RR2 can support steering-wheel controls, retained factory features + warning chimes, vehicle information, gauges + OBD-derived data, tire-pressure/check-engine info where supported, programmable control behavior. Availability is radio-, firmware-, vehicle- + configuration-dependent — build from the current iDatalink compatibility page + installation guide for the exact radio model, not a generic video.
**Bench-planning (before dash disassembly):** exact radio model + firmware; RR2 serial/firmware; exact Focus harness/kit; antenna adapter; USB retention/replacement; microphone location; backup-camera plan; amp/speaker architecture; OBD connection strategy; steering-control button assignment; chime + vehicle-info behavior; parking-brake/reverse/speed-signal requirements; ventilation + screen-clearance.
**Install sequence:** update/program Maestro on the bench → label every harness branch → verify pin locks + grounds → dry-fit bezel/radio/USB → connect + test before final assembly → test ignition states, sleep/wake, battery draw → test every retained function → scan all modules → then secure, dress + close the dash.
**Final function test:** key-on/start/shutdown + retained accessory power; all steering buttons (incl. long-press); front/rear speakers + balance/fader; microphone/call quality; Android Auto connect/reconnect; GPS/Wi-Fi/BT coexistence; dimmer/illumination; reverse camera + trigger; chimes/alerts; gauges + OBD data; no parasitic wake cycle; no new U-codes or module faults.

## OBDLink MX+ + gauge integration
Use the MX+ primarily for diagnostics + logging. A radio's Maestro gauge screen + the OBDLink app may compete for the diagnostic connection. Rules: verify whether the final radio uses Maestro's dedicated OBD connection; don't run multiple active adapters that load the bus; remove/disable continuous polling when diagnosing sleep/battery draw; record PID names/units/sampling rate; treat calculated values as estimates; don't mount a bright diagnostic display where it distracts the driver. Display hierarchy: safety warning from factory IPC → coolant/charge temperature trend → boost/load → fuel-pressure or ignition data only during diagnosis/tuning → entertainment last. Don't turn the daily screen into an alarm wall.

## FORScan configuration control
FORScan exposes configuration + module as-built, but incorrect edits create lighting/communication/battery/feature faults. Workflow: fully charge/test battery + regulated support → known-compatible adapter + current software → save original config/as-built per module separately → record exact address/value changed → one change at a time → cycle ignition exactly as directed → scan modules + test affected functions → revert immediately if abnormal. Classes worth evaluating: convenience lighting; lock/unlock; global windows where supported; splash screens/themes where compatible; audio config after hardware changes; backup camera/parking-assist if adding supported OEM hardware. No raw hex stored as universal instructions — match module/software/equipment. Forum reports include incorrect edits causing lights to stay on or other unexpected behavior.

## Power distribution for accessories
Categories: radio/Maestro/USB; wireless charging; ambient lighting; dash camera; amplifier/subwoofer; optional auxiliary display. Rules: dedicated fused distribution rather than many unrelated add-a-fuse taps; deliberate ignition-switched vs constant power; verify circuit capacity + sleep behavior; one high-quality chassis ground or engineered distribution (not random sheet-metal screws); protect wiring through bulkheads + moving panels; label both ends. Parasitic-draw validation: let modules sleep → measure total draw without waking the vehicle → compare with baseline → isolate accessories by fuse if excessive → verify Bluetooth/Wi-Fi accessories aren't repeatedly waking modules.

## Wireless charging tray
Requirements: Qi2/current high-quality Qi where compatible; secure phone under accel/braking; no interference with shifter/parking brake/cup holders/HVAC; serviceable removable insert; hidden fused power; thermal path + ventilation; wired USB-C backup; indicator light without nighttime glare. Build: removable ABS/PETG/automotive insert; mount the coil at the phone's actual coil location with minimal material gap; non-slip silicone + adjustable alignment; quality automotive 12V→USB-C PD/Qi controller with over-temp + over-current protection; airflow beneath the coil (AZ cabin temps reduce/stop charging); avoid enclosing lithium battery packs. Validation: test with the phone case installed; wired vs wireless Android Auto; measure charging stability during navigation + high cabin temperature; verify no radio noise, touch-screen interference, or battery draw after shutdown.

## Ambient lighting — blue accent
Use blue as an accent only: door-pocket/handle glow; center-console edge; footwell indirect light; restrained dash line without visible hotspots. Electrical: dimmable; tied to an appropriate illumination/ignition strategy; separately fused; no visible bare LED points; no interference with airbags/door movement/window regulators; connectors at removable panels; no exterior-facing blue light that could violate law or resemble emergency lighting. Set a maximum nighttime brightness + lock a default blue shade; no flash/chase/distraction while driving.

## Audio architecture
Improve clarity, midbass + low-frequency extension without sacrificing cargo utility or service access. Order: diagnose existing speakers + rattles → treat doors + cargo panels selectively → choose front speakers by mounting depth/sensitivity/amp plan → add DSP/amplification when tuning control is needed → add spare-well subwoofer + enclosure → tune crossover/polarity/delay/level by measurement, not bass boost. Sound treatment: constrained-layer damping on resonant metal; closed-cell foam for decoupling; mass barrier only where weight/water/attachment are managed; fabric tape/foam at trim contact. Don't block door drains, seal moisture inside panels, or cover service fasteners permanently.
**Spare-tire-well subwoofer:** enclosure volume matched to the driver; rigid mounting + sealed cable pass-through; amplifier ventilation; access to fuel-pump/service areas; water-intrusion inspection + drainage strategy; cargo-floor load support; removable quick-disconnect design; documented spare/roadside plan. A shallow truck-style 10" is acceptable only if its enclosure/excursion/efficiency/thermal needs fit the actual available volume. **Underbody spare:** don't fabricate without evaluating exhaust heat, suspension travel, ground clearance, crash behavior, water/debris, structural attachment — prefer a compact spare inside cargo, an engineered false-floor, or a repair-kit + roadside coverage.

## Interior ergonomics (user ~6 ft, 215 lb, knee/thigh clearance)
Order: optimize seat height/back/telescoping-wheel position → inspect seat-track travel + obstructions → use a professionally built retained-airbag + controls wheel if changing shape/thickness → avoid unsafe quick-release/non-airbag conversion on a street car → lower-profile console/phone solutions → route cables away from knees/pedals → seat swap only with SRS/occupancy/buckle/legal addressed. **Steering emblem:** part of the airbag cover environment — no rigid/sharp/heavy badge over the deployment surface; only a thin correctly-sized overlay; never disassemble the airbag module for appearance. **Recaro/seat retrofit:** compare connectors + module config; preserve side airbags + occupancy classification; preserve belt pretensioner + buckle sensing; scan SRS before + after; never resistor-mask an active restraint fault.

## Interior modernization dependency matrix
| Upgrade | Required first | Validate after |
|---|---|---|
| Head unit + RR2 | Module backup, exact compatibility, harness plan | Retained functions, sleep draw, full scan |
| Wireless charger | Power budget + tray dimensions | Heat, charge rate, radio noise, shutdown |
| Ambient lighting | Airbag/panel/wiring route plan | Dimmer, no glare, no module wake |
| DSP/amplifier | Signal-source architecture + load plan | Noise floor, clipping, crossover/polarity |
| Spare-well sub | Volume, water, cargo + spare plan | Enclosure leaks, heat, rattles, floor load |
| Seat retrofit | SRS/occupancy/buckle compatibility | SRS scan + restraint function |
| Steering wheel | Airbag/control compatibility | SRS, controls, clockspring, alignment |
| FORScan change | Original backup + exact module match | Full functional test + scan |

## Final acceptance
Complete only when: no SRS/BCM/APIM/ACM/network fault introduced; all factory safety functions operational; added circuits fused/documented/serviceable; the car sleeps normally; no visible loose wiring/sharp attachment; every removed panel fits without new rattle; every modification diagnosable without dismantling unrelated systems.

## Related
[[cockpit-electronics]] · [[exterior-lighting]] · [[forscan-master-reference]] · [[05 Diagnostics & DTC]] · [[_KB-Home|KB Home]]
