# FOST Garage — Project Context

## What this is
A **digital-garage platform** — one hub, many machines — built around a 2017 Ford
Focus ST (2.0L EcoBoost, MT82 6-speed, MK3) as the first fully-populated vehicle.
Everything shares one design language and one data logic; **the GitHub repo is the
database.** It's a monorepo with **self-contained per-vehicle modules** so adding a
machine is "copy the module."

0. **The Garage** (`web/index.html`) — the platform hub/homepage. Reads
   `data/fleet.json` (vehicle registry), links each vehicle's cockpit + the shared
   tools, front-and-center code lookup, and live status from the fleet.
1. **Shared tools** (`web/tools/`) — multi-vehicle utilities:
   - `dtc.html` — OBD-II / DTC code lookup over `data/dtc-codes.json` (curated +
     range fallback so *any* code resolves at least to a category).
   - `parts.html` — the parts-tracker PWA. Vehicle-aware via `?v=<slug>`; reads/writes
     that vehicle's `PARTS.md`/`MODS.md` on GitHub via the Contents API + a PAT.
2. **Vehicle modules** (`web/vehicles/<slug>/` + `data/vehicles/<slug>/`) — each
   vehicle's cockpit screen + its data. Focus ST: `web/vehicles/focus-st/index.html`
   (the HUD dashboard) hydrates from `web/vehicles/focus-st/garage.json`.
3. **Digital Garage** (`digital-garage/`) — Postgres + FastAPI + MCP truth store that
   exports a vehicle's `garage.json` + `MODS.md`. Its own README documents it.

All pages share one design system: `web/assets/hud.css`.

- **The Garage:** https://2smok3d.github.io/focus-st/web/index.html
- **Focus ST cockpit:** https://2smok3d.github.io/focus-st/web/vehicles/focus-st/index.html
- **Code lookup:** https://2smok3d.github.io/focus-st/web/tools/dtc.html
- **Repo:** https://github.com/2smok3d/focus-st

## Layout
```
index.html                     Root landing → enter the garage
web/                           The platform — GitHub Pages serves the repo tree
  index.html                   THE GARAGE hub (fleet picker + tools + status)
  assets/hud.css               Shared design system (tokens + components)
  manifest.json                PWA manifest — start_url index.html, share target → tools/parts.html
  sw.js                        Service worker — caches shell (fst-v4), bypasses the GitHub API
  icon.svg  serve.ps1          Icon + local dev server
  tools/
    dtc.html                   OBD-II / DTC code lookup (multi-vehicle)
    parts.html                 Parts tracker PWA (vehicle-aware via ?v=)
  vehicles/
    focus-st/
      index.html               Focus ST cockpit (HUD dashboard)
      garage.json              Focus ST live feed — GENERATED, do not hand-edit
data/
  fleet.json                   Vehicle registry (the garage bays)
  dtc-codes.json               DTC reference database
  vehicles/
    focus-st/
      PARTS.md                 Source of truth — hand-authored catalog + wishlist
      MODS.md                  Changes-from-stock — GENERATED
docs/                          Obsidian knowledge base (unchanged workflow)
digital-garage/                Backend (its own README)
assets/banner.svg              README hero
.github/                       CI: pytest + garage.json validation
```

## The parts tracker (`web/tools/parts.html`) — three tabs
1. **Add** — form (name, category strip, subcategory strip, URL, notes). Submitting
   appends a line under `## Wishlist` in the vehicle's `PARTS.md`.
   ⚠️ **The category/subcategory pills are cosmetic**: `injectLine()` always appends to
   `## Wishlist`; the category is only saved to `localStorage` + shown in "Recent".
2. **Garage** — browses the `PARTS.md` catalog. Parses each
   `<details><summary><b>SECTION</b>` into slots (`#### Slot`); tapping a slot opens the
   upgrade sheet; confirming rewrites that slot's `**Installed:**` line, marks `<!-- MOD -->`.
3. **Mods** — filtered view of slots carrying `<!-- MOD -->`. Each install regenerates `MODS.md`.

