/**
 * Instagram Reel Transcriber — pi custom tool
 *
 * Transcribes Instagram Reels using local Whisper + Ollama models.
 * Backed by the aiw Python tool (``python -m ai_workspace.mcp_tools.instagram_transcriber``).
 *
 * Install:
 *   cp instagram-transcriber.ts ~/.pi/agent/extensions/
 *
 * Then ask pi:
 *   "Transcribe this reel: https://www.instagram.com/reel/C9hh6DKtYUb/"
 *   "List my cached transcripts"
 */

import { Type } from "@earendil-works/pi-ai";
import { defineTool, type ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { execSync } from "node:child_process";

const PY_MODULE = "ai_workspace.mcp_tools.instagram_transcriber";

function runPython(args: string[]): string {
	return execSync(["python3", "-m", PY_MODULE, ...args].join(" "), {
		timeout: 600_000,
		encoding: "utf-8",
		maxBuffer: 10 * 1024 * 1024,
	});
}

// ── Tool: transcribe_instagram_reel ──────────────────────────────────────

const transcribeTool = defineTool({
	name: "transcribe_instagram_reel",
	label: "Transcribe Instagram Reel",
	description:
		"Download an Instagram Reel, transcribe speech with Whisper, " +
		"and optionally analyze with a local Ollama model. " +
		"Returns caption text, full transcript, audio duration, and optional AI analysis.",

	parameters: Type.Object({
		url: Type.String({
			description: "Full Instagram Reel URL (e.g. https://www.instagram.com/reel/C9hh6DKtYUb/)",
		}),
		model: Type.Optional(
			Type.String({ description: "Whisper model size: tiny, base, small, medium, large (default: small)" }),
		),
		language: Type.Optional(Type.String({ description: "Spoken language code (e.g. en, pt, es). Auto-detected if omitted." })),
		analyze: Type.Optional(Type.Boolean({ description: "Analyze transcript with local Ollama model (default: false)" })),
		ollama_model: Type.Optional(Type.String({ description: "Ollama model for analysis (default: qwen3.5:9b)" })),
		force: Type.Optional(Type.Boolean({ description: "Re-download even if cached (default: false)" })),
	}),

	async execute(_toolCallId, params, _signal, onUpdate) {
		const args = [
			"--url", params.url,
			"--model", params.model ?? "small",
			"--json",
		];
		if (params.language) args.push("--language", params.language);
		if (params.analyze) args.push("--analyze", "--ollama-model", params.ollama_model ?? "qwen3.5:9b");
		if (params.force) args.push("--force");

		onUpdate?.({ content: [{ type: "text", text: `Downloading reel + transcribing with whisper (${params.model ?? "small"})...` }] });

		try {
			const output = runPython(args);
			const result = JSON.parse(output);

			if (!result.success) {
				return {
					content: [{ type: "text", text: `Transcription failed: ${result.error ?? "unknown error"}` }],
					isError: true,
					details: result,
				};
			}

			const lines = [
				`## Instagram Reel: ${result.shortcode}`,
				`**URL:** ${result.url}`,
				`**Duration:** ${result.duration_s}s`,
				`**Language:** ${result.language || "(auto-detected)"}`,
				result.cache_hit ? "*(cached)*" : "",
				"",
			];
			if (result.caption) lines.push("### Caption", result.caption, "");
			lines.push("### Transcript", result.transcript || "(no speech detected)", "");
			if (result.analysis) lines.push("### Ollama Analysis", result.analysis);

			return {
				content: [{ type: "text", text: lines.join("\n") }],
				details: {
					shortcode: result.shortcode,
					url: result.url,
					duration_s: result.duration_s,
					has_transcript: !!result.transcript,
					has_caption: !!result.caption,
					has_analysis: !!result.analysis,
					cache_hit: result.cache_hit,
				},
			};
		} catch (err: unknown) {
			const message = err instanceof Error ? err.message : String(err);
			return {
				content: [{ type: "text", text: `Transcription failed: ${message}` }],
				isError: true,
				details: { error: message },
			};
		}
	},
});

// ── Tool: list_transcripts ───────────────────────────────────────────────

const listTool = defineTool({
	name: "list_transcripts",
	label: "List Instagram Transcripts",
	description: "List all cached Instagram Reel transcripts with metadata.",

	parameters: Type.Object({
		limit: Type.Optional(Type.Integer({ description: "Max results (default: 20)", minimum: 1, maximum: 100 })),
	}),

	async execute(_toolCallId, params) {
		const limit = params.limit ?? 20;
		try {
			const output = runPython(["--list", "--json", "--limit", String(limit)]);
			return {
				content: [{ type: "text", text: output }],
				details: { count: JSON.parse(output).length },
			};
		} catch {
			return {
				content: [{ type: "text", text: "No cached transcripts found." }],
				details: { count: 0 },
			};
		}
	},
});

// ── Extension entry ──────────────────────────────────────────────────────

export default function (pi: ExtensionAPI) {
	pi.registerTool(transcribeTool);
	pi.registerTool(listTool);
}
