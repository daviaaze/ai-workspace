#!/usr/bin/env python3
"""
pi-telemetry — zero-dependency telemetry dashboard for pi coding agent.

Scans pi session files (~/.pi/agent/sessions/), stores in SQLite,
and serves a live web dashboard. Python stdlib only + Chart.js from CDN.

Usage:
    python3 pi-telemetry.py scan          # scan all sessions into SQLite
    python3 pi-telemetry.py serve         # start dashboard server (default :8811)
    python3 pi-telemetry.py scan --serve  # scan + serve in one step
    python3 pi-telemetry.py serve --port 8080
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

# ── Config ─────────────────────────────────────────────────────────────────
DEFAULT_PORT = 8811

# Pi session directories: (path, origin_label)
SESSION_DIRS = [
    (os.path.expanduser("~/.pi/agent/sessions"), "personal"),
    (os.path.expanduser("~/.pi/agent-work/sessions"), "work"),
]

DB_DIR = os.path.expanduser("~/.pi/agent")
DB_PATH = os.path.join(DB_DIR, "pi-telemetry.db")

# ── DB Schema ──────────────────────────────────────────────────────────────

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    origin      TEXT DEFAULT 'personal',
    project     TEXT,
    provider    TEXT,
    model       TEXT,
    first_ts    TEXT,
    last_ts     TEXT,
    turns       INTEGER DEFAULT 0,
    msg_count   INTEGER DEFAULT 0,
    input_tok   INTEGER DEFAULT 0,
    output_tok  INTEGER DEFAULT 0,
    cache_read  INTEGER DEFAULT 0,
    cache_write INTEGER DEFAULT 0,
    total_tok   INTEGER DEFAULT 0,
    cost_input  REAL DEFAULT 0.0,
    cost_output REAL DEFAULT 0.0,
    cost_cache_read  REAL DEFAULT 0.0,
    cost_cache_write REAL DEFAULT 0.0,
    cost_total  REAL DEFAULT 0.0,
    compactions INTEGER DEFAULT 0,
    model_switches INTEGER DEFAULT 0,
    session_name TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT,
    entry_id    TEXT,
    parent_id   TEXT,
    ts          TEXT,
    role        TEXT,
    provider    TEXT,
    model       TEXT,
    input_tok   INTEGER DEFAULT 0,
    output_tok  INTEGER DEFAULT 0,
    cache_read  INTEGER DEFAULT 0,
    cache_write INTEGER DEFAULT 0,
    total_tok   INTEGER DEFAULT 0,
    cost_total  REAL DEFAULT 0.0,
    stop_reason TEXT,
    tool_name   TEXT,
    cmd_exit    INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS compactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT,
    entry_id    TEXT,
    ts          TEXT,
    tokens_before INTEGER,
    summary     TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS model_changes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT,
    entry_id    TEXT,
    ts          TEXT,
    provider    TEXT,
    model_id    TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_msg_ts ON messages(ts);
CREATE INDEX IF NOT EXISTS idx_sessions_last ON sessions(last_ts);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project);
CREATE INDEX IF NOT EXISTS idx_sessions_model ON sessions(model);
"""

# ── Scanner ────────────────────────────────────────────────────────────────

def init_db() -> sqlite3.Connection:
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def parse_iso(ts: Any) -> str:
    """Normalize timestamp to ISO string."""
    if not ts:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).isoformat()
    return str(ts).replace("Z", "+00:00")


