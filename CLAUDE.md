# Focus ST — Project Context

This repo is **two things sharing one Git history**:

1. **The parts-tracker PWA** — a single-file, no-build web app (`add.html`) that reads
   and writes `PARTS.md` / `MODS.md` directly on GitHub. The repo *is* the database.
2. **The FOST documentation system** (`docs/`) — a version-controlled knowledge base
   for a specific 2017 Ford Focus ST (specs, project builds, maintenance log,
   FORScan reference, automation), mirrored to a Google Drive library called **FOST**.

The car: 2017 Ford Focus ST (5-door, 2.0 L EcoBoost, 6-speed manual, MK3.5 facelift),
VIN `1FADP3L94HL223134`, owned by Brandon Berault (Phoenix, AZ).

- **Live app:** https://2smok3d.github.io/focus-st/add.html
- **Repo:** https://github.com/2smok3d/focus-st

---

## Top-level layout
| Path | Subsystem | Purpose |
|------|-----------|---------|
| `add.html` | PWA | The entire app — markup, CSS, and JS in one file. Edit directly. |
| `PARTS.md` | PWA | Source of truth for the catalog + app-appended wishlist. |
| `MODS.md` | PWA | **Auto-generated** by the app on each install. Do not hand-edit. |
| `manifest.json` | PWA | PWA manifest — Web Share Target, icons, standalone display. |
| `sw.js` | PWA | Service worker — caches app shell, bypasses the GitHub API. |
| `serve.ps1` | PWA | Local dev server (PowerShell `HttpListener`, no Node needed). |
| `icon.svg` | PWA | Home-screen / tab icon (inline SVG, red "ST" on black). |
| `README.md` | PWA | User-facing docs. ⚠️ Stale — still describes an old "My List" tab. |
| `docs/` | Docs | The FOST documentation system (see its own section below). |

---

# Part 1 — The PWA (`add.html`)

Single-file PWA + GitHub-backed parts/mods tracker. No build step, no framework, no
dependencies — hand-written vanilla HTML/CSS/JS. There is no backend; the app talks to
the GitHub Contents API using a fine-grained Personal Access Token in `localStorage`.

## The three tabs
1. **Add** — a form (name, category strip, subcategory strip, URL, optional notes).
   Submitting appends a line under a `## Wishlist` section in `PARTS.md`.
   ⚠️ **The category/subcategory pills are cosmetic today**: `injectLine()` ignores
   them (`_cat`, `_sub` params) and always appends to `## Wishlist`, creating that
   section if it's missing. The selected category is only saved to `localStorage`
   and shown in the "Recent" list. The `CATS` taxonomy here
   (Performance / Exterior / Interior / Maintenance) is **separate** from the catalog
   section names in `PARTS.md` — don't conflate them.
