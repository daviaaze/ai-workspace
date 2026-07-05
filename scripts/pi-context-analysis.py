#!/usr/bin/env python3
"""
pi context analysis — deep dive into context growth, cache efficiency,
duplication, and optimization opportunities.

Usage:
    python3 pi-context-analysis.py                  # full analysis
    python3 pi-context-analysis.py --work-only      # only work sessions
    python3 pi-context-analysis.py --session <id>   # deep-dive one session
    python3 pi-context-analysis.py --worst 10       # top 10 most wasteful sessions
"""

from __future__ import annotations

import os
import sqlite3
import sys
from collections import defaultdict

# ── Config ─────────────────────────────────────────────────────────────────
DB_PATH = os.path.expanduser("~/.pi/agent/pi-telemetry.db")
WORK_SESSION_DIR = os.path.expanduser("~/.pi/agent-work/sessions")
PERSONAL_SESSION_DIR = os.path.expanduser("~/.pi/agent/sessions")

# Provider pricing for cost estimation (per million tokens, USD)
# These are approximations — update as needed
PRICING: dict[str, dict[str, float]] = {
    "gpt-5.5":          {"input": 15.00, "output": 60.00, "cache_read": 7.50},
    "gpt-5.4":          {"input": 10.00, "output": 40.00, "cache_read": 5.00},
    "gpt-5.4-mini":     {"input": 2.50,  "output": 10.00, "cache_read": 1.25},
    "deepseek-v4-pro":  {"input": 0.50,  "output": 2.00,  "cache_read": 0.10},
    "deepseek-v4-flash": {"input": 0.15, "output": 0.60, "cache_read": 0.03},
    "claude-opus-4-8":  {"input": 15.00, "output": 75.00, "cache_read": 1.50},
    "kimi-for-coding":  {"input": 0.50,  "output": 2.00,  "cache_read": 0.25},
}

# ── Analysis ───────────────────────────────────────────────────────────────

def fmt_cost(c: float) -> str:
    if c >= 1: return f"${c:.2f}"
    if c >= 0.01: return f"${c:.4f}"
    return f"${c:.6f}"

def fmt_tok(t: int) -> str:
    if t >= 1_000_000: return f"{t/1_000_000:.1f}M"
    if t >= 1_000: return f"{t/1_000:.1f}k"
    return str(t)

def pct(a: float, b: float) -> str:
    if b == 0: return "—"
    return f"{a/b*100:.1f}%"

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_messages_for_session(conn: sqlite3.Connection, session_id: str, origin: str) -> list[dict]:
    """Load all messages for a session, ordered by timestamp, including tool results."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ts, role, provider, model, input_tok, output_tok, cache_read, cache_write,
               total_tok, cost_total, stop_reason, tool_name, cmd_exit
        FROM messages
        WHERE session_id = ?
        ORDER BY rowid ASC
    """, (session_id,))
    return [dict(r) for r in cursor.fetchall()]


def analyze_context_growth(conn: sqlite3.Connection, origin_filter: str | None = None) -> dict:
    """Analyze context growth patterns across sessions."""
    cursor = conn.cursor()

    where = "WHERE origin = ?" if origin_filter else ""
    params = (origin_filter,) if origin_filter else ()

    cursor.execute(f"""
        SELECT id, origin, project, model, first_ts, last_ts, msg_count, turns,
               input_tok, output_tok, cache_read, cache_write, total_tok,
               cost_total, compactions
        FROM sessions
        {where}
        ORDER BY first_ts
    """, params)
    sessions = [dict(r) for r in cursor.fetchall()]

    # 1. Context growth per turn (average)
    results = {
        "session_count": len(sessions),
        "by_model": defaultdict(lambda: {"sessions": 0, "msgs": 0, "input": 0, "output": 0,
                                          "cache_read": 0, "cache_write": 0, "cost": 0,
                                          "compactions": 0}),
        "by_project": defaultdict(lambda: {"sessions": 0, "cost": 0, "input": 0, "output": 0}),
        "context_growth": [],  # per-session detail for analysis
        "cache_efficiency": [],
        "runaway_sessions": [],  # sessions with extreme growth
        "compaction_effectiveness": [],
    }

    for s in sessions:
        model = s["model"] or "unknown"
        proj = s["project"] or "unknown"

        m = results["by_model"][model]
        m["sessions"] += 1
        m["msgs"] += s["msg_count"]
        m["input"] += s["input_tok"]
        m["output"] += s["output_tok"]
        m["cache_read"] += s["cache_read"]
        m["cache_write"] += s["cache_write"]
        m["cost"] += s["cost_total"]
        m["compactions"] += s["compactions"]

        p = results["by_project"][proj]
        p["sessions"] += 1
        p["cost"] += s["cost_total"]
        p["input"] += s["input_tok"]
        p["output"] += s["output_tok"]

        # Context per turn
        total_msgs = max(s["msg_count"], 1)
        input_per_turn = s["input_tok"] / total_msgs if total_msgs > 0 else 0
        output_per_turn = s["output_tok"] / total_msgs if total_msgs > 0 else 0
        cache_ratio = s["cache_read"] / (s["input_tok"] + s["cache_read"]) * 100 if (s["input_tok"] + s["cache_read"]) > 0 else 0

        results["context_growth"].append({
            "id": s["id"][:20],
            "origin": s["origin"],
            "project": proj,
            "model": model,
            "date": (s["first_ts"] or "")[:10],
            "msgs": s["msg_count"],
            "total_input": s["input_tok"],
            "total_output": s["output_tok"],
            "input_per_turn": input_per_turn,
            "output_per_msg": output_per_turn,
            "cache_ratio": cache_ratio,
            "cost": s["cost_total"],
            "compactions": s["compactions"],
        })

        results["cache_efficiency"].append({
            "model": model,
            "cache_ratio": cache_ratio,
            "cost": s["cost_total"],
            "input": s["input_tok"],
            "cache_read": s["cache_read"],
        })

        # Identify runaway sessions (>100k input per turn average, or >$10)
        if input_per_turn > 100_000 or s["cost_total"] > 10:
            results["runaway_sessions"].append(results["context_growth"][-1])

        if s["compactions"] > 0:
            results["compaction_effectiveness"].append({
                "model": model,
                "project": proj,
                "compactions": s["compactions"],
                "total_input": s["input_tok"],
                "cost": s["cost_total"],
                "cache_ratio": cache_ratio,
            })

    return results


