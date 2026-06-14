# AI Workspace — Comprehensive Improvement Plan

**Generated:** 2026-06-13
**Source:** Analysis of 19 source files, all project docs, PyPI metadata, and upstream documentation (crewAI 1.14.7, pgvector 0.8.2, Huey 3.0.3, Langtrace 3.8.21, Textual 8.2.7, Streamlit 1.58.0, poetry2nix)

---

## Priority Legend

| Emoji | Priority | Meaning |
|-------|----------|---------|
| 🔴 | P0-Critical | Broken, security risk, or blocking |
| 🟠 | P1-High | Significant improvement, should be done soon |
| 🟡 | P2-Medium | Important, but not urgent |
| 🟢 | P3-Low | Nice to have, polish |

---

## 1. 🔴 DEPENDENCY VERSION EMERGENCY

### 1.1 crewAI version constraint is dangerously wrong

**Problem:** `pyproject.toml` pins `crewai[tools]>=0.80.0,<1.0` but crewAI has been on 1.x since early 2025 and is now at **1.14.7**. The `<1.0` constraint means `pip install` will resolve to 0.83.0 or similar — missing **Flows, checkpoints, guardrails, structured state, persistence, planning LLM, streaming, and the new YAML config format**.

**Fix:**
```toml
# pyproject.toml — change from:
"crewai[tools]>=0.80.0,<1.0"
# to:
"crewai[tools]>=1.0.0"
```

### 1.2 Missing crewAI features to adopt immediately

Based on crewAI 1.14.7 docs (scraped 2026-06-13):

| Feature | What it does | Where to apply |
|---------|-------------|----------------|
| **Flows (`@start`, `@listen`)** | Event-driven workflow orchestration — could replace or complement the custom DAG engine | `swarm.py`, `workflow/engine.py` |
| **Guardrail + `guardrail_max_retries`** | Validate task output before proceeding | All crew tasks |
| **Planning (`planning=True`)** | Crew auto-plans before executing | `research_crew()` |
| **Pydantic `output_pydantic`** | Structured outputs with validation | Replace manual JSON parsing in `deep_search.py` |
| **`@persist` decorator** | Automatic state persistence (built-in SQLite) | Could simplify custom state in `engine.py` |
| **Knowledge Sources** | Built-in RAG + knowledge per agent | `swarm.py` agents |
| **Streaming (`stream=True`)** | Real-time output tokens | `cli.py ask` command |
| **Checkpoint** | Auto-resume on failure | `engine.py` |
| **Mem0 integration** | Native memory (already using mem0ai dependency!) | `store.py` Agent memory layer |

### 1.3 Other version updates needed

| Package | Current Constraint | Latest | Action |
|---------|-------------------|--------|--------|
| `pgvector` | `>=0.3.0` | **0.4.2** (Python), **0.8.2** (Postgres ext) | Update constraint and Postgres extension |
| `huey` | `>=2.5.0` | **3.0.3** | OK (compatible), but check breaking changes |
| `textual` | `>=0.60.0` | **8.2.7** | **Major** — update constraint, Textual 1.0+ has completely different API |
| `streamlit` | in optional deps | **1.58.0** | Update constraint |
| `pytest-asyncio` | `>=0.24.0` | newer available | Ensure `asyncio_mode = auto` (already set ✓) |

---

## 2. 🔴 TESTING — ZERO TESTS WRITTEN

The `tests/` directory is empty. This is the single biggest risk to the project.

