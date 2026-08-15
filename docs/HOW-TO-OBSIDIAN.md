---
title: How to use this as an Obsidian vault
aliases: [Obsidian, Vault setup, How to]
tags: [meta, obsidian, setup]
---

# 📓 Open this as an Obsidian vault

The `docs/` folder **is** the vault — every note is plain markdown with wikilinks, tags, and mermaid diagrams that Obsidian renders natively. Start at [[INDEX|🏠 Home]].

## Fastest way (auto-syncing, recommended)
Keep the vault in sync with GitHub automatically so edits on phone/laptop merge and nothing is lost.

1. Install **[Obsidian](https://obsidian.md)** (free, desktop + mobile).
2. Clone the repo and open its `docs/` folder as a vault:
   ```bash
   git clone https://github.com/2smok3d/focus-st.git
   # In Obsidian: "Open folder as vault" → choose focus-st/docs
   ```
3. Enable **Community plugins → Obsidian Git**. Settings:
   - *Vault backup interval*: 10 min · *Pull on startup*: on · *Commit-and-sync*: on.
   That's the automation: edits auto-commit + push, and pull on open. Your notes and the repo stay one thing.

> On mobile: Obsidian Git works on Android; on iOS use the **Working Copy** app to sync the repo, then open `docs` as a vault.

## Recommended community plugins
| Plugin | Why |
|--------|-----|
| **Obsidian Git** | auto pull/commit/push (the automation) |
| **Dataview** | turn tags/frontmatter into live tables (e.g. all `#project` notes, all open issues) |
| **Templater** | quick new service-log / receipt / project entries |
| **Kanban** | drag project bundles across Todo → Doing → Done |

## How it's wired
- **Home / MOC:** [[INDEX]] — set it as the Obsidian home note.
- **Wikilinks** connect every note; open **Graph view** (Ctrl/Cmd-G) to see the whole system.
- **Tags:** `#focus-st #project #kb #reference #automation #maintenance #spec #recall` — click to filter.
- **Frontmatter** on each note (title/aliases/tags) powers search + Dataview.
- **Mermaid** wiring/system diagrams render inline.

## Example Dataview snippets (paste into any note)
````markdown
```dataview
TABLE status, bundle FROM #project SORT priority ASC
```
```dataview
LIST FROM #recall
```
````

## Keeping the Google Drive side
The Drive **FFST Knowledge Base** (Google Docs) mirrors the KB for reading on any device; the vault here is the **editable source of truth**. Live sheets (Receipts Log, Master Tracker) stay in Drive — linked from [[INDEX]]. See [[SETUP]] for the full data-flow.
