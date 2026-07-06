# Leilão Radar — Domain Decomposition & AIW Integration

**Date:** 2026-07-04
**Supersedes:** the symmetric two-feature framing in `2026-07-04-web-exploration-integration-review.md` (kept as the layer-mapping appendix).
**Locked decisions (from review):** (1) fold leilão into `ai_workspace/leilao_radar/`, reusing `tools/leilao_scraper.py` sources; (2) drive all recurrence through the existing **DB-tasks** path (`periodic_check_db_tasks` → `run_scheduled_db_task`) — no new crontab entries.

---

## 1. Reframe: the leilão is the local context

The earlier review treated *doc indexer* and *leilão radar* as symmetric peers. They aren't.

- **Leilão Radar** is a **domain** — it has a business plan, an investor daily routine, a valuation engine (the IP), alerts, an operational schema, and a forward-looking portfolio track. It is the thing we're integrating *into* the platform.
- **Doc indexer** is a **reusable capability** — a "crawl → extract → chunk → embed → store" engine. It serves two consumers: (a) the general "index external library docs" use case, and (b) the leilão's own *knowledge/memory* sub-domain (RAG over historical lots). It is *not* a peer product.

So the decomposition is **leilão-spine-first**: break the leilão into bounded contexts, then show where each context plugs into AIW, then position web-exploration (incl. the doc indexer) as the cross-cutting capability that one of those contexts consumes.

---

## 2. Leilão Radar — bounded contexts (the spine)

Six bounded contexts. The first five exist today (in `projects/leilao-radar/`); the sixth is the integration pivot we're adding.

### BC1 — Ingestion (sources)
**Job:** fetch editais + raw lotes from auction sources on a per-source cadence.
- **Source registry** already modeled in SQLite `sources`: `name, tier (A/B/C), source_type, check_interval_hours, last_scraped_at, is_active`. Seeded with SLE (6h) + leilão.net (12h).
- Each source: `scrape() → SourceResult{editais, lotes, errors, duration_ms, http_requests}`.
- `scrape_log` table records every run (lots_found/new, status, error, duration).
- **The duplication lives here.** Two parallel abstractions:
  - `tools/leilao_scraper.py`: `LeilaoSource` base + 7 sources (SLE, Caixa, BB, PF, PRF, Judiciais, Sefaz) + `LeilaoScraperEngine` + `LeilaoScraperTool` + an embedded `_get_db()` sqlite. SLE here is an **older, thinner** impl.
  - `projects/leilao-radar/sources/`: `BaseSource` (with valuation-adjacent helpers: `_extract_price`, `_normalize_tipo`, `_is_permitido_pf`) + a **richer** REST-API `ReceitaFederalSLE` (`KNOWN_EDITAIS`, `ORGAO_LOCATION`, cent-scale handling) + `leilao_net`.
  - → Fold: canonical `BaseSource` = project's (it has the business helpers); port the rich SLE + leilão.net; port the 6 other source classes from `tools/` onto that base. One registry, one SLE.

### BC2 — Valuation (analysis) — *the differentiator / IP*
**Job:** turn a raw lote into a decision-grade ROI estimate.
- `ROICalculator`: 3 confidence levels (`confiavel` / `estimado` / `desconhecido`), cost model (ML fee, freight, risk), **ROI total + ROI mensal** (liquidity-adjusted), depreciation, `lance_maximo_recomendado`, **silver-bullet** detection.
- `manual_prices`: `PriceEntry` table, category fallback, `liquidity_days`, depreciation adjustment.
- Output: `lote_analysis` rows.
- **Integration posture: keep this pure.** No tool/MCP/scheduler wiring — it's a library the pipeline calls. Over-integrating it would be a mistake. It must stay testable and I/O-free.

### BC3 — Notification (alerts)
**Job:** decide what's worth alerting and deliver it.
- `AlertFilter`: applies `user_filters` (max_price, min_roi, min_roi_mensal, max_distance_km, categories, locations, min_confidence) → `AlertDecision` with priority `silver_bullet` / `high_roi` / `info` / `none`.
- `TelegramBot`: digest delivery; `alertas` table dedups (delivered/read flags).
- Priority-based message formatting.
- **Integration posture:** internal to the pipeline. Not a standalone agent tool. (Later: an optional `leilao_digest` MCP tool for "send me today's digest on demand".)

### BC4 — Operations (storage + config) — *system of record*
**Job:** own the operational truth.
- SQLite schema: `sources, editais, lotes, lote_itens, market_prices, lote_analysis, alertas, user_filters, scrape_log`.
- `Config`: env-driven (Telegram creds, CEP, raio, filters, paths, rate_limit_per_domain).
- **This SQLite is NOT the knowledge/RAG store.** It's transactional/operational. RAG lives in pgvector `chunks`. Keep them separate; bridge, don't merge.

### BC5 — Portfolio (post-purchase / paper trading) — *forward-looking, thin today*
**Job:** track bought lots, resale, actual vs estimated ROI.
- Today: CLI `paper` stub + plan items (B4 portfolio, B5 paper trading). Not built out.
- **Integration posture:** when built, this is a natural **agent tool** (`portfolio_status`) and possibly MCP-exposed — an agent that reasons about your active positions. Defer.

