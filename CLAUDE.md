# Focus ST Parts — Project Context

## What this is
PWA + GitHub-backed parts wishlist for a Ford Focus ST.
- `add.html` — the PWA (served via GitHub Pages, also runs locally via `serve.ps1`)
- `PARTS.md` — the actual parts list, updated by the app via GitHub Contents API
- `manifest.json` — PWA manifest with Web Share Target (Android share sheet integration)

## How it works
The app writes directly to `PARTS.md` on GitHub using a PAT stored in localStorage.
SHA caching means repeat adds skip the GET request. 409 conflicts auto-retry.
Parts inject under `## Category > ### Subcategory` sections in PARTS.md.

## Category structure
Performance: Engine / Intake · Exhaust · Suspension · Brakes · Cooling · Drivetrain · Tune / ECU
Exterior: Wheels & Tires · Body / Aero · Lighting · Wraps & Paint
Interior: Seats / Harness · Gauges & Displays · Audio · Pedals & Steering · Other Interior
Maintenance & Consumables: Fluids & Filters · Wear Items · Tools

## Dev server
`pwsh -File serve.ps1` — serves on http://localhost:3000 (PowerShell HttpListener, no Node needed)

## Deployment
GitHub Pages — master branch root. Push to deploy.
Repo: https://github.com/2smok3d/focus-st
