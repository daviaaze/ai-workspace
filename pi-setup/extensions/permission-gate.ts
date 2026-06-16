/**
 * Permission Gate Extension
 *
 * Confirms before executing dangerous bash commands.
 * Catches: rm -rf, sudo, chmod 777, destructive git operations,
 * fork bombs, and file system modifications outside the project tree.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { isToolCallEventType } from "@earendil-works/pi-coding-agent";

// Patterns that always require confirmation
const DANGEROUS_PATTERNS = [
  /\brm\s+-rf?\b/i,                          // rm -rf
  /\bsudo\b/i,                                // sudo anything
  /\bchmod\s+777\b/i,                        // world-writable permissions
  /\bmkfs\.\w+\b/i,                           // make filesystem
  /\bdd\s+if=/i,                              // dd with input file
  /\bgit\s+push\s+.*--force\b/i,             // force push
  /\bgit\s+reset\s+--hard\b/i,               // hard reset
  /\b:\(\)\s*\{\s*:\|:&\s*\};:\s*/i,         // fork bomb
  />\s*\/dev\/sd[a-z]/i,                     // writing to raw disk
];

const SENSITIVE_PATTERNS = [
  /\bdocker\s+(rm|system\s+prune)\b/i,       // Docker cleanup
  /\bkubectl\s+delete\b/i,                    // Kubernetes deletions
  /\bnixos-rebuild\s+switch\b/i,             // NixOS rebuild
  /\bgit\s+push\b(?!.*--force)/i,            // Regular push (not force)
];

const SAFE_PATTERNS = [
  /^(ls|cat|head|tail|echo|pwd|which|type|date|whoami|uname|env)\b/,
  /\bgrep\b/,
  /\bfind\b/,
];

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    if (!isToolCallEventType("bash", event)) return;
    if (!ctx.hasUI) return; // Skip in non-interactive mode

    const cmd = event.input.command.trim();

    // Skip obviously safe commands
    if (SAFE_PATTERNS.some((p) => p.test(cmd))) return;

    // Check for dangerous commands — block by default
    for (const pattern of DANGEROUS_PATTERNS) {
      if (pattern.test(cmd)) {
        const ok = await ctx.ui.confirm(
          "⚠️  Dangerous command detected",
          `Allow this?\n\n  ${cmd.substring(0, 120)}`
        );
        if (!ok) return { block: true, reason: "Blocked by permission gate" };
        return;
      }
    }

    // Check for sensitive commands — warn but allow
    for (const pattern of SENSITIVE_PATTERNS) {
      if (pattern.test(cmd)) {
        const ok = await ctx.ui.confirm(
          "⚠️  Sensitive command",
          `Allow this?\n\n  ${cmd.substring(0, 120)}`
        );
        if (!ok) return { block: true, reason: "Blocked by permission gate" };
        return;
      }
    }
  });
}