### 2.1 Test infrastructure (add to pyproject.toml)

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=5.0",           # NEW: coverage
    "pytest-timeout>=2.3",       # NEW: timeout protection
    "pytest-mock>=3.14",         # NEW: mocking
    "pytest-textual-snapshot>=0.1",  # NEW: Textual snapshot testing
    "faker>=25.0",               # NEW: test data generation
    "ruff>=0.4.0",
    "mypy>=1.10.0",
]
```

### 2.2 Test suite structure

```
tests/
├── conftest.py              # Shared fixtures (DB, registry, ollama mock)
├── test_cli.py              # Typer CLI command tests
├── test_agents/
│   └── test_swarm.py        # Agent creation, crew assembly
├── test_search/
│   └── test_deep_search.py  # Research pipeline
├── test_knowledge/
│   ├── test_store.py        # PostgreSQL/pgvector CRUD
│   └── test_sync.py         # Obsidian sync
├── test_workflow/
│   ├── test_engine.py       # DAG engine, retry, resume
│   └── test_workflows.py    # Workflow definitions
├── test_providers/
│   └── test_providers.py    # Provider registry, chat
├── test_tui/
│   └── test_app.py          # Textual TUI (snapshot + pilot)
├── test_dashboard/
│   └── test_app.py          # Streamlit app
├── test_tasks/
│   └── test_scheduler.py    # Huey tasks, periodic schedules
```

### 2.3 Key testing patterns from Textual docs (scraped 2026-06-13)

Textual provides a dedicated test framework:
- **`Pilot` object** via `run_test()` — simulates key presses, clicks, screen size changes
- **`pytest-textual-snapshot`** — generates SVG screenshots for visual regression testing
- **`pause()`** — waits for all pending messages to be processed before assertions
- Use `pytest-asyncio` with `asyncio_mode = auto` (already configured ✓)

**Example for `tui/app.py`:**
```python
import pytest
from ai_workspace.tui.app import AIWorkspaceApp

async def test_app_launches():
    async with AIWorkspaceApp().run_test() as pilot:
        assert pilot.app.title == "AI Workspace"

async def test_search_input():
    async with AIWorkspaceApp().run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+f")  # Focus search
        await pilot.press(*"research query")
        await pilot.press("enter")
        await pilot.pause()  # Wait for async processing
        # assert result appears in output widget
```

### 2.4 Testing patterns for crewAI agents

crewAI agents call LLMs — must mock these in tests:

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_llm():
    with patch("crewai.llm.LLM") as mock:
        yield mock

def test_researcher_agent_creation():
    from ai_workspace.agents.swarm import SwarmConfig, create_researcher
    cfg = SwarmConfig()
    agent = create_researcher(cfg)
    assert agent.role == "Research Specialist"
    assert agent.allow_delegation is True
```

### 2.5 Testing patterns for workflow engine

```python
import pytest
from ai_workspace.workflow.engine import BaseWorkflow, Context, StepStatus

class TestWorkflow(BaseWorkflow):
    name = "test_wf"
    
    async def step_a(self, ctx: Context): 
        return {"result": "a"}
    
    async def step_b(self, ctx: Context):
        a_result = ctx.get("step_a")
        return {"result": f"b_from_{a_result}"}

async def test_workflow_execution():
    wf = TestWorkflow(db_url="postgresql:///ai_workspace_test")
    result = await wf.run()
    assert result.status == StepStatus.DONE
    assert result.steps["step_a"].output == {"result": "a"}
```

### 2.6 Streamlit testing

Streamlit has `AppTest` class (since 1.28):
```python
from streamlit.testing.v1 import AppTest

def test_dashboard():
    at = AppTest.from_file("src/ai_workspace/dashboard/app.py")
    at.run()
    assert not at.exception
```

---

## 3. 🟠 CODE QUALITY & ARCHITECTURE

### 3.1 Use crewAI YAML config instead of hardcoded agent definitions

**Current:** `swarm.py` defines agents inline with hardcoded role/goal/backstory strings.

**Better:** crewAI 1.x recommends YAML config files:

```
src/ai_workspace/config/
├── agents.yaml
└── tasks.yaml
```

```yaml
# agents.yaml
researcher:
  role: "{topic} Research Specialist"
  goal: "Conduct thorough research on {topic}..."
  backstory: "You are a senior research analyst..."
  llm: ollama/deepseek-r1:14b
  verbose: true
  allow_delegation: true
  max_retries: 3

coder:
  role: "Senior Software Engineer"
  goal: "Write clean, efficient code..."
  backstory: "You are a senior engineer..."
  llm: ollama/qwen3-coder:30b
```

Then use `@CrewBase` decorator:
```python
from crewai import CrewBase, Agent, Task, Crew

@CrewBase
class ResearchCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    
    @Agent
    def researcher(self) -> Agent: ...
    
    @Task
    def research_task(self) -> Task: ...
```

**Benefit:** Non-developers can tune agent prompts without touching Python.

### 3.2 Use Pydantic structured output instead of JSON parsing

