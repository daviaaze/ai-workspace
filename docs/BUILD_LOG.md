# AI Workspace — Build Log & Project State

**Last updated:** 2026-06-17
**Session:** SmartRouter cross-provider + Gemini + health cmd + doc cleanup

---

## Session 2026-06-17 — SmartRouter v2 + Docs Cleanup

### Test suite: 424 pass, 0 fail, 28 skip

| Metric | Before | After |
|--------|--------|-------|
| Passing tests | 385 | **424** |
| Failed tests | 0 | **0** |
| New test files | 0 | **2** (test_router.py 34 + test_pipeline.py 39) |

### What was delivered

| Area | Changes | Files |
|------|---------|-------|
| **SmartRouter v2** | Cross-provider fallback (Ollama→DeepSeek→Gemini→OpenRouter), availability check, 7 task types, cost estimation | `agents/router.py` (rewrite, 372 linhas) |
| **Gemini integration** | ProviderRegistry: Gemini API key via env/sops-nix, OpenAI-compatible endpoint | `providers/__init__.py` |
| **Embedding fallback** | sentence-transformers auto-fallback when Ollama down, padding 384→768 | `core/cost.py` |
| **aiw health cmd** | Real-time: providers + cache + budget + sources in one view | `cli.py` (+95 linhas) |
| **Tests** | 34 new router tests: routing, fallback, complexity, cost, availability | `tests/test_agents/test_router.py` |
| **E2E tests** | 39 tests: router+budget+cache pipeline, source reputation, agent worker, provider health, full pipeline, error handling | `tests/test_e2e/test_pipeline.py` |

### Docs findings (corrected)
- Source reputation: FULLY implemented (CRED-1+CrediNet+cross-ref), docs said "pending"
- Diff Edit + Auto-Fix: 824 lines of code + 18 tests, docs said "not implemented"
- Crawl4AI + scraping chain: implemented, docs said "new"
- CRED-1 weekly update: Huey task exists, docs said "not scheduled"

---

## Session 2026-06-16 — Complete Summary

### Test suite: 278 pass, 0 fail, 26 skip

| Metric | Before | After |
|--------|--------|-------|
| Passing tests | 117 | **278** |
| Failing tests | 22 | **0** |
| New test files | 0 | **6** |
| Code coverage | ~15% | **29%** |

### What was delivered

| Area | Changes | Files |
|------|---------|-------|
| **P0: Fixes** | 22→188 tests, Ollama timeout, bug fix | 6 files |
| **P2: crewAI 1.14.7** | output_pydantic, planning, guardrail | 4 files |
| **P3: Connection pool** | ThreadedConnectionPool, transparent DI | 2 files |
| **Textual 8.x** | SpawnDialog→Screen, Footer widget | 2 files |
| **@step decorator** | Explicit DAG replaces inspect.getsource | 3 files |
| **HNSW + logging** | pgvector HNSW index, print→logging | 3 files |
| **YAML config** | agents.yaml, tasks.yaml, loader | 4 files |
| **Orchestrator** | AgentOrchestrator → CLI agent command | 2 files |
| **Browser agent** | browser-use packaged in Nix flake | 2 files |
| **Tests** | +161 tests (providers, MCP, pool, orchestrator) | 6 files |

### Architecture now

