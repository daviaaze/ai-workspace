/**
 * Git Checkpoint Extension
 *
 * Creates git stash checkpoints at each turn so /fork can restore code state.
 * When forking, offers to restore code to that point in history.
 *
 * Based on the PI example extension with added safety and debouncing.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

async function safeExec(pi: ExtensionAPI, cmd: string, args: string[]): Promise<string | null> {
  try {
    const { stdout } = await pi.exec(cmd, args);
    return stdout;
  } catch {
    return null;
  }
}

export default function (pi: ExtensionAPI) {
  const checkpoints = new Map<string, string>();
  let currentEntryId: string | undefined;

  // Track the current entry ID when user messages are saved
  pi.on("tool_result", async (_event, ctx) => {
    try {
      const leaf = ctx.sessionManager.getLeafEntry();
      if (leaf) currentEntryId = leaf.id;
    } catch {
      // session manager not available yet
    }
  });

  pi.on("turn_start", async () => {
    try {
      // Skip if working tree is clean (no changes to stash)
      const statusOut = await safeExec(pi, "git", ["status", "--porcelain"]);
      if (!statusOut?.trim()) return;

      // Create a git stash entry before LLM makes changes
      const stdout = await safeExec(pi, "git", ["stash", "create"]);
      const ref = stdout?.trim();
      if (ref && currentEntryId) {
        checkpoints.set(currentEntryId, ref);
      }
    } catch {
      // git checkpoint failed silently — not worth crashing a turn
    }
  });

  pi.on("session_before_fork", async (event, ctx) => {
    try {
      const ref = checkpoints.get(event.entryId);
      if (!ref) return;

      if (!ctx.hasUI) return;

      const choice = await ctx.ui.select("Restore code state?", [
        "Yes, restore code to that point",
        "No, keep current code",
      ]);

      if (choice?.startsWith("Yes")) {
        await pi.exec("git", ["stash", "apply", ref]);
        ctx.ui.notify("Code restored to checkpoint", "info");
      }
    } catch {
      // fork restoration failed — let the fork proceed without restoring
    }
  });

  pi.on("session_shutdown", async () => {
    checkpoints.clear();
  });
}
