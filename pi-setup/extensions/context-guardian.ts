/**
 * Context Guardian Extension
 *
 * Monitors context growth, cache effectiveness, tool call patterns, and
 * system prompt overhead turn-by-turn to prevent expensive sessions.
 *
 * Key behaviors:
 *   1. Auto-compacts when context exceeds 60% of model's window (≥10k tokens)
 *      NOTE: pi's getContextUsage() returns percent as 0-100, not 0-1 — ratio is divided by 100
 *   2. Compresses old tool results (> 2k chars) via context event (bash + read)
 *   3. Warns when cache hit rate drops below 70% for 3+ consecutive turns
 *   4. Warns on excessive consecutive same-tool calls (15+)
 *   5. Checks skills/AGENTS.md size at session start and warns if bloated
 *   6. /context-guardian command for session + skills metrics
 *   7. Persistent footer status showing cache%, cost, turn count
 *
 * Safeguards against retry loops:
 *   - Skips compaction when session < 10k tokens (pi rejects "Nothing to compact")
 *   - 5min cooldown between compaction attempts
 *   - Detects "too small" errors and permanently disables auto-compact for the session
 *   - Uses ctx.getContextUsage() instead of ctx.model?.contextWindow for reliability
 *
 * RTK (github.com/rtk-ai/rtk) can also handle bash compression (60-90% savings)
 * via its own mechanism; this extension covers both read tool results and bash,
 * cache monitoring, skills overhead, and auto-compaction.
 *
 * Install: symlink from pi-setup/extensions/context-guardian.ts
 *   → ~/.pi/agent/extensions/
 *   → ~/.pi/agent-work/extensions/
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

// ─── Configuration ───────────────────────────────────────────────────────────

const CONFIG = {
  /** Compact when context exceeds this ratio of the model's context window */
  contextThresholdRatio: 0.6,

  /** Minimum context tokens before compaction is attempted */
  minCompactTokens: 10_000,

  /** Cooldown between compaction attempts (ms) */
  compactCooldown: 300_000,

  /** Warn after N consecutive turns with cache rate below this threshold */
  cacheRateWarningThreshold: 0.7,
  cacheRateConsecutiveTurns: 3,

  /** Warn after this many consecutive same-tool calls */
  sameToolWarningThreshold: 15,

  /** Automatically compact on high context? */
  autoCompactOnHighContext: true,

  /** Compact automatically when cache rate drops? */
  autoCompactOnCacheDrop: false,

  /** Compress old tool results in the context event? */
  compressToolResults: true,

  /** Max chars for old tool result text before compression */
  toolResultMaxChars: 2_000,

  /** Number of recent tool results to keep intact (from newest) */
  keepRecentToolResults: 3,

  /** Warn if total skill file chars exceeds this (~token estimate) */
  skillsWarnThresholdChars: 40_000,

  /** Minimum interval between repeated notifications (ms) */
  notifyCooldown: 60_000,

  /** Fallback context window in tokens when pi cannot determine the active model's window. */
  modelContextWindow: 200_000,

  /** Assumed cost per 1M input tokens for overhead estimates */
  costPerInputMTok: 15,
};

// ─── Types ───────────────────────────────────────────────────────────────────

interface ToolMetrics {
  cost: number;
  input: number;
  output: number;
  cacheRead: number;
  turns: number;
  totalMsgs: number;
  lowCacheTurns: number;
  compactions: number;
  warnings: number;
  compressedResults: number;
  totalToolChars: number;
}