### BC6 — Knowledge / Memory — *the integration pivot (NEW)*
**Job:** give the agent semantic memory over the leilão domain — "lots similar to X that closed at price Y", "price history for category Z", "which sources reliably produce good ROI".
- **Does not exist today.** Lots live only in SQLite; nothing is searchable by meaning.
- Mechanism: mirror *interesting / closed* lots + their analysis into pgvector `chunks`, reusing the web-exploration engine's **embed + store + search spine** (see §3).
- **Nuance:** the doc indexer chunks *prose paragraphs*. A lot is *structured*. Reuse the embed/store/search path, but swap the chunker for a **per-record serializer** (one lot → one text blob → one embedding). Don't force lots through a paragraph chunker.
- **Bonus tie-in:** AIW *already has* a source-reputation mechanism (`periodic_source_reputation_update_mon/thu`, `update_source_reputation_task`, CRED-1 dataset). Leilão source reliability should plug into **that**, not invent a parallel one.

---

## 3. Web Exploration — ONE shared web-access layer, composed by everyone

There is **one** shared web-access layer, and it already exists and works. The problem is not that we need to build one — it's that two consumers **bypass it and roll their own fetch**. Kill the bypasses; don't invent a new layer.

**The shared layer (already built, in `tools/`):**
```
WebFetchTool        httpx + BeautifulSoup   static HTML   fastest, $0
Crawl4AITool        Playwright + markdown   JS render     medium, $0
HeadlessBrowserTool Playwright              SPAs/tables   slow, $0
PaginatedScraperTool Playwright             next-page     paginated lists
ScrapingChainTool   orchestrator w/ fallback  tries cheapest→most expensive
```
`ScrapingChainTool` is the single entry point: it picks the cheapest primitive that works for a given URL and falls back up the chain. **Every consumer of the web should go through it** (or a specific primitive when the consumer knows exactly what it needs).

**Who composes it today vs. who bypasses** (P0 fetch-rewire complete — zero `httpx` clients remain in leilão sources or `DocCrawler`):
| Consumer | Status | Fetch code |
|---|---|---|
| `tools/leilao_scraper.py` (mainstream leilão) | ✅ composes `ScrapingChainTool` (l.501) | shared |
| `knowledge/doc_indexer.py` `DocCrawler` | ✅ composes `WebFetchTool` via `_fetch_html` (P0c — 42 tests green) | shared |
| `projects/.../sources/receita_federal_sle.py` | ✅ routes through `BaseSource._fetch_json` → `WebFetchTool` (P0b — 8 tests green) | shared |
| `projects/.../sources/leilao_net.py` | ✅ routes through `BaseSource._fetch_html` → `WebFetchTool` (P0b — 3 tests, skip on missing `selectolax`) | shared |

> **Shared fetch point:** `BaseSource._fetch` / `_fetch_html` / `_fetch_json` (in `sources/base.py`) lazily import `WebFetchTool`. `_fetch_json` uses `extract_text=False` to get the raw response body (avoids running JSON through BeautifulSoup, which would corrupt it). Failures surface as `None`, not exceptions. `DocCrawler` has its own thin `_fetch_html` wrapper (separate package; same underlying primitive).

**The fix is uniform:** make every consumer call `WebFetch`/`ScrapingChain` instead of its own `httpx`. The only part that legitimately differs per consumer is the **thin tail** — parse the returned text into the consumer's shape and store it:
- leilão ingestion (BC1): parse → structured `lote` dicts → SQLite
- doc indexer / BC6 mirror: parse → chunks/records → embed → pgvector

That tail is small and per-consumer by necessity. Everything upstream of it — fetch, JS render, headless, pagination, retries, fallback — is shared and must not be duplicated.

**Consequence for the fold (P0):** `tools/leilao_scraper.py` is the *correct* shape (composes the shared layer); the project's `projects/.../sources/` are the *wrong* shape (bypass it). So the fold direction is: take the project's richer SLE/leilão.net parsing + business-helper `BaseSource`, but rewire their fetch through the shared layer — matching what `tools/leilao_scraper.py` already does. One `BaseSource` that calls `ScrapingChain`, not its own `httpx`.

---

## 4. Integration map — each bounded context → AIW layer

With fold + DB-tasks locked. ✅ = already true · 🔧 = work needed · ➖ = deliberately not integrated.

| BC | L1 Tool | L2 Agent | L3 MCP | L4 Scheduler | L5 Storage |
|---|---|---|---|---|---|
| **BC1 Ingestion** | ✅ `LeilaoScraperTool` (consolidate sources) | 🔧 pipeline tool | 🔧 `leilao_scan` | 🔧 DB-task reads `sources` due | ✅ SQLite |
| **BC2 Valuation** | ➖ pure lib | ➖ called by pipeline | ➖ | ➖ | writes `lote_analysis` |
| **BC3 Notification** | ➖ pipeline side-effect | ➖ | 🔧 (later) `leilao_digest` | ➖ | writes `alertas` |
| **BC4 Operations** | ➖ | ➖ | ➖ | ➖ | ✅ SQLite (system of record) |
| **BC5 Portfolio** | 🔧 (future) `portfolio_status` | 🔧 future | 🔧 future | ➖ | SQLite |
| **BC6 Knowledge** | 🔧 `search_similar_lots` | 🔧 | 🔧 | 🔧 DB-task mirrors closed lots | 🔧 pgvector `chunks` |

