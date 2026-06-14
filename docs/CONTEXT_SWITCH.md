# Context Switch — Progress Report

**Date:** 2026-06-13
**Agent:** pi (deepseek-v4-pro via DeepSeek/OpenAI)
**Status:** Research & dependency audit phase

---

## What was requested

> "Faça pesquisas na web por termos relacionados aos nossos projetos"

User asked for web searches on terms related to the AI Workspace project.

## What was done

### 1. Project discovery
Read the full project structure and documentation:
- `README.md` — full architecture overview
- `pyproject.toml` — dependencies and scripts
- `docs/INTEGRATION.md` — NixOS integration guide
- All source files in `src/ai_workspace/`

### 2. Web search attempt (FAILED)
Tried 8 parallel web searches via pi's built-in web_search tool on these topics:
- crewAI multi-agent orchestration 2025
- pgvector PostgreSQL vector search performance
- Huey task queue vs Celery
- Langtrace Python LLM telemetry
- Deep research recursive search pipeline
- Nix flakes reproducible Python dev
- Ollama deepseek-r1 vs qwen3 local LLM comparison
- DAG workflow engine Python async retry

**Failed reason:** The pi model (deepseek-v4-pro via deepseek/openai-completions) does not support native web search. pi does not auto-fallback to another model for cost reasons.

### 3. Fallback: PyPI version checks (SUCCESS)
Checked latest versions of all key dependencies via PyPI API:

| Package | Latest Version | Summary |
|---------|---------------|---------|
| **crewai** | 1.14.7 | Multi-agent orchestration framework |
| **pgvector** | 0.4.2 | PostgreSQL vector support for Python |
| **huey** | 3.0.3 | Lightweight task queue |
| **langtrace-python-sdk** | 3.8.21 | LLM telemetry tracing SDK |
| **textual** | 8.2.7 | Modern TUI framework |
| **streamlit** | 1.58.0 | Data app dashboard framework |

### 4. DuckDuckGo API attempt (minimal results)
Tried DuckDuckGo Instant Answer API — returned empty results.

---

## Current project state

### Source tree (19 Python files)

```
src/ai_workspace/
├── __init__.py
├── cli.py                    # Typer CLI (aiw command)
├── agents/
│   ├── __init__.py
│   └── swarm.py              # crewAI agent definitions
├── search/
│   ├── __init__.py
│   └── deep_search.py        # Recursive search pipeline
├── knowledge/
│   ├── __init__.py
│   ├── store.py              # PostgreSQL + pgvector KB
│   └── sync.py               # Obsidian vault sync
├── tasks/
│   ├── __init__.py
│   └── scheduler.py          # Huey task scheduler
├── workflow/
│   ├── __init__.py
│   ├── engine.py             # Custom DAG workflow engine
│   └── workflows.py          # Workflow definitions (deep_research, etc.)
├── providers/
│   ├── __init__.py           # LLM providers (Ollama, DeepSeek, Kimi)
├── tui/
│   ├── __init__.py
│   └── app.py                # Textual TUI app
├── dashboard/
│   ├── __init__.py
│   └── app.py                # Streamlit dashboard
```

### Other files
- `tests/` — empty directory (NO TESTS YET)
- `scripts/` — exists but not explored
- `data/` — exists but not explored
- `flake.nix` / `flake.lock` — Nix flake for reproducible builds
- `shell.nix` — Nix shell for development

### Key observations
1. **No tests written** — tests/ directory is empty
2. **pyproject.toml** pins `crewai>=0.80.0,<1.0` but current PyPI version is **1.14.7** — version constraint needs updating
3. **Python 3.13** detected in __pycache__ (cpython-313), but pyproject says `>=3.12`
4. All core modules have code (not stubs) — project is actively developed
5. Nix integration module is designed for dvision-thinkbook NixOS config

---

## Next steps (for next agent)

### ✅ DONE by previous agent
1. **Researched improvements across all 8 core topics:** crewAI, pgvector, Huey, Langtrace, Textual, Streamlit, Nix flakes, Python testing — via scraping upstream documentation (google.com search not supported by model)
2. **Fixed crewAI version constraint:** `pyproject.toml` updated `crewai[tools]>=0.80.0,<1.0` → `>=1.0`, added `crewai-tools>=0.16.0`
3. **Updated pgvector constraint:** `>=0.3.0` → `>=0.3.5`
4. **Added test dependencies:** pytest-cov, pytest-mock, pytest-timeout, pytest-textual-snapshot, faker
5. **Created comprehensive `docs/IMPROVEMENT_PLAN.md`** (25KB) covering 13 sections with prioritized action items, code examples, and execution timeline

### Immediate actions (remaining)
1. **Explore scripts/ and data/ directories** — understand data pipeline
2. **Read key source files** to understand implementation depth:
   - `cli.py` — what commands are actually implemented vs. documented
   - `swarm.py` — agent definitions and crew setup
   - `engine.py` — DAG workflow implementation
   - `store.py` — PostgreSQL schema and vector operations

### Development options
- Write tests for existing code
- Implement missing CLI commands from README
- Build the web search tool integration (for deep_search)
- Set up CI/CD pipeline
- Create the NixOS module referenced in docs/INTEGRATION.md

### User's original intent
User wanted web research on project-related terms. With the model limitation:
- Option A: Switch pi to a model that supports web search (qwen3.7-max, qwen3.7-plus, minimax)
- Option B: Use `curl` + external search APIs (Google Custom Search, Brave Search API, etc.)
- Option C: Scrape specific documentation pages (crewAI docs, pgvector docs, etc.)

---

## Environment

- **OS:** NixOS (unstable)
- **Python:** 3.13
- **PostgreSQL:** 17
- **Shell:** fish (likely)
- **Project path:** `/home/daviaaze/Projects/ai-workspace`
- **Virtual env:** `.venv/` present
