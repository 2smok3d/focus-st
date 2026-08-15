#!/usr/bin/env python3
"""Concatenate the whole FOST vault into one sectioned master with a TOC."""
import re, os

DOCS = "/home/user/focus-st/docs"
OUT = os.path.join(DOCS, "FOST-COMPLETE.md")

# ordered (path, section title)
ORDER = [
    ("VEHICLE.md", "Vehicle Master Spec"),
    ("knowledge-base/00 Vault Overview.md", "KB · Vault Overview"),
    ("knowledge-base/00 Command Center.md", "KB · Command Center"),
    ("knowledge-base/01 Vehicle Record & Baseline.md", "KB · Vehicle Record & Baseline"),
    ("knowledge-base/02 Maintenance Master.md", "KB · Maintenance Master"),
    ("knowledge-base/03 OEM Specifications.md", "KB · OEM Specifications"),
    ("knowledge-base/03 Spec Correction.md", "KB · Spec Correction"),
    ("knowledge-base/04 Recalls & TSBs.md", "KB · Recalls & TSBs"),
    ("knowledge-base/05 Diagnostics & DTC.md", "KB · Diagnostics & DTC"),
    ("knowledge-base/06 Powertrain.md", "KB · Powertrain Manual"),
    ("knowledge-base/07 Chassis.md", "KB · Chassis Manual"),
    ("knowledge-base/08 Electronics & Interior.md", "KB · Electronics & Interior"),
    ("knowledge-base/09 Mods & Tuning.md", "KB · Mods & Tuning"),
    ("knowledge-base/10 Forum Consensus.md", "KB · Forum Consensus"),
    ("knowledge-base/11 Build Roadmap.md", "KB · Build Roadmap"),
    ("knowledge-base/11 Project Database.md", "KB · Project Database"),
    ("knowledge-base/12 Sources.md", "KB · Sources & Changelog"),
    ("MAINTENANCE.md", "Maintenance & Service Log"),
    ("PROJECTS.md", "Projects Index & Build Map"),
    ("projects/cooling-oil-service.md", "Build · Cooling & Oil-Leak Service"),
    ("projects/exterior-lighting.md", "Build · Exterior Lighting"),
    ("projects/cockpit-electronics.md", "Build · Cockpit Electronics + RR2"),
    ("projects/forscan-session.md", "Build · FORScan Session"),
    ("projects/handling-brakes.md", "Build · Handling & Brakes"),
    ("projects/key-fob-security.md", "Build · Key Fob & Security"),
    ("projects/powertrain.md", "Build · Powertrain / Performance"),
    ("reference/forscan-master-reference.md", "Reference · FORScan Master Reference"),
    ("SETUP.md", "Setup · Connections & Data Flow"),
    ("FOST-CLEANUP-MAP.md", "Appendix · FOST Drive Cleanup Map"),
    ("HOW-TO-OBSIDIAN.md", "Appendix · Obsidian Vault Setup"),
]

def strip_frontmatter(t):
    if t.startswith("---"):
        m = re.match(r"^---\n.*?\n---\n", t, re.DOTALL)
        if m:
            return t[m.end():]
    return t

def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def demote(t):
    # demote every heading one level so the file's own H1s sit under the section H1
    return re.sub(r"^(#{1,5}) ", r"#\1 ", t, flags=re.MULTILINE)

toc, body = [], []
n = 0
for rel, title in ORDER:
    p = os.path.join(DOCS, rel)
    if not os.path.exists(p):
        continue
    n += 1
    num = f"{n:02d}"
    anchor = slug(f"{num}-{title}")
    toc.append(f"{n}. [{title}](#{anchor})")
    with open(p, encoding="utf-8") as f:
        content = strip_frontmatter(f.read()).strip()
    body.append(f"\n\n---\n\n<a id=\"{anchor}\"></a>\n\n# {num} · {title}\n\n{demote(content)}")

header = (
    "---\n"
    "title: FOST — Complete Compendium\n"
    "aliases: [FOST-COMPLETE, Compendium, Everything]\n"
    "tags: [focus-st, compendium, moc]\n"
    "---\n\n"
    "# 📕 FOST — Complete Compendium\n\n"
    "> **100% of the vault in one place.** Auto-generated from every note by "
    "`scratchpad/build_compendium.py` — do not hand-edit; edit the source notes and rebuild.\n"
    "> 2017 Ford Focus ST · VIN 1FADP3L94HL223134 · Phoenix, AZ. Home: [[INDEX]].\n\n"
    "## Table of contents\n" + "\n".join(toc) + "\n"
)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(header + "".join(body) + "\n")

print(f"wrote {OUT}: {n} sections, {os.path.getsize(OUT)//1024} KB")
