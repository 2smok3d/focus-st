# Toyota Pickup (22R-E) Manual

> Working manual for a **1986 Toyota Pickup**, single cab, RWD, W56 5-speed, **22R-E**
> 2.4L EFI four. Engine data is **web-verified**; ⚠️ items need confirming against the
> Toyota factory manual for this chassis (1984–88 and 2WD/4WD parts differ). This truck
> is a **ground-up build** — the cab is bare and the engine needs replacing — so this
> manual is both engine service reference and build guide.

## Identification
- **Chassis:** 1986 Toyota Pickup (N50/N60 gen), single cab, **RWD**, W56 5-speed manual.
- **Engine:** **22R-E** — 2.4L SOHC EFI inline-four. The **E** = electronic fuel injection
  (vs the carbureted 22R). Legendarily durable.
- **Diagnostics:** **OBD-I** — flash codes at the check connector, **not** OBD-II.

## 22R-E specification (verified)
| System | Spec | Confidence |
|---|---|---|
| Type | 2.4L (2,366 cc) SOHC 8-valve EFI inline-4 · cast-iron block, alloy head | verified |
| Bore × stroke | **92.0 × 89.0 mm** | verified |
| Compression | **9.0:1** | verified |
| Power | **105–113 hp @ 4,800 rpm** | verified |
| Torque | **136–140 lb-ft @ 2,800–3,600 rpm** | verified |
| Firing order | **1-3-4-2** | corroborated |
| Transmission | **W56** 5-speed manual · RWD | corroborated |
| Front susp. | IFS (1986 2WD) — verify vs 4WD solid axle | ⚠️ verify |
| Brakes | Front disc · rear drum · DOT 3 | corroborated |

## Fluids & capacities (verified)
- **Engine oil:** **~4.2 L (4.4 qt)** with filter · ~3.8 L without · **5W-30 or 10W-30**.
- **Coolant / transmission / diff:** capacities ⚠️ verify in the manual for this chassis.

## Tune-up data (verified)
- **Valve clearance (adjustable):** **Intake 0.20 mm (0.008 in) · Exhaust 0.30 mm (0.012 in)**.
  This engine has adjustable valves — check + set on a schedule (a ticking top-end is often
  just valves out of spec).
- **Spark plugs:** **NGK BPR5EY** or **Denso W16EXR-U**, gap **0.80 mm (0.031 in)**.
- **Ignition:** EFI with a **mechanical distributor** — base timing is set at the distributor
  (procedure/spec ⚠️ verify; typically with the diagnostic terminals jumpered per the manual).

## ⚠️ Timing chain — the 22R-E's known weak point
Post-'83/'85 22R engines use a **single-row timing chain with plastic guides**. The guides
**wear or break around 80,000–120,000 miles**, causing chain rattle; if ignored the chain can
**saw into the timing cover / water jacket** and dump coolant. On any 22R-E of unknown history:
- Listen for **cold-start chain rattle**.
- Budget a **timing chain + metal-reinforced guides + tensioner** as preventive maintenance.
- **Head gasket** failure is the other common item — check for coolant/oil cross-contamination.

## OBD-I flash-code diagnosis
The 22R-E is **OBD-I** — no OBD-II port scan. Read faults as **flash codes**:
1. Ignition **ON**, engine off (or per the manual).
2. Jumper the diagnostic **check-connector** terminals (commonly **TE1 → E1**).
3. Count the **Check-Engine-Light** blinks: a steady even flash = "system normal"; grouped
   blinks form a two-digit code (e.g. RPM signal, O2 sensor, etc.).
4. Look the code up in the **Toyota factory manual** for this engine.
Otherwise it's classic mechanical diagnosis: **compression, fuel pressure, spark, base timing**.

## Common problems (verified pattern)
- **Timing chain guide wear/failure** (80–120k) — the big one; do it preventively.
- **Head gasket failure** — check for coolant loss / oil emulsion.
- Aged EFI supply (rusty tank, tired pump/filter) on a truck that's sat.

## Build order (this truck)
Because the cab is bare and the engine is out, sequence the build:
1. **Engine decision + install** — fresh 22R-E (simplest, keeps EFI + W56), or a swap
   (3RZ 2.7 / 5VZ 3.4 V6) with the fab/wiring that implies. Decide **first** — it drives the
   harness, mounts, cooling, and cluster.
2. **Wiring** — cab + engine harness matched to the engine (the backbone).
3. **Interior from bare** — dash + cluster, steering column + wheel (ignition + stalks),
   pedal box, HVAC.
4. **Seats + belts + trim.**
5. **Brakes / fuel / cooling refresh** — master + lines + pads/shoes; clean tank + pump +
   filter for EFI; radiator + hoses sized to the engine.
6. **Suspension, steering, rolling stock** — ball joints, bushings, shocks; tires/wheels
   (verify bolt pattern); alignment.
7. **First start, dial-in, title/registration** — prime, set base timing/idle, read flash
   codes, road-test, then paperwork.

## Related
- Cockpit: the Pickup 22RE bay (build phases, engine-swap decision, spec).
- Parts: the build BOM at `?v=toyota-pickup` (engine, full interior, brakes, cooling, suspension).