def analyze_context_growth_per_turn(conn: sqlite3.Connection, origin_filter: str | None = None):
    """Deep-dive: for each session, look at context size over turns."""
    cursor = conn.cursor()
    where = "WHERE origin = ?" if origin_filter else ""
    params = (origin_filter,) if origin_filter else ()
    cursor.execute(f"""
        SELECT id, origin, project, model, first_ts, last_ts, msg_count, input_tok, output_tok, cache_read, total_tok, cost_total
        FROM sessions {where} ORDER BY cost_total DESC LIMIT 20
    """, params)
    sessions = [dict(r) for r in cursor.fetchall()]

    print(f"\n{'='*72}")
    print(" TOP 20 MOST EXPENSIVE SESSIONS — DETAILED ANALYSIS")
    print(f"{'='*72}")

    for s in sessions:
        msgs = load_messages_for_session(conn, s["id"], s["origin"])
        if not msgs:
            continue

        # Extract assistant messages with usage data
        assistant_msgs = [m for m in msgs if m["role"] == "assistant"]
        tool_msgs = [m for m in msgs if m["role"] == "toolResult"]

        if not assistant_msgs:
            continue

        # Calculate context accumulation over turns
        running_input = 0
        running_cache = 0
        growth_points = []
        turn_tools = defaultdict(int)
        turn_inputs = []
        turn_outputs = []

        for i, m in enumerate(assistant_msgs):
            running_input += m["input_tok"]
            running_cache += m["cache_read"]
            cache_pct = running_cache / (running_input + running_cache) * 100 if (running_input + running_cache) > 0 else 0
            growth_points.append({
                "turn": i + 1,
                "input": m["input_tok"],
                "output": m["output_tok"],
                "cache": m["cache_read"],
                "cache_pct": cache_pct,
                "running_input": running_input,
                "running_cache": running_cache,
            })
            turn_inputs.append(m["input_tok"])
            turn_outputs.append(m["output_tok"])

        # Count tool types
        for m in tool_msgs:
            if m["tool_name"]:
                turn_tools[m["tool_name"]] += 1

        # First 3 turns vs rest analysis
        first_3 = assistant_msgs[:3]
        rest = assistant_msgs[3:]
        first_3_input = sum(m["input_tok"] for m in first_3)
        first_3_output = sum(m["output_tok"] for m in first_3)
        first_3_cache = sum(m["cache_read"] for m in first_3)
        rest_input = sum(m["input_tok"] for m in rest) if rest else 0

        # Cache pattern
        cache_reads = [m["cache_read"] for m in assistant_msgs]
        avg_cache = sum(cache_reads) / len(cache_reads) if cache_reads else 0
        cache_consistency = len([c for c in cache_reads if c > 0]) / len(cache_reads) * 100 if cache_reads else 0

        # Consecutive same-tool analysis (potential duplication)
        tool_sequence = [m["tool_name"] for m in tool_msgs]
        consecutive_same = 0
        for i in range(1, len(tool_sequence)):
            if tool_sequence[i] == tool_sequence[i-1] and tool_sequence[i]:
                consecutive_same += 1

        print(f"\n{'─'*72}")
        print(f"  Session: {s['id'][:20]}  |  {s['project']:20s}  |  {s['model']:20s}")
        print(f"  Cost: {fmt_cost(s['cost_total']):>10s}  |  Turns: {s['msg_count']:>4d}  |  Date: {(s['first_ts'] or '')[:10]}")
        print(f"{'─'*72}")
        print("  INPUT TOKENS:")
        print(f"    Total:     {fmt_tok(s['input_tok']):>10s}")
        if turn_inputs:
            print(f"    Per turn:  {fmt_tok(sum(turn_inputs)//len(turn_inputs)):>10s} avg  |  {fmt_tok(max(turn_inputs)):>10s} max  |  {fmt_tok(min(turn_inputs)):>10s} min")
        print(f"    First 3:   {fmt_tok(first_3_input):>10s}  ({pct(first_3_input, s['input_tok'])} of total)")
        if rest:
            print(f"    After 3:   {fmt_tok(rest_input):>10s}  ({pct(rest_input, s['input_tok'])} of total)")

        print("\n  CACHE ANALYSIS:")
        print(f"    Cache reads: {fmt_tok(s['cache_read']):>10s}  ({pct(s['cache_read'], s['input_tok'] + s['cache_read'])} of context)")
        print(f"    Consistent caching: {cache_consistency:.0f}% of turns had cache hits")
        print(f"    Avg cache per turn: {fmt_tok(avg_cache)}")

        print("\n  OUTPUT TOKENS:")
        print(f"    Total:     {fmt_tok(s['output_tok']):>10s}")
        if turn_outputs:
            print(f"    Per turn:  {fmt_tok(sum(turn_outputs)//len(turn_outputs)):>10s} avg  |  {fmt_tok(max(turn_outputs)):>10s} max")

        print("\n  TOOL USAGE:")
        sorted_tools = sorted(turn_tools.items(), key=lambda x: -x[1])
        for tool_name, count in sorted_tools[:8]:
            bar = "█" * min(count // 5, 40)
            print(f"    {tool_name:20s}  {count:>4d} calls  {bar}")

        print("\n  POTENTIAL ISSUES:")
        issues = []

        # High context overhead
        avg_input = s["input_tok"] / s["msg_count"] if s["msg_count"] > 0 else 0
        if avg_input > 50_000:
            issues.append(f"🔴 Very high context per turn ({fmt_tok(avg_input)}) — system prompt + files too large?")
        elif avg_input > 20_000:
            issues.append(f"🟡 High context per turn ({fmt_tok(avg_input)})")

        # Low cache ratio for long sessions
        cache_pct = s["cache_read"] / (s["input_tok"] + s["cache_read"]) * 100 if (s["input_tok"] + s["cache_read"]) > 0 else 0
        if cache_pct < 50 and s["msg_count"] > 10:
            issues.append(f"🔴 Low cache hit rate ({cache_pct:.0f}%) for a long session — context is changing too much between turns")
        elif cache_pct < 30:
            issues.append(f"🔴 Very low cache hit rate ({cache_pct:.0f}%) — almost no prompt reuse")

        # High output (expensive)
        avg_output = s["output_tok"] / s["msg_count"] if s["msg_count"] > 0 else 0
        if avg_output > 2000:
            issues.append(f"🔴 High output per turn ({fmt_tok(avg_output)}) — agent generating very long responses")

        # Many consecutive same-tool calls
        if consecutive_same > 10:
            dup_pct = consecutive_same / len(tool_sequence) * 100 if tool_sequence else 0
            issues.append(f"🔴 {consecutive_same} consecutive same-tool calls ({dup_pct:.0f}% of all calls) — potential redundant operations")
        elif consecutive_same > 3:
            issues.append(f"🟡 {consecutive_same} consecutive same-tool calls — check for redundant work")

        # First-turn overhead
        first_input = turn_inputs[0] if turn_inputs else 0
        if first_input > 100_000:
            issues.append(f"🔴 Massive first turn ({fmt_tok(first_input)}) — system prompt + context files are huge")
        elif first_input > 50_000:
            issues.append(f"🟡 Large first turn ({fmt_tok(first_input)})")

        for issue in issues:
            print(f"    {issue}")

    return sessions


def analyze_duplication(conn: sqlite3.Connection, origin_filter: str | None = None):
    """Analyze tool call patterns to find duplication and redundancy."""
    cursor = conn.cursor()

    where = "AND origin = ?" if origin_filter else ""
    params = (origin_filter,) if origin_filter else ()

    print(f"\n{'='*72}")
    print(" TOOL CALL PATTERNS — DUPLICATION ANALYSIS")
    print(f"{'='*72}")

    # Top tools by frequency
    cursor.execute(f"""
        SELECT m.tool_name, 
               COUNT(*) as calls,
               SUM(CASE WHEN m.cmd_exit IS NOT NULL AND m.cmd_exit != 0 THEN 1 ELSE 0 END) as errors,
               AVG(m.total_tok) as avg_tok,
               s.origin
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        WHERE m.tool_name != '' AND m.role = 'toolResult' {where.replace('AND', 'AND s.') if origin_filter else ''}
        GROUP BY m.tool_name
        ORDER BY calls DESC
        LIMIT 20
    """, params if origin_filter else ())
    rows = cursor.fetchall()

    print("\n  Tool                   Calls      Errors     Avg tok")
    print(f"  {'─'*55}")
    for r in rows:
        tok = r["avg_tok"] or 0
        err_pct = (r["errors"] / r["calls"] * 100) if r["calls"] > 0 else 0
        bar = "█" * min(r["calls"] // 20, 30)
        print(f"  {r['tool_name']:22s} {r['calls']:>6d}  {err_pct:>5.1f}% err  {tok:>6.0f} tok  {bar}")

    # Sessions with highest tool call density
    if origin_filter:
        cursor.execute("""
            SELECT * FROM (
                SELECT s.id, s.origin, s.project, s.model, s.msg_count, s.cost_total,
                    (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id AND m.role = 'toolResult') as tool_calls
                FROM sessions s
                WHERE s.origin = ?
            ) WHERE tool_calls > 50
            ORDER BY tool_calls DESC
            LIMIT 15
        """, (origin_filter,))
    else:
        cursor.execute("""
            SELECT * FROM (
                SELECT s.id, s.origin, s.project, s.model, s.msg_count, s.cost_total,
                    (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id AND m.role = 'toolResult') as tool_calls
                FROM sessions s
            ) WHERE tool_calls > 50
            ORDER BY tool_calls DESC
            LIMIT 15
        """)
    rows = cursor.fetchall()

    print("\n  Sessions with most tool calls:")
    print(f"  {'Project':20s} {'Model':22s} {'Tool calls':>10s} {'Cost':>10s}  {'Tools/turn'}")
    print(f"  {'─'*72}")
    for r in rows:
        tools_per_turn = r["tool_calls"] / max(r["msg_count"], 1)
        print(f"  {r['project']:20s} {r['model']:22s} {r['tool_calls']:>6d}     {fmt_cost(r['cost_total']):>8s}  {tools_per_turn:.1f}")


def analyze_by_model(conn: sqlite3.Connection, origin_filter: str | None = None):
    """Compare models on efficiency metrics."""
    cursor = conn.cursor()

    where = "WHERE origin = ?" if origin_filter else ""
    params = (origin_filter,) if origin_filter else ()

    print(f"\n{'='*72}")
    print(" MODEL EFFICIENCY COMPARISON")
    print(f"{'='*72}")

    cursor.execute(f"""
        SELECT model,
               COUNT(*) as sessions,
               SUM(msg_count) as msgs,
               SUM(input_tok) as input_tok,
               SUM(output_tok) as output_tok,
               SUM(cache_read) as cache_read,
               SUM(cost_total) as cost
        FROM sessions {where} AND model != ''
        GROUP BY model
        ORDER BY cost DESC
    """, params if origin_filter else ())
    rows = cursor.fetchall()

    print(f"\n  {'Model':25s} {'Sessions':>9s} {'Input':>10s} {'Output':>10s} {'Cache':>10s} {'Cost':>10s} {'Cache%':>7s} {'Cost/1M in':>10s}")
    print(f"  {'─'*95}")
    for r in rows:
        c = r["cache_read"]
        i = r["input_tok"]
        cache_p = c / (i + c) * 100 if (i + c) > 0 else 0
        cost_per_m_in = (r["cost"] / i * 1_000_000) if i > 0 else 0
        print(f"  {r['model']:25s} {r['sessions']:>6d}    {fmt_tok(r['input_tok']):>10s} {fmt_tok(r['output_tok']):>10s} {fmt_tok(r['cache_read']):>10s} {fmt_cost(r['cost']):>10s} {cache_p:>5.1f}%  {fmt_cost(cost_per_m_in):>10s}/M")

    # Cost breakdown: input vs output vs cache savings
    print("\n  Cost breakdown by model (what you're paying for):")
    print(f"  {'Model':25s} {'Input cost':>12s} {'Output cost':>12s} {'Cache saved':>12s}")
    print(f"  {'─'*65}")

    for r in rows:
        model = r["model"]
        pricing = PRICING.get(model, {})
        in_rate = pricing.get("input", 0)
        out_rate = pricing.get("output", 0)
        cache_rate = pricing.get("cache_read", 0)

        # Estimate what it WOULD cost without caching
        input_cost = r["input_tok"] / 1_000_000 * in_rate
        output_cost = r["output_tok"] / 1_000_000 * out_rate
        actual_input_cost = (r["input_tok"]) / 1_000_000 * in_rate  # non-cached input
        cache_saving = r["cache_read"] / 1_000_000 * (in_rate - cache_rate) if cache_rate else r["cache_read"] / 1_000_000 * in_rate * 0.9

        print(f"  {model:25s} {fmt_cost(input_cost):>12s} {fmt_cost(output_cost):>12s} {fmt_cost(cache_saving):>12s}")


def analyze_cache_deep(conn: sqlite3.Connection):
    """Deep cache analysis — find sessions with worst/best cache behavior."""
    cursor = conn.cursor()

    print(f"\n{'='*72}")
    print(" CACHE EFFECTIVENESS — DEEP DIVE")
    print(f"{'='*72}")

    # Best cache performers (long sessions with high cache ratio)
    cursor.execute("""
        SELECT id, origin, project, model, msg_count, input_tok, cache_read, cost_total
        FROM sessions
        WHERE (input_tok + cache_read) > 0 AND msg_count > 5
        ORDER BY CAST(cache_read AS REAL) / (input_tok + cache_read) DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    print("\n  BEST cache efficiency (long sessions, high cache %):")
    print(f"  {'Project':20s} {'Model':22s} {'Msgs':>5s} {'Input':>10s} {'Cache':>10s} {'Cache%':>7s} {'Cost':>10s}")
    print(f"  {'─'*80}")
    for r in rows:
        ratio = r["cache_read"] / (r["input_tok"] + r["cache_read"]) * 100 if (r["input_tok"] + r["cache_read"]) > 0 else 0
        print(f"  {r['project']:20s} {r['model']:22s} {r['msg_count']:>5d} {fmt_tok(r['input_tok']):>10s} {fmt_tok(r['cache_read']):>10s} {ratio:>5.1f}%  {fmt_cost(r['cost_total']):>10s}")

    # Worst cache performers (long sessions, low cache %)
    cursor.execute("""
        SELECT id, origin, project, model, msg_count, input_tok, cache_read, cost_total
        FROM sessions
        WHERE (input_tok + cache_read) > 0 AND msg_count > 5 AND cache_read < input_tok * 0.5
        ORDER BY CAST(cache_read AS REAL) / (input_tok + cache_read) ASC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    print("\n  WORST cache efficiency (long sessions, low cache %):")
    print(f"  {'Project':20s} {'Model':22s} {'Msgs':>5s} {'Input':>10s} {'Cache':>10s} {'Cache%':>7s} {'Cost':>10s}")
    print(f"  {'─'*80}")
    for r in rows:
        ratio = r["cache_read"] / (r["input_tok"] + r["cache_read"]) * 100 if (r["input_tok"] + r["cache_read"]) > 0 else 0
        print(f"  {r['project']:20s} {r['model']:22s} {r['msg_count']:>5d} {fmt_tok(r['input_tok']):>10s} {fmt_tok(r['cache_read']):>10s} {ratio:>5.1f}%  {fmt_cost(r['cost_total']):>10s}")

    # Cache consistency over time
    cursor.execute("""
        SELECT DATE(first_ts) as day,
               COALESCE(SUM(input_tok),0) as input_tok,
               COALESCE(SUM(cache_read),0) as cache_read,
               COALESCE(SUM(cost_total),0) as cost
        FROM sessions
        WHERE origin = 'work'
        GROUP BY day
        ORDER BY day
    """)
    rows = cursor.fetchall()
    print("\n  Cache ratio over time (work sessions):")
    print(f"  {'Date':12s} {'Input':>10s} {'Cache':>10s} {'Cache%':>7s} {'Cost':>10s}")
    print(f"  {'─'*55}")
    for r in rows[-14:]:  # Last 14 days
        ratio = r["cache_read"] / (r["input_tok"] + r["cache_read"]) * 100 if (r["input_tok"] + r["cache_read"]) > 0 else 0
        print(f"  {r['day']:12s} {fmt_tok(r['input_tok']):>10s} {fmt_tok(r['cache_read']):>10s} {ratio:>5.1f}%  {fmt_cost(r['cost']):>10s}")


def analyze_context_duplication(conn: sqlite3.Connection, origin_filter: str | None = None):
    """Analyze potential context duplication — large system prompts, redundant reads."""
    cursor = conn.cursor()

    where = "AND origin = ?" if origin_filter else ""
    params = (origin_filter,) if origin_filter else ()

    print(f"\n{'='*72}")
    print(" CONTEXT DUPLICATION ANALYSIS")
    print(f"{'='*72}")

    # First-turn overhead: how much of the total input is in the first turn?
    print("\n  First-turn overhead (system prompt + context files + skills):")
    print("  Looking at sessions where the first turn dominates input...")
    print(f"  {'Project':20s} {'Model':22s} {'Total in':>10s} {'First turn':>10s} {'Overhead%':>9s} {'Cost':>10s}")
    print(f"  {'─'*85}")

    # This requires per-message analysis. Let's sample the most expensive sessions.
    cursor.execute(f"""
        SELECT id, origin, project, model, msg_count, input_tok, cost_total
        FROM sessions
        {where.replace('AND', 'WHERE') if origin_filter else 'WHERE 1=1'}
        AND cost_total > 1
        ORDER BY cost_total DESC
        LIMIT 20
    """, params if origin_filter else ())
    top_sessions = [dict(r) for r in cursor.fetchall()]

    for s in top_sessions:
        msgs = load_messages_for_session(conn, s["id"], s["origin"])
        assistant_msgs = [m for m in msgs if m["role"] == "assistant"]
        if not assistant_msgs:
            continue

        first_input = assistant_msgs[0]["input_tok"]
        overhead_pct = first_input / s["input_tok"] * 100 if s["input_tok"] > 0 else 0
        remaining = s["input_tok"] - first_input
        remaining_per_turn = remaining / max(len(assistant_msgs) - 1, 1) if len(assistant_msgs) > 1 else 0

        bar = "█" * min(int(overhead_pct / 2), 30)
        print(f"  {s['project']:20s} {s['model']:22s} {fmt_tok(s['input_tok']):>10s} {fmt_tok(first_input):>10s} {overhead_pct:>6.1f}%  {fmt_cost(s['cost_total']):>10s}  {bar}")
        if len(assistant_msgs) > 1:
            print(f"  {'':20s} {'':22s} {'':10s} {'→ subsequent turns':>16s} {fmt_tok(remaining_per_turn):>10s}/turn avg")

    # Sessions where first turn is >50% of total input
    if origin_filter:
        cursor.execute("""
            SELECT s.id, s.origin, s.project, s.model, s.msg_count, s.input_tok, s.cost_total
            FROM sessions s
            WHERE s.origin = ? AND s.cost_total > 0.5 AND s.msg_count > 3
            ORDER BY s.cost_total DESC
        """, (origin_filter,))
    else:
        cursor.execute("""
            SELECT s.id, s.origin, s.project, s.model, s.msg_count, s.input_tok, s.cost_total
            FROM sessions s
            WHERE s.cost_total > 0.5 AND s.msg_count > 3
            ORDER BY s.cost_total DESC
        """)
    print("\n  Sessions where first turn may dominate (check for oversized context files):")
    count = 0
    for s_raw in cursor.fetchall():
        if count >= 8:
            break
        s = dict(s_raw)
        msgs = load_messages_for_session(conn, s["id"], s["origin"])
        assistant_msgs = [m for m in msgs if m["role"] == "assistant"]
        if not assistant_msgs or len(assistant_msgs) < 3:
            continue
        first_input = assistant_msgs[0]["input_tok"]
        if first_input > s["input_tok"] * 0.4:
            print(f"  🔴 {s['project']:20s} {s['model']:22s} {fmt_tok(first_input):>10s} first turn  ({pct(first_input, s['input_tok'])} of {fmt_tok(s['input_tok'])} total)")
            count += 1
    if count == 0:
        print("  ✅ No sessions with excessive first-turn overhead found")


def estimate_savings(conn: sqlite3.Connection, origin_filter: str | None = None):
    """Estimate potential savings from optimizations."""
    cursor = conn.cursor()

    where = "WHERE origin = ?" if origin_filter else ""
    params = (origin_filter,) if origin_filter else ()

    print(f"\n{'='*72}")
    print(" POTENTIAL SAVINGS ESTIMATES")
    print(f"{'='*72}")

    # Total cost
    cursor.execute(f"SELECT COALESCE(SUM(cost_total),0) FROM sessions {where}", params if origin_filter else ())
    total_cost = cursor.fetchone()[0]

    # Cache improvement: if we could get to 90% cache hit (typical max)
    cursor.execute(f"""
        SELECT COALESCE(SUM(input_tok),0), COALESCE(SUM(cache_read),0)
        FROM sessions {where}
    """, params if origin_filter else ())
    total_input, total_cache = cursor.fetchone()
    current_cache_pct = total_cache / (total_input + total_cache) * 100 if (total_input + total_cache) > 0 else 0

    # What if we could get 10% more cache hits?
    # That means 10% fewer fresh input tokens
    # Each fresh input token costs price_per_token, cached costs half (roughly)
    improved_cache_input = total_input * (1 - (0.9 - current_cache_pct/100))
    if improved_cache_input < total_input:
        saved_input = total_input - improved_cache_input
        # Rough $ estimate: assume avg $5/M input
        cache_saving_est = saved_input / 1_000_000 * 5
    else:
        cache_saving_est = 0

    # Output reduction: assuming we could reduce output by 20%
    cursor.execute(f"SELECT COALESCE(SUM(output_tok),0) FROM sessions {where}", params if origin_filter else ())
    total_output = cursor.fetchone()[0]
    cursor.execute(f"SELECT COALESCE(SUM(cost_total),0) FROM sessions {where}", params if origin_filter else ())
    # Output savings estimate
    output_saving_est = total_cost * 0.15  # rough: 15% of cost is output we could trim

    # Compaction savings: each compaction saves roughly 50% of tokens before it
    cursor.execute(f"""
        SELECT COALESCE(SUM(c.tokens_before),0) as saved
        FROM compactions c
        JOIN sessions s ON c.session_id = s.id
        {where.replace('WHERE', 'WHERE s.') if origin_filter else ''}
    """, params if origin_filter else ())
    compaction_saved = cursor.fetchone()[0]
    compaction_saving_est = compaction_saved / 1_000_000 * 3  # rough: $3/M saved

    print(f"\n  {'─'*60}")
    print(f"  Current total cost:     {fmt_cost(total_cost):>10s}")
    print(f"  Current cache rate:    {current_cache_pct:>5.1f}%")
    print(f"  {'─'*60}")
    print("  POTENTIAL SAVINGS:")
    if cache_saving_est > 0:
        print(f"  Improve cache rate by 10%:      {fmt_cost(cache_saving_est):>10s}/yr est.")
    print(f"  Reduce output verbosity (15%):  {fmt_cost(output_saving_est):>10s}")
    if compaction_saving_est > 0:
        print(f"  Improve compaction:             {fmt_cost(compaction_saving_est):>10s} already saved")
    print(f"  {'─'*60}")

    # If using gpt-5.5, what would switching to deepseek save?
    cursor.execute(f"""
        SELECT COALESCE(SUM(cost_total),0) FROM sessions {where} AND model LIKE '%gpt-5.5%'
    """, params if origin_filter else ())
    gpt55_cost = cursor.fetchone()[0]
    if gpt55_cost > 0:
        # DeepSeek v4 pro is ~30x cheaper for input, ~30x for output
        deepseek_equivalent = gpt55_cost / 30
        print("\n  Model swap savings (gpt-5.5 → deepseek-v4-pro):")
        print(f"    Current gpt-5.5 cost:     {fmt_cost(gpt55_cost):>10s}")
        print(f"    Est. deepseek cost:       {fmt_cost(deepseek_equivalent):>10s}")
        print(f"    Potential saving:         {fmt_cost(gpt55_cost - deepseek_equivalent):>10s}")

    return {
        "total_cost": total_cost,
        "cache_pct": current_cache_pct,
        "cache_saving_est": cache_saving_est,
        "output_saving_est": output_saving_est,
    }


def deep_dive_session(conn: sqlite3.Connection, session_id_prefix: str, origin: str | None = None):
    """Deep dive into a specific session."""
    cursor = conn.cursor()

    # Find the session
    if origin:
        cursor.execute("SELECT * FROM sessions WHERE id LIKE ? AND origin = ?", (f"%{session_id_prefix}%", origin))
    else:
        cursor.execute("SELECT * FROM sessions WHERE id LIKE ?", (f"%{session_id_prefix}%",))
    session = cursor.fetchone()
    if not session:
        print(f"Session not found: {session_id_prefix}")
        return

    s = dict(session)
    print(f"\n{'='*72}")
    print(f" DEEP DIVE: {s['project']} / {s['model']} / {s['id'][:20]}")
    print(f"{'='*72}")
    print(f"  Origin:     {s['origin']}")
    print(f"  Project:    {s['project']}")
    print(f"  Model:      {s['model']}")
    print(f"  Date:       {(s['first_ts'] or '')[:10]} → {(s['last_ts'] or '')[:10]}")
    print(f"  Messages:   {s['msg_count']}")
    print(f"  Cost:       {fmt_cost(s['cost_total'])}")
    print(f"  Compactions: {s['compactions']}")
    print(f"  Name:       {s['session_name'] or '—'}")

    print("\n  TOKEN BREAKDOWN:")
    total = s["input_tok"] + s["output_tok"] + s["cache_read"] + s["cache_write"]
    print(f"    Input:      {fmt_tok(s['input_tok']):>10s}  ({pct(s['input_tok'], total)} of total)")
    print(f"    Output:     {fmt_tok(s['output_tok']):>10s}  ({pct(s['output_tok'], total)} of total)")
    print(f"    Cache read: {fmt_tok(s['cache_read']):>10s}  ({pct(s['cache_read'], total)} of total)")
    print(f"    Cache write:{fmt_tok(s['cache_write']):>10s}  ({pct(s['cache_write'], total)} of total)")
    print("    ──────────────────────────")
    print(f"    Total:      {fmt_tok(total):>10s}")
    print(f"    Cache rate: {s['cache_read']/(s['input_tok']+s['cache_read'])*100:.1f}%" if (s['input_tok']+s['cache_read'])>0 else "    Cache rate: N/A")
    print(f"    In/Out ratio: {s['input_tok']/max(s['output_tok'],1):.1f}:1")

    # Per-turn breakdown
    msgs = load_messages_for_session(conn, s["id"], s["origin"])
    assistant_msgs = [m for m in msgs if m["role"] == "assistant"]
    tool_msgs = [m for m in msgs if m["role"] == "toolResult"]

    if assistant_msgs:
        print("\n  CONTEXT GROWTH OVER TURNS:")
        print(f"  {'Turn':>5s} {'Input':>10s} {'Output':>10s} {'Cache':>10s} {'Cache%':>7s} {'Running':>10s} {'Model':>20s}")
        print(f"  {'─'*76}")
        running_input = 0
        running_cache = 0
        for i, m in enumerate(assistant_msgs[:20]):  # first 20 turns
            running_input += m["input_tok"]
            running_cache += m["cache_read"]
            cache_pct = m["cache_read"] / (m["input_tok"] + m["cache_read"]) * 100 if (m["input_tok"] + m["cache_read"]) > 0 else 0
            print(f"  {i+1:>5d} {fmt_tok(m['input_tok']):>10s} {fmt_tok(m['output_tok']):>10s} {fmt_tok(m['cache_read']):>10s} {cache_pct:>5.1f}%  {fmt_tok(running_input):>10s} {m['model']:>20s}")
        if len(assistant_msgs) > 20:
            remaining_turns = assistant_msgs[20:]
            rest_input = sum(m["input_tok"] for m in remaining_turns)
            rest_cache = sum(m["cache_read"] for m in remaining_turns)
            rest_output = sum(m["output_tok"] for m in remaining_turns)
            cache_pct = rest_cache / (rest_input + rest_cache) * 100 if (rest_input + rest_cache) > 0 else 0
            print(f"  {'...':>5s} {fmt_tok(rest_input):>10s} {fmt_tok(rest_output):>10s} {fmt_tok(rest_cache):>10s} {cache_pct:>5.1f}%  ({len(remaining_turns)} more turns)")

    if tool_msgs:
        tool_counts = defaultdict(int)
        for m in tool_msgs:
            if m["tool_name"]:
                tool_counts[m["tool_name"]] += 1
        print(f"\n  TOOL CALLS ({len(tool_msgs)} total):")
        for name, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
            bar = "█" * min(count // 2, 40)
            print(f"    {name:22s} {count:>4d}  {bar}")


def main():
    args = sys.argv[1:]

    conn = get_db()

    # Check DB exists
    if not os.path.exists(DB_PATH):
        print("❌ Telemetry DB not found. Run pi-telemetry.py scan first.")
        sys.exit(1)

    origin_filter = None
    deep_session = None
    worst_n = 0

    # Parse args
    for i, arg in enumerate(args):
        if arg == "--work-only":
            origin_filter = "work"
        elif arg == "--personal-only":
            origin_filter = "personal"
        elif arg == "--session" and i + 1 < len(args):
            deep_session = args[i + 1]
        elif arg == "--worst" and i + 1 < len(args):
            worst_n = int(args[i + 1])

    # Full analysis
    print(f"\n  π Context Analysis — {'work sessions' if origin_filter == 'work' else 'personal sessions' if origin_filter == 'personal' else 'all sessions'}")

    # 1. Model efficiency comparison
    analyze_by_model(conn, origin_filter)

    # 2. Cache deep dive
    analyze_cache_deep(conn)

    # 3. Context duplication analysis
    analyze_context_duplication(conn, origin_filter)

    # 4. Context growth (expensive sessions deep dive)
    analyze_context_growth_per_turn(conn, origin_filter)

    # 5. Tool call patterns
    analyze_duplication(conn, origin_filter)

    # 6. Savings estimates
    estimate_savings(conn, origin_filter)

    # 7. Deep dive into specific session if requested
    if deep_session:
        deep_dive_session(conn, deep_session, origin_filter)

    # 8. Worst offenders
    if worst_n > 0:
        cursor = conn.cursor()
        where = "WHERE origin = ?" if origin_filter else ""
        params = (origin_filter,) if origin_filter else ()
        cursor.execute(f"""
            SELECT id, origin, project, model, first_ts, msg_count, input_tok, output_tok, cache_read, cost_total
            FROM sessions {where}
            ORDER BY cost_total DESC
            LIMIT {worst_n}
        """, params if origin_filter else ())
        print(f"\n{'='*72}")
        print(f" TOP {worst_n} MOST EXPENSIVE SESSIONS")
        print(f"{'='*72}")
        print(f"  {'Date':12s} {'Origin':9s} {'Project':20s} {'Model':22s} {'Cost':>10s} {'Input':>10s}")
        print(f"  {'─'*85}")
        for r in cursor.fetchall():
            date = (r["first_ts"] or "")[:10] if r["first_ts"] else "—"
            print(f"  {date:12s} {r['origin']:9s} {r['project']:20s} {r['model']:22s} {fmt_cost(r['cost_total']):>10s} {fmt_tok(r['input_tok']):>10s}")

    conn.close()


if __name__ == "__main__":
    main()

    print(f"\n{'='*72}")
    print(" KEY TAKEAWAYS & ACTIONS")
    print(f"{'='*72}")
    print("""
  🎯 To reduce costs:

  1. Switch expensive models: gpt-5.5 costs ~30x more than deepseek-v4-pro
     and ~100x more than deepseek-v4-flash for most tasks.

  2. Improve cache hits: keep conversations focused — context changes between
     turns kill cache. Starting fresh sessions for unrelated tasks helps.

  3. Trim system prompt: AGENTS.md and skills add to every first turn.
     Check if you have oversized context files loading on every session.

  4. Reduce tool call volume: consecutive same-tool calls (bash, read) suggest
     the agent is iterating inefficiently. Tighter prompting helps.

  5. Compact more aggressively: manual /compact when sessions get long.
     Each compaction saves ~50% of context tokens.

  6. Use faster models for simple tasks: deepseek-v4-flash is 50x cheaper
     than gpt-5.5 and handles most coding tasks well.
""")