```
CLI (typer)
├─ aiw ask        → ProviderRegistry.chat() → Ollama /api/chat
├─ aiw agent      → AgentOrchestrator.run()
│   ├─ CLIStreamSink (terminal output)
│   ├─ ContextManager (project context)
│   ├─ SmartRouter (model selection)
│   └─ AgentWorker (crewAI execution)
├─ aiw search     → DeepSearchEngine.research()
│   ├─ PlanOutput (output_pydantic)
│   ├─ ResearchAnswer (output_pydantic)
│   └─ SynthesisReport (output_pydantic)
├─ aiw code       → coding_crew() [YAML-driven]
├─ aiw task       → KnowledgeStore [connection pool]
├─ aiw tui        → Textual 8.x Screen API
└─ aiw worker     → Huey consumer (systemd)

Config (YAML, non-devs can edit):
├─ agents.yaml    → 14 agent definitions
├─ tasks.yaml     → 12 task templates
└─ loader.py      → load_agent() / load_task()

Infra:
├─ PostgreSQL 15  → port 2284 (homelab)
├─ pgvector       → HNSW index (m=16, ef_construction=64)
├─ ConnectionPool → ThreadedConnectionPool (1-5 conns)
└─ Nix flake      → 8 custom Python derivations (browser-use, etc.)

Tests (278 pass):
├─ test_agents/   → swarm (26), deep_search (23), orchestrator (17)
├─ test_core/     → db pool (24), services (14 skipped)
├─ test_knowledge/ → store (30)
├─ test_mcp_server/ → handlers (19)
├─ test_providers/ → registry (29), chat (14)
├─ test_tools/    → filesystem, git, shell (24)
├─ test_workflow/ → engine (34)
├─ test_dashboard/ → app (5)
└─ test_tui/      → app (10 skipped)
```

---

## Session 2026-06-16 — P0 + P1 fixes (earlier today)

### 1. Test suite fixed (188 pass, 0 fail, 26 skip)

**Before:** 22 failures (ImportError, git env, CLI detection) — 117 pass
**After:** 188 pass (+71 new tests), 26 legitimately skipped

| Fix | File |
|-----|------|
| Added `LD_LIBRARY_PATH` for numpy in NixOS venv | run command |
| Git tests: pass `repo=str(git_repo)` explicitly | `tests/test_tools/test_git.py` |
| Dashboard CLI tests: use `c.callback.__name__` + `registered_groups` | `tests/test_dashboard/test_app_dashboard.py` |
| Fixed `test_app.py` name collision (`test_dashboard/` vs `test_tui/`) | renamed to `test_app_dashboard.py` |

### 2. `aiw ask` Ollama timeout fix

**Root cause:** `/v1/chat/completions` (OpenAI-compatible) struggles with thinking models.

**Fix:** All Ollama calls now use native `/api/chat` endpoint. Renamed `_chat_ollama_stream()` → `_chat_ollama()` with non-streaming support.

**File:** `src/ai_workspace/providers/__init__.py`

### 3. Bug fix: `tool_descriptions` undefined in `_answer_sub_question()`

**Root cause:** Variable local to `_create_researcher_agent()`, referenced from different function.

**Fix:** Made `self._tool_descriptions` a lazy-computed instance attribute.

**File:** `src/ai_workspace/search/deep_search.py`

### 4. New tests — agents + deep_search (+49 tests)

| Module | Tests | What |
|--------|-------|------|
| `tests/test_agents/test_swarm.py` | 26 | SwarmConfig, agent factories, crew assembly, tool bundles, create_agent |
| `tests/test_agents/test_deep_search.py` | 23 | Data classes, safe_float, parse_json, Engine init, research pipeline |

### 5. pgvector extension — confirmed installed ✅

---

## What was achieved (previous sessions)

### 1. NixOS deployment on homelab (`dvision-homelab`)

`aiw` is now installed system-wide via Nix on the homelab, served by PostgreSQL 15 on port **2284** (not 5432 — Immich forces this port).

| Component | How |
|-----------|-----|
| Flake input | `inputs.ai-workspace.url = "github:daviaaze/ai-workspace"` |
| Overlay | `ai-workspace = inputs.ai-workspace.packages.${system}.default` |
| Package exposure | `inherit (pkgs) ai-workspace` in `packages.nix` |
| System install | `modules/shared/package-categories.nix` → `development` category |
| DB service | `hosts/dvision-homelab/services/ai-workspace-db.nix` |
| Worker service | `hosts/dvision-homelab/services/ai-workspace-worker.nix` |

### 2. Bugs fixed during deployment

#### `services.postgresql.ensurePermissions` → `ensureClauses`
**Error:** `The option 'services.postgresql.ensureUsers...ensurePermissions' does not exist`
**Fix:** NixOS-unstable removed `ensurePermissions`. Replaced with `ensureClauses.login`, `ensureClauses.superuser`, `ensureDBOwnership`.
**File:** `nixfiles/hosts/dvision-homelab/services/ai-workspace-db.nix`

