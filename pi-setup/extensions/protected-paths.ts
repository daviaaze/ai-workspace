/**
 * Protected Paths Extension
 *
 * Blocks write/edit/bash operations on sensitive files to prevent
 * accidental damage by the AI agent.
 *
 * Protected: .env files, secrets, credentials, SSH keys, .git/config
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { isToolCallEventType } from "@earendil-works/pi-coding-agent";
import { resolve } from "node:path";

const PROTECTED_PATTERNS = [
  /\.env$/i,                     // .env
  /\.env\.[a-z]+$/i,            // .env.production, .env.local
  /\/\.git\/config$/,           // .git/config
  /credentials/i,                // Any file with "credentials" in path
  /\/secrets\//i,                // secrets/ directory
  /secret\.(yml|yaml|json)$/i,  // secret files
  /\.pem$/i,                     // PEM keys
  /id_rsa/,                      // SSH private keys
  /id_ed25519/,                  // SSH Ed25519 keys
  /\.key$/i,                     // Generic key files
  /\/node_modules\//i,           // node_modules (shouldn't be edited)
];

function isProtected(filePath: string): boolean {
  const resolved = resolve(filePath);
  return PROTECTED_PATTERNS.some((p) => p.test(resolved));
}

export default function (pi: ExtensionAPI) {
  pi.on("tool_call", async (event, ctx) => {
    let targetPath: string | undefined;

    // Check write/edit tool calls
    if (isToolCallEventType("write", event)) {
      targetPath = event.input.path;
    } else if (isToolCallEventType("edit", event)) {
      targetPath = event.input.path;
    }

    if (targetPath && isProtected(targetPath)) {
      const msg = `Protected path: ${targetPath}\n\nContinue anyway?`;
      if (!ctx.hasUI) {
        return { block: true, reason: `Blocked write to protected path: ${targetPath}` };
      }
      const ok = await ctx.ui.confirm("⚠️  Protected Path", msg);
      if (!ok) return { block: true, reason: `Blocked write to ${targetPath}` };
      return; // User confirmed — allow
    }

    // Check bash commands for protected path operations
    if (isToolCallEventType("bash", event)) {
      const cmd = event.input.command;

      // Check for redirections/modifications targeting protected paths
      for (const pattern of PROTECTED_PATTERNS) {
        if (pattern.test(cmd)) {
          if (!ctx.hasUI) {
            return { block: true, reason: `Blocked bash command targeting protected path` };
          }
          const ok = await ctx.ui.confirm(
            "⚠️  Protected path in command",
            `This command may modify a protected path:\n\n  ${cmd.substring(0, 120)}\n\nContinue?`
          );
          if (!ok) return { block: true, reason: "Blocked by protected paths gate" };
          return;
        }
      }
    }
  });
}
