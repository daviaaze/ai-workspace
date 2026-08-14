# AI Workspace — Knowledge Vault

Personal knowledge workspace (Obsidian-style vault) previously part of the
`ai-workspace` (aiw) agent monorepo. The aiw agent code has been retired
and replaced by **pi** (pi coding agent, `~/.pi`) + official pi extensions.

## What this vault is

Markdown-first knowledge content, indexed into pi-knowledge for agent retrieval:

| Area | Contents |
|------|----------|
| `Knowledge-Base/`, `knowledge/`, `knowledge-base/` | Curated knowledge: research, business, legal analysis |
| `Research/` | Spikes, POCs, benchmarks |
| `Projects/` | Project context: architecture, links, decisions |
| `Technical-Decisions/` | ADRs |
| `analysis/` | Analysis documents (incl. Leilão Radar domain decomposition) |
| `memory/` | Conventions, learning log, project patterns |
| `Development/` | Feature tracking |
| `Prompts/`, `Templates/` | Prompt & doc templates |
| `career-ops/` | Standalone Python utility (job applications) |
| `pi-setup/` | pi configuration layer (extensions, skills, nix) — symlinked into `~/.pi` |
| `Media-Inbox/` | Raw media backlog |
| `.trash/` | Archived aiw docs (rollback: git tag `pre-aiw-removal`) |

## Searching this vault

This vault is indexed as a pi-knowledge KB. In pi:

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