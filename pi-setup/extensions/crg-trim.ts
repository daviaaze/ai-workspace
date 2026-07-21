/**
 * Trimmed Code Review Graph Extension
 *
 * A leaner version of code-review-graph.ts — registers only the top 6 tools
 * (by actual usage frequency) instead of all 28+. Same MCP server under the hood.
 *
 * Top 6 (87% of all CRG calls):
 *   build_or_update_graph, get_impact_radius, query_graph,
 *   get_review_context, semantic_search_nodes, detect_changes
 */

import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { StringEnum } from "@earendil-works/pi-ai";
import { Type } from "typebox";

// ---------------------------------------------------------------------------
// MCP Protocol Types
// ---------------------------------------------------------------------------

interface McpRequest { jsonrpc: "2.0"; id?: number; method: string; params?: unknown; }
interface McpResponse { jsonrpc: "2.0"; id: number; result?: unknown; error?: { code: number; message: string; data?: unknown }; }
interface McpTool { name: string; description?: string; inputSchema?: Record<string, unknown>; }
interface PendingRequest { resolve: (value: unknown) => void; reject: (reason: Error) => void; timer: ReturnType<typeof setTimeout>; }

// ---------------------------------------------------------------------------
// MCP Client (same as full extension)
// ---------------------------------------------------------------------------

class McpClient {
	private process: ChildProcessWithoutNullStreams | null = null;
	private requestId = 0;
	private pending = new Map<number, PendingRequest>();
	private buffer = "";
	private tools: McpTool[] = [];
	private initialized = false;

	getToolList(): McpTool[] { return this.tools; }
	isInitialized(): boolean { return this.initialized; }

	async start(command: string, args: string[], cwd?: string): Promise<void> {
		this.process = spawn(command, args, {
			stdio: ["pipe", "pipe", "pipe"],
			cwd,
			env: {
				...process.env,
				NO_COLOR: "1",
				FORCE_COLOR: "0",
				PYTHONUNBUFFERED: "1",
			},
		});

		this.process.stderr?.on("data", (data: Buffer) => {
			const text = data.toString();
			// stderr from MCP server — suppress to avoid noise
		});

		this.process.on("error", (_err) => {
			// MCP server error — handled by caller
		});

		this.process.on("exit", (_code) => {
			this.cleanup();
		});

		this.process.stdin.on("error", () => {});
		this.process.stdout.on("data", (data: Buffer) => this.handleData(data.toString()));

		await this.initialize();
	}

	private async initialize(): Promise<void> {
		await this.request("initialize", {
			protocolVersion: "2024-11-05",
			capabilities: {},
			clientInfo: { name: "pi-crg-trim", version: "1.0.0" },
		});
		this.sendNotification("notifications/initialized", {});
		const listResult = (await this.request("tools/list", {})) as { tools?: McpTool[] };
		this.tools = listResult.tools ?? [];
		this.initialized = true;
	}

	private sendNotification(method: string, params?: unknown): void {
		if (!this.process || this.process.killed) return;
		const req: McpRequest = { jsonrpc: "2.0", method, params };
		this.process.stdin.write(JSON.stringify(req) + "\n");
	}

	private handleData(data: string): void {
		this.buffer += data;
		const lines = this.buffer.split("\n");
		this.buffer = lines.pop() ?? "";
		for (const line of lines) {
			if (!line.trim()) continue;
			try {
				const msg = JSON.parse(line) as McpResponse;
				if (msg.id !== undefined) {
					const pending = this.pending.get(msg.id);
					if (pending) {
						this.pending.delete(msg.id);
						clearTimeout(pending.timer);
						if (msg.error) pending.reject(new Error(msg.error.message));
						else pending.resolve(msg.result);
					}
				}
			} catch { /* not JSON */ }
		}
	}

	private async request(method: string, params?: unknown, timeoutMs = 15_000): Promise<unknown> {
		const id = ++this.requestId;
		return new Promise((resolve, reject) => {
			const timer = setTimeout(() => {
				this.pending.delete(id);
				reject(new Error(`MCP request "${method}" timed out after ${timeoutMs}ms`));
			}, timeoutMs);
			this.pending.set(id, { resolve, reject, timer });
			if (!this.process || this.process.killed) {
				clearTimeout(timer);
				this.pending.delete(id);
				reject(new Error("MCP server not running"));
				return;
			}
			const req: McpRequest = { jsonrpc: "2.0", id, method, params };
			this.process.stdin.write(JSON.stringify(req) + "\n");
		});
	}

