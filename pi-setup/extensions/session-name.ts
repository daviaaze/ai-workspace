/**
 * Auto-Session-Name Extension
 *
 * Automatically names sessions from the first prompt for easy findability
 * in /resume and /session. Skips if a name is already set.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  pi.on("before_agent_start", async (event) => {
    if (pi.getSessionName()) return;

    // Extract first meaningful line — strip common prefixes, truncate
    let prompt = event.prompt.trim();

    // Remove leading /skill:, /template, /command prefixes
    prompt = prompt.replace(/^\/[\w.:-]+\s*/, "");

    // Take first line only
    const firstLine = prompt.split("\n")[0].trim();
    if (!firstLine) return;

    // Truncate to ~50 chars, break at word boundary
    const name = firstLine.length > 50
      ? (firstLine.substring(0, 47).split(" ").slice(0, -1).join(" ") || firstLine.substring(0, 47)) + "..."
      : firstLine;

    pi.setSessionName(name);
  });
}
