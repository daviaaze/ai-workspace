/**
 * Workspace Search Extension
 *
 * Registers a `workspace_search` tool for the LLM and a `/ws` command
 * for the user. Searches across the workspace knowledge base (memory,
 * TODOs, dailies, knowledge base, projects, templates, and memory) for relevant content.
 *
 * Uses filesystem grep — no external dependencies.
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { resolve, relative } from "node:path";
import { homedir } from "node:os";

const WORKSPACE_ROOT =
  process.env.WORKSPACE ||
  resolve(homedir(), "Projects/pessoal/ai-workspace");

// Directories to search (relative to workspace root, non-git)
const SEARCH_DIRS = [
  "memory",
  "Development",
  "Knowledge-Base",
  "References",
  "Templates",
  "Projects",
  "Research",
  "Technical-Decisions",
  "Runbooks",
  "analysis",
  "Ideas-and-Backlog",
  "docs",
];

function collectResults(output: string, workspaceRoot: string, maxResults: number, results: string[]): void {
  for (const line of output.trim().split("\n").slice(0, maxResults)) {
    const [file, num, ...text] = line.split(":");
    const relPath = relative(workspaceRoot, file);
    const snippet = text.join(":").trim().substring(0, 200);
    results.push(`${relPath}:${num}: ${snippet}`);
  }
}

async function searchWorkspace(pi: ExtensionAPI, query: string, maxResults = 10, signal?: AbortSignal): Promise<string> {
  const results: string[] = [];
  const searchPattern = query.replace(/['"\\]/g, "\\$&"); // escape for grep

  for (const dir of SEARCH_DIRS) {
    if (signal?.aborted) break;
    const fullPath = resolve(WORKSPACE_ROOT, dir);
    try {
      const { stdout } = await pi.exec("grep", [
        "-rin", "--include=*.md",
        "-m", String(maxResults),
        searchPattern, fullPath,
      ], { timeout: 10_000, signal });
      collectResults(stdout, WORKSPACE_ROOT, maxResults - results.length, results);
    } catch {
      // dir may not exist or grep fails
    }
    if (results.length >= maxResults) break;
  }

  if (results.length === 0) {
    return `No results found for "${query}" in workspace.`;
  }

  const output = results.join("\n");
  // Truncate to avoid overwhelming context
  if (output.length > 5000) {
    return output.substring(0, 5000) + "\n... (truncated, results limited to 5000 chars)";
  }
  return output;
}

export default function (pi: ExtensionAPI) {
  // Tool: callable by LLM
  pi.registerTool({
    name: "workspace_search",
    label: "Workspace Search",
    description:
      "Search the ai-workspace knowledge base (memory, TODOs, dailies, knowledge base, templates, projects) for relevant content. Use when you need to find previous analysis, decisions, or reference material.",
    promptSnippet: "Search workspace for relevant knowledge",
    parameters: Type.Object({
      query: Type.String({ description: "Search query (exact text match)" }),
      max_results: Type.Optional(
        Type.Number({ description: "Max results (default: 10)" })
      ),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
      const results = await searchWorkspace(pi, params.query, params.max_results ?? 10, _signal);
      return {
        content: [{ type: "text", text: results }],
        details: { query: params.query },
      };
    },
  });

  // Command: /ws <query> for user
  pi.registerCommand("ws", {
    description: "Search workspace knowledge base",
    handler: async (args, ctx) => {
      if (!args) {
        ctx.ui.notify("Usage: /ws <search query>", "error");
        return;
      }
      const results = await searchWorkspace(pi, args, 15);
      ctx.ui.notify(results.substring(0, 500), "info");
    },
  });
}
