# Architecture Review — Integrating Doc Indexer + Leilão Radar into AIW

**Date:** 2026-07-04
**Scope:** Review the two "outlier" features added in commit `09e9d65` (`doc_indexer`) and `cc3687c`/`298140b` (`leilao-radar`), and design how to fold them into the mainstream AIW stack: web exploration as an agent capability + recurring workflows (doc refresh, periodic scraping).
**Status:** Review + proposed target architecture. No code changes yet.

---

## TL;DR

Both features work in isolation but sit **outside** AIW's five-layer mainstream stack. They each have the right *storage* hooks but are missing the other four integrations:

| Layer | Doc Indexer | Leilão Radar |
|---|---|---|
| L1 Tool registry (`tools/`) | ❌ not a `Tool` | ⚠️ **duplicated** — `tools/leilao_scraper.py` already registered, project reimplements |
| L2 Agent loop | ❌ agents can't call it | ❌ agents can't call it |
| L3 MCP server | ❌ not exposed | ❌ not exposed |
| L4 Huey scheduler | ❌ no recurring refresh *(despite `content_hash` incremental support!)* | ❌ no periodic scan *(despite `sources.check_interval_hours` column!)* |
| L5 Knowledge/storage | ✅ writes shared `chunks` (pgvector) | ⚠️ own SQLite, no bridge to `chunks` for RAG |

The good news: **the integration surface already exists** — AIW has a tool registry, an MCP server, a Huey scheduler with a *data-driven* DB-task mechanism, and a shared pgvector store. We're mostly wiring, not building.

---

## 1. The Mainstream AIW Stack (the target shape)

AIW is a layered Python agent platform. A capability is "mainstream" when it is reachable through all five layers:

```
┌─────────────────────────────────────────────────────────────────┐
│  External clients (pi, Claude, IDE)        ┌──────────────────┐ │
│                                            │  aiw CLI         │ │
│                                            │  (aiw docs/...)  │ │
└───────────────────┬────────────────────────┴──────────────────┘ │
        L3  MCP server (mcp_server/server.py) ── curated subset ──┘
                        │
        L2  Agent loop  (cli/_agent.py + agent_loop)
                        │  consumes tools from registry
        L1  Tool registry (tools/__init__.py — PEP 562 lazy import)
              │  base: tools/base.py::Tool  (crewai-compatible)
              │
        L4  Huey scheduler (tasks/scheduler.py)
              ├─ crontab @huey.periodic_task(...)        ← hardcoded
              └─ periodic_check_db_tasks (hourly)        ← data-driven
                   → store.get_due_tasks() → run_scheduled_db_task
                        │
        L5  Knowledge / Storage
              ├─ chunks (pgvector) ← shared RAG store
              │     written by DocumentIndexer (workspace) +
              │              DocIndexer (external docs)
              ├─ engines: PgVector / Obsidian / LightRAG
              └─ KnowledgeStore (SQLite: tasks, sources, reputation)
```

**Web exploration tools already present in L1** (`tools/__init__.py`):
`WebFetchTool`, `HeadlessBrowserTool`, `PaginatedScraperTool`, `Crawl4AITool`, `ScrapingChainTool`, plus marketplace tools. So "web exploration as an agent capability" is *partially* built — the tools exist and are registered, they're just not all surfaced to MCP, and the doc indexer doesn't reuse them.

**L4 has two scheduling modes** — important for this review:
1. **Hardcoded crontab** — `@huey.periodic_task(crontab(...))`. Used by `periodic_daily_research`, `periodic_morning_briefing`, etc.
2. **Data-driven DB tasks** — `periodic_check_db_tasks` runs hourly, pulls `store.get_due_tasks()` and dispatches `run_scheduled_db_task(id)`. This lets you add recurring jobs *without code changes* (a row in the DB with a due time).

---

## 2. Feature A — Doc Indexer

**Files:** `src/ai_workspace/knowledge/doc_indexer.py` (695 lines), `src/ai_workspace/cli/_docs.py`

**What it does:** crawl an external doc site → extract text (BeautifulSoup) → chunk → embed (Ollama, `EMBED_MODEL`) → store in the shared `chunks` pgvector table. Optional `--review` LLM step suggests chunk/extraction rules. CLI: `aiw docs index|search|list|remove`.

**Strengths (already aligned):**
- Writes to the **shared `chunks` table** with doc-specific metadata — coexists with workspace RAG.
- Reuses `EMBED_MODEL` from `rag.py` (embedding is unified, not duplicated).
- **`content_hash`-based incremental re-indexing** — purpose-built for recurring refresh; unchanged pages are skipped. This is the single most important property for the "recurring doc update" workflow.