	async callTool(name: string, argsRaw: Record<string, unknown>): Promise<unknown> {
		const mcpName = name.endsWith("_tool") ? name : `${name}_tool`;
		return this.request("tools/call", { name: mcpName, arguments: argsRaw });
	}

	private cleanup(): void {
		for (const [, pending] of this.pending) {
			clearTimeout(pending.timer);
			pending.reject(new Error("MCP server disconnected"));
		}
		this.pending.clear();
		this.initialized = false;
	}

	stop(): void {
		if (this.process) {
			this.process.kill();
			this.process = null;
		}
		this.cleanup();
	}
}

// ---------------------------------------------------------------------------
// Parameter Schemas
// ---------------------------------------------------------------------------

const RepoRootParam = Type.Optional(Type.String({ description: "Repository root path. Auto-detected if omitted." }));

const BuildParams = Type.Object({
	repo_root: RepoRootParam,
	postprocess: StringEnum(["none", "minimal", "full"] as const, { description: "Post-build processing level", default: "full" }),
	changed_files: Type.Optional(Type.Array(Type.String(), { description: "Explicit list of changed files for incremental update" })),
});

const ImpactRadiusParams = Type.Object({
	changed_files: Type.Optional(Type.Array(Type.String(), { description: "Explicit changed file paths (relative to repo root). Auto-detected from git if omitted." })),
	max_depth: Type.Optional(Type.Integer({ description: "Traversal depth", default: 2 })),
	max_results: Type.Optional(Type.Integer({ description: "Max impacted nodes", default: 500 })),
	repo_root: RepoRootParam,
	base: Type.Optional(Type.String({ description: "Git ref for diff comparison", default: "HEAD~1" })),
	detail_level: StringEnum(["standard", "minimal"] as const, { description: "Output detail level", default: "standard" }),
});

const QueryGraphParams = Type.Object({
	pattern: StringEnum(["callers_of", "callees_of", "imports_of", "importers_of", "children_of", "tests_for", "inheritors_of", "file_summary"] as const, { description: "Query pattern" }),
	target: Type.String({ description: "Target name or qualified name to query" }),
	repo_root: RepoRootParam,
	max_results: Type.Optional(Type.Integer({ description: "Max results", default: 100 })),
});

const ReviewContextParams = Type.Object({
	changed_files: Type.Optional(Type.Array(Type.String())),
	max_depth: Type.Optional(Type.Integer({ default: 2 })),
	include_source: Type.Optional(Type.Boolean({ default: true })),
	max_lines_per_file: Type.Optional(Type.Integer({ default: 200 })),
	repo_root: RepoRootParam,
	base: Type.Optional(Type.String({ default: "HEAD~1" })),
	detail_level: StringEnum(["standard", "minimal"] as const, { description: "Output detail level", default: "standard" }),
});

const SemanticSearchParams = Type.Object({
	query: Type.String({ description: "Search query" }),
	kind: Type.Optional(Type.String({ description: "Node kind filter" })),
	limit: Type.Optional(Type.Integer({ default: 20 })),
	repo_root: RepoRootParam,
	use_embeddings: Type.Optional(Type.Boolean({ default: true })),
});

const DetectChangesParams = Type.Object({
	changed_files: Type.Optional(Type.Array(Type.String())),
	repo_root: RepoRootParam,
	base: Type.Optional(Type.String({ default: "HEAD~1" })),
	detail_level: StringEnum(["standard", "minimal"] as const, { description: "Output detail level", default: "standard" }),
});

// ---------------------------------------------------------------------------
// Additional Tool Parameter Schemas
// ---------------------------------------------------------------------------

const ArchOverviewParams = Type.Object({
	repo_root: Type.Optional(Type.String({ description: "Repository root path. Auto-detected if omitted." })),
	detail_level: Type.Optional(StringEnum(["minimal", "standard"] as const, { description: "Output detail level", default: "minimal" })),
});

const ListCommunitiesParams = Type.Object({
	repo_root: Type.Optional(Type.String({ description: "Repository root path. Auto-detected if omitted." })),
	sort_by: Type.Optional(Type.String({ description: "Sort column: size, cohesion, or name", default: "size" })),
	min_size: Type.Optional(Type.Integer({ description: "Minimum community size", default: 0 })),
	detail_level: Type.Optional(StringEnum(["standard", "minimal"] as const, { description: "Output detail level", default: "standard" })),
});

const HubBridgeParams = Type.Object({
	repo_root: Type.Optional(Type.String({ description: "Repository root path. Auto-detected if omitted." })),
	top_n: Type.Optional(Type.Integer({ description: "Number of top results", default: 10 })),
});