**Current:** `deep_search.py` does fragile manual JSON parsing:
```python
try:
    data = json.loads(str(result))
    sq.answer = data.get("answer", str(result))
except (json.JSONDecodeError, TypeError):
    sq.answer = str(result)
```

**Better:** Use crewAI 1.x `output_pydantic`:
```python
from pydantic import BaseModel

class SubQuestionResult(BaseModel):
    answer: str
    sources: list[str]
    confidence: float
    further_questions: list[str] = []

task = Task(
    description="...",
    expected_output="A structured research result",
    output_pydantic=SubQuestionResult,  # Auto-validated!
    agent=researcher,
)
```

### 3.3 Replace fragile dependency inference with explicit DAG

**Current:** `engine.py` uses `inspect.getsource()` to parse method bodies for `ctx.get("step_name")` calls — fragile and breaks with refactoring.

**Better:** Explicit step declaration:
```python
class MyWorkflow(BaseWorkflow):
    name = "my_wf"
    
    # Option 1: decorator with deps
    @step(depends_on=[])  
    async def step_plan(self, ctx): ...
    
    @step(depends_on=["step_plan"])
    async def step_research(self, ctx): ...
    
    # Option 2: crewAI Flows native
    @start()
    async def step_plan(self): ...
    
    @listen(step_plan)
    async def step_research(self, plan_output): ...
```

### 3.4 Add proper logging instead of print()

Multiple files use `print()` for logging. Replace with structured logging:
```python
# Instead of:
print(f"[db] Could not save research: {e}", file=sys.stderr)

# Use:
logger.error("Could not save research", extra={"error": str(e)})
```

### 3.5 Connection pooling for PostgreSQL

**Current:** `KnowledgeStore` creates raw `psycopg2` connections — no pooling.

**Fix:** Use `psycopg2.pool.SimpleConnectionPool` or async `asyncpg`:
```python
import asyncpg

class KnowledgeStore:
    async def initialize(self):
        self.pool = await asyncpg.create_pool(self.db_url, min_size=2, max_size=10)
```

### 3.6 Add dependency injection

**Current:** Components create their own dependencies internally (e.g., `KnowledgeStore()` called in 6+ places).

**Fix:** Use a simple DI pattern or a `dependencies` module:
```python
# src/ai_workspace/dependencies.py
from functools import lru_cache
from ai_workspace.knowledge import KnowledgeStore

@lru_cache
def get_knowledge_store() -> KnowledgeStore:
    store = KnowledgeStore()
    store.initialize()
    return store
```

---

## 4. 🟠 SECURITY IMPROVEMENTS

### 4.1 SQL injection risk in dynamic queries

**Current:** Multiple methods build SQL with f-strings:
```python
# store.py line 102:
c.execute(
    f"SELECT * FROM knowledge_entries WHERE {where} ORDER BY created_at DESC LIMIT %s",
    params + [limit],
)
```

**Fix:** Use parameterized queries throughout. For dynamic column names, use a whitelist:
```python
ALLOWED_COLUMNS = {"content", "title", "content_type", "created_at"}
# ...
```

### 4.2 API key management

**Current:** `providers/__init__.py` reads API keys from env and sops-nix paths. Good pattern, but no validation that keys exist before use.

**Fix:** Add explicit key validation on startup:
```python
def validate_providers():
    registry = ProviderRegistry()
    missing = [p for p, cfg in registry.providers.items() if not cfg.api_key]
    if missing:
        logger.warning(f"Providers without API keys: {missing}")
```

### 4.3 crewAI code execution safety

crewAI 1.x supports code execution (`allow_code_execution=True`, `code_execution_mode="safe"` via Docker). Current agents don't use this, but if enabled in the future:
- Always use `"safe"` mode (Docker sandbox)
- Never use `"unsafe"` mode in production

---

## 5. 🟡 DATABASE & PERFORMANCE

### 5.1 pgvector Postgres extension version

**Current:** Extension created with default version. pgvector is at **0.8.2** (June 2026).

**Upgrade:** `ALTER EXTENSION vector UPDATE TO '0.8.2'` — brings half-precision vectors (`halfvec`), sparse vectors (`sparsevec`), and binary quantization.

### 5.2 HNSW index instead of IVFFlat

**Current:** `store.py` creates an IVFFlat index (line 53):
```sql
CREATE INDEX ... USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
```