#### `listen_addresses = "'*'"` — extra quotes
**Error:** PostgreSQL fatal: `could not translate host name "'*'"`
**Fix:** `listen_addresses = lib.mkForce "*"` (no quotes around asterisk).
**File:** `nixfiles/hosts/dvision-homelab/services/ai-workspace-db.nix`

#### Collation version mismatch (glibc 2.40 → 2.42)
**Error:** `template database "template1" has a collation version mismatch`
**Result:** `postgresql-setup.service` fails → user/database never created.
**Fix:** `sudo -u postgres psql -p 2284 -c "ALTER DATABASE template1 REFRESH COLLATION VERSION;"`
**Note:** This is a NixOS-upgrade recurring issue — any future glibc bump will require this.

#### `huey.run_consumer()` doesn't exist
**Error:** `AttributeError: 'SqliteHuey' object has no attribute 'run_consumer'`
**Cause:** Huey 2.6.0 (nixpkgs) uses `huey.create_consumer().run()`, not `run_consumer()`.
**Fix:** Changed `scheduler.py` `start_worker()`.
**File:** `src/ai_workspace/tasks/scheduler.py`

#### Worker service used venv path, not Nix package
**Error:** Service pointed to `/home/daviaaze/Projects/ai-workspace/.venv/bin/aiw`
**Fix:** Changed to `${pkgs.ai-workspace}/bin/aiw`
**File:** `nixfiles/hosts/dvision-homelab/services/ai-workspace-worker.nix`

#### Worker service had wrong DB URL
**Error:** `AIW_DB_URL=postgresql:///ai_workspace` (Unix socket, port 5432 — no PostgreSQL there)
**Fix:** `AIW_DB_URL=postgresql://ai_workspace:ai_workspace@localhost:2284/ai_workspace`
**File:** `nixfiles/hosts/dvision-homelab/services/ai-workspace-worker.nix`
**Also:** `environment.variables.AIW_DB_URL` in `ai-workspace-db.nix`

### 3. `pyproject.toml` fixes

| Change | Reason |
|--------|--------|
| `crewai[tools]>=0.80.0,<1.0` → `>=1.0` | crewAI 1.14.7 is current; old constraint blocked it |
| Added `huey>=2.5.0` | Was missing from core deps |
| `psycopg2-binary` → `psycopg2` | nixpkgs provides `psycopg2`, not `psycopg2-binary` |
| `mem0ai`, `langtrace-python-sdk`, `crewai-tools` → optional | Not in nixpkgs, code guards with try/except |
| Added `pgvector>=0.3.5` | Updated from `0.3.0` |

### 4. `flake.nix` fixes (ai-workspace repo)

- Added `huey` to `propagatedBuildInputs` (both `ai-workspace` and `ai-workspace-full`)
- Removed failed `pythonRelaxDepsHook` approach — it doesn't activate in `pyproject=true` builds
- Instead moved incompatible deps to `[project.optional-dependencies]`

### 5. `--provider deepseek` support for `aiw search`

**Problem:** `aiw search` was hardcoded for Ollama (local), but homelab GPU model loading takes 30-45s and models expire after 15min idle.

**Added:**
- `--provider deepseek` flag to CLI
- `DeepSearchEngine` now accepts `provider="deepseek"` using `deepseek-chat` + `deepseek-reasoner` via your DeepSeek API key (from sops-nix)
- `--provider ollama` remains the default

**File:** `src/ai_workspace/cli.py`, `src/ai_workspace/search/deep_search.py`

### 6. Live progress output for `aiw search`

Replaced the useless spinner (`⠸ Researching...`) with step-by-step progress:

```
📋 ⟳ Generating research plan...
📋 ✓ Plan: 5 sub-questions to research
    1. What specific items are in the lot?
    2. How to find market prices on Mercado Livre?
    ...

🔍 ▰▱▱▱▱ [1/5] What specific items are in the lot?...
🔍 ✓ [1/5] Done (confidence: 85%)
🔍 ▰▰▱▱▱ [2/5] How to find market prices on Mercado Livre?...
...

📝 ⟳ Synthesizing final report...
📝 ✓ Report complete
```