// ─── Extension ───────────────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
  // ── State ────────────────────────────────────────────────────────────────

  let consecutiveLowCache = 0;
  let prevToolName = "";
  let sameToolStreak = 0;
  let compactInFlight = false;
  let lastCompactAttempt = 0;
  let compactFailedDueToSize = false;
  let sessionStartTs = 0;
  let sessionMetrics: ToolMetrics = resetMetrics();
  let isWorkSession = false;
  let knownSkillsSize = 0;
  let skillsScanned = false;

  // ULTRA gate: dedup identical commands
  const commandCache = new Map<string, string>();

  function resetMetrics(): ToolMetrics {
    return {
      cost: 0,
      input: 0,
      output: 0,
      cacheRead: 0,
      turns: 0,
      totalMsgs: 0,
      lowCacheTurns: 0,
      compactions: 0,
      warnings: 0,
      compressedResults: 0,
      totalToolChars: 0,
    };
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  const lastNotify: Record<string, number> = {};

  function shouldNotify(key: string): boolean {
    const now = Date.now();
    if (now - (lastNotify[key] ?? 0) < CONFIG.notifyCooldown) return false;
    lastNotify[key] = now;
    return true;
  }

  function notify(
    ctx: { ui: { notify: (msg: string, level: "info" | "warning" | "error") => void } },
    key: string,
    msg: string,
    level: "info" | "warning" | "error" = "info",
  ) {
    if (!shouldNotify(key)) return;
    try {
      ctx.ui.notify(msg, level);
    } catch {
      /* extension may not have full UI in all modes */
    }
  }

  function fmtCost(n: number): string {
    if (!n || n < 0.001) return "$0";
    if (n < 0.01) return `${(n * 100).toFixed(1)}¢`;
    return `$${n.toFixed(2)}`;
  }

  function fmtNum(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
    return String(n);
  }

  function fmtDuration(ms: number): string {
    const min = ms / 60000;
    if (min < 60) return `${min.toFixed(0)}m`;
    return `${(min / 60).toFixed(1)}h`;
  }

  function estimateTokens(text: string): number {
    return Math.round(text.length / 3.5);
  }

  function updateFooter(ctx: { ui: { setStatus: (id: string, text: string) => void } }) {
    const m = sessionMetrics;
    const totalForCache = m.input + m.cacheRead;
    const cachePct = totalForCache > 0 ? ((m.cacheRead / totalForCache) * 100).toFixed(0) : "—";
    const label = [`🛡️ ${cachePct}%`, fmtCost(m.cost), `${m.turns}t`];
    if (m.compactions > 0) label.push(`cmp:${m.compactions}`);
    if (m.compressedResults > 0) label.push(`zip:${m.compressedResults}`);
    if (consecutiveLowCache >= CONFIG.cacheRateConsecutiveTurns) label.push("⚠️");
    try {
      ctx.ui.setStatus("context-guard", label.join(" | "));
    } catch {
      /* safe to ignore */
    }
  }

  // ── Skills overhead scan ─────────────────────────────────────────────────

  function scanSkillsSize(): number {
    if (skillsScanned) return knownSkillsSize;
    skillsScanned = true;
    try {
      const home = homedir();
      // Check common skill locations
      const dirs = [
        join(home, ".pi", "agent", "skills"),
        join(home, ".pi", "agent-work", "skills"),
      ];
      let total = 0;
      for (const dir of dirs) {
        try {
          total += scanDirRecursive(dir);
        } catch {
          /* dir not found */
        }
      }
      // Also scan AGENTS.md files
      const agentsPaths = [
        join(home, ".pi", "AGENTS.md"),
        join(home, ".pi", "agent-work", "AGENTS.md"),
      ];
      for (const p of agentsPaths) {
        try {
          const stats = statSync(p);
          total += stats.size;
        } catch {
          /* file not found */
        }
      }
      knownSkillsSize = total;
      return total;
    } catch {
      return 0;
    }
  }

  function scanDirRecursive(dir: string): number {
    let total = 0;
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const full = join(dir, entry.name);
      try {
        if (entry.isDirectory()) {
          total += scanDirRecursive(full);
        } else if (entry.isFile() && (entry.name.endsWith(".md") || entry.name.endsWith(".sh") || entry.name.endsWith(".txt"))) {
          const stats = statSync(full);
          total += stats.size;
        }
      } catch {
        /* skip unreadable */
      }
    }
    return total;
  }

  // ── Tool result compression ──────────────────────────────────────────────

  function getTailLines(text: string, n: number): string {
    const lines = text.split("\n");
    if (lines.length <= n + 3) return text;
    const head = lines.slice(0, n).join("\n");
    const tail = lines.slice(-n).join("\n");
    return `${head}\n... [${lines.length - 2 * n} lines omitted] ...\n${tail}`;
  }

  function compressText(
    text: string,
    toolName: string,
    isError: boolean,
    command?: string,
  ): { text: string; compressed: boolean } {
    const maxChars = CONFIG.toolResultMaxChars;
    const estTok = estimateTokens(text);

    // FULL gate: preserve all signal on errors
    if (isError) {
      return { text: `[⚠️ ERROR - full signal preserved]\n${text}`, compressed: false };
    }

    // ULTRA gate: identical repeat → collapse
    if (command) {
      const sig = `${command}::${text.length}::${text.slice(0, 100)}`;
      const prev = commandCache.get(sig);
      if (prev) {
        if (prev === text) {
          return { text: `[🔄 ULTRA - repeat of previous identical command - ${fmtNum(text.length)} chars]`, compressed: true };
        }
      } else {
        commandCache.set(sig, text);
        // Limit cache size
        if (commandCache.size > 100) {
          const firstKey = commandCache.keys().next().value;
          if (firstKey !== undefined) commandCache.delete(firstKey);
        }
      }
    }

    if (text.length <= maxChars) return { text, compressed: false };

    // STANDARD compression
    const estLines = text.split("\n").length;
    const headChars = Math.min(500, Math.floor(maxChars * 0.4));
    const tailChars = maxChars - headChars - 100; // 100 for overhead

    const compressed = `[Output compressed: ${fmtNum(text.length)} chars, ${fmtNum(estLines)} lines, ~${estTok} tok]` +
      `\n─── first ${fmtNum(headChars)} chars ───` +
      `\n${text.slice(0, headChars)}` +
      `\n─── last ${fmtNum(tailChars)} chars ───` +
      `\n${text.slice(-tailChars)}`;

    return { text: compressed, compressed: true };
  }

  // ── Session start ────────────────────────────────────────────────────────

  pi.on("session_start", async (_event, ctx) => {
    sessionMetrics = resetMetrics();
    consecutiveLowCache = 0;
    prevToolName = "";
    sameToolStreak = 0;
    compactInFlight = false;
    sessionStartTs = Date.now();
    commandCache.clear();

    // Detect work session from file path
    try {
      const sf = ctx.sessionManager.getSessionFile() ?? "";
      isWorkSession = sf.includes("agent-work");
    } catch {
      isWorkSession = false;
    }

    // Check skills overhead (lazy — only once)
    const skillsSize = scanSkillsSize();
    const skillsTok = estimateTokens(skillsSize);

    if (skillsSize > CONFIG.skillsWarnThresholdChars) {
      // getContextUsage may not be available at session_start depending on extension lifecycle
      const ctxUsage = typeof ctx.getContextUsage === "function" ? ctx.getContextUsage() : undefined;
      const contextWindow = ctxUsage?.contextWindow ?? CONFIG.modelContextWindow;
      const pct = ((skillsTok / contextWindow) * 100).toFixed(0);
      const costPer = (skillsTok / 1_000_000) * CONFIG.costPerInputMTok;
      notify(
        ctx,
        "skills-bloat",
        `Skills/AGENTS.md load: ~${fmtNum(skillsTok)} tok (${pct}% of ${fmtNum(contextWindow)}, ~$${costPer.toFixed(2)}/first turn). Trim unused skills to recover context.`,
        "warning",
      );
    }

    updateFooter(ctx);
    try {
      ctx.ui.setStatus(
        "context-guard",
        isWorkSession ? "🛡️ Guardian active (work)" : "🛡️ Guardian active",
      );
    } catch {
      /* ignore */
    }
  });

  // ── Context event: compress old tool results before LLM sees them ────────

  pi.on("context", async (event, ctx) => {
    if (!CONFIG.compressToolResults) return;

    const messages = event.messages;
    if (!messages || messages.length < 3) return;

    let compressed = 0;

    // Walk from newest to oldest to find recent tool results
    let toolResultCount = 0;

    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i] as any;

      // Track the last N tool results
      if (msg.role === "toolResult" || msg.role === "bashExecution") {
        toolResultCount++;
        if (toolResultCount <= CONFIG.keepRecentToolResults) continue;
      }

      // Compress tool result text content
      if (msg.role === "toolResult") {
        const content = msg.content as Array<any> | undefined;
        if (!content || !Array.isArray(content)) continue;

        const isError = msg.isError === true;
        let modified = false;

        for (let j = 0; j < content.length; j++) {
          const block = content[j];
          if (!block || block.type !== "text" || !block.text) continue;

          const result = compressText(block.text, msg.toolName || "tool", isError);
          if (result.compressed) {
            block.text = result.text;
            sessionMetrics.compressedResults++;
            compressed++;
            modified = true;
          }
        }

        if (modified) sessionMetrics.totalToolChars +=
          content.reduce((acc: number, c: any) => acc + (c.text?.length || 0), 0);
      }

      // Compress bash execution output
      if (msg.role === "bashExecution") {
        const output = msg.output as string | undefined;
        if (!output || typeof output !== "string") continue;

        const isError = msg.exitCode !== 0 && msg.exitCode !== undefined;
        const result = compressText(output, "bash", isError, msg.command);

        if (result.compressed) {
          msg.output = result.text;
          sessionMetrics.compressedResults++;
          compressed++;
        }
      }
    }

    if (compressed > 0) {
      updateFooter(ctx);
      return { messages };
    }
  });

  // ── Turn-end analysis ────────────────────────────────────────────────────

  pi.on("turn_end", async (event, ctx) => {
    const m = sessionMetrics;
    const now = Date.now();
    m.turns++;

    // ── 1. Context usage check ──────────────────────────────────────────
    const usage = ctx.getContextUsage();
    if (usage?.tokens && usage?.contextWindow) {
      const maxT = usage.contextWindow;
      // NOTE: pi's getContextUsage() returns percent as 0-100, not 0-1
      // Convert to decimal ratio for correct comparison with threshold.
      const ratio = usage.percent != null ? usage.percent / 100 : usage.tokens / maxT;

      const shouldAttemptCompact =
        ratio > CONFIG.contextThresholdRatio &&
        CONFIG.autoCompactOnHighContext &&
        !compactInFlight &&
        !compactFailedDueToSize &&
        usage.tokens >= CONFIG.minCompactTokens &&
        now - lastCompactAttempt > CONFIG.compactCooldown;

      if (shouldAttemptCompact) {
        notify(
          ctx,
          "high-context",
          `Context at ${(ratio * 100).toFixed(0)}% (${fmtNum(usage.tokens)}/${fmtNum(maxT)}). Auto-compacting…`,
          "warning",
        );
        compactInFlight = true;
        lastCompactAttempt = now;

        ctx.compact({
          customInstructions: `The conversation context is large (${fmtNum(usage.tokens)} tokens). Create a structured summary following this format:

## Goal
## Constraints & Preferences
## Progress
### Done
### In Progress
### Blocked
## Key Decisions
## Next Steps
## Critical Context
- Files read: <list>
- Files modified: <list>

Keep it dense enough to continue work without losing context on decisions, file changes, or next steps.`,
          onComplete: () => {
            m.compactions++;
            compactInFlight = false;
            compactFailedDueToSize = false;
            notify(ctx, "compact-done", "Context compacted. Cache reuse should improve.", "info");
          },
          onError: (err) => {
            compactInFlight = false;
            // Mark session-too-small to stop retrying
            if (err.message?.includes?.("Nothing to compact") || err.message?.includes?.("too small")) {
              compactFailedDueToSize = true;
            }
            notify(ctx, "compact-error", `Compaction failed: ${err.message}`, "error");
          },
        });
        updateFooter(ctx);
      }
    }

    // ── 2. Cache rate analysis ──────────────────────────────────────────
    const msg = (event as any).message;
    if (msg?.usage?.cacheRead !== undefined && msg?.usage?.input !== undefined) {
      const totalWithCache = msg.usage.input + msg.usage.cacheRead;
      const cacheRate = totalWithCache > 0 ? msg.usage.cacheRead / totalWithCache : 0;

      // Accumulate totals
      m.cost += msg.usage.cost?.total ?? 0;
      m.input += msg.usage.input;
      m.output += msg.usage.output ?? 0;
      m.cacheRead += msg.usage.cacheRead;
      m.totalMsgs++;

      if (cacheRate < CONFIG.cacheRateWarningThreshold) {
        consecutiveLowCache++;
        m.lowCacheTurns++;
      } else {
        // Reset on any good cache turn
        if (consecutiveLowCache >= CONFIG.cacheRateConsecutiveTurns) {
          notify(ctx, "cache-recovered", "Cache rate recovered. Good focus! ✅", "info");
        }
        consecutiveLowCache = 0;
      }

      if (consecutiveLowCache >= CONFIG.cacheRateConsecutiveTurns && consecutiveLowCache % 3 === 0) {
        const isFirst = consecutiveLowCache === CONFIG.cacheRateConsecutiveTurns;
        notify(
          ctx,
          "low-cache",
          `Cache rate ${(cacheRate * 100).toFixed(0)}% for ${consecutiveLowCache} turns. ` +
            (isFirst
              ? "Starting a fresh session (/fork) would cut cost 2-3x."
              : "Context is changing too much between turns — try keeping conversations focused."),
          "warning",
        );
        m.warnings++;

        const ctxUsage = ctx.getContextUsage();
        if (CONFIG.autoCompactOnCacheDrop && !compactInFlight && !compactFailedDueToSize && ctxUsage.tokens >= CONFIG.minCompactTokens && now - lastCompactAttempt > CONFIG.compactCooldown) {
          compactInFlight = true;
          lastCompactAttempt = now;
          ctx.compact({
            customInstructions: `Cache efficiency is poor (${(cacheRate * 100).toFixed(0)}%). Create a dense summary of all decisions, file changes, blockers, and next steps so work can continue with fresh cache benefits.`,
            onComplete: () => {
              m.compactions++;
              compactInFlight = false;
              compactFailedDueToSize = false;
            },
            onError: () => {
              compactInFlight = false;
              compactFailedDueToSize = true;
            },
          });
        }
      }
    }

    // ── 3. Tool call pattern analysis ───────────────────────────────────
    const toolResults: Array<{ toolName: string }> = (event as any).toolResults ?? [];
    for (const tr of toolResults) {
      const name = tr.toolName;
      if (name === prevToolName) {
        sameToolStreak++;
      } else {
        if (sameToolStreak >= CONFIG.sameToolWarningThreshold) {
          notify(
            ctx,
            "same-tool",
            `${sameToolStreak} consecutive "${prevToolName}" calls. Consider consolidating to reduce context bloat.`,
            "warning",
          );
          m.warnings++;
        }
        sameToolStreak = 1;
        prevToolName = name;
      }
    }

    updateFooter(ctx);
  });

  // ── /context-guardian command ─────────────────────────────────────────────

  pi.registerCommand("context-guardian", {
    description: "Show session context metrics and guardian activity",
    handler: async (_args, ctx) => {
      const m = sessionMetrics;
      const elapsed = Date.now() - sessionStartTs;
      const totalForCache = m.input + m.cacheRead;
      const cachePct = totalForCache > 0 ? ((m.cacheRead / totalForCache) * 100).toFixed(1) : "—";
      const avgInput = m.turns > 0 ? fmtNum(m.input / m.turns) : "—";
      const avgOutput = m.turns > 0 ? fmtNum(Math.round(m.output / m.turns)) : "—";

      // Skills stats
      const skillsSize = scanSkillsSize();
      const skillsTok = estimateTokens(skillsSize);
      const ctxUsage = typeof ctx.getContextUsage === "function" ? ctx.getContextUsage() : undefined;
      const contextWindow = ctxUsage?.contextWindow ?? CONFIG.modelContextWindow;
      const skillsPct = ((skillsTok / contextWindow) * 100).toFixed(0);
      const skillsCost = (skillsTok / 1_000_000) * CONFIG.costPerInputMTok;

      const lines: string[] = [
        `╔═══════════════════════════════════════════════╗`,
        `║         Context Guardian Report               ║`,
        `╠═══════════════════════════════════════════════╣`,
        `║ Session:  ${fmtDuration(elapsed).padStart(5)}, ${m.turns.toString().padStart(4)} turns, ${isWorkSession ? "work" : "personal"}        ║`,
        `║                                               ║`,
        `║ Cache rate:       ${cachePct.padStart(5)}%  (${fmtNum(m.cacheRead)}/${fmtNum(totalForCache)})     ║`,
        `║ Total cost:       ${fmtCost(m.cost).padStart(9)}                    ║`,
        `║ Avg input/turn:   ${avgInput.padStart(8)} tok                   ║`,
        `║ Avg output/turn:  ${avgOutput.padStart(8)} tok                   ║`,
        `║                                               ║`,
        `║ Low-cache turns:  ${m.lowCacheTurns.toString().padStart(4)} / ${m.turns.toString().padStart(4)}                ║`,
        `║ Compactions:      ${m.compactions.toString().padStart(4)}                       ║`,
        `║ Results compressed: ${m.compressedResults.toString().padStart(4)}                    ║`,
        `║ Warnings issued:  ${m.warnings.toString().padStart(4)}                       ║`,
        `║                                               ║`,
        `║ ── System Prompt Overhead ──                  ║`,
        `║ Skills/AGENTS.md: ${fmtNum(skillsTok).padStart(7)} tok  (${skillsPct}% of ${fmtNum(contextWindow).padStart(6)})        ║`,
        `║ Skill cost/turn:  ~$${skillsCost.toFixed(3)}                              ║`,
        `╚═══════════════════════════════════════════════╝`,
      ];

      ctx.ui.notify(lines.join("\n"), "info");
    },
  });
}
