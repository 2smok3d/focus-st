---
title: 08 Electronics, Infotainment & Interior
aliases: ["08 Electronics & Interior", Electronics, Interior]
tags: [focus-st, kb, electronics, interior]
---

# 08 · Electronics, Infotainment & Interior

> Reversible, serviceable 2030 cabin without network faults. Full version → [Google Doc](https://docs.google.com/document/d/1yD_tvzCRSEhMDMYUTIB9jesPTTHVZ5c6v3wePrqOr50). Build → [[cockpit-electronics]].

Start: 4" SYNC 1, factory steering controls + gauge pod, OBDLink MX+. Planned: head unit + **iDatalink Maestro RR2**, wireless Android Auto, blue ambient, wireless charging, spare-well sub.

## Electrical rules
Record DTCs/as-built before disconnecting · regulated supply for programming · never probe SRS w/ test light · fuse every added circuit at source · size wire for current/length/heat · one engineered ground · label both ends · document every fuse/splice.

## RR2 integration
Retains steering controls/chimes/vehicle info + OBD gauges (radio/firmware dependent). **Build from iDatalink's Focus RR2 compatibility list for the exact radio.** Bench-program RR2 first; verify sleep-draw + full module scan after.

## Wireless charger / ambient / audio
Qi at phone's coil location, switched fused 12V, ventilation (AZ heat), wired USB-C backup. Blue = accent only, dimmable, no bare LEDs, no SRS interference. Audio: diagnose→treat→front speakers→DSP/amp→spare-well sub (heat/water/cargo/roadside plan).

## Ergonomics (user ~6ft/215lb)
Optimize seat/wheel first; retained-airbag wheel only if clearance stays poor; never resistor-mask a restraint fault.

## Related
[[cockpit-electronics]] · [[exterior-lighting]] · [[forscan-master-reference]] · [[_KB-Home|KB Home]]