def scan_session(conn: sqlite3.Connection, fpath: str, session_dir: str = "", origin: str = "personal") -> dict:
    """Scan a single session JSONL file and return aggregated stats."""
    path = Path(fpath)
    session_id = path.stem  # use filename stem as session id

    # Extract project name from session directory
    if session_dir:
        rel = path.relative_to(session_dir)
        parts = str(rel).split(os.sep)
        raw = parts[0].strip("--") if parts else ""
        project = raw.split("-")[-1] if raw else ""
    else:
        project = ""
        origin = ""

    stats = {
        "id": session_id,
        "project": project,
        "provider": "",
        "origin": origin,
        "model": "",
        "first_ts": "",
        "last_ts": "",
        "msg_count": 0,
        "turns": 0,
        "input_tok": 0,
        "output_tok": 0,
        "cache_read": 0,
        "cache_write": 0,
        "total_tok": 0,
        "cost_input": 0.0,
        "cost_output": 0.0,
        "cost_cache_read": 0.0,
        "cost_cache_write": 0.0,
        "cost_total": 0.0,
        "compactions": 0,
        "model_switches": 0,
        "session_name": "",
    }

    messages_batch: list[dict] = []
    compactions_batch: list[dict] = []
    model_changes_batch: list[dict] = []

    # Track seen model/provider
    models_seen: set[tuple[str, str]] = set()

    try:
        with open(fpath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                etype = entry.get("type", "")
                ts = parse_iso(entry.get("timestamp", ""))
                eid = entry.get("id", "")
                parent = entry.get("parentId", "")

                if etype == "session":
                    # session header — skip for now
                    continue

                elif etype == "message":
                    msg = entry.get("message", {})
                    role = msg.get("role", "")
                    usage = msg.get("usage", {})
                    cost_obj = usage.get("cost", {}) or {}

                    msg_row = {
                        "session_id": session_id,
                        "entry_id": eid,
                        "parent_id": parent,
                        "ts": ts,
                        "role": role,
                        "provider": msg.get("provider", ""),
                        "model": msg.get("model", ""),
                        "input_tok": usage.get("input", 0) or 0,
                        "output_tok": usage.get("output", 0) or 0,
                        "cache_read": usage.get("cacheRead", 0) or 0,
                        "cache_write": usage.get("cacheWrite", 0) or 0,
                        "total_tok": usage.get("totalTokens", 0) or 0,
                        "cost_total": cost_obj.get("total", 0) or 0,
                        "stop_reason": msg.get("stopReason", ""),
                        "tool_name": "",
                        "cmd_exit": None,
                    }

                    # For tool results, capture tool name
                    if role == "toolResult":
                        msg_row["tool_name"] = msg.get("toolName", "")
                    elif role == "bashExecution" or role == "tool_execution":
                        msg_row["tool_name"] = msg.get("toolName", "")
                        msg_row["cmd_exit"] = msg.get("exitCode") or entry.get("exitCode")

                    # For assistant messages, update session stats
                    if role == "assistant":
                        provider = msg.get("provider", "")
                        model = msg.get("model", "")
                        if provider:
                            stats["provider"] = provider
                        if model:
                            stats["model"] = model
                            models_seen.add((provider or "", model or ""))

                        stats["input_tok"] += msg_row["input_tok"]
                        stats["output_tok"] += msg_row["output_tok"]
                        stats["cache_read"] += msg_row["cache_read"]
                        stats["cache_write"] += msg_row["cache_write"]
                        stats["total_tok"] += msg_row["total_tok"]
                        stats["cost_input"] += cost_obj.get("input", 0) or 0
                        stats["cost_output"] += cost_obj.get("output", 0) or 0
                        stats["cost_cache_read"] += cost_obj.get("cacheRead", 0) or 0
                        stats["cost_cache_write"] += cost_obj.get("cacheWrite", 0) or 0
                        stats["cost_total"] += msg_row["cost_total"]

                    messages_batch.append(msg_row)

                    # Track first/last timestamp
                    if not stats["first_ts"] or ts < stats["first_ts"]:
                        stats["first_ts"] = ts
                    if not stats["last_ts"] or ts > stats["last_ts"]:
                        stats["last_ts"] = ts

                elif etype == "compaction":
                    stats["compactions"] += 1
                    compactions_batch.append({
                        "session_id": session_id,
                        "entry_id": eid,
                        "ts": ts,
                        "tokens_before": entry.get("tokensBefore", 0),
                        "summary": (entry.get("summary", "") or "")[:500],
                    })

                elif etype == "model_change":
                    stats["model_switches"] += 1
                    model_changes_batch.append({
                        "session_id": session_id,
                        "entry_id": eid,
                        "ts": ts,
                        "provider": entry.get("provider", ""),
                        "model_id": entry.get("modelId", ""),
                    })

                elif etype == "session_info":
                    stats["session_name"] = entry.get("name", "")

    except Exception as e:
        print(f"  ⚠ Error reading {fpath}: {e}", file=sys.stderr)
        return stats

    stats["turns"] = len(messages_batch)
    stats["msg_count"] = len(messages_batch)

    # Batch insert messages
    if messages_batch:
        conn.executemany(
            """INSERT OR IGNORE INTO messages
            (session_id, entry_id, parent_id, ts, role, provider, model,
             input_tok, output_tok, cache_read, cache_write, total_tok,
             cost_total, stop_reason, tool_name, cmd_exit)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [
                (
                    m["session_id"], m["entry_id"], m["parent_id"], m["ts"],
                    m["role"], m["provider"], m["model"],
                    m["input_tok"], m["output_tok"], m["cache_read"],
                    m["cache_write"], m["total_tok"], m["cost_total"],
                    m["stop_reason"], m["tool_name"], m["cmd_exit"],
                )
                for m in messages_batch
            ],
        )

    if compactions_batch:
        conn.executemany(
            """INSERT OR IGNORE INTO compactions
            (session_id, entry_id, ts, tokens_before, summary)
            VALUES (?,?,?,?,?)""",
            [(c["session_id"], c["entry_id"], c["ts"], c["tokens_before"], c["summary"]) for c in compactions_batch],
        )

    if model_changes_batch:
        conn.executemany(
            """INSERT OR IGNORE INTO model_changes
            (session_id, entry_id, ts, provider, model_id)
            VALUES (?,?,?,?,?)""",
            [(m["session_id"], m["entry_id"], m["ts"], m["provider"], m["model_id"]) for m in model_changes_batch],
        )

    conn.commit()
    return stats


def do_scan(verbose: bool = True) -> None:
    """Scan all session files into SQLite."""
    conn = init_db()
    cursor = conn.cursor()

    # Clear previous data
    cursor.executescript("DELETE FROM messages; DELETE FROM compactions; DELETE FROM model_changes; DELETE FROM sessions;")
    conn.commit()

    total_stats = defaultdict(float)
    start = time.time()
    total_files = 0

    for session_dir, origin in SESSION_DIRS:
        if not os.path.isdir(session_dir):
            print(f"⚠ Session directory not found: {session_dir}")
            continue

        files = sorted(Path(session_dir).rglob("*.jsonl"))
        # Filter out subagent worktree sessions
        files = [f for f in files if "/run-" not in str(f)]

        if not files:
            continue

        print(f"🔍 [{origin}] Scanning {len(files)} files from {session_dir}...")
        total_files += len(files)

        for i, sf in enumerate(files):
            try:
                stats = scan_session(conn, str(sf), session_dir, origin)
            except Exception as e:
                print(f"  ❌ {sf.name}: {e}", file=sys.stderr)
                continue

            # Upsert session
            cursor.execute(
                """INSERT OR REPLACE INTO sessions
                (id, origin, project, provider, model, first_ts, last_ts, turns, msg_count,
                 input_tok, output_tok, cache_read, cache_write, total_tok,
                 cost_input, cost_output, cost_cache_read, cost_cache_write, cost_total,
                 compactions, model_switches, session_name)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    stats["id"], stats["origin"], stats["project"], stats["provider"], stats["model"],
                    stats["first_ts"], stats["last_ts"], stats["turns"], stats["msg_count"],
                    stats["input_tok"], stats["output_tok"], stats["cache_read"],
                    stats["cache_write"], stats["total_tok"],
                    stats["cost_input"], stats["cost_output"], stats["cost_cache_read"],
                    stats["cost_cache_write"], stats["cost_total"],
                    stats["compactions"], stats["model_switches"], stats["session_name"],
                ),
            )

            for k in ("cost_total", "input_tok", "output_tok", "cache_read", "cache_write", "msg_count"):
                total_stats[k] += stats.get(k, 0) if isinstance(stats.get(k), (int, float)) else 0
            total_stats["sessions"] += 1

    conn.commit()
    elapsed = time.time() - start

    print(f"\n✅ Scanned {int(total_stats['sessions'])} sessions from {total_files} files in {elapsed:.1f}s")
    print(f"   Total cost: ${total_stats.get('cost_total', 0):.4f}")
    print(f"   Total tokens: {int(total_stats.get('input_tok', 0) + total_stats.get('output_tok', 0) + total_stats.get('cache_read', 0) + total_stats.get('cache_write', 0)):,}")
    conn.close()