2. **Garage** — browses the `PARTS.md` catalog. Parses each `<details><summary><b>SECTION</b>`
   into slots (`#### Slot`), shows the installed part + condition emoji. Tapping a slot
   opens the upgrade sheet (the slot's nested table). Selecting a row and confirming
   rewrites that slot's `**Installed:**` line and marks it `<!-- MOD -->`.
3. **Mods** — filtered view of slots carrying the `<!-- MOD -->` marker (parts that
   diverge from stock). Each install regenerates `MODS.md` from this data.

## PARTS.md format (matters — the parser depends on it)
Two coexisting structures:

**Catalog** (hand-authored, drives Garage + Mods):
```markdown
<details>
<summary><b>SECTION NAME</b></summary>
<br>

#### Slot Name *(optional spec note in italics)*
**Installed:** [Part Name](url) — OEM · PART-NUM · ⚠️ unknown

<details>
<summary>Upgrade</summary>

| Tier | Part | # | ~Price | Notes |
|------|------|---|--------|-------|
| OEM | [Stock part](url) | PART-NUM | ~$15 | ... |
| Performance | [Upgrade](url) | — | ~$55 | ... |

</details>

---
</details>
```
Parser rules (`parseCatalog`) to preserve when editing:
- Sections are detected by `<summary><b>...</b></summary>`.
- Slots are `#### ` headings; the base name is everything before ` *(`.
- `**Installed:**` line: a `[name](url)` link is extracted if present; condition is
  the first emoji found among `✅` / `🔧` / else defaults to `⚠️`.
- `<!-- MOD -->` on the `**Installed:**` line = "changed from stock" (shows in Mods).
- The upgrade table's first column is the tier; a row whose tier is exactly `OEM` is
  treated as the stock reference in the Mods view. Header rows (`Tier` / `Tool` /
  `Item`) are skipped.

Currently there are 13 catalog sections (ENGINE, FORCED INDUCTION, EXHAUST, COOLING,
DRIVETRAIN, SUSPENSION, BRAKES, WHEELS & TIRES, ELECTRICAL, LIGHTING, INTERIOR,
MAINTENANCE, TOOLS & DIAGNOSTICS) and no `## Wishlist` section yet — it's created
lazily on the first Add.

**Wishlist** (app-appended): a `## Wishlist` section of `- [ ] [name](url) — notes`
lines. Created lazily on first Add if absent.

## GitHub sync internals
- Auth: `token` header with a PAT needing **Contents: read & write** on `2smok3d/focus-st`.
  Owner/repo are hardcoded (`OWNER`/`REPO` constants in `add.html`).
- Reads/writes go through `ghGet` / `ghPut` (Contents API, base64 content).
- **SHA cache:** `localStorage` holds `{sha, content, ts}` with a 5-minute TTL. Writes
  reuse the cached SHA to skip the GET. On a `409` conflict, the cache is cleared, the
  file re-fetched, and the write retried once.
- **Install flow** (`doInstallPart`): update the PARTS.md slot → PUT → then regenerate
  and PUT `MODS.md`. A MODS.md failure is logged but non-fatal.

### localStorage keys
`fst_tok` (PAT) · `fst_cache` (SHA+content) · `fst_hist` (last 8 adds) ·
`fst_cat` (last category) · `fst_sub` (per-category subcategory map).

## Web Share Target
`manifest.json` registers a GET share target → `add.html?url=…&text=…&title=…`.
On Android, sharing a product link opens the app pre-filled; `cleanTitle()` strips
retailer boilerplate (Amazon, eBay, etc.) from the shared title.

## Service worker (`sw.js`)
Cache `fst-v1`, precaches the shell (`add.html`, `manifest.json`, `icon.svg`), serves
network-first with cache fallback, and **explicitly skips `api.github.com`** so data
calls always hit the network. Bump the cache name when shipping shell changes.

## PWA conventions
- Everything lives in `add.html` — one file, no build, no npm. Match the existing terse
  vanilla style (compact arrow-function helpers, no framework idioms).
- Design: dark theme (`#0d0d0d`), red accent (`#e8000d`), mobile-first, respects
  iOS/Android safe-area insets. Keep it self-contained (no external assets/CDNs).
- HTML injected via template strings is escaped with `esc()` — keep using it for any
  user/remote content.

## Dev server
```powershell
pwsh -File serve.ps1     # → http://localhost:3000 (serves add.html at /)
```
No build. Edit `add.html` and refresh. (Web Share Target and installability need HTTPS,
so those only fully work on the deployed GitHub Pages site.)

## Deployment
GitHub Pages, `master` branch root. Push to deploy — there is no CI/build. When changing
cached shell files, bump `CACHE` in `sw.js` so clients update.

---

# Part 2 — The FOST documentation system (`docs/`)

A deep, human-authored knowledge base for this specific car. Markdown + mermaid
diagrams, diffable here, **mirrored to a Google Drive library called FOST** (which also
holds the master tracking Sheet, receipts, manuals, and OBD/FORScan backups). The PWA
stays the quick add/track catalog; `docs/` is the reference layer.

## Structure
| Path | Purpose |
|------|---------|
| `docs/README.md` | Index of the whole system. |
| `docs/VEHICLE.md` | **Master vehicle spec — the source of truth for car facts.** VIN, trim (ST1), all specs, installed mods, known issues, FORScan module map. |
| `docs/PROJECTS.md` | Project index / build map. 30 projects grouped into 7 "streamlined bundles" (🅐–🅖) by shared teardown, with a cost/time roll-up. |
| `docs/MAINTENANCE.md` | Chronological service log (newest at top) + service intervals. |
| `docs/SETUP.md` | System architecture: repo ↔ FOST (Drive) mirror, connector status, the Gmail→receipts pipeline, and the user's action checklist. |
| `docs/projects/*.md` | 7 full build docs, one per bundle (cooling-oil-service, exterior-lighting, cockpit-electronics, forscan-session, handling-brakes, key-fob-security, powertrain). |
| `docs/reference/forscan-master-reference.md` | FORScan cheat-sheet (module addresses, starter-pack tweaks, risks). |
| `docs/automation/gmail-receipts.gs` | Google Apps Script — auto-logs Gmail receipts to the master Sheet. |

## Project-doc standard
Every `docs/projects/*.md` follows the same shape — preserve it when adding/editing:
`Overview → Parts list (linked + costed) → Tools → Time & difficulty → Wiring/system
diagram (mermaid) → Step-by-step → Verification → Notes/risks.` Diagrams are mermaid
(render on GitHub and in the PWA). Keep parts links live and costs synced to the master
Sheet.

## Authoring rules — important for AI edits
- **`VEHICLE.md` is canonical for car facts.** When a fact about the car changes, update
  `VEHICLE.md` first; everything else references it.
- **`VEHICLE.md` deliberately overrides `PARTS.md` in several places** where the older
  catalog was wrong. Treat these as correct and do not "fix" them back:
  - Transmission is **MMT6** (Getrag-Ford), *not* "MT82" — different fluid
    (WSS-M2C200-D2 / Motorcraft XT-11-QDC). Verify variant at the car before buying.
  - Output is **~252 hp / 270 lb-ft** canonical (PARTS.md's 247 hp is stale).
  - Fog bulb is **H11** on this ST1 (PARTS.md lists H16 — verify at car).
  - On any spec conflict, Ford/NHTSA "Grade-A" values from the FFST vault win.
- **PII lives outside the repo.** Insurance/purchase/loan records (SSNs, DOBs) are kept
  private in FOST, *not* committed here. Don't add PII to the repo.

## The wider system (context, not in this repo)
- **FOST (Google Drive)** is the canonical library the docs mirror into: the master
  tracking Sheet, `_Archive/receipts/YYYY/`, manuals, and FORScan `.abt` backups.
- **Gmail → receipts pipeline:** order/receipt emails are logged to the Sheet's Receipts
  tab and PDFs filed in FOST. The reliable path is the bound Apps Script
  (`docs/automation/gmail-receipts.gs`), which scans Gmail hourly and labels processed
  threads (`FOST-Logged`) so it never double-logs. IFTTT can't do this (no Gmail
  "new email" trigger).
- These connectors (Drive, Gmail, Calendar, GitHub) live in the user's Claude
  environment, not in the code. `SETUP.md` tracks their status and open blockers.

---

## Working in this repo
- **Docs-only change?** Touch `docs/` — no build, no app impact.
- **App change?** Edit `add.html` (and bump `sw.js` `CACHE` if the shell changed).
- **Car fact change?** Update `docs/VEHICLE.md` first, then any project/maintenance doc
  and the PWA catalog if relevant.
- Deployment is a plain `git push` to `master`; there is no CI.
