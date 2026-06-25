/**
 * Auto-Commit-on-Exit Extension
 *
 * Automatically commits all changes when a PI session ends.
 * Only commits — never pushes. Uses --no-verify to skip hooks
 * (the agent's changes are already approved by you during the session).
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.on("session_shutdown", async (_event) => {
    // Check if we're in a git repo
    try {
      await pi.exec("git", ["rev-parse", "--git-dir"]);
    } catch {
      return; // Not a git repo
    }

    // Check for uncommitted changes
    const { stdout } = await pi.exec("git", ["status", "--porcelain"]);
    if (!stdout.trim()) return; // Clean tree

    // Build a descriptive commit message
    const sessionName = pi.getSessionName();
    const timestamp = new Date().toISOString().replace("T", " ").substring(0, 19);
    const msg = sessionName
      ? `chore(auto): ${sessionName}`
      : `chore(auto): snapshot at ${timestamp}`;

    // Stage everything and commit
    await pi.exec("git", ["add", "-A"]);
    await pi.exec("git", ["commit", "-m", msg, "--no-verify"]);

    console.log(`[auto-commit] Committed: ${msg}`);
  });
}
