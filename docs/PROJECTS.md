# Project Index & Build Map — Focus ST

> Every planned project, grouped into **streamlined bundles** (jobs that share teardown, tools, or a service session so you do them once, not five times).
> Each project links to its own full build doc under [`projects/`](projects/).
> Status: 🟢 done · 🟡 in progress · 🔵 planned/decided · ⚪ researching · 🔴 blocked

---

## How this is organized

Individual mods are cheap to *plan* and expensive to *repeat* — every job that opens the same panel, drains the same fluid, or needs the same laptop should happen in one sitting. Projects below are therefore bundled by **shared access**, then sequenced by dependency (e.g. wheels before Brembos, alignment after suspension).

Each build doc follows the same standard: **Overview → Parts list (linked, costed) → Tools → Time & difficulty → Wiring / system diagram → Step-by-step → Verification → Notes/risks.**

---

## Streamlined bundles (recommended routes)

### 🅰 Cockpit Electronics & Trim — *one dash/console teardown*
[`projects/cockpit-electronics.md`](projects/cockpit-electronics.md)
Center console tray (3D print) · **INBAY Qi wireless charger** (slot below stereo) · interior LED swap · shift knob · (optional) head-unit/CarPlay upgrade · SYNC S23 text sync. All share center-stack / console access — pull the trim once.

### 🅱 Exterior Lighting — *one evening, minimal teardown*
[`projects/exterior-lighting.md`](projects/exterior-lighting.md)
Rear 3157 LED · front 7440 LED · fog H11 · reverse/trunk LED · headlight halogen upgrade (Osram). Pair with a **FORScan** session (Bambi mode, shift-light, DRL) since you're already in the lighting/electrical mindset.

### 🅲 Cooling & Oil-Leak Service — *one coolant drain, AZ-heat priority*
[`projects/cooling-oil-service.md`](projects/cooling-oil-service.md)
**Radiator (Mishimoto)** · coolant flush · valve-cover gasket + oil-leak fix · oil change (drain anyway) · cap floating vacuum line · thermostat inspect. This is the **first priority** — radiator has a hole.

### 🅳 FORScan / Digital Session — *laptop + OBDLink, no hand tools*
[`projects/forscan-session.md`](projects/forscan-session.md)
Extended License · full `.abt` module backups · starter-pack tweaks · **program 2nd IA key (PATS)** · **MyKey reset** (clear the 3 auction MyKeys) · TPMS config. Pure software.

### 🅴 Handling & Brakes — *big spend, corner access, alignment after*
[`projects/handling-brakes.md`](projects/handling-brakes.md)
Wheels/tires → **RS→ST Brembo swap (M-2300-W)** → sway bars + endlinks → springs/coilovers → Quaife diff. Strict sequence: wheels first (Brembo clearance), alignment last.

### 🅵 Key Fob & Security — *bench + FORScan*
[`projects/key-fob-security.md`](projects/key-fob-security.md)
Key-fob PCB transplant to slim shell (Thingiverse 2638706) · 2nd key programming (overlaps 🅳).

### 🅶 Powertrain / Performance — *tune-gated path*
[`projects/powertrain.md`](projects/powertrain.md)
Cobb AccessPort → charge pipes / BOV → downpipe → catback → clutch (when it slips). Sequenced so the tune lands after supporting hardware.

---

## Master cost & time roll-up

| Bundle | Core spend (budget→nice) | Shop time | Priority |
|--------|--------------------------|-----------|----------|
| 🅲 Cooling & Oil Service | $350 → $600 | 4–6 h | **1 — do first** (radiator hole) |
| 🅳 FORScan session | $0 → $12/yr | 2–3 h | 2 — free wins + keys/security |
| 🅱 Exterior Lighting | $120 → $260 | 2–4 h | 3 |
| 🅐 Cockpit Electronics & Trim | $150 → $600 | 3–5 h | 4 |
| 🅕 Key Fob & Security | $30 → $70 | 1–2 h | 5 (pairs w/ 🅳) |
| 🅔 Handling & Brakes | $900 → $4,000+ | 8–14 h | later — biggest spend |
| 🅖 Powertrain | $650 → $3,000+ | phased | ongoing |

> Numbers are hardware only; see each doc for line items and the master Sheet in FOST for live cost tracking against real receipts.

---

## Full project inventory (flat list)

| # | Project | Bundle | Status | Doc |
|---|---------|--------|--------|-----|
| 1 | Radiator replacement (Mishimoto) | 🅲 | 🔵 decided | cooling-oil-service |
| 2 | Coolant flush | 🅲 | 🔵 | cooling-oil-service |
| 3 | Valve-cover gasket / oil-leak fix | 🅲 | ⚪ diagnosing | cooling-oil-service |
| 4 | Oil change | 🅲 | 🔵 | cooling-oil-service |
| 5 | Cap floating vacuum line / EVAP | 🅲 | ⚪ | cooling-oil-service |
| 6 | Rear 3157 LED | 🅱 | 🔵 researched | exterior-lighting |
| 7 | Front 7440 LED | 🅱 | 🔵 | exterior-lighting |
| 8 | Fog H11 LED | 🅱 | 🔵 | exterior-lighting |
| 9 | Reverse/trunk LED | 🅱 | 🔵 | exterior-lighting |
| 10 | Headlight halogen upgrade (Osram) | 🅱 | 🔵 | exterior-lighting |
| 11 | Interior LED swap | 🅐 | 🔵 | cockpit-electronics |
| 12 | INBAY Qi wireless charger | 🅐 | ⚪ researched | cockpit-electronics |
| 13 | Center console tray (3D print) | 🅐 | ⚪ | cockpit-electronics |
| 14 | Shift knob | 🅐 | ⚪ | cockpit-electronics |
| 15 | Head unit / CarPlay upgrade | 🅐 | ⚪ optional | cockpit-electronics |
| 16 | SYNC ↔ Galaxy S23 text sync | 🅐 | 🟡 in progress | cockpit-electronics |
| 17 | FORScan starter-pack tweaks | 🅳 | 🔵 | forscan-session |
| 18 | Program 2nd IA key (PATS) | 🅳/🅕 | 🔵 | forscan-session |
| 19 | MyKey reset (clear auction keys) | 🅳 | 🔵 | forscan-session |
| 20 | Key-fob PCB → slim shell | 🅕 | ⚪ fit unconfirmed | key-fob-security |
| 21 | Wheels / tires | 🅔 | ⚪ | handling-brakes |
| 22 | RS→ST Brembo swap (M-2300-W) | 🅔 | ⚪ | handling-brakes |
| 23 | Sway bars + endlinks | 🅔 | ⚪ | handling-brakes |
| 24 | Springs / coilovers | 🅔 | ⚪ | handling-brakes |
| 25 | Quaife/Wavetrac ATB diff | 🅔 | ⚪ | handling-brakes |
| 26 | Cobb AccessPort tune | 🅖 | ⚪ | powertrain |
| 27 | Charge pipes / BOV | 🅖 | ⚪ | powertrain |
| 28 | Downpipe | 🅖 | ⚪ | powertrain |
| 29 | Catback exhaust | 🅖 | ⚪ | powertrain |
| 30 | Clutch upgrade | 🅖 | ⚪ future | powertrain |

*Status here mirrors the Projects tab of the master Sheet in FOST. Update both when a project moves.*