**Implementation:** `DeepSearchEngine.research()` accepts a `progress: Callable` parameter. CLI passes a lambda that prints to `rich.Console`.

### 7. JSON parsing robustness

**Problem:** DeepSeek API wraps JSON responses in markdown code blocks (` ```json ... ``` `), causing `json.loads()` to fail.

**Fix:** Added `_parse_json_safe()` function that:
1. Strips ` ``` ` fences
2. Falls back to regex extraction of the first JSON array/object in text
3. Filters markdown artifacts from line-splitting fallback (` ``` `, `[]`, `{}` lines)

**File:** `src/ai_workspace/search/deep_search.py`

### 8. Confidence field type safety

**Problem:** LLMs sometimes return descriptive text for `confidence` instead of a float (e.g., "The analysis combines findings..."), causing PostgreSQL `REAL` column to reject the value.

**Fix:** Added `_safe_float()` helper that coerces strings/ints/floats, returns a safe default for unparseable text.
**Files:** `deep_search.py`, `cli.py`, `scheduler.py`

---

## Current project state

### What works (tested on homelab)

| Command | Status | Notes |
|---------|--------|-------|
| `aiw --help` | ✅ | Full CLI with all subcommands |
| `aiw init` | ✅ | Tables created via `KnowledgeStore.initialize()` |
| `aiw task add/list/due/update` | ✅ | PostgreSQL CRUD |
| `aiw memory add/recall` | ✅ | Agent memory with type filtering |
| `aiw kb add/search` | ✅ | Text-based search (no vector yet — needs pgvector ext) |
| `aiw telemetry` | ✅ | Shows counts from DB |
| `aiw wf list` | ✅ | 3 workflows registered |
| `aiw schedule status` | ✅ | Shows periodic task config |
| `aiw sync status` | ✅ | Reports sync state |
| `aiw search --provider deepseek` | ✅ | Live progress, plan→research→synthesize |
| `aiw worker` (systemd) | ✅ | Running as `aiw-worker.service` |
| `aiw ask` | ❌ | Times out — `ProviderRegistry` uses `/v1` path that Ollama handles slowly for thinking models |
| `aiw search --provider ollama` | ⚠️ | Works but slow (38s GPU load on homelab) |

### What still needs attention

| Issue | Priority | Where |
|-------|----------|-------|
| `aiw ask` timeout with Ollama | 🟠 | `providers/__init__.py` — OpenAI client timeout or `/v1` path issue |
| pgvector extension not installed | 🟠 | Needs `sudo -u postgres psql -p 2284 -d ai_workspace -c "CREATE EXTENSION vector;"` — one-time |
| No tests written | 🟠 | `tests/` directory is empty. See `IMPROVEMENT_PLAN.md` §2 |
| `aiw worker` scheduler uses Ollama, not deepseek | 🟡 | `scheduler.py` `deep_research_task` hardcodes `ollama/` prefix |
| `aiw search` doesn't scrape URLs | 🟡 | User wants to scrape edital pages — need a web fetch tool or `--scrape` flag |
| LiteLLM bedroch/sagemaker warnings | 🟢 | Harmless — missing `botocore` module for AWS. Cosmetic only. |
| `crewai-tools` optional dep | 🟢 | Not in nixpkgs. Devs must `pip install` separately for `SerperDevTool` etc. |
| `mem0ai`, `langtrace-python-sdk` | 🟢 | Optional. Guarded by try/except. Need pip in dev shell. |
| DB port hardcoded (2284) in env vars | 🟢 | Homelab-specific. Thinkbook uses different port. |

### Service architecture (homelab)

```
systemd units:
├── postgresql.service     (port 2284, Immich-enforced)
├── aiw-worker.service     (Huey consumer, user=daviaaze, auto-restart)
├── aiw-backup.timer       (daily pg_dump at midnight)
└── aiw-telemetry.timer    (daily telemetry + learning at 8:00 UTC)
```

### Environment variables

