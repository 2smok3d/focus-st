# Focus ST Service Manual

> Working manual for the **2017 Ford Focus ST** (MK3.5, ST1) — 2.0L EcoBoost, MT82
> 6-speed. Condensed from the fact-checked knowledge base; the **full 16-section vault**
> lives in `docs/knowledge-base/` and the cockpit's embedded live manual. Torque values
> are safety-critical — confirm against the Ford workshop manual before final assembly.

## Identification
- **VIN:** 1FADP3L94HL223134 · Phoenix, AZ · ex-auction.
- **Trim:** ST1, MK3.5 facelift, "Central Config" (CC) electrical platform.
- **Engine:** 2.0L EcoBoost I4 turbo (GTDI), code **R9DA**-family.

## Specification (verified)
| System | Spec | Confidence |
|---|---|---|
| Engine | 2.0L EcoBoost I4 turbo GTDI · 87.5 × 83.1 mm · 9.3:1 | oem-verified |
| Firing order | **1-3-4-2** | oem-verified |
| Output | **252 hp @ 5,500** · **270 lb-ft @ 2,500** | oem-verified |
| Transmission | **MT82** (Getrag) 6-speed manual · 240 mm clutch + DMF | oem-verified |
| Final drive | 3.82:1 | corroborated |
| Wheels | 18 × 8 · 5×108 · **ET55** · 235/40R18 | oem-verified |
| Front brakes | 320 × 25 mm vented | oem-verified |
| Rear brakes | 302 × 10 mm solid | oem-verified |
| Battery | Group 96R · 590 CCA (upgraded) | vehicle-verified |

## Fluids & capacities (verified)
- **Engine oil:** **5W-30** (Motorcraft synthetic blend, WSS-M2C946-B1) · **~4.3 qt** with
  filter · filter **FL-910S**. (KB notes 5.7 qt on some references — confirm on the dipstick.)
- **Coolant:** Motorcraft Orange (WSS-M97B44-D / "VC-3-B") · ~5.3 qt · ~78°C thermostat.
- **Transmission (MT82):** **WSS-M2C200-D2** / Motorcraft XT-11-QDC · ~1.8 qt. Ford lists
  fill-for-life; community changes it — shorten under hard use.
- **Brake/clutch:** shared reservoir · **DOT 4 LV** (WSS-M6C65-A2). Any level loss →
  inspect **both** brake and clutch hydraulics.

## Tune-up data
- **Spark plugs:** Motorcraft **SP-537** · gap **0.028–0.031 in** (tighten toward
  0.025–0.026 if tuned). Coils **DG-565**.
- **Wheel torque:** **100 lb-ft**. Spark plug ~13 lb-ft (confirm).

## Maintenance schedule
| Item | Interval | Note |
|---|---|---|
| Engine oil & filter | 5,000 mi / 6 mo | Severe/turbo + AZ heat → shorter end |
| Tire rotation | 5,000 mi | Pair with oil |
| Cabin air filter | 20,000 mi / 12 mo | AZ dust → sooner |
| Engine air filter | 30,000 mi | |
| MT82 fluid | ~60,000 mi | Community-preferred; shorten under hard use |
| Spark plugs | ~60,000 mi | ~30–45k if tuned |
| Brake fluid | 24 mo | Critical with track/spirited use |
| Coolant | 100k / 6 yr then shorter | |

## Diagnosis (OBD-II)
Full DTC coverage in the garage's **[Code Lookup](../../tools/dtc.html?v=focus-st)** — the
EcoBoost-specific ones (P0299 underboost, P0234 overboost, P04DB crankcase vent, P1450/P144A
EVAP purge, P2196, P0087/P0191 fuel pressure) carry a diagnostic path. Save freeze-frame +
scan **all** modules, not just the PCM; verify battery/charging first (low voltage fakes faults).

## Open campaigns / known issues (verify by VIN)
- **EVAP purge-valve campaign 18S32 / 26S40** — stuck-open valve → P1450 / rough idle after
  refuel. Confirm completion against the VIN before chasing EVAP codes.
- **P04DB crankcase ventilation** — treat as a case: smoke/pressure-test, confirm the
  calibration expects the installed PCV; a permanent DTC lingers post-repair until monitors run.
- **Intercooler heat-soak** — stock IC heat-soaks under AZ load; prioritized R1 upgrade.
- **Radiator** — cracked/through-holed core on this car (decided fix: Mishimoto).

## Build notes
Full project system (30 projects → 7 bundles), stage plan (R0→BT2), and the deep
diagnostic/powertrain/chassis/electronics manuals live in the **knowledge base**
(`docs/knowledge-base/`) and the cockpit's embedded searchable manual.

## Related
- Cockpit: the Focus ST bay (live dossier, engine bay, projects, recalls, full manual).
- Backend: the `digital-garage` truth store exports this car's live feed + MODS.
