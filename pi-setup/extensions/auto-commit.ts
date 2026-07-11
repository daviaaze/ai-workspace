/**
 * Auto-Commit-on-Exit Extension
 *
 * Commits workspace changes when a named PI session ends.
 * Only fires when the session has a name (explicitly set, not timestamp-generated).
 * Only stages tracked files — skips untracked. Never pushes.
 * Uses --no-verify to skip hooks (agent changes already approved during session).
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.on("session_shutdown", async (_event, ctx) => {
    try {
      // Only auto-commit named sessions (intentional work, not random prompts)
      const sessionName = pi.getSessionName();
      if (!sessionName) return;

      // Check if we're in a git repo
      try {
        await pi.exec("git", ["rev-parse", "--git-dir"]);
      } catch {
        return; // Not a git repo
      }

      // Check for uncommitted changes to tracked files
      const { stdout } = await pi.exec("git", ["status", "--porcelain"]);
      if (!stdout.trim()) return; // Clean tree

      const msg = `chore(auto): ${sessionName}`;

      // Stage tracked files only (no untracked — avoids committing secrets, build artifacts)
      await pi.exec("git", ["add", "-u"]);
      await pi.exec("git", ["commit", "-m", msg, "--no-verify"]);
    } catch (err) {
      console.error("[auto-commit] Failed:", err);
      // Never let this crash PI shutdown
    }
  });
}
