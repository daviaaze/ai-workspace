/**
 * Clickable File Paths — pi extension
 *
 * Wraps file paths in pi's/output in OSC 8 terminal hyperlinks.
 * Clicking a path opens Neovim at the right file:line:col.
 *
 * Requires:
 *   - Kitty (or any terminal with OSC 8 hyperlink support)
 *
 * How it works:
 *   - Intercepts assistant messages and wraps file paths in
 *     \x1b]8;;file:///path:line\x1b\\display text\x1b]8;;\x1b\\
 *   - Validates paths exist on disk to avoid false positives
 *   - Only activates in TUI mode (not in -p, --json mode)
 *
 * NOTE: AssistantMessage.content is (TextContent|ThinkingContent|ToolCall)[],
 * not a plain string. This version iterates over content blocks to handle
 * the array format correctly.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { existsSync } from "node:fs";
import { resolve, isAbsolute } from "node:path";

// Common file extensions in programming — avoids false positives
const EXTENSIONS =
  "ts|tsx|js|jsx|mjs|cjs|mts|cts|py|rs|go|rb|java|kt|scala|clj|cljs|edn" +
  "|c|cpp|cxx|cc|h|hpp|hxx|hh" +
  "|css|scss|sass|less|styl" +
  "|json|jsonc|yaml|yml|toml|xml|svg|graphql|gql" +
  "|md|mdx|rst|adoc|tex" +
  "|nix|sh|bash|zsh|fish|lua|vim|vimrc|tcl" +
  "|conf|cfg|ini|env|editorconfig|gitignore" +
  "|vue|svelte|astro|solid" +
  "|sql|prisma|proto|gradle|sbt" +
  "|txt|log|out|err" +
  "|dockerfile|Makefile|cmake";

// Static pattern — matches paths with known extensions and optional :line:col
// Group 1: full path (including extension)
// Group 2: line number (optional)
// Group 3: column number (optional)
//
// Matches:
//   /abs/path/to/file.ts:42
//   src/relative/path.ts:42:10
//   ./local/file.rs
//   ../sibling/file.go:5
//   packages/cli/src/index.ts
//
// Avoids:
//   URLs (https://...) — negative lookbehind
//   Random words — requires at least one / in the path
const PATH_RE = new RegExp(
  "(?<![\\w/#])" +                        // boundary — not preceded by word char, /, or #
  "((?:" +
    "\\/[^\\s:()\"]+[\\w/]" +            // absolute: /path/to/file
    "|" +
    "(?:\\.\\.?\\/)?" +                  // optional ./ or ../
    "[\\w@][\\w.\\-]*" +                 // first path component
    "(?:\\/[\\w.\\-]+)+" +               // more components (at least one /)
  ")" +
  "\\.(?:" + EXTENSIONS + ")" +          // extension
  ")" +
  "(?::(\\d+))?" +                       // optional :line
  "(?::(\\d+))?" +                       // optional :col
  "(?![\\w:])",                          // boundary — not followed by word char or :
  "gm"
);

function pathExists(p: string): boolean {
  try {
    return existsSync(p);
  } catch {
    return false;
  }
}

/**
 * Try to resolve a candidate path. Returns the absolute path if the
 * file exists, or null if it doesn't (avoids false positives).
 */
function resolvePath(candidate: string, cwd: string): string | null {
  // Already absolute
  if (isAbsolute(candidate)) {
    return pathExists(candidate) ? candidate : null;
  }

  // Try relative to cwd
  const abs = resolve(cwd, candidate);
  if (pathExists(abs)) return abs;

  return null;
}

function addHyperlinks(text: string, cwd: string): string {
  const urlRoot = `file://`;

  return text.replace(PATH_RE, (match, path, line, col) => {
    // Skip matches that look like URLs
    if (/^https?:\/\//.test(path) || /^file:\/\//.test(path)) return match;

    // Resolve the path
    const absPath = resolvePath(path, cwd);
    if (!absPath) return match; // file doesn't exist — not a valid path

    // Build the file:// URL with optional line:col appended to the path
    let urlPath = absPath;
    if (line) {
      urlPath += `:${line}`;
      if (col) urlPath += `:${col}`;
    }

    // OSC 8 hyperlink: \x1b]8;;<uri>\x1b\\<text>\x1b]8;;\x1b\\
    const osc8 = `\x1b]8;;${urlRoot}${urlPath}\x1b\\${match}\x1b]8;;\x1b\\`;
    return osc8;
  });
}

export default function (pi: ExtensionAPI) {
  pi.on("message_end", async (event, ctx) => {
    // Only activate in TUI mode
    if (ctx.mode !== "tui") return;
    // Only process assistant messages with text content blocks
    if (event.message.role !== "assistant") return;

    const content = event.message.content;
    // Assistant content is always (TextContent|ThinkingContent|ToolCall)[]
    if (!Array.isArray(content)) return;
    if (content.length === 0) return;

    let changed = false;
    const newContent = content.map((block) => {
      if (block.type === "text" && typeof block.text === "string" && block.text.trim()) {
        const processed = addHyperlinks(block.text, ctx.cwd);
        if (processed !== block.text) {
          changed = true;
          return { ...block, text: processed };
        }
      }
      return block;
    });

    if (!changed) return;

    return {
      message: {
        ...event.message,
        content: newContent,
      },
    };
  });
}