Which vehicle's files it edits is chosen by `?v=<slug>` (default `focus-st`), resolved
against the `VEHICLES` map at the top of the `<script>`. All vehicles live in the one
repo, so a single PAT covers them.

## PARTS.md format (matters — the parser depends on it)
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
Parser rules to preserve:
- Sections detected by `<summary><b>...</b></summary>`.
- Slots are `#### ` headings; base name is everything before ` *(`.
- `**Installed:**` line: a `[name](url)` link is extracted if present; condition is the
  first emoji among `✅` / `🔧` / else `⚠️`.
- `<!-- MOD -->` on the `**Installed:**` line = "changed from stock" (shows in Mods).
- Upgrade table's first column is the tier; a row whose tier is exactly `OEM` is the
  stock reference. Header rows (`Tier` / `Tool` / `Item`) are skipped.

**Wishlist** (app-appended): a `## Wishlist` section of `- [ ] [name](url) — notes` lines.

## GitHub sync internals (parts PWA)
- Auth: `token` header with a PAT needing **Contents: read & write** on `2smok3d/focus-st`.
  `OWNER`/`REPO` and the per-vehicle `PARTS_PATH` / `MODS_PATH` (e.g.
  `data/vehicles/focus-st/PARTS.md`) come from the `VEHICLES` map + `?v=`.
- Reads/writes go through `ghGet` / `ghPut` (Contents API, base64).
- **SHA cache:** `localStorage` `{sha, content, ts}`, 5-min TTL. On `409` the cache
  clears, refetches, retries once.
- **Install flow** (`doInstallPart`): update PARTS.md slot → PUT → regenerate + PUT
  MODS.md (a MODS.md failure is non-fatal).

### localStorage keys
`fst_tok` · `fst_cache` · `fst_hist` · `fst_cat` · `fst_sub`.

## Web Share Target
`web/manifest.json` registers a GET share target → `tools/parts.html?url=…&text=…&title=…`.
`cleanTitle()` strips retailer boilerplate from the shared title.

## Service worker (`web/sw.js`)
Cache `fst-v4`, precaches the shell (hub, tools, the FOST cockpit, `assets/hud.css`,
manifest, icon), network-first with cache fallback, **explicitly skips `api.github.com`**.
Registered once by the hub (scope `/web/` covers tools + vehicles). Bump `CACHE` on shell changes.

## digital-garage coupling
`python -m app.cli export` (and auto-export after any approval) writes, for the Focus ST:
- `web/vehicles/focus-st/garage.json` — the cockpit's live feed
- `data/vehicles/focus-st/MODS.md` — human-readable changes-from-stock

If you move these paths, update `digital-garage/app/export.py` and
`.github/scripts/validate_garage_json.py` together.

## Adding a vehicle (the module pattern)
1. Add an entry to `data/fleet.json` (slug, name, specs, `accent`, `screen`,
   `feed`/`parts`/`mods` paths).
2. Create `web/vehicles/<slug>/index.html` (copy the FOST cockpit as a starting point)
   and `data/vehicles/<slug>/PARTS.md`.
3. Add the slug to the `VEHICLES` map in `web/tools/parts.html`.
4. It now appears as a garage bay and shares every tool automatically.

## Conventions
- Web files are single-file, no build, no npm; match the terse vanilla style.
- **Design system:** black `#0a0a0b`, ST red `#e8000d`, Chakra Petch / IBM Plex Mono
  (system fallbacks), mobile-first, safe-area aware. Self-contained — no CDNs. Pages
  may share `web/assets/hud.css` (same-origin, not a CDN).
- HTML injected via template strings is escaped with `esc()`.

## Dev server
```powershell
pwsh -File web/serve.ps1     # → http://localhost:3000 (serves web/index.html)
```
No build. (Web Share Target + installability need HTTPS, so those only fully work on
the deployed Pages site.)

## Deployment
GitHub Pages, `master` branch root serves the whole tree — the platform lives at
`/focus-st/web/…`, the landing at `/focus-st/`. Push to deploy; no build. Bump `CACHE`
in `web/sw.js` when changing shell files. The `digital-garage` backend runs locally
(Docker), not on Pages.
