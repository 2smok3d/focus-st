# 🧹 FOST Drive — Cleanup & Filing Map

> **Why this is a checklist, not done-for-you:** my Google Drive connector can only **create and copy** — it **cannot move, rename, or delete**. Reorganizing existing files requires drag-and-drop / delete, which only you can do. This map makes that ~10-minute job precise.

## What happened (the mess, explained)
FOST currently has **three competing organizations**:
1. **`FFST Knowledge Base/`** — my clean set (16 reference docs) + `FOST — Receipts Log`, `FOST — Master Tracker`, `FOST — START HERE`. ✅ populated, canonical.
2. **Root numbered folders** `00 – Command Center` … `11 – Project Development`, `99 – Archive` — a second scheme (likely an earlier ChatGPT pass).
3. **`DIGITAL GARAGE — OPENAI BUILD/`** — a ChatGPT run that **duplicated itself**: it contains two each of the `08 –`, `09 –`, `10 –`, `11 –`, `12 –`, `13 –`, `98 –`, `99 –` subfolders (created in repeated bursts). Mostly an empty skeleton.

Plus **loose files at the FOST root** (workshop manuals, FORScan installers, OBD logs, the Mishimoto radiator receipt, photos, duplicates).

## Recommended end state (pick ONE scheme)
Keep the **root numbered folders** (00–11, 99) as the canonical filing cabinet — they're sensibly named and already at root — and nest the knowledge + trackers inside them. Then delete the duplicated `DIGITAL GARAGE` tree.

```
FOST/
├── 00 – Command Center      → START HERE index, dashboards
├── 01 – Vehicle & Ownership → title, insurance, loan, purchase order
├── 02 – Diagnostics         → OBD logs, DTC/scan exports
├── 03 – Maintenance & Service
├── 04 – Mods & Build        → FFST Knowledge Base (nest here), LED/console-tray
├── 05 – Parts & Research
├── 06 – Costs & Receipts    → Receipts Log, Master Tracker, receipt PDFs
├── 08 – Manuals & Reference → workshop manuals, OBDLink QSG
├── 09 – Media & CAD         → photos, SVG zips, console-tray CAD
├── 10 – Software & Tools    → FORScan/OBDwiz installers, .py, ChatGPT setup
├── 11 – Project Development
└── 99 – Archive             → legacy FFST sheets, dropbox link, superseded
```

## Step 1 — delete duplicates (verify empty first)
- [ ] Open **`DIGITAL GARAGE — OPENAI BUILD/`**. If its numbered subfolders are empty skeletons (they appear to be), **delete the whole folder**. If any contain real files, drag those out first.
- [ ] Delete the **duplicate loose files** at root (one copy each — keep the newest):
  - `FFST-ChatGPT-Project-Setup.md` (2 copies) · `focus_st_*` zips (2 sets) · `Ford-Focus-Mk3-2012-2018-WSM.zip` (2) · `Helm Ford Focus … Shop Manual.rar` (2)

## Step 2 — file the loose root files
| Loose file(s) | → Folder |
|---------------|----------|
| `FOST — START HERE (Index)` | 00 – Command Center |
| `FOST — Receipts Log`, `FOST_Master_Tracker.xlsx`, `20260803_MMRAD-FOST-13.pdf` (Mishimoto radiator receipt) | 06 – Costs & Receipts |
| `ConfirmationStatement2026.pdf`, `Signature_Request_for_application_1330079.pdf` | 01 – Vehicle & Ownership |
| `DTC_…txt`, `Info_…txt`, `Log_…txt` (OBD exports) | 02 – Diagnostics |
| `Ford-Focus-Mk3-2012-2018-WSM.zip`, `Helm … Shop Manual.rar`, `obdlink_mxp_qsg-web…pdf` | 08 – Manuals & Reference |
| `focus_st_*` (svg/photo zips), `…contact_sheet…jpg`, `Ford Focus ST center console tray - 4566871.zip` | 09 – Media & CAD |
| `FORScanLiteNG….apk`, `FORScanSetup….exe`, `OBDwizSetup….exe`, `forscan_organizer.py`, `FFST-ChatGPT-Project-Setup.md` | 10 – Software & Tools |
| `focus-st1-led-conversion.md/.pdf` | 05 – Parts & Research |
| `FFST Knowledge Base/` (whole folder) | 04 – Mods & Build (or leave at root — it's self-contained) |
| `FFST - *` legacy sheets, `https://www.dro.txt` | 99 – Archive |

## Step 3 — collapse the old `2017-Ford-Focus-ST/` and `ODB/` folders
Their contents (insurance/PO/LED/FORScan ref/photos, and OBDLink settings) overlap the scheme above — drag their files into 01 / 08 / 09 / 10 as appropriate, then delete the empty shells.

---
**If you'd rather I do it by copying** (I'd duplicate files into the target folders and you delete the originals), say so and I'll batch it — but drag-and-drop is cleaner and avoids duplicate IDs. This map is also in Drive as **`FOST — CLEANUP PLAN`**.
