---
title: README — FOST vault
aliases: [README]
tags: [focus-st, meta]
---

# FOST — Focus ST Documentation System

Everything about the car: specs, projects, maintenance, records. Version-controlled here, mirrored to **FOST** in Google Drive.

## Start here
- **[INDEX.md](INDEX.md)** — 📇 master index of **everything** (repo + Drive vault + sheets), with a site map and cross-reference matrix.
- **[VEHICLE.md](VEHICLE.md)** — master spec (VIN, trim, all specs, mods, known issues). *Source of truth.*
- **[PROJECTS.md](PROJECTS.md)** — every project, grouped into streamlined build bundles, with cost/time roll-up.
- **[MAINTENANCE.md](MAINTENANCE.md)** — chronological service log.
- **[SETUP.md](SETUP.md)** — connections/tools setup guide + what you need to authorize.

## Projects (full builds)
| Bundle | Doc |
|--------|-----|
| 🅲 Cooling & Oil-Leak Service *(priority 1)* | [projects/cooling-oil-service.md](projects/cooling-oil-service.md) |
| 🅱 Exterior Lighting | [projects/exterior-lighting.md](projects/exterior-lighting.md) |
| 🅐 Cockpit Electronics & Trim | [projects/cockpit-electronics.md](projects/cockpit-electronics.md) |
| 🅳 FORScan / Digital Session | [projects/forscan-session.md](projects/forscan-session.md) |
| 🅔 Handling & Brakes | [projects/handling-brakes.md](projects/handling-brakes.md) |
| 🅕 Key Fob & Security | [projects/key-fob-security.md](projects/key-fob-security.md) |
| 🅖 Powertrain / Performance | [projects/powertrain.md](projects/powertrain.md) |

## Reference
- [reference/forscan-master-reference.md](reference/forscan-master-reference.md) — FORScan cheat-sheet.

## Doc standard (every project doc)
`Overview → Parts list (linked + costed) → Tools → Time & difficulty → Wiring/system diagram (mermaid) → Step-by-step → Verification → Notes/risks.`
Diagrams are mermaid (render on GitHub + in the PWA). Keep parts links live; keep costs synced to the master Sheet.

## Relationship to the app
This repo also hosts the parts-tracker PWA (`add.html` + `PARTS.md`). The `docs/` system is the deep knowledge layer; `PARTS.md` stays the quick add/track catalog. See the root [README](../README.md).
