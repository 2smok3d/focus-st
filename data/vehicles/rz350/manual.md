# RZ350 Service Manual

> Working mechanic's manual for the **1984–1985 US Yamaha RZ350** (Kenny Roberts
> edition). Two-stroke, YPVS powervalve, Autolube oil injection. Core specs are
> **web-verified**; ⚠️ items need confirming against the **Yamaha service manual** for
> this bike. US models were **catalyzed and detuned** — de-cat + rejet changes fueling
> throughout, so treat jetting as bike-specific.

## Identification
- **Model:** RZ350, sold in the US **1983–1985** (**1985 = last US year**). The Kenny
  Roberts edition wears the yellow/black GP "speed-block" livery.
- **Lineage:** the final evolution of Yamaha's **RD** two-stroke line, and the **only**
  RD/RZ to get **YPVS** (Yamaha Power Valve System). Closely related to the European
  **RD350 YPVS / RD350LC F2**.
- **Emissions:** US bikes ran **catalytic converters** in the exhaust and leaner jetting to
  pass US rules — the origin of the "de-cat and rejet to wake it up" culture.

## Specification (verified)
| System | Spec | Confidence |
|---|---|---|
| Engine | 347 cc liquid-cooled 2-stroke parallel twin · reed valve · YPVS | verified |
| Bore × stroke | **64 × 54 mm** | verified |
| Power | ~**59 hp @ 9,000** (uncatted/RR) · **~46 hp** US catted | verified |
| Torque | ~40 Nm (~30 lb-ft) @ 8,000 rpm | verified |
| Carburetion | **2× Mikuni VM26** (26 mm slide-valve) | verified |
| Lubrication | **Autolube** oil injection (tank under seat) · gearbox separate | verified |
| Ignition | CDI · NGK **B8ES / BR8ES** | verified |
| Transmission | 6-speed · wet clutch · chain | verified |
| Front brake | Single disc | corroborated |
| Rear brake | Disc (some earlier drum — verify this bike) | ⚠️ verify |
| Tires | **90/90-18 front · 110/80-18 rear** (18") | verified |
| Fuel capacity | **5.2 US gal (~19.7 L)** | verified |
| Weight | ~371 lb (half tank) | verified |
| Frame | Steel · Monocross single-shock rear | corroborated |

## Fluids & tune-up (verified where noted)
- **2-stroke oil:** Autolube injection — keep the under-seat tank full with a quality
  injector 2-stroke oil (Yamalube 2 or equiv.). **Never run it dry.**
- **Premix conversion (optional):** if you block off the pump, a common street ratio is
  **~32:1** (4 oz per US gallon) — but then you must mix **every** fill or it seizes.
- **Gearbox oil:** separate from the fuel/injection oil — capacity/grade ⚠️ verify in the
  manual (typical ~10W-30/10W-40 GL; small volume).
- **Coolant:** liquid-cooled — capacity ⚠️ verify; ethylene-glycol, aluminium-safe.
- **Spark plugs:** **NGK B8ES / BR8ES**, gap **0.022–0.025 in (~0.6 mm)**. Two-strokes foul —
  keep graded spares and **read plug color** to judge jetting.
- **Brake fluid:** DOT 4.

## Torque & timing
> Confirm all torque + ignition-timing figures in the Yamaha manual for this model — these
> are safety/tune-critical and vary. Do not guess head-nut or flywheel torque.

## YPVS (Yamaha Power Valve System)
A servo-driven valve in the exhaust port raises/lowers the port timing with rpm, broadening
the powerband. It **carbons up** and the **servo/cables stick** with age:
1. Remove the valves and **decarbon** the bores + valves.
2. Verify the **servo drives the valves fully open and closed** (full sweep) and set cable
   free-play per the manual.
3. A stuck/half-open valve = a flat spot or lost top-end.

## Fueling & jetting (2× Mikuni VM26)
- After any sit, carbs **varnish** → flooding and hard starts. Clean/rebuild both:
  jets, o-rings, float valves; set **float height** to spec ⚠️.
- Jetting is sensitive and **must be re-set** whenever intake/exhaust changes (de-cat,
  chambers, air filter). **Read the plugs** — the safe default on any two-stroke is
  **jet rich and read the plug**; a lean RZ is a seized RZ.
- Balance the carbs after cleaning.

## Crank seals (2-stroke seize risk)
Old crankcase seals harden and draw air → a **lean** condition under load → **seizure**.
**Pressure/vacuum-test the crankcase** before trusting the engine, especially after a long
sit. This is the single most important check on a 40-year-old two-stroke.

## Maintenance schedule
| Item | Interval | Notes |
|---|---|---|
| Autolube oil level | every ride | Never run dry |
| Spark plugs | frequent · carry spares | B8ES; plug color = jetting gauge |
| Gearbox oil | ~2,000–3,000 mi | Separate from injection oil |
| YPVS decarbon + servo sweep | periodic | Clean valves, verify full travel |
| Crank seals | inspect / as needed | Pressure-test; a lean leak seizes it |
| Coolant | 2–3 yr | Inspect hoses + pump seal |
| Brake fluid | 2 yr | DOT 4 |
| Chain clean + lube | 300–500 mi | Adjust slack; inspect sprockets |
| Exhaust studs / mounts | inspect | Vibration cracks pipes + breaks studs |

## Common faults & fixes (verified pattern)
- **Cracked exhaust / broken exhaust studs** — the RZ's **vibration** is hard on pipes and
  mounting studs; inspect and re-secure, use quality studs.
- **Hard start after sitting / flooding** — varnished carbs; clean + rebuild, check float level.
- **Hesitation, fouling, lean/rich spots** — jetting sensitivity; rejet to the actual
  intake/exhaust and read plugs.
- **Flat spot / weak top-end** — carboned or stuck **YPVS**; decarbon + servo sweep.
- **Sudden seizure risk** — worn **crank seals** (air leak → lean); pressure-test.
- **Mid-range flat spots** — a known cylinder/carburation trait; dial jetting + YPVS together.

## Recommission from a long sit
1. **Crankcase pressure test** (crank seals) — do this before running it.
2. **Fill + verify the Autolube** tank and pump/cable; never dry-start.
3. Drain old fuel, **clean/rebuild both carbs**, set jetting for the actual config.
4. **Decarbon + sync the YPVS**; verify full servo sweep.
5. Fresh **B8ES** plugs, gearbox oil, coolant flush.
6. Brakes DOT 4; inspect exhaust studs/mounts; tires (date code); chain.
7. Start, warm, **plug-chop** to confirm jetting; road-test.

## Diagnosis (2-stroke — no OBD)
No ECU, no codes. Analog only:
- **Crankcase pressure test** (air leaks → lean seize — first).
- **Cylinder compression** (even, to spec).
- **Spark-plug color reads** for jetting.
- **Ignition/CDI** + coil checks.
- **YPVS** operation.
Default: **jet rich, read the plug.**

## Related
- Cockpit: the RZ350 bay (recommission checklist, systems, quick spec).
- Parts: tracker at `?v=rz350` (powervalve, crank seals, reeds, carbs/jetting, chambers).