**Why it's an outlier:**
1. **Orphaned from the public API** — imported in `knowledge/__init__.py` but **not in `__all__`**. Other code can't discover it through the package surface.
2. **Not a `Tool`** — no entry in `tools/__init__.py`, so the agent loop can't call it. An agent that wants to "go learn this library's docs" has no tool to do it.
3. **Not MCP-exposed** — external clients (pi) can't trigger `index`/`search`. (Contrast: `transcribe_instagram_reel` *is* exposed.)
4. **No recurring task** — despite `content_hash` being tailor-made for refresh, there is no `periodic_doc_refresh`. Indexed docs silently go stale.
5. **Crawl path duplicated** — `DocCrawler._extract_text` + `_fetch_page` overlap with `tools/web_fetch.py` (fetch+extract) and `tools/scraping_chain.py`/`paginated_scraper.py` (multi-page crawl). The indexer reimplements fetching instead of composing existing tools.

---

## 3. Feature B — Leilão Radar

**Files:** `projects/leilao-radar/` (standalone project, own `pyproject.toml`) + the pre-existing `src/ai_workspace/tools/leilao_scraper.py` (32 KB)

**What it does:** auction scanning pipeline — `scrape → analyze (ROI) → alert (Telegram) → paper trading`. Standalone `leilao_radar` package with CLI `leilao-radar scrape|analyze|digest|run|summary|list|paper`, its own SQLite schema, ROI calculator, and Telegram bot.

**Strengths (already aligned):**
- A `LeilaoScraperTool` + 7 sources (`ReceitaFederalSLE`, `CaixaImoveis`, `BancoDoBrasilLeiloes`, `PoliciaFederalLeiloes`, `PRFLeiloes`, `LeiloesJudiciais`, `SefazLeiloes`) **are already registered** in `tools/__init__.py`. The capability exists in L1.
- The SQLite `sources` table has `check_interval_hours` + `last_scraped_at` — **the data model for "scrape from time to time" is already designed in**, there's just no scheduler reading it.

**Why it's an outlier:**
1. **Genuine duplication** — `projects/leilao-radar/src/leilao_radar/sources/base.py` defines a *second* `BaseSource`/`SourceResult` abstraction (`_extract_price`, `_normalize_tipo`, `_is_permitido_pf`) parallel to `tools/leilao_scraper.py`'s sources. Two scrapers, same domain, drifting independently. (The business plan even says "reaproveitar `tools/leilao_scraper.py`" — that reuse never happened.)
2. **Separate installable project** — lives in `projects/`, not `ai_workspace`. Not imported by the platform; agents can't reach it.
3. **Not a `Tool` for the *pipeline*** — `LeilaoScraperTool` covers raw scraping, but the *analyze→alert* pipeline isn't an agent-callable tool. An agent can't say "scan and surface good lots."
4. **Not MCP-exposed.**
5. **No periodic task** — the `sources.check_interval_hours` column is dead schema; nothing polls it. The business's "rotina diária de varredura" is unimplemented.
6. **No knowledge bridge** — lots live only in SQLite. No RAG over past auction results (e.g., "show me lots similar to X that closed at price Y"), which is exactly what would make the *agent* valuable for this domain.
7. **Alerts standalone** — Telegram bot isn't wired into AIW's briefing/notification system.

---

## 4. Target Integration Architecture

The principle: **align both features to the five layers, eliminate the leilão duplication, and let the data-driven scheduler drive recurrence.**

### 4.1 Web exploration as a first-class agent capability (L1 + L3)

Consolidate the crawl/fetch surface and make it reachable from agents and MCP:

- **Keep** `WebFetchTool` / `HeadlessBrowserTool` / `PaginatedScraperTool` / `Crawl4AITool` as the low-level fetch primitives.
- **Refactor** `DocIndexer` to *compose* `PaginatedScraperTool`/`ScrapingChainTool` instead of its own `DocCrawler._fetch_page`. One crawl path.
- **Add `DocIndexerTool`** — a `Tool` wrapper (`tools/doc_indexer.py`) exposing `index(url, name, review?)` / `search(query)` / `list()` / `remove(name)`, so the agent loop can index-on-demand. Register in `tools/__init__.py`.
- **Expose via MCP** — add `index_docs` and `search_docs` MCP tools (precedent: `transcribe_instagram_reel`). This makes "agent fetches docs → indexes → searches" an end-to-end external workflow.
- **Export** `DocIndexer`/`DocCrawler` in `knowledge/__init__.py.__all__`.

### 4.2 Recurring doc-update workflow (L4)

- **Add `periodic_doc_refresh`** — a crontab task (e.g. weekly) that iterates a **doc-sources registry** (name → url + opts, stored in `KnowledgeStore`), re-indexes each via `DocIndexer.index()`, and relies on `content_hash` to skip unchanged pages. Idempotent and cheap.
- **Also support data-driven refresh** — register doc sources as DB tasks so an individual source can be refreshed on its own cadence via the existing `periodic_check_db_tasks` → `run_scheduled_db_task` path, no code change per source.
- **CLI** — `aiw docs refresh [name]` to trigger manually; surfaced in `aiw schedule run`.

