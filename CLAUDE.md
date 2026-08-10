# Focus ST Parts — Project Context

## What this is
A single-file PWA + GitHub-backed parts/mods tracker for a 2017 Ford Focus ST
(2.0L EcoBoost, MT82 6-speed, MK3). No build step, no framework, no dependencies —
everything is hand-written vanilla HTML/CSS/JS.

The app reads and writes `PARTS.md` (and `MODS.md`) directly on GitHub via the
Contents API, using a fine-grained Personal Access Token stored in the browser's
`localStorage`. There is no backend — the GitHub repo *is* the database.

- **Live:** https://2smok3d.github.io/focus-st/add.html
- **Repo:** https://github.com/2smok3d/focus-st

## Files
| File | Purpose |
|------|---------|
| `add.html` | The entire app — markup, CSS, and JS in one file. Edit this directly. |
| `PARTS.md` | Source of truth. Hand-authored catalog + app-appended wishlist. |
| `MODS.md` | **Auto-generated** by the app on each install. Do not hand-edit. |
| `manifest.json` | PWA manifest — Web Share Target, icons, standalone display. |
| `sw.js` | Service worker — caches app shell, bypasses the GitHub API. |
| `serve.ps1` | Local dev server (PowerShell `HttpListener`, no Node needed). |
| `icon.svg` | Home-screen / tab icon (inline SVG, red "ST" on black). |
| `README.md` | User-facing docs. |

## The three tabs (in `add.html`)
1. **Add** — a form (name, category strip, subcategory strip, URL, optional notes).
   Submitting appends a line under a `## Wishlist` section in `PARTS.md`.
   ⚠️ **The category/subcategory pills are cosmetic today**: `injectLine()` ignores
   them (`_cat`, `_sub` params) and always appends to `## Wishlist`, creating that
   section if it's missing. The selected category is only saved to `localStorage`
   and shown in the "Recent" list. The `CATS` taxonomy here
   (Performance / Exterior / Interior / Maintenance) is **separate** from the
   catalog section names in `PARTS.md` — don't conflate them.
2. **Garage** — browses the `PARTS.md` catalog. Parses each `<details><summary><b>SECTION</b>`
   into slots (`#### Slot`), shows the installed part + condition emoji. Tapping a
   slot opens the upgrade sheet (the slot's nested table). Selecting a row and
   confirming rewrites that slot's `**Installed:**` line and marks it `<!-- MOD -->`.
3. **Mods** — filtered view of slots carrying the `<!-- MOD -->` marker (i.e. parts
   that diverge from stock). Each install regenerates `MODS.md` from this data.

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
Parser rules to preserve when editing:
- Sections are detected by `<summary><b>...</b></summary>`.
- Slots are `#### ` headings; the base name is everything before ` *(`.
- `**Installed:**` line: a `[name](url)` link is extracted if present; condition is
  the first emoji found among `✅` / `🔧` / else defaults to `⚠️`.
- `<!-- MOD -->` on the `**Installed:**` line = "changed from stock" (shows in Mods).
- The upgrade table's first column is the tier; a row whose tier is exactly
  `OEM` is treated as the stock reference in the Mods view. Header rows
  (`Tier` / `Tool` / `Item`) are skipped.

**Wishlist** (app-appended): a `## Wishlist` section of `- [ ] [name](url) — notes`
lines. Created lazily on first Add if absent.

## GitHub sync internals
- Auth: `token` header with a PAT needing **Contents: read & write** on `2smok3d/focus-st`.
  Owner/repo are hardcoded (`OWNER`/`REPO` constants in `add.html`).
- Reads/writes go through `ghGet` / `ghPut` (Contents API, base64 content).
- **SHA cache:** `localStorage` holds `{sha, content, ts}` with a 5-minute TTL.
  Writes reuse the cached SHA to skip the GET. On a `409` conflict, the cache is
  cleared, the file re-fetched, and the write retried once.
- **Install flow** (`doInstallPart`): update PARTS.md slot → PUT → then regenerate
  and PUT `MODS.md`. A MODS.md failure is logged but non-fatal.

### localStorage keys
`fst_tok` (PAT) · `fst_cache` (SHA+content) · `fst_hist` (last 8 adds) ·
`fst_cat` (last category) · `fst_sub` (per-category subcategory map).

## Web Share Target
`manifest.json` registers a GET share target → `add.html?url=…&text=…&title=…`.
On Android, sharing a product link opens the app pre-filled; `cleanTitle()` strips
retailer boilerplate (Amazon, eBay, etc.) from the shared title.

## Service worker (`sw.js`)
Cache `fst-v1`, precaches the shell (`add.html`, `manifest.json`, `icon.svg`),
serves network-first with cache fallback, and **explicitly skips `api.github.com`**
so data calls always hit the network. Bump the cache name when shipping shell changes.

## Conventions
- Everything lives in `add.html` — one file, no build, no npm. Match the existing
  terse vanilla style (compact arrow-function helpers, no framework idioms).
- Design: dark theme (`#0d0d0d`), red accent (`#e8000d`), mobile-first, respects
  iOS/Android safe-area insets. Keep it self-contained (no external assets/CDNs).
- HTML injected via template strings is escaped with `esc()` — keep using it for
  any user/remote content.

## Dev server
```powershell
pwsh -File serve.ps1     # → http://localhost:3000 (serves add.html at /)
```
No build. Edit `add.html` and refresh. (Note: Web Share Target and installability
need HTTPS, so those only fully work on the deployed GitHub Pages site.)

## Deployment
GitHub Pages, `master` branch root. Push to deploy — there is no CI/build.
When changing cached shell files, bump `CACHE` in `sw.js` so clients update.