**Better:** HNSW provides better speed-recall tradeoff (from pgvector docs):
```sql
CREATE INDEX ON knowledge_entries 
USING hnsw (embedding vector_cosine_ops) 
WITH (m = 16, ef_construction = 64);
```

**Search query tuning:**
```sql
SET hnsw.ef_search = 100;  -- Higher = better recall, slower
SELECT * FROM knowledge_entries ORDER BY embedding <=> $1 LIMIT 10;
```

### 5.3 Missing indexes

Add these indexes for query performance:
```sql
CREATE INDEX idx_knowledge_type ON knowledge_entries(content_type);
CREATE INDEX idx_knowledge_tags ON knowledge_entries USING gin(tags);
CREATE INDEX idx_tasks_status ON tasks(status, priority);
CREATE INDEX idx_tasks_schedule ON tasks(schedule) WHERE schedule IS NOT NULL;
CREATE INDEX idx_tasks_next_run ON tasks(next_run) WHERE next_run IS NOT NULL;
CREATE INDEX idx_agent_memory_agent ON agent_memory(agent_name, memory_type);
```

### 5.4 pgvector-python 0.4.2 features

Use the latest Django-free ORM integration:
```python
# Use HalfVector for 2x storage savings on embeddings
from pgvector.psycopg2 import register_vector, HalfVector
register_vector(conn)

# Half-precision embeddings
c.execute("INSERT INTO knowledge_entries (embedding) VALUES (%s)", 
          (HalfVector(embedding_list),))
```

### 5.5 Connection retry & circuit breaker

PostgreSQL might be on a remote machine (homelab via Tailscale). Add:
```python
import tenacity

@tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential())
def connect():
    return psycopg2.connect(db_url)
```

---

## 6. 🟡 HUEY UPGRADE CONSIDERATIONS

Huey 3.0.3 (released) has changes from 2.x:

| Feature | Huey 3.0 | Status in project |
|---------|----------|-------------------|
| Django 5.0+ integration | Native support | N/A (no Django) |
| `TaskWrapper` improvements | Better introspection | Should check |
| `on_shutdown` signal | Graceful cleanup | `register_signal_handlers()` already handles this |
| Pipeline/chains | Composable task chains | Not used yet |
| Task locking | Via `lock_task()` | Not used |

### Recommendations:
1. **Add task pipelines** for sequential operations:
   ```python
   pipeline = deep_research_task.s(query="X").then(
       daily_briefing_task.s(topics=["X"])
   )
   pipeline()
   ```

2. **Add task timeouts** explicitly:
   ```python
   @huey.task(retries=2, retry_delay=30, timeout=600)
   def deep_research_task(...):
   ```

3. **Add rate limiting** for LLM-heavy tasks:
   ```python
   @huey.task()
   @huey.lock_task("deep-research-lock")
   def deep_research_task(...):
   ```

4. **Use Huey's `key_value` storage** for progress tracking:
   ```python
   # In task:
   huey.storage.put_data(f"progress:{task_id}", "50%")
   # In status check:
   progress = huey.storage.peek_data(f"progress:{task_id}")
   ```

---

## 7. 🟡 LANGTRACE OBSERVABILITY

### 7.1 Current state
- SDK installed and init'd in `init_telemetry()`
- `write_to_remote=False` — local-only
- Custom `TelemetrySpan` for non-crewAI operations

### 7.2 Improvements

**Add automatic instrumentation:**
```python
def init_telemetry() -> None:
    import langtrace_python_sdk as langtrace
    langtrace.init(
        api_key=os.getenv("LANGTRACE_API_KEY", ""),
        batch=True,
        instrumentations={
            "openai": True,      # Auto-trace OpenAI calls
            "anthropic": True,   # If using Anthropic
            "chromadb": True,    # If using ChromaDB
            "pinecone": True,    # If using Pinecone
        },
        write_spans_to_console=False,
    )
```

**Add custom spans for database operations:**
```python
from langtrace_python_sdk import with_langtrace_span

@with_langtrace_span("knowledge_store.search")
def search_knowledge(self, query, ...):
    ...
```

**Set up Langtrace dashboard** (self-hosted or cloud):
- The self-hosted option is free
- Provides: token usage tracking, cost analysis, latency percentiles, success rate monitoring

---

## 8. 🟡 TEXTUAL TUI IMPROVEMENTS

