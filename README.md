# AI Workspace - README

## Architecture

```
aiw (CLI)
├── aiw search <query>       Deep recursive research
├── aiw ask <question>       Quick chat with any model
├── aiw models               List available models
├── aiw task list|add|due    Task management
├── aiw memory add|recall    Agent memory
├── aiw kb add|search        Knowledge base
├── aiw obsidian sync        Obsidian vault sync
├── aiw schedule run|status  Recurring flows (Prefect)
└── aiw init                 Initialize database
```

## Quick Start

### 1. Create database
```bash
createdb ai_workspace
```

### 2. Install
```bash
cd Projects/ai-workspace
nix develop    # or: pip install -e .
```

### 3. Initialize
```bash
aiw init
```

### 4. Use!
```bash
aiw models                    # List your 14 Ollama models
aiw search "rust async patterns"  # Deep research
aiw ask "explain this code"   # Quick chat
aiw task add "Review NixOS config" --priority 8 --schedule "0 9 * * *"
```

## Providers

Uses your existing models:

| Provider | Default Model | When |
|----------|--------------|------|
| Ollama | `qwen3:14b` | General tasks |
| Ollama | `deepseek-r1:14b` | Deep reasoning |
| Ollama | `qwen3-coder:30b` | Code generation |
| DeepSeek API | `deepseek-chat` | Cloud fallback |

## Deep Search Pipeline

```
Query → Planner Agent → Sub-questions (tree)
                          ├── Sub-Q1 → Researcher Agent → Answer
                          ├── Sub-Q2 → Researcher Agent → Answer
                          └── Sub-Q3 → Researcher Agent → Answer
                                          ↓
                              Synthesizer Agent → Report
```

## Agent Swarm (crewAI)

| Agent | Role | Model | Use |
|-------|------|-------|-----|
| Researcher | Deep search | `deepseek-r1:14b` | Research queries |
| Coder | Code gen/review | `qwen3-coder:30b` | Development |
| Analyst | Pattern detection | `qwen3:14b` | Data analysis |
| Writer | Content synthesis | `qwen3:14b` | Reports |
| Planner | Task planning | `deepseek-r1:14b` | Daily planning |

## Recurring Tasks (Prefect)

```bash
# One-off test
aiw schedule run morning_briefing

# Deploy to Prefect server
prefect server start
prefect deploy daily_research_flow --cron "0 8 * * *"
```

| Flow | Schedule | What |
|------|----------|------|
| `morning_briefing` | Daily 7:00 BRT | Sync Obsidian, generate briefing |
| `daily_research` | Daily 8:00 BRT | Research configured topics |
| `continuous_learning` | Daily 2:00 BRT | Extract patterns from history |
| `obsidian_sync` | Every 6h | Sync KB ↔ Obsidian |

## Knowledge Base (PostgreSQL + pgvector)

Tables:
- `knowledge_entries` — Your curated knowledge (with vector embeddings)
- `research_entries` — Deep search results
- `tasks` — Task management with cron scheduling
- `agent_memory` — Agent learnings (mem0-like)

## Nix Integration

To add to your nixfiles, import in `flake.nix`:

```nix
inputs.ai-workspace.url = "path:/home/daviaaze/Projects/ai-workspace";
```

Then in `modules/packages/ai-workspace.nix`:

```nix
{ inputs, ... }: {
  environment.systemPackages = [ inputs.ai-workspace.packages.x86_64-linux.ai-workspace ];
}
```
