# AI Workspace — Knowledge Vault

Personal knowledge workspace (Obsidian-style vault), formerly part of the
`ai-workspace` (aiw) agent monorepo. The aiw agent code was retired in favor of
**pi** (pi coding agent) + official pi extensions. This repo is now markdown
content + pi configuration only.

## Vault layout

| Path | Contents |
|------|----------|
| `Knowledge/` | Curated knowledge: research, business, legal analysis (single root — see below) |
| `Knowledge/streaming-debrid/` | Streaming/Debrid legal & business research project (10 files + index) |
| `Research/` | Spikes, POCs, benchmarks (incl. `agent-research/`) |
| `Projects/` | Active projects: DVISION-ERPNext-Brasil, dshell, nix-home |
| `Technical-Decisions/` | ADRs + migration records (e.g. `GAP_ANALYSIS_AIW_VS_PI.md`) |
| `analysis/` | Analysis documents (incl. Leilão Radar domain decomposition) |
| `Career/` | CVs, LinkedIn profile, career-agent prompts (salvaged from aiw) |
| `memory/` | Conventions, learning log, project patterns |
| `notes/` | Working notes (auction operation solo plans, OmniRoute setup) |
| `references/` | Cheat-sheets: git aliases, pi commands, graph tools |
| `reports/` | Community research (Stremio gaps) |
| `Development/` | Feature tracking & implementation plans |
| `Prompts/`, `Templates/` | Prompt & doc templates (incl. `knowledge-note.md`) |
| `pi-setup/` | pi configuration layer — symlinked into `~/.pi` |
| `.trash/` | Archived aiw docs / dead content (rollback: git tag `pre-aiw-removal`) |

## Knowledge note convention

Every file in `Knowledge/` uses YAML front-matter:

```yaml
---
title: Note title
date: YYYY-MM-DD
status: draft | active | superseded
tags: [tag1, tag2]
source: https://example.com   # optional
superseded_by: path/to/new.md # required when status: superseded
---
```

Start new notes from `Templates/knowledge-note.md`. When content is superseded,
flip `status` and set `superseded_by` instead of deleting.

## Searching this vault

This vault is indexed as the **`aiw-vault`** pi-knowledge KB. In pi:

- `knowledge_search` — semantic/hybrid search across the vault
- `knowledge_symbol_search` — exact symbol/heading/config-key lookup
- `knowledge_update` — re-index after content changes

## What replaced aiw

| aiw feature | Replacement |
|-------------|-------------|
| `aiw kb` (pgvector RAG) | pi-knowledge (`knowledge_*` tools) |
| `aiw memory` (L1/L2/L3) | pi-memory extension (markdown in `~/.pi/agent/memory/`) |
| `aiw search` (deep research) | `deep-research` skill + `web_search` |
| `aiw task` (queue/schedules) | pi `todo` + schedules + `daily` skill |
| `aiw agent` (tools) | pi built-ins (fs/git/shell/web) |
| aiw MCP server / extension | pi native extension tooling |

**Leilão Radar** (auction scanner + Telegram bot) was extracted to its own
repo: `~/Projects/leilao-radar` (14 tests passing; markdown export hook for
pi-knowledge indexing).