const ListFlowsParams = Type.Object({
	repo_root: Type.Optional(Type.String({ description: "Repository root path. Auto-detected if omitted." })),
	sort_by: Type.Optional(Type.String({ description: "Sort column: criticality, depth, node_count, file_count, or name", default: "criticality" })),
	limit: Type.Optional(Type.Integer({ description: "Maximum flows to return", default: 50 })),
	detail_level: Type.Optional(StringEnum(["standard", "minimal"] as const, { description: "Output detail level", default: "standard" })),
});

const FindLargeFuncsParams = Type.Object({
	repo_root: Type.Optional(Type.String({ description: "Repository root path. Auto-detected if omitted." })),
	min_lines: Type.Optional(Type.Integer({ description: "Minimum line count to flag", default: 50 })),
	kind: Type.Optional(Type.String({ description: "Optional filter: Function, Class, File, or Test" })),
	file_path_pattern: Type.Optional(Type.String({ description: "Filter by file path substring" })),
	limit: Type.Optional(Type.Integer({ description: "Maximum results", default: 50 })),
});

const KnowlegeGapsParams = Type.Object({
	repo_root: Type.Optional(Type.String({ description: "Repository root path. Auto-detected if omitted." })),
});

// ---------------------------------------------------------------------------
// Result Formatting
// ---------------------------------------------------------------------------

function formatResult(result: unknown): { content: Array<{ type: "text"; text: string }>; details: unknown } {
	if (result === null || result === undefined) return { content: [{ type: "text", text: "(no result)" }], details: result };
	if (typeof result === "string") return { content: [{ type: "text", text: result }], details: result };
	if (typeof result === "object") {
		const obj = result as Record<string, unknown>;
		const summary = obj.summary ?? obj.status ?? "";
		const text = typeof summary === "string" ? summary : JSON.stringify(summary, null, 2);
		const content = obj.content as Array<{ type: string; text: string }> | undefined;
		if (content) {
			const full = content.map((c: { type: string; text: string }) => c.text).join("\n");
			return { content: [{ type: "text", text: full }], details: result };
		}
		return { content: [{ type: "text", text }], details: result };
	}
	return { content: [{ type: "text", text: String(result) }], details: result };
}

// ---------------------------------------------------------------------------
// Binary/Entry Point Discovery
// ---------------------------------------------------------------------------

function findExecutable(): { command: string; args: string[] } | null {
	// Check home-manager path first
	const homePrefix = process.env.HOME ?? "";
	const hmPrefix = `${homePrefix}/.local/state/nix/profiles/home-manager`;
	for (const profile of ["/etc/profiles/per-user/daviaaze", hmPrefix, `${homePrefix}/.nix-profile`]) {
		const binPath = resolve(profile, "bin", "code-review-graph");
		if (existsSync(binPath)) return { command: binPath, args: ["serve"] };
	}
	// Try PATH
	try {
		const { execSync } = require("node:child_process");
		const path = execSync("which code-review-graph", { encoding: "utf8", stdio: ["pipe", "pipe", "ignore"] }).trim();
		if (path) return { command: path, args: ["serve"] };
	} catch { /* not in PATH */ }
	// Try uvx
	try {
		const { execSync } = require("node:child_process");
		execSync("which uvx", { stdio: "ignore" });
		return { command: "uvx", args: ["code-review-graph", "serve"] };
	} catch { /* uvx not available */ }
	// Try common paths
	const candidates = [
		resolve(homePrefix, ".local/bin/code-review-graph"),
		"/usr/local/bin/code-review-graph",
		"/usr/bin/code-review-graph",
		"/run/current-system/sw/bin/code-review-graph",
	];
	for (const path of candidates) { if (existsSync(path)) return { command: path, args: ["serve"] }; }
	return null;
}

// ---------------------------------------------------------------------------
// Extension Entry Point
// ---------------------------------------------------------------------------

let client: McpClient | null = null;
let isAvailable = false;