# ── Web Dashboard ──────────────────────────────────────────────────────────

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>pi telemetry</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-chart-matrix@2.0.1/dist/chartjs-chart-matrix.min.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
       background: #0d1117; color: #c9d1d9; min-height: 100vh; }
.header { background: #161b22; border-bottom: 1px solid #30363d; padding: 16px 24px;
           display: flex; justify-content: space-between; align-items: center; }
.header h1 { font-size: 20px; font-weight: 600; color: #f0f6fc; }
.header span { color: #8b949e; font-size: 14px; }
.container { max-width: 1400px; margin: 0 auto; padding: 20px; }
.stats-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
             gap: 12px; margin-bottom: 24px; }
.stat-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px;
             padding: 16px; text-align: center; }
.stat-card .value { font-size: 28px; font-weight: 700; color: #f0f6fc; margin-bottom: 4px; }
.stat-card .label { font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-card .sub { font-size: 11px; color: #484f58; margin-top: 2px; }
.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
.chart-card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; }
.chart-card.full { grid-column: 1 / -1; }
.chart-card h3 { font-size: 14px; color: #8b949e; margin-bottom: 12px; font-weight: 500; }
.chart-card canvas { max-height: 300px; }
.tabs { display: flex; gap: 4px; margin-bottom: 16px; }
.tab { padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 13px;
       color: #8b949e; background: transparent; border: 1px solid transparent;
       transition: all 0.15s; }
.tab:hover { color: #c9d1d9; background: #1c2128; }
.tab.active { color: #f0f6fc; background: #1f6feb33; border-color: #1f6feb88; }
.tab-content { display: none; }
.tab-content.active { display: block; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 8px 12px; border-bottom: 1px solid #30363d;
     color: #8b949e; font-weight: 500; font-size: 11px; text-transform: uppercase;
     letter-spacing: 0.5px; white-space: nowrap; }
td { padding: 8px 12px; border-bottom: 1px solid #21262d; }
tr:hover td { background: #1c2128; }
.text-right { text-align: right; }
.text-muted { color: #8b949e; }
.text-success { color: #3fb950; }
.text-warning { color: #d29922; }
.text-danger { color: #f85149; }
.badge { display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 11px;
         background: #1f6feb33; color: #79c0ff; }
.loading { text-align: center; padding: 60px; color: #8b949e; }
.error { color: #f85149; padding: 20px; text-align: center; }
@media (max-width: 800px) { .chart-grid { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<div class="header">
  <h1>π telemetry</h1>
  <span>last scan: <span id="scan-time">—</span></span>
</div>
<div class="container">
  <div class="stats-row" id="stats-row"></div>

  <div class="tabs">
    <div class="tab active" data-tab="overview" onclick="switchTab('overview')">Overview</div>
    <div class="tab" data-tab="models" onclick="switchTab('models')">Models</div>
    <div class="tab" data-tab="tools" onclick="switchTab('tools')">Tool Calls</div>
    <div class="tab" data-tab="sessions" onclick="switchTab('sessions')">Sessions</div>
    <div class="tab" data-tab="context" onclick="switchTab('context')">Context & Compaction</div>
  </div>

  <div id="tab-overview" class="tab-content active">
    <div class="chart-grid">
      <div class="chart-card full"><h3>Daily Cost ($)</h3><canvas id="chart-daily-cost"></canvas></div>
      <div class="chart-card"><h3>Cost by Model</h3><canvas id="chart-cost-model"></canvas></div>
      <div class="chart-card"><h3>Tokens by Model</h3><canvas id="chart-tokens-model"></canvas></div>
      <div class="chart-card"><h3>Daily Token Volume</h3><canvas id="chart-daily-tokens"></canvas></div>
      <div class="chart-card"><h3>Cost by Project (top 10)</h3><canvas id="chart-cost-project"></canvas></div>
    </div>
  </div>

  <div id="tab-models" class="tab-content">
    <div class="chart-card full">
      <h3>Model Usage Comparison</h3>
      <div style="overflow-x:auto"><table><thead><tr>
        <th>Model</th><th class="text-right">Sessions</th><th class="text-right">Messages</th>
        <th class="text-right">Input</th><th class="text-right">Output</th>
        <th class="text-right">Cache Read</th><th class="text-right">Cache Hit %</th>
        <th class="text-right">Cost</th><th class="text-right">$/1M in</th><th class="text-right">$/1M out</th>
      </tr></thead><tbody id="model-table-body"></tbody></table></div>
    </div>
    <div class="chart-grid">
      <div class="chart-card"><h3>Input vs Output by Model</h3><canvas id="chart-model-inout"></canvas></div>
      <div class="chart-card"><h3>Cache Hit Rate by Model</h3><canvas id="chart-cache-rate"></canvas></div>
    </div>
  </div>

  <div id="tab-tools" class="tab-content">
    <div class="chart-card full">
      <h3>Tool Calls Breakdown</h3>
      <div style="overflow-x:auto"><table><thead><tr>
        <th>Tool</th><th class="text-right">Calls</th><th class="text-right">Avg Tokens/Call</th>
        <th class="text-right">% of Total</th><th class="text-right">Error Rate</th>
      </tr></thead><tbody id="tool-table-body"></tbody></table></div>
    </div>
    <div class="chart-grid">
      <div class="chart-card"><h3>Tool Usage Distribution</h3><canvas id="chart-tool-dist"></canvas></div>
      <div class="chart-card"><h3>Tool Error Rates</h3><canvas id="chart-tool-errors"></canvas></div>
    </div>
  </div>

  <div id="tab-sessions" class="tab-content">
    <div class="chart-card full">
      <h3>Session History</h3>
      <div style="overflow-x:auto"><table><thead><tr>
        <th>Date</th><th>Origin</th><th>Project</th><th>Model</th><th class="text-right">Msgs</th>
        <th class="text-right">Input</th><th class="text-right">Output</th>
        <th class="text-right">Cost</th><th class="text-right">Cache %</th><th>Name</th>
      </tr></thead><tbody id="session-table-body"></tbody></table></div>
    </div>
  </div>

  <div id="tab-context" class="tab-content">
    <div class="chart-grid">
      <div class="chart-card"><h3>Context Growth (last 50 sessions)</h3><canvas id="chart-context-growth"></canvas></div>
      <div class="chart-card"><h3>Context Growth per Turn</h3><canvas id="chart-context-per-turn"></canvas></div>
      <div class="chart-card"><h3>Compactions Over Time</h3><canvas id="chart-compactions"></canvas></div>
      <div class="chart-card"><h3>Tokens Saved by Compaction</h3><canvas id="chart-compaction-savings"></canvas></div>
    </div>
  </div>
</div>

<script>
const COLORS = ['#1f6feb','#3fb950','#d29922','#f85149','#db61a2','#58a6ff','#79c0ff','#56d364',
                '#e3b341','#ff7b72','#bc8cff','#a5d6ff','#c9d1d9','#7ee787','#ffa657','#d2a8ff'];

let charts = {};

async function loadData() {
  try {
    const r = await fetch('/api/data');
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return await r.json();
  } catch(e) {
    document.querySelector('.container').innerHTML =
      '<div class="error">Failed to load telemetry data. Run <code>python3 pi-telemetry.py scan</code> first.<br><br>Error: ' + e.message + '</div>';
    throw e;
  }
}

function formatCost(v) { return '$' + (v || 0).toFixed(4); }
function formatUSD(v) { return '$' + (v || 0).toFixed(2); }
function formatTok(v) { return (v || 0).toLocaleString(); }
function formatPct(v) { return ((v || 0) * 100).toFixed(1) + '%'; }

function renderStats(d) {
  const e = document.getElementById('stats-row');
  const items = [
    { v: d.sessions, l: 'Sessions', s: '' },
    { v: d.messages.toLocaleString(), l: 'Messages', s: '' },
    { v: d.tokens_total_est.toLocaleString(), l: 'Total Tokens',
      s: d.input_tok.toLocaleString() + ' in / ' + d.output_tok.toLocaleString() + ' out' },
    { v: formatUSD(d.total_cost), l: 'Total Cost', s: '' },
    { v: d.models.toLocaleString(), l: 'Unique Models', s: '' },
    { v: d.compactions, l: 'Compactions', s: '' },
    { v: d.cache_hit_pct.toFixed(1) + '%', l: 'Cache Hit Rate', s: '' },
    { v: d.projects, l: 'Projects', s: '' },
  ];
  e.innerHTML = items.map(i =>
    '<div class="stat-card"><div class="value">' + i.v + '</div><div class="label">' + i.l + '</div>' +
    (i.s ? '<div class="sub">' + i.s + '</div>' : '') + '</div>'
  ).join('');
}

function renderDailyCost(d) {
  const ctx = document.getElementById('chart-daily-cost').getContext('2d');
  if (charts.dailyCost) charts.dailyCost.destroy();
  charts.dailyCost = new Chart(ctx, {
    type: 'bar', data: {
      labels: d.daily_labels, datasets: [{
        label: 'Cost ($)',
        data: d.daily_costs,
        backgroundColor: '#1f6feb88',
        borderColor: '#1f6feb',
        borderWidth: 1,
        borderRadius: 2,
      }]
    },
    options: { responsive: true, maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, ticks: { callback: v => '$' + v.toFixed(2) } } },
      plugins: { legend: { display: false } }
    }
  });
}

function renderDailyTokens(d) {
  const ctx = document.getElementById('chart-daily-tokens').getContext('2d');
  if (charts.dailyTokens) charts.dailyTokens.destroy();
  charts.dailyTokens = new Chart(ctx, {
    type: 'bar', data: {
      labels: d.daily_labels, datasets: [
        { label: 'Input', data: d.daily_input, backgroundColor: '#58a6ff88', borderColor: '#58a6ff', borderWidth: 1 },
        { label: 'Output', data: d.daily_output, backgroundColor: '#3fb95088', borderColor: '#3fb950', borderWidth: 1 },
        { label: 'Cache Read', data: d.daily_cache, backgroundColor: '#d2992288', borderColor: '#d29922', borderWidth: 1 },
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, stacked: true,
      scales: { y: { beginAtZero: true, ticks: { callback: v => (v/1000).toFixed(0) + 'k' } } },
    }
  });
}

function renderModelCost(d) {
  const ctx = document.getElementById('chart-cost-model').getContext('2d');
  if (charts.modelCost) charts.modelCost.destroy();
  charts.modelCost = new Chart(ctx, {
    type: 'doughnut', data: {
      labels: d.model_names, datasets: [{
        data: d.model_costs,
        backgroundColor: COLORS.slice(0, d.model_names.length),
      }]
    },
    options: { responsive: true, maintainAspectRatio: false,
      plugins: { legend: { position: 'right', labels: { color: '#8b949e', font: { size: 11 } } } }
    }
  });
}

function renderModelTokens(d) {
  const ctx = document.getElementById('chart-tokens-model').getContext('2d');
  if (charts.modelTokens) charts.modelTokens.destroy();
  charts.modelTokens = new Chart(ctx, {
    type: 'bar', data: {
      labels: d.model_names, datasets: [
        { label: 'Input', data: d.model_input, backgroundColor: '#58a6ff88', borderColor: '#58a6ff', borderWidth: 1 },
        { label: 'Output', data: d.model_output, backgroundColor: '#3fb95088', borderColor: '#3fb950', borderWidth: 1 },
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y',
      scales: { x: { beginAtZero: true, ticks: { callback: v => (v/1000).toFixed(0) + 'k' } } },
      plugins: { legend: { position: 'top', labels: { color: '#8b949e', font: { size: 11 } } } }
    }
  });
}

function renderProjectCost(d) {
  const ctx = document.getElementById('chart-cost-project').getContext('2d');
  if (charts.projectCost) charts.projectCost.destroy();
  charts.projectCost = new Chart(ctx, {
    type: 'bar', data: {
      labels: d.project_names, datasets: [{
        label: 'Cost ($)',
        data: d.project_costs,
        backgroundColor: '#db61a288',
        borderColor: '#db61a2',
        borderWidth: 1,
      }]
    },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y',
      scales: { x: { beginAtZero: true, ticks: { callback: v => '$' + v.toFixed(2) } } },
      plugins: { legend: { display: false } }
    }
  });
}

function renderModelTable(d) {
  const tbody = document.getElementById('model-table-body');
  tbody.innerHTML = d.model_rows.map(r =>
    '<tr><td><b>' + r.name + '</b></td>'
    + '<td class="text-right">' + r.sessions + '</td>'
    + '<td class="text-right">' + r.messages + '</td>'
    + '<td class="text-right">' + formatTok(r.input) + '</td>'
    + '<td class="text-right">' + formatTok(r.output) + '</td>'
    + '<td class="text-right">' + formatTok(r.cache_read) + '</td>'
    + '<td class="text-right">' + formatPct(r.cache_hit) + '</td>'
    + '<td class="text-right">' + formatUSD(r.cost) + '</td>'
    + '<td class="text-right">' + formatUSD(r.cost_per_m_in) + '</td>'
    + '<td class="text-right">' + formatUSD(r.cost_per_m_out) + '</td></tr>'
  ).join('');
}

function renderToolTable(d) {
  const tbody = document.getElementById('tool-table-body');
  tbody.innerHTML = d.tool_rows.map(r =>
    '<tr><td><span class="badge">' + r.name + '</span></td>'
    + '<td class="text-right">' + r.calls + '</td>'
    + '<td class="text-right">' + formatTok(r.avg_tokens) + '</td>'
    + '<td class="text-right">' + formatPct(r.pct) + '</td>'
    + '<td class="text-right">' + (r.error_rate > 0.05 ? '<span class="text-danger">' : '') + formatPct(r.error_rate) + (r.error_rate > 0.05 ? '</span>' : '') + '</td></tr>'
  ).join('');
}

function renderSessionTable(d) {
  const tbody = document.getElementById('session-table-body');
  tbody.innerHTML = d.session_rows.slice(0, 100).map(r => {
    const date = r.ts ? r.ts.slice(0, 10) : '—';
    const originBadge = r.origin === 'work'
      ? '<span class="badge" style="background:#3fb95033;color:#3fb950">work</span>'
      : '<span class="badge" style="background:#1f6feb33;color:#79c0ff">personal</span>';
    return '<tr><td class="text-muted">' + date + '</td>'
    + '<td>' + originBadge + '</td>'
    + '<td>' + r.project + '</td>'
    + '<td>' + r.model + '</td>'
    + '<td class="text-right">' + r.messages + '</td>'
    + '<td class="text-right">' + formatTok(r.input) + '</td>'
    + '<td class="text-right">' + formatTok(r.output) + '</td>'
    + '<td class="text-right">' + formatUSD(r.cost) + '</td>'
    + '<td class="text-right">' + formatPct(r.cache_pct) + '</td>'
    + '<td class="text-muted">' + (r.name || '') + '</td></tr>';
  }).join('');
}

function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab === name));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.toggle('active', t.id === 'tab-' + name));
}

// ── Unused charts (keep references to avoid errors) ──
function renderModelInOut(d) {
  const ctx = document.getElementById('chart-model-inout')?.getContext('2d');
  if (!ctx) return;
  if (charts.modelInOut) charts.modelInOut.destroy();
  charts.modelInOut = new Chart(ctx, {
    type: 'bar', data: {
      labels: d.model_names, datasets: [
        { label: 'Input', data: d.model_input, backgroundColor: '#58a6ff88' },
        { label: 'Output', data: d.model_output, backgroundColor: '#3fb95088' },
      ]
    },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y',
      scales: { x: { beginAtZero: true, ticks: { callback: v => (v/1000).toFixed(0) + 'k' } } },
      plugins: { legend: { position: 'top', labels: { color: '#8b949e', font: { size: 11 } } } }
    }
  });
}

function renderCacheRate(d) {
  const ctx = document.getElementById('chart-cache-rate')?.getContext('2d');
  if (!ctx) return;
  if (charts.cacheRate) charts.cacheRate.destroy();
  charts.cacheRate = new Chart(ctx, {
    type: 'bar', data: {
      labels: d.model_names, datasets: [{
        label: 'Cache Hit Rate',
        data: d.model_cache_hit_pcts,
        backgroundColor: '#d2992288',
        borderColor: '#d29922',
        borderWidth: 1,
      }]
    },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y',
      scales: { x: { min: 0, max: 1, ticks: { callback: v => (v*100).toFixed(0) + '%' } } },
      plugins: { legend: { display: false } }
    }
  });
}

function renderToolDist(d) {
  const ctx = document.getElementById('chart-tool-dist')?.getContext('2d');
  if (!ctx) return;
  if (charts.toolDist) charts.toolDist.destroy();
  charts.toolDist = new Chart(ctx, {
    type: 'doughnut', data: {
      labels: d.tool_names, datasets: [{ data: d.tool_calls, backgroundColor: COLORS }]
    },
    options: { plugins: { legend: { position: 'right', labels: { color: '#8b949e', font: { size: 11 } } } } }
  });
}

function renderToolErrors(d) {
  const ctx = document.getElementById('chart-tool-errors')?.getContext('2d');
  if (!ctx) return;
  if (charts.toolErrors) charts.toolErrors.destroy();
  charts.toolErrors = new Chart(ctx, {
    type: 'bar', data: {
      labels: d.tool_names, datasets: [{
        label: 'Error Rate',
        data: d.tool_error_rates,
        backgroundColor: '#f8514988',
        borderColor: '#f85149',
        borderWidth: 1,
      }]
    },
    options: { responsive: true, maintainAspectRatio: false, indexAxis: 'y',
      scales: { x: { beginAtZero: true, ticks: { callback: v => (v*100).toFixed(0) + '%' } } }
    }
  });
}

function renderContextGrowth(d) {
  const ctx = document.getElementById('chart-context-growth')?.getContext('2d');
  if (!ctx) return;
  if (charts.ctxGrowth) charts.ctxGrowth.destroy();
  charts.ctxGrowth = new Chart(ctx, {
    type: 'line', data: {
      labels: d.ctx_labels, datasets: [{
        label: 'Average context per session (tokens)',
        data: d.ctx_sizes,
        borderColor: '#58a6ff',
        backgroundColor: '#58a6ff22',
        fill: true,
        tension: 0.3,
        pointRadius: 2,
      }]
    },
    options: { responsive: true, maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, ticks: { callback: v => (v/1000).toFixed(0) + 'k' } } }
    }
  });
}

function renderCompactions(d) {
  const ctx = document.getElementById('chart-compactions')?.getContext('2d');
  if (!ctx) return;
  if (charts.compactions) charts.compactions.destroy();
  charts.compactions = new Chart(ctx, {
    type: 'bar', data: {
      labels: d.compaction_labels, datasets: [{
        label: 'Compactions',
        data: d.compaction_counts,
        backgroundColor: '#d2992288',
        borderColor: '#d29922',
        borderWidth: 1,
      }]
    },
    options: { responsive: true, maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
    }
  });
}

function renderCompactionSavings(d) {
  const ctx = document.getElementById('chart-compaction-savings')?.getContext('2d');
  if (!ctx) return;
  if (charts.compactSavings) charts.compactSavings.destroy();
  charts.compactSavings = new Chart(ctx, {
    type: 'bar', data: {
      labels: d.compaction_labels2, datasets: [{
        label: 'Tokens Saved',
        data: d.compaction_savings,
        backgroundColor: '#3fb95088',
        borderColor: '#3fb950',
        borderWidth: 1,
      }]
    },
    options: { responsive: true, maintainAspectRatio: false,
      scales: { y: { beginAtZero: true, ticks: { callback: v => (v/1000).toFixed(0) + 'k' } } }
    }
  });
}

async function init() {
  try {
    const d = await loadData();
    document.getElementById('scan-time').textContent = d.scan_time || '—';
    renderStats(d);
    renderDailyCost(d);
    renderDailyTokens(d);
    renderModelCost(d);
    renderModelTokens(d);
    renderProjectCost(d);
    renderModelTable(d);
    renderToolTable(d);
    renderSessionTable(d);
    renderModelInOut(d);
    renderCacheRate(d);
    renderToolDist(d);
    renderToolErrors(d);
    renderContextGrowth(d);
    renderCompactions(d);
    renderCompactionSavings(d);
  } catch(e) {
    // error already handled in loadData
  }
}
init();
</script>
</body>
</html>"""


class DashboardHandler(SimpleHTTPRequestHandler):
    """HTTP handler serving the dashboard HTML and JSON data."""

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif path == "/api/data":
            data = self._build_json()
            body = json.dumps(data).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

    def _build_json(self) -> dict:
        conn = init_db()
        cursor = conn.cursor()

        # Totals
        cursor.execute("""
            SELECT COUNT(*) as sessions,
                   COALESCE(SUM(msg_count),0) as messages,
                   COALESCE(SUM(input_tok),0) as input_tok,
                   COALESCE(SUM(output_tok),0) as output_tok,
                   COALESCE(SUM(cache_read),0) as cache_read,
                   COALESCE(SUM(cache_write),0) as cache_write,
                   COALESCE(SUM(cost_total),0) as total_cost,
                   COALESCE(SUM(compactions),0) as compactions
            FROM sessions
        """)
        row = dict(cursor.fetchone())
        total_tokens_est = row["input_tok"] + row["output_tok"] + row["cache_read"] + row["cache_write"]
        total_cache = row["cache_read"] + row["cache_write"]
        cache_hit_pct = (total_cache / (row["input_tok"] + total_cache) * 100) if (row["input_tok"] + total_cache) > 0 else 0

        # Unique models and projects count
        cursor.execute("SELECT COUNT(DISTINCT model) as c FROM sessions WHERE model != ''")
        models_count = cursor.fetchone()["c"]
        cursor.execute("SELECT COUNT(DISTINCT project) as c FROM sessions WHERE project != ''")
        projects_count = cursor.fetchone()["c"]

        # Daily aggregates
        cursor.execute("""
            SELECT DATE(first_ts) as day,
                   COALESCE(SUM(input_tok),0) as input,
                   COALESCE(SUM(output_tok),0) as output,
                   COALESCE(SUM(cache_read),0) as cache_r,
                   COALESCE(SUM(cost_total),0) as cost
            FROM sessions
            WHERE first_ts != ''
            GROUP BY day ORDER BY day
        """)
        daily_rows = cursor.fetchall()
        daily_labels = [r["day"] for r in daily_rows]
        daily_costs = [r["cost"] for r in daily_rows]
        daily_input = [r["input"] for r in daily_rows]
        daily_output = [r["output"] for r in daily_rows]
        daily_cache = [r["cache_r"] for r in daily_rows]

        # Model aggregates
        cursor.execute("""
            SELECT model,
                   COUNT(*) as sessions,
                   COALESCE(SUM(msg_count),0) as messages,
                   COALESCE(SUM(input_tok),0) as input_tok,
                   COALESCE(SUM(output_tok),0) as output_tok,
                   COALESCE(SUM(cache_read),0) as cache_read,
                   COALESCE(SUM(cost_total),0) as cost
            FROM sessions
            WHERE model != ''
            GROUP BY model
            ORDER BY cost DESC
        """)
        model_rows = cursor.fetchall()
        model_names = [r["model"] for r in model_rows]
        model_costs = [r["cost"] for r in model_rows]
        model_input = [r["input_tok"] for r in model_rows]
        model_output = [r["output_tok"] for r in model_rows]

        model_rows_formatted = []
        for r in model_rows:
            total_in = r["input_tok"]
            total_cache_r = r["cache_read"]
            cache_hit = total_cache_r / (total_in + total_cache_r) if (total_in + total_cache_r) > 0 else 0
            cost_per_m_in = (r["cost"] / r["input_tok"] * 1_000_000) if r["input_tok"] > 0 else 0
            cost_per_m_out = (r["cost"] / r["output_tok"] * 1_000_000) if r["output_tok"] > 0 else 0
            model_rows_formatted.append({
                "name": r["model"],
                "sessions": r["sessions"],
                "messages": r["messages"],
                "input": r["input_tok"],
                "output": r["output_tok"],
                "cache_read": r["cache_read"],
                "cache_hit": cache_hit,
                "cost": r["cost"],
                "cost_per_m_in": cost_per_m_in,
                "cost_per_m_out": cost_per_m_out,
            })

        model_cache_hit_pcts = []
        for r in model_rows:
            total_in = r["input_tok"]
            total_cache_r = r["cache_read"]
            pct = total_cache_r / (total_in + total_cache_r) if (total_in + total_cache_r) > 0 else 0
            model_cache_hit_pcts.append(pct)

        # Tool aggregates
        cursor.execute("""
            SELECT tool_name,
                   COUNT(*) as calls,
                   COALESCE(AVG(total_tok),0) as avg_tokens,
                   SUM(CASE WHEN cmd_exit IS NOT NULL AND cmd_exit != 0 THEN 1 ELSE 0 END) as errors
            FROM messages
            WHERE tool_name != '' AND role = 'toolResult'
            GROUP BY tool_name
            ORDER BY calls DESC
        """)
        tool_rows = cursor.fetchall()
        total_tool_calls = sum(r["calls"] for r in tool_rows) if tool_rows else 1
        tool_names = [r["tool_name"] for r in tool_rows]
        tool_calls_data = [r["calls"] for r in tool_rows]
        tool_error_rates = [(r["errors"] or 0) / r["calls"] for r in tool_rows]

        tool_rows_formatted = []
        for r in tool_rows:
            tool_rows_formatted.append({
                "name": r["tool_name"],
                "calls": r["calls"],
                "avg_tokens": r["avg_tokens"],
                "pct": r["calls"] / total_tool_calls,
                "error_rate": (r["errors"] or 0) / r["calls"] if r["calls"] > 0 else 0,
            })

        # Session list
        cursor.execute("""
            SELECT id, origin, project, model, first_ts, msg_count,
                   input_tok, output_tok, cache_read,
                   cost_total, compactions, session_name
            FROM sessions
            ORDER BY first_ts DESC
            LIMIT 200
        """)
        session_rows = []
        for r in cursor.fetchall():
            total_in = r["input_tok"]
            total_cache_r = r["cache_read"]
            cache_pct = total_cache_r / (total_in + total_cache_r) if (total_in + total_cache_r) > 0 else 0
            session_rows.append({
                "ts": r["first_ts"],
                "origin": r["origin"],
                "project": r["project"],
                "model": r["model"],
                "messages": r["msg_count"],
                "input": r["input_tok"],
                "output": r["output_tok"],
                "cost": r["cost_total"],
                "cache_pct": cache_pct,
                "compactions": r["compactions"],
                "name": r["session_name"] or "",
            })

        # Session context sizes (total tokens per session, over time)
        cursor.execute("""
            SELECT first_ts, total_tok FROM sessions
            WHERE total_tok > 0 ORDER BY first_ts DESC LIMIT 50
        """)
        ctx_rows = list(reversed(cursor.fetchall()))
        ctx_labels = [r["first_ts"][:10] if r["first_ts"] else "" for r in ctx_rows]
        ctx_sizes = [r["total_tok"] for r in ctx_rows]

        # Compactions over time
        cursor.execute("""
            SELECT DATE(ts) as day, COUNT(*) as cnt, COALESCE(SUM(tokens_before),0) as saved
            FROM compactions
            WHERE ts != ''
            GROUP BY day ORDER BY day
        """)
        comp_rows = cursor.fetchall()
        compaction_labels = [r["day"] for r in comp_rows]
        compaction_counts = [r["cnt"] for r in comp_rows]
        compaction_labels2 = [r["day"] for r in comp_rows]
        compaction_savings = [r["saved"] for r in comp_rows]

        # Context per turn (avg)
        cursor.execute("""
            SELECT AVG(total_tok) as avg_ctx FROM sessions WHERE total_tok > 0 AND msg_count > 0
        """)
        avg_ctx_row = cursor.fetchone()

        # Project aggregates (fetch before closing)
        cursor.execute("""
            SELECT project, COALESCE(SUM(cost_total),0) as total
            FROM sessions WHERE project != ''
            GROUP BY project ORDER BY total DESC LIMIT 10
        """)
        proj_rows = cursor.fetchall()
        project_names = [r["project"] for r in proj_rows]
        project_costs = [r["total"] for r in proj_rows]

        conn.close()

        return {
            "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "sessions": row["sessions"],
            "messages": row["messages"],
            "input_tok": row["input_tok"],
            "output_tok": row["output_tok"],
            "cache_read": row["cache_read"],
            "cache_write": row["cache_write"],
            "tokens_total_est": total_tokens_est,
            "total_cost": row["total_cost"],
            "compactions": row["compactions"],
            "models": models_count,
            "projects": projects_count,
            "cache_hit_pct": cache_hit_pct,
            "daily_labels": daily_labels,
            "daily_costs": daily_costs,
            "daily_input": daily_input,
            "daily_output": daily_output,
            "daily_cache": daily_cache,
            "model_names": model_names,
            "model_costs": model_costs,
            "model_input": model_input,
            "model_output": model_output,
            "model_cache_hit_pcts": model_cache_hit_pcts,
            "model_rows": model_rows_formatted,
            "project_names": project_names,
            "project_costs": project_costs,
            "tool_names": tool_names,
            "tool_calls": tool_calls_data,
            "tool_error_rates": tool_error_rates,
            "tool_rows": tool_rows_formatted,
            "session_rows": session_rows,
            "ctx_labels": ctx_labels,
            "ctx_sizes": ctx_sizes,
            "compaction_labels": compaction_labels,
            "compaction_counts": compaction_counts,
            "compaction_labels2": compaction_labels2,
            "compaction_savings": compaction_savings,
        }


def do_serve(port: int = DEFAULT_PORT, scan_first: bool = True) -> None:
    """Start the dashboard server."""
    if scan_first and not os.path.exists(DB_PATH):
        print("📡 Scanning sessions...")
        do_scan(verbose=True)

    server = HTTPServer(("0.0.0.0", port), DashboardHandler)
    host = "127.0.0.1" if port == DEFAULT_PORT else "0.0.0.0"
    print(f"\n📊 pi telemetry dashboard: http://localhost:{port}")
    print(f"   Press Ctrl+C to stop\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Stopped.")
        server.server_close()


# ── CLI ────────────────────────────────────────────────────────────────────

def print_help():
    print(__doc__)


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print_help()
        return

    if args[0] == "scan":
        do_scan()
    elif args[0] == "serve":
        port = DEFAULT_PORT
        if "--port" in args:
            idx = args.index("--port")
            if idx + 1 < len(args):
                port = int(args[idx + 1])
        do_serve(port=port, scan_first=True)
    elif args[0] == "stats":
        port = DEFAULT_PORT
        if "--port" in args:
            idx = args.index("--port")
            if idx + 1 < len(args):
                port = int(args[idx + 1])
        do_scan()
        do_serve(port=port, scan_first=False)
    else:
        print(f"Unknown command: {args[0]}")
        print_help()


if __name__ == "__main__":
    main()