### 8.1 Upgrade to Textual 8.x

Textual 0.60 (current constraint) is ancient. Textual 8.2.7 has:
- **`textual devtools`** — live CSS editing, debug console, browser serving
- **`textual serve`** — run TUI as web app
- **`textual console`** — debug output in separate terminal
- **Worker system** — background threads for non-blocking ops
- **Command palette** — built-in `ctrl+p` command search
- **Reactive attributes** — `reactive` descriptors for automatic UI updates
- **Snapshot testing** — `pytest-textual-snapshot` for visual regression

### 8.2 Development workflow

```bash
# Terminal 1: dev console
textual console

# Terminal 2: run with live CSS editing
textual run --dev src/ai_workspace/tui/app.py

# Or serve in browser
textual serve src/ai_workspace/tui/app.py
```

### 8.3 Use Textual Workers for non-blocking operations

If the TUI triggers deep search or agent tasks:
```python
from textual.worker import Worker, get_current_worker

@on(Input.Submitted)
async def handle_search(self, event: Input.Submitted):
    self.run_worker(self.perform_search(event.value), exclusive=True)

async def perform_search(self, query: str):
    result = await asyncio.to_thread(deep_search, query)
    self.call_from_thread(self.display_results, result)
```

---

## 9. 🟡 STREAMLIT DASHBOARD IMPROVEMENTS

### 9.1 Caching strategy

Streamlit 1.58.0 provides 4 cache primitives. Review caching in `dashboard/app.py`:

```python
# Cache data that doesn't change often (research history, metrics)
@st.cache_data(ttl=300)
def load_research_history(limit=20):
    store = KnowledgeStore()
    store.initialize()
    history = store.get_research_history(limit=limit)
    store.close()
    return history

# Cache global resources (DB connections)
@st.cache_resource
def get_knowledge_store():
    store = KnowledgeStore()
    store.initialize()
    return store

# Session state for UI state
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "research"
```

### 9.2 Production deployment

```python
# Add to streamlit config (~/.streamlit/config.toml)
[server]
headless = true
port = 8501
maxUploadSize = 50

[browser]
gatherUsageStats = false

[theme]
base = "dark"
```

---

## 10. 🟢 NIX IMPROVEMENTS

### 10.1 Use poetry2nix for dependency management

**Current:** `flake.nix` manually lists `propagatedBuildInputs` — duplicates `pyproject.toml`.

**Better:** Use `poetry2nix` (from scraped docs):
```nix
{
  inputs.poetry2nix.url = "github:nix-community/poetry2nix";
  
  outputs = { nixpkgs, poetry2nix, ... }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};
      inherit (poetry2nix.lib.mkPoetry2Nix { inherit pkgs; }) 
        mkPoetryApplication;
    in {
      packages.${system}.default = mkPoetryApplication {
        projectDir = ./.;
        overrides = poetry2nix.overrides.withDefaults (final: prev: {
          # Custom overrides for packages poetry2nix can't handle
        });
      };
    };
}
```

### 10.2 Create NixOS module

As referenced in `docs/INTEGRATION.md`, create the actual module:
```nix
# In nixfiles/modules/ai-workspace.nix
{
  services.ai-workspace = {
    enable = true;
    package = inputs.ai-workspace.packages.x86_64-linux.default;
    postgresql = {
      host = "homelab.tailnet-name.ts.net";
      database = "ai_workspace";
    };
  };
}
```

### 10.3 `.envrc` for direnv

```bash
# .envrc
use flake
export AIW_DB_URL="postgresql:///ai_workspace"
export OLLAMA_HOST="http://localhost:11434"
```

---

## 11. 🟢 QUALITY OF LIFE

### 11.1 Add pre-commit hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.11.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mypy
    rev: v1.10.0
    hooks:
      - id: mypy
```

### 11.2 Add Makefile / Justfile

```makefile
# Makefile
.PHONY: test lint format check dev worker

test:
	pytest tests/ -v --cov=ai_workspace --cov-report=term-missing

lint:
	ruff check src/
	mypy src/

format:
	ruff format src/

check: lint test

dev:
	textual run --dev src/ai_workspace/tui/app.py

worker:
	python -m ai_workspace.cli worker

dashboard:
	streamlit run src/ai_workspace/dashboard/app.py