**The scheduler story (DB-tasks only), concretely:**
- BC1: the `sources` table *is* the schedule registry (`check_interval_hours`, `last_scraped_at`, `is_active`). The hourly `periodic_check_db_tasks` finds sources whose `last_scraped_at + check_interval_hours < now` and dispatches a scrape DB-task per due source. **No new crontab.** Add a DB-task handler `run_leilao_scrape(source_name)`.
- BC6: a DB-task `mirror_closed_lots_to_chunks` runs (e.g. daily via a `scheduled_tasks` row) to push newly-closed lots into pgvector.
- Composite: a daily `leilao_pipeline_run` DB-task = scan(due sources) → analyze → filter → deliver → mirror. Orchestrates the BCs; itself just a DB-task row.

**The fold (P0), concretely:**
- Canonical `BaseSource` = project's (business helpers). Lives at `ai_workspace/leilao_radar/sources/base.py`.
- Port project's rich `ReceitaFederalSLE` + `leilao_net` → `ai_workspace/leilao_radar/sources/`.
- Port the 6 source classes from `tools/leilao_scraper.py` (Caixa, BB, PF, PRF, Judiciais, Sefaz) onto the canonical `BaseSource`.
- `tools/leilao_scraper.py` becomes a **thin re-export** (`from ai_workspace.leilao_radar.sources import ...`) + keeps `LeilaoScraperTool` so `tools/__init__.py` registry is unchanged. Delete the old `LeilaoSource` base + old SLE + embedded `_get_db()`.

---

## 5. The pipeline (where the BCs meet the scheduler)

```
   DB-task: leilao_pipeline_run (daily)
        │
        ├─ BC1 scan:   for each due source (sources table) → scrape → editais+lotes (SQLite)
        ├─ BC2 analyze: ROICalculator over new lotes → lote_analysis (SQLite)
        ├─ BC3 alert:  AlertFilter(user_filters) → alertas → Telegram digest
        └─ BC6 mirror: closed/interesting lotes → serialize → embed → chunks (pgvector)
```

Each BC is independently testable; the pipeline only orchestrates. Per-source cadence is honored by BC1's own due-check, not by the daily composite — so a 6h source still scans 4×/day even though the composite "run" is daily. (Or: drop the composite and let each BC be its own DB-task on its own cadence. Open.)

---

## 6. Revised phased plan (leilão-spine, priority-ordered)

| Phase | Scope | Unblocks |
|---|---|---|
| **P0 — Ingestion consolidation** | Canonical `BaseSource`; fold rich SLE + leilão.net + 6 `tools/` sources; thin `tools/leilao_scraper.py` re-export; delete duplicates | everything leilão |
| **P1 — Fold domain** | Move `analysis/`, `alerts/`, `storage/`, `config.py`, `pipeline.py` into `ai_workspace/leilao_radar/`; `projects/` → README/ops notes | P2, P3 |
| **P2 — DB-task scheduling** | `run_leilao_scrape(source)` + `leilao_pipeline_run` DB-task handlers; `periodic_check_db_tasks` honors `sources` due-check; `cli` trigger | recurring scans live |
| **P3 — Knowledge mirror (BC6)** | Per-record serializer + reuse embed/store/search spine → `chunks`; `search_similar_lots` tool; `mirror_closed_lots` DB-task; tie source reliability into existing reputation mechanism | agent value-add |
| **P4 — Web-exploration engine** | `DocCrawler` composes `ScrapingChain`; `DocIndexerTool`; export `DocIndexer` in `__all__`; MCP `index_docs`/`search_docs` | general docs + BC6 reuse |
| **P5 — Portfolio + agent tooling** (future) | `portfolio_status` tool/MCP; paper-trading loop | — |

**Key reordering vs. the earlier plan:** P4 (doc-indexer generalization) now follows P3, because the leilão is the driver and BC6 is what creates the pressure to generalize the engine. The general "index docs" capability can still ship standalone earlier if you want it — it just isn't on the critical path.

---

## 7. Open questions for the next step

1. **Composite vs. per-BC cadence** — one daily `leilao_pipeline_run` DB-task, or separate DB-tasks per BC (scan/analyze/alert/mirror) each on its own cadence? (Affects P2.)
2. **Mirror scope** — mirror *all* closed lots, or only `silver_bullet`/`high_roi` + a sample? (Affects pgvector growth + P3 cost.)
3. **Portfolio timing** — is P5 in scope soon, or genuinely deferred? (Determines whether BC5 stays a stub.)
4. **General docs (P4) priority** — ship the standalone `aiw docs` MCP/tooling now in parallel, or strictly after P3 since the leilão drives it?