| Variable | Where set | Value |
|----------|-----------|-------|
| `AIW_DB_URL` | `ai-workspace-db.nix` (system-wide) | `postgresql://ai_workspace:ai_workspace@localhost:2284/ai_workspace` |
| `DEEPSEEK_API_KEY` | sops-nix secret | Read by `ProviderRegistry` |
| `OLLAMA_HOST` | default | `http://localhost:11434` |

---

## Nix architecture notes

### ai-workspace flake → homelab flake chain

```
ai-workspace (github:daviaaze/ai-workspace)
  └─ packages.<system>.default = buildPythonPackage { ... }
       └─ propagatedBuildInputs: typer, rich, httpx, openai, ollama,
           pydantic, pydantic-settings, pyyaml, python-dotenv,
           beautifulsoup4, lxml, psycopg2, pgvector, crewai, huey
       └─ mainProgram = "aiw"

nixfiles (github:daviaaze/nixfiles)
  └─ inputs.ai-workspace → overlay → pkgs.ai-workspace
  └─ packages.ai-workspace = pkgs.ai-workspace
  └─ package-categories.nix → development = [ ai-workspace, ... ]
  └─ ai-workspace-db.nix → PostgreSQL + pgvector config
  └─ ai-workspace-worker.nix → systemd service
```

### Key gotcha: `pyproject = true` + `pythonRelaxDepsHook`

The hook **does not activate** in `pyproject=true` builds because Nix's Python infrastructure doesn't source `pythonRelaxDepsHook`'s setup hook automatically. Workaround: move incompatible deps to `[project.optional-dependencies]` and provide them in the flake's `propagatedBuildInputs` where available.

### To add new Python deps

1. Check if available: `nix eval nixpkgs#python3Packages.<name> --raw`
2. If yes: add to `propagatedBuildInputs` in `flake.nix`
3. If no: add to `[project.optional-dependencies]` in `pyproject.toml`
4. If optional and code-guarded: no further changes needed

---

## Useful commands (future AI agents)

```bash
# Test aiw installation
which aiw && aiw --help

# Check worker service
systemctl status aiw-worker
journalctl -u aiw-worker -f

# Check DB connectivity
psql -h localhost -p 2284 -U ai_workspace -d ai_workspace -c "SELECT 1;"

# Rebuild ai-workspace only
cd ~/Projects/ai-workspace && nix build .#default

# Update homelab lock + rebuild
cd ~/nixfiles && nix flake lock --update-input ai-workspace && \
  sudo nixos-rebuild switch --flake .#dvision-homelab

# Collation fix (after glibc updates)
sudo -u postgres psql -p 2284 -c "ALTER DATABASE template1 REFRESH COLLATION VERSION;"

# Install pgvector extension (one-time)
sudo -u postgres psql -p 2284 -d ai_workspace -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run search with live progress
export AIW_DB_URL="postgresql://ai_workspace:ai_workspace@localhost:2284/ai_workspace"
aiw search --provider deepseek "your research query"
```

---

## Files modified/created this session

### In `ai-workspace` repo
- `pyproject.toml` — dep cleanup
- `flake.nix` — added huey, removed relax hook
- `src/ai_workspace/cli.py` — `--provider deepseek`, live progress, safe confidence
- `src/ai_workspace/search/deep_search.py` — provider support, progress callback, JSON parsing fix, safe float
- `src/ai_workspace/tasks/scheduler.py` — `create_consumer().run()` fix, safe confidence
- `docs/IMPROVEMENT_PLAN.md` — comprehensive improvement guide
- `docs/CONTEXT_SWITCH.md` — previous session handoff
- `docs/BUILD_LOG.md` — this file

### In `nixfiles` repo
- `flake.nix` — added `ai-workspace` input
- `flake.lock` — updated
- `modules/flake-parts/overlays.nix` — added `ai-workspace` to overlay
- `modules/flake-parts/packages.nix` — exposed `ai-workspace` package
- `modules/shared/package-categories.nix` — added to development packages
- `hosts/dvision-homelab/services/ai-workspace-db.nix` — PG config fixes
- `hosts/dvision-homelab/services/ai-workspace-worker.nix` — new service file
- `hosts/dvision-homelab/services/default.nix` — imports