### 4.3 Periodic web-scraping workflow — Leilão (L1 + L3 + L4)

- **Resolve the duplication first** (§4.4). One scraper, in `ai_workspace`.
- **Add a pipeline tool** — `LeilaoRadarTool` (or extend `LeilaoScraperTool`) exposing `scan(sources?) → analyze → alert` as a single agent-callable `Tool`, not just raw scraping.
- **Expose via MCP** — `leilao_scan` tool so pi/external agents can run a scan on demand.
- **Wire `periodic_leilao_scan`** — a daily crontab task that runs `scan → analyze → alert`, reading the `sources` table's `is_active`/`check_interval_hours` to decide what to scan. The schema is already there; the scheduler just needs to honor it.

### 4.4 Eliminate the leilão duplication

Pick one home for the leilão domain logic (see Open Decisions):

- **Option 1 — Fold in (recommended):** move the project's *business logic* (ROI, alerts, paper trading, SQLite schema) into `ai_workspace/leilao_radar/` as a first-class module that **reuses** the existing `LeilaoScraperTool` sources. Delete `projects/leilao-radar/src/leilao_radar/sources/`. The `projects/` folder becomes a thin README/ops notes, or is removed.
- **Option 2 — Project depends on platform:** keep `projects/leilao-radar/` as the "product" but make it `pip install` `ai-workspace` and import `LeilaoScraperTool`/sources from there. Delete its `sources/`. More moving parts, preserves the "separate product" framing.

Either way: **one `BaseSource`, one source registry, one scraper.**

### 4.5 Knowledge bridge — lots → RAG (L5)

Mirror "interesting" / closed lots from SQLite into the `chunks` pgvector table (reusing `DocIndexer`'s chunk+embed path, or `DocumentIndexer`). This gives agents RAG over historical auction results — the differentiator for an *agent*-driven auction tool. SQLite stays the system-of-record for operational lots; pgvector is the searchable mirror.

---

## 5. Phased Plan

| Phase | Scope | Outcome |
|---|---|---|
| **P0 — Dedup** | Single leilão source-of-truth (fold or depend); `DocCrawler` composes `ScrapingChainTool` | No duplicated fetch/source code |
| **P1 — Tools** | `DocIndexerTool` + `LeilaoRadarTool` wrappers; export `DocIndexer` in `__all__` | Agent loop can invoke both |
| **P2 — MCP** | `index_docs`, `search_docs`, `leilao_scan` MCP tools | External agents (pi) can trigger |
| **P3 — Scheduler** | `periodic_doc_refresh` (weekly) + `periodic_leilao_scan` (daily), data-driven via DB tasks + `sources` table | Recurring workflows live |
| **P4 — Knowledge bridge** | Mirror lots → `chunks` for RAG | Agents answer "lots similar to X" |

Each phase is independently shippable. P0 is the prerequisite for the leilão path; the doc path can start at P1 immediately.

---

## 6. Open Decisions (need your call)

1. **Leilão home: fold into `ai_workspace/leilao_radar/` (P0 Opt 1) vs. keep `projects/` product depending on platform (Opt 2)?** — shapes all leilão work.
2. **Lots storage: keep SQLite (operational) + mirror to pgvector for RAG, or unify into pgvector only?** — affects P4 and whether we keep two stores.
3. **Refresh cadence defaults:** weekly docs / daily leilão — or per-source (`check_interval_hours`) for everything?
4. **MCP exposure scope:** expose `WebFetch`/`HeadlessBrowser` to external agents too, or only the high-level `index_docs`/`leilao_scan`? (Broader exposure = more agent power, more surface to police.)

---

## 7. Key Files Touched (per phase, estimate)

- **P0:** `projects/leilao-radar/src/leilao_radar/sources/*` (delete/merge), `src/ai_workspace/tools/leilao_scraper.py` (absorb business helpers), `src/ai_workspace/knowledge/doc_indexer.py` (refactor crawler to compose tools).
- **P1:** new `src/ai_workspace/tools/doc_indexer.py`, new `src/ai_workspace/tools/leilao_radar.py`, `src/ai_workspace/tools/__init__.py`, `src/ai_workspace/knowledge/__init__.py`.
- **P2:** `src/ai_workspace/mcp_server/server.py` (add tool defs + handlers).
- **P3:** `src/ai_workspace/tasks/scheduler.py` + `tasks/__init__.py`; `cli/_docs.py` (`refresh` cmd), `cli/_schedule.py` (list new periodics).
- **P4:** new bridge in `leilao_radar/` or `knowledge/` writing to `chunks`.
