# Focus ST Parts

Personal parts tracker, mod wishlist, and maintenance log for a Ford Focus ST (2013–2018 MK3 EcoBoost).

**Live app → [2smok3d.github.io/focus-st](https://2smok3d.github.io/focus-st/add.html)**

---

## What it does

- **Add tab** — add parts by name, category, subcategory, URL, and notes. One tap to submit.
- **My List tab** — browse everything in PARTS.md, filtered by status (Want / Ordered / Installed). Tap a status dot to cycle it — commits back to GitHub instantly.
- **Android share sheet** — share any product link from Chrome/Amazon/eBay directly to the app. It pre-fills the URL and cleans the page title. One tap to save.
- **Offline badge** — shows when you have no connection, blocks submit.

All data lives in [`PARTS.md`](PARTS.md) on this repo. The app reads and writes it directly via the GitHub Contents API using a PAT stored locally on your device.

---

## Android setup

1. Open [the app](https://2smok3d.github.io/focus-st/add.html) in Chrome
2. Tap **⋮ → Add to Home screen** — installs as a standalone PWA
3. Open the app, tap **⚙** and enter:
   - GitHub username: `2smok3d`
   - Repository: `focus-st`
   - [Personal access token](https://github.com/settings/personal-access-tokens/new) with **Contents: read & write**
4. Tap **Test connection** to confirm, then **Save**

After that: share any product link from anywhere → Focus ST appears in the share sheet → fills in automatically → one tap to add.

---

## Status

| Dot | Meaning |
|-----|---------|
| ○ dim | Want — on the wishlist |
| ● amber | Ordered — purchased, waiting on delivery |
| ● green | Installed — on the car |

Tap any dot in **My List** to cycle through. Each tap commits to `PARTS.md` on GitHub.

---

## Categories

| Category | Subcategories |
|----------|--------------|
| **Performance** | Engine / Intake · Exhaust · Suspension · Brakes · Cooling · Drivetrain · Tune / ECU |
| **Exterior** | Wheels & Tires · Body / Aero · Lighting · Wraps & Paint |
| **Interior** | Seats / Harness · Gauges & Displays · Audio · Pedals & Steering · Other Interior |
| **Maintenance & Consumables** | Fluids & Filters · Wear Items · Tools |

---

## Files

| File | Purpose |
|------|---------|
| [`add.html`](add.html) | The PWA — Add tab, My List tab, config screen, share flow |
| [`PARTS.md`](PARTS.md) | The parts list — source of truth, edited by the app |
| [`manifest.json`](manifest.json) | PWA manifest — share target, icons, display mode |
| [`icon.svg`](icon.svg) | Home screen icon |
| [`serve.ps1`](serve.ps1) | Local dev server (PowerShell, no Node needed) |
| [`CLAUDE.md`](CLAUDE.md) | Context for Claude Code sessions on this repo |

---

## Local dev

```powershell
pwsh -File serve.ps1
# → http://localhost:3000
```

No build step. Edit `add.html` directly.

---

## PARTS.md format

```markdown
## Category

### Subcategory
- [ ] [Part name](https://url) — notes
- [~] Part name without URL — ordered, no link
- [x] [Installed part](https://url) — install date, cost
```

Completed installs go in the `## Done` section at the bottom with a date/cost note.