```

### 11.3 Add CI/CD pipeline

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: ai_workspace_test
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install -e ".[dev]"
      - run: pytest tests/ --cov --cov-report=xml
        env:
          AIW_DB_URL: postgresql://postgres:postgres@localhost:5432/ai_workspace_test
```

### 11.4 Add `py.typed` marker

For downstream type checking:
```bash
touch src/ai_workspace/py.typed
```

### 11.5 Add API documentation

Use mkdocs-material or Sphinx for API docs:
```
docs/
├── api/
│   ├── agents.md
│   ├── search.md
│   ├── knowledge.md
│   ├── workflow.md
│   └── providers.md
├── guides/
│   ├── getting-started.md
│   ├── deep-search.md
│   └── multi-pc-sync.md
└── IMPROVEMENT_PLAN.md  (this file)
```

---

## 12. FEATURE GAPS (from CLI docstring vs. implementation)

The CLI docstring in `cli.py` lists commands not all implemented:

| Command | Status | Action |
|---------|--------|--------|
| `aiw tui` | ✅ Implemented | Improve with Textual 8.x features |
| `aiw dashboard` | ✅ Implemented | Add caching, tests |
| `aiw search <query>` | ✅ Implemented | Use Pydantic structured output |
| `aiw ask` | ✅ Implemented | Add streaming |
| `aiw task list\|add\|run` | ⚠️ `run` missing | Add `task run <id>` command |
| `aiw memory add\|recall` | ✅ Implemented | Add vector search to recall |
| `aiw kb add\|search\|sync` | ⚠️ `kb sync` missing | Add kb sync command |
| `aiw schedule run\|status` | ✅ Implemented | OK |
| `aiw worker` | ✅ Implemented | Add health check endpoint |
| `aiw wf run\|status\|logs\|retry\|stats` | ✅ Implemented | Add `wf resume` |
| `aiw obsidian sync\|pull` | ⚠️ Only `sync` | Add `pull` subcommand |
| `aiw sync push\|pull\|vault` | ✅ Implemented | OK |
| `aiw telemetry` | ✅ Implemented | Add to dashboard |

---

## 13. EXECUTION ORDER

### Week 1 (Critical fixes)
1. Fix `pyproject.toml` crewAI constraint and test with 1.14.7
2. Add `py.typed` marker
3. Write `tests/conftest.py` with DB fixtures
4. Write `tests/test_knowledge/test_store.py` (most critical path)
5. Fix SQL injection vectors

### Week 2 (Test coverage)
6. Write `tests/test_workflow/test_engine.py`
7. Write `tests/test_agents/test_swarm.py`
8. Write `tests/test_tui/test_app.py` (snapshot tests)
9. Set up pre-commit hooks

### Week 3 (Architecture improvements)
10. Migrate agent definitions to YAML config
11. Use Pydantic structured output in deep_search
12. Replace dependency inference with explicit DAG
13. Add connection pooling

### Week 4 (Polish)
14. Add Makefile
15. Set up CI/CD
16. Create NixOS module
17. Add missing CLI commands
18. Documentation

---

## Appendix: Useful URLs from research

| Resource | URL |
|----------|-----|
| crewAI Docs (1.14) | https://docs.crewai.com |
| crewAI Flows | https://docs.crewai.com/concepts/flows |
| crewAI Agents | https://docs.crewai.com/concepts/agents |
| crewAI Tasks | https://docs.crewai.com/concepts/tasks |
| crewAI Tools | https://docs.crewai.com/concepts/tools |
| pgvector GitHub | https://github.com/pgvector/pgvector |
| pgvector-python | https://github.com/pgvector/pgvector-python |
| Huey 3.0 Docs | https://huey.readthedocs.io |
| Langtrace AI | https://docs.langtrace.ai |
| Textual 8.x Docs | https://textual.textualize.io |
| Textual Testing | https://textual.textualize.io/guide/testing/ |
| Textual Devtools | https://textual.textualize.io/guide/devtools/ |
| Streamlit Docs | https://docs.streamlit.io |
| Streamlit Caching | https://docs.streamlit.io/develop/api-reference/caching-and-state |
| poetry2nix | https://github.com/nix-community/poetry2nix |
| NixOS Wiki: Python | https://nixos.wiki/wiki/Python |