export default function (pi: ExtensionAPI) {
	function registerGraphTool(
		name: string,
		label: string,
		description: string,
		promptSnippet: string,
		promptGuidelines: string[],
		parameters: ReturnType<typeof Type.Object>,
	) {
		pi.registerTool({
			name,
			label,
			description,
			promptSnippet,
			promptGuidelines,
			parameters,
			async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
				if (!client || !client.isInitialized())
					throw new Error("code-review-graph MCP server not available. Run: pip install code-review-graph && code-review-graph build");
				const result = await client.callTool(name, params as Record<string, unknown>);
				return formatResult(result);
			},
		});
	}

	// ── Session Lifecycle ──────────────────────────────────────────────────

	pi.on("session_start", async (_event, ctx) => {
		const exec = findExecutable();
		if (!exec) {
			// Silent startup — user discovers availability via /crg-status or tool errors
			return;
		}
		try {
			client = new McpClient();
			await client.start(exec.command, exec.args, ctx.cwd);
			isAvailable = true;
		} catch {
			isAvailable = false;
		}
	});

	pi.on("session_shutdown", () => {
		if (client) { client.stop(); client = null; }
		isAvailable = false;
	});

	// ── Register Top 6 Tools (87% of all CRG usage) ───────────────────────

	// [BUILD] Tool 1: build_or_update_graph (150 calls)
	registerGraphTool(
		"build_or_update_graph",
		"Build Graph",
		"Build or incrementally update the code review knowledge graph. Run this first when working with a new or changed codebase.",
		"Build or update the code review graph for the current project",
		[
			"Use build_or_update_graph when starting work on a project without a graph, or after significant changes.",
			"Use build_or_update_graph with changed_files for faster incremental updates.",
		],
		BuildParams,
	);

	// [ANALYSIS] Tool 2: get_impact_radius (115 calls)
	registerGraphTool(
		"get_impact_radius",
		"Impact Radius",
		"Analyze the blast radius of changed files. Returns changed nodes, impacted nodes, impacted files, and connecting edges.",
		"Find all code affected by recent changes (blast radius analysis)",
		[
			"Use get_impact_radius BEFORE reading files to understand what needs review.",
			"Use get_impact_radius with detail_level='minimal' for a quick risk assessment.",
			"Always check get_impact_radius before making changes to understand downstream effects.",
		],
		ImpactRadiusParams,
	);

	// [QUERY] Tool 3: query_graph (161 calls)
	registerGraphTool(
		"query_graph",
		"Query Graph",
		"Run predefined graph queries: callers_of, callees_of, imports_of, importers_of, children_of, tests_for, inheritors_of, file_summary.",
		"Find callers, callees, imports, tests, or inheritance for a symbol",
		[
			"Use query_graph callers_of to find what calls a function before modifying it.",
			"Use query_graph tests_for to check test coverage for a function or class.",
			"Use query_graph inheritors_of before refactoring base classes.",
			"Use query_graph imports_of to understand module dependencies.",
		],
		QueryGraphParams,
	);

	// [REVIEW] Tool 4: get_review_context (28 calls)
	registerGraphTool(
		"get_review_context",
		"Review Context",
		"Generate focused review context from changed files: subgraph, source snippets, and review guidance. Token-optimized for code review.",
		"Get focused review context for changed files with source snippets",
		[
			"Use get_review_context for PR reviews instead of reading entire files.",
			"Use get_review_context with detail_level='minimal' for a quick risk summary.",
		],
		ReviewContextParams,
	);

	// [SEARCH] Tool 5: semantic_search_nodes (210 calls — most used)
	registerGraphTool(
		"semantic_search_nodes",
		"Semantic Search",
		"Search graph nodes by keyword or vector similarity. Finds functions, classes, and other symbols.",
		"Search for functions, classes, or symbols by name or description",
		[
			"Use semantic_search_nodes instead of grep when looking for symbols by meaning, not just text.",
			"Use semantic_search_nodes with kind='Function' to find specific function types.",
		],
		SemanticSearchParams,
	);

	// [REVIEW] Tool 6: detect_changes (68 calls)
	registerGraphTool(
		"detect_changes",
		"Detect Changes",
		"Risk-scored change impact analysis. Detects changed files, analyzes risk, finds test gaps, and suggests review focus.",
		"Analyze code changes with risk scoring for review",
		[
			"Use detect_changes as the FIRST step in any code review workflow.",
			"Use detect_changes to get a risk score and identify test gaps before reviewing.",
		],
		DetectChangesParams,
	);

	// ── Tool 7–13: Architecture & Analysis Passthroughs ─────────────────────

	// [ARCH] Tool 7: get_architecture_overview
	registerGraphTool(
		"get_architecture_overview",
		"Architecture Overview",
		"Generate an architecture overview based on community structure. Builds a high-level view of the codebase with cross-community coupling warnings.",
		"Get architecture overview of the codebase",
		["Use get_architecture_overview for understanding high-level codebase structure."],
		ArchOverviewParams,
	);

	// [ARCH] Tool 8: list_communities
	registerGraphTool(
		"list_communities",
		"List Communities",
		"List detected code communities in the codebase. Each community represents a cluster of related code entities.",
		"List code communities for codebase structure",
		["Use list_communities to understand module boundaries and cluster structure."],
		ListCommunitiesParams,
	);

	// [ARCH] Tool 9: get_hub_nodes
	registerGraphTool(
		"get_hub_nodes",
		"Hub Nodes",
		"Find the most connected nodes in the codebase (architectural hotspots). Changes to them have disproportionate blast radius.",
		"Find architectural hotspots",
		["Use get_hub_nodes to identify high-risk, highly-connected code."],
		HubBridgeParams,
	);

	// [ARCH] Tool 10: get_bridge_nodes
	registerGraphTool(
		"get_bridge_nodes",
		"Bridge Nodes",
		"Find architectural chokepoints via betweenness centrality. If they break, multiple code regions lose connectivity.",
		"Find architectural chokepoints",
		["Use get_bridge_nodes to find critical path code that connects different regions."],
		HubBridgeParams,
	);

	// [ARCH] Tool 11: list_flows
	registerGraphTool(
		"list_flows",
		"List Flows",
		"List execution flows in the codebase, sorted by criticality. Each flow represents a call chain from an entry point.",
		"List critical execution flows",
		["Use list_flows to understand execution paths and entry points."],
		ListFlowsParams,
	);

	// [ARCH] Tool 12: find_large_functions
	registerGraphTool(
		"find_large_functions",
		"Large Functions",
		"Find functions, classes, or files exceeding a line-count threshold. Useful for decomposition audits.",
		"Find large functions for refactoring candidates",
		["Use find_large_functions to identify refactoring candidates."],
		FindLargeFuncsParams,
	);

	// [ARCH] Tool 13: get_knowledge_gaps
	registerGraphTool(
		"get_knowledge_gaps",
		"Knowledge Gaps",
		"Identify structural weaknesses: isolated nodes, thin communities, untested hotspots, single-file communities.",
		"Find knowledge gaps and weak spots",
		["Use get_knowledge_gaps to find structural weaknesses in the codebase."],
		KnowlegeGapsParams,
	);

	// ── Commands ────────────────────────────────────────────────────────────

	pi.registerCommand("crg-status", {
		description: "Show code-review-graph connection status",
		handler: async (_args, ctx) => {
			if (!ctx.hasUI) return;
			if (isAvailable && client?.isInitialized()) {
				const toolCount = client.getToolList().length;
				ctx.ui.notify("code-review-graph: connected (" + toolCount + " tools available)", "success");
			} else {
				ctx.ui.notify("code-review-graph: not connected. Install with: pip install code-review-graph", "warning");
			}
		},
	});

	pi.registerCommand("crg-build", {
		description: "Build or update the code review graph",
		handler: async (_args, ctx) => {
			if (!ctx.hasUI) return;
			if (!isAvailable || !client) {
				ctx.ui.notify("code-review-graph not connected", "error");
				return;
			}
			try {
				ctx.ui.notify("Building code review graph...", "info");
				const result = await client.callTool("build_or_update_graph", {});
				const summary = (result as Record<string, unknown>)?.summary ?? "Build complete";
				ctx.ui.notify(String(summary), "success");
			} catch (err) {
				ctx.ui.notify("Build failed: " + (err instanceof Error ? err.message : String(err)), "error");
			}
		},
	});

	// ── System Prompt Enhancement ───────────────────────────────────────────

	pi.on("before_agent_start", async (event) => {
		if (!isAvailable) return {};

		const graphGuidelines = `
## Code Review Graph Guidelines

This project has a code-review-graph knowledge graph available. ALWAYS prefer graph tools over file scanning:

1. **Before exploring**: Use semantic_search_nodes or query_graph instead of grep/find
2. **Before reviewing**: Use detect_changes + get_review_context instead of reading entire files
3. **Before modifying**: Use get_impact_radius to understand blast radius
4. **For architecture**: Use get_architecture_overview, list_communities, get_hub_nodes, get_bridge_nodes, and list_flows
5. **For architecture (deep)**: Use find_large_functions and get_knowledge_gaps for refactoring candidates and weak spots
6. **For testing**: Use query_graph with pattern="tests_for" to check coverage

Workflow:
- Start with build_or_update_graph if unsure if graph is current
- Use detect_changes for any review task
- Use get_impact_radius to find affected code
- Use get_architecture_overview / list_communities for high-level codebase structure
- Use query_graph callers_of/callees_of for dependency tracing
- Fall back to read/bash ONLY when graph tools don't cover the need
`;

		return {
			systemPrompt: event.systemPrompt + graphGuidelines,
		};
	});
}
