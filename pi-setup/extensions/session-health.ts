/**
 * Session Health Monitor Extension
 *
 * Shows session file size in the footer and warns when sessions
 * grow too large. Helps prevent context window issues.
 *
 * Thresholds:
 *   < 1MB   → green (healthy)
 *   1-5MB   → yellow (warning)
 *   > 5MB   → red (compaction recommended)
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { statSync } from "node:fs";

const MB = 1024 * 1024;
const WARN_THRESHOLD = 1 * MB;
const CRIT_THRESHOLD = 5 * MB;

let warned = false;

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < MB) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / MB).toFixed(1)} MB`;
}

async function updateStatus(ctx: { ui: { setStatus: (id: string, text: string) => void } }, sessionFile: string | null) {
  if (!sessionFile) {
    ctx.ui.setStatus("session-size", "");
    return;
  }

  try {
    const stats = statSync(sessionFile);
    const size = formatSize(stats.size);
    const isLarge = stats.size > WARN_THRESHOLD;
    const isCritical = stats.size > CRIT_THRESHOLD;

    let label = `📄 ${size}`;
    if (isCritical) label = `⚠️ ${size}`;
    else if (isLarge) label = `📄 ${size}`;

    ctx.ui.setStatus("session-size", label);
  } catch {
    // session file not readable yet
  }
}

export default function (pi: ExtensionAPI) {
  let sessionFile: string | null = null;

  pi.on("session_start", async (_event, ctx) => {
    sessionFile = ctx.sessionManager.getSessionFile() ?? null;
    await updateStatus(ctx, sessionFile);
    warned = false;
  });

  pi.on("message_end", async (_event, ctx) => {
    if (!sessionFile) return;

    await updateStatus(ctx, sessionFile);

    // Warn if exceeding critical threshold
    try {
      const stats = statSync(sessionFile!);
      if (stats.size > CRIT_THRESHOLD && !warned) {
        warned = true;
        ctx.ui.notify(
          `Session is large (${formatSize(stats.size)}). Consider /compact to reduce context usage.`,
          "warning"
        );
      }
    } catch {
      // session file not readable
    }
  });
}
