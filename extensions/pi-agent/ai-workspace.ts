/**
 * AI Workspace extension for Pi Coding Agent.
 * 
 * Registers custom tools that give pi access to:
 * - aiw deep search
 * - aiw workflows
 * - aiw knowledge base queries
 * - aiw task management
 * 
 * Place in: ~/.pi/agent/extensions/ai-workspace.ts
 * Or project-local: .pi/extensions/ai-workspace.ts
 */

import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function (pi: ExtensionAPI) {
  // ─── Notify on load ───────────────────────────────────
  pi.on("session_start", async (_event, ctx) => {
    ctx.ui.notify("AI Workspace extension loaded", "info");
  });

  // ─── Tool: deep_research ──────────────────────────────
  pi.registerTool({
    name: "aiw_search",
    label: "Deep Research",
    description: 
      "Run deep recursive research using aiw (AI Workspace). " +
      "Breaks down a query into sub-questions, researches each in parallel, " +
      "and synthesizes a comprehensive report. Uses local Ollama models.",
    parameters: {
      query: {
        type: "string",
        description: "The research query to investigate deeply",
      },
      depth: {
        type: "number",
        default: 2,
        description: "Recursion depth (1-4). 2 is good for most topics.",
      },
      model: {
        type: "string",
        default: "deepseek-r1:14b",
        description: "Model for deep reasoning (default: deepseek-r1:14b)",
      },
      save: {
        type: "boolean",
        default: true,
        description: "Save results to knowledge base",
      },
    },
    execute: async (input, _ctx) => {
      const { execSync } = await import("child_process");
      
      try {
        const result = execSync(
          `aiw search "${input.query}" --depth ${input.depth || 2} ` +
          `--model ${input.model || "deepseek-r1:14b"} ` +
          `${input.save !== false ? "--save" : "--no-save"}`,
          { encoding: "utf-8", maxBuffer: 50 * 1024 * 1024, timeout: 600000 }
        );
        return { success: true, output: result.trim() };
      } catch (e: any) {
        return { success: false, error: e.stderr || e.message };
      }
    },
  });

  // ─── Tool: aiw_ask ────────────────────────────────────
  pi.registerTool({
    name: "aiw_ask",
    label: "Quick Ask",
    description:
      "Quick one-shot question to an LLM. Use for simple questions " +
      "that don't need deep research. Faster than aiw_search.",
    parameters: {
      message: {
        type: "string",
        description: "The question or prompt",
      },
      provider: {
        type: "string",
        default: "ollama",
        description: "Provider: ollama, deepseek",
      },
      model: {
        type: "string",
        default: "qwen3:14b",
        description: "Model name",
      },
    },
    execute: async (input, _ctx) => {
      const { execSync } = await import("child_process");
      
      try {
        const result = execSync(
          `aiw ask "${input.message}" --provider ${input.provider || "ollama"} ` +
          `--model ${input.model || "qwen3:14b"}`,
          { encoding: "utf-8", maxBuffer: 10 * 1024 * 1024, timeout: 120000 }
        );
        return { success: true, output: result.trim() };
      } catch (e: any) {
        return { success: false, error: e.stderr || e.message };
      }
    },
  });

  // ─── Tool: knowledge_base ─────────────────────────────
  pi.registerTool({
    name: "aiw_kb",
    label: "Knowledge Base",
    description:
      "Search the AI Workspace knowledge base (PostgreSQL). " +
      "Contains past research, notes, agent memories, and task history.",
    parameters: {
      query: {
        type: "string",
        description: "Search query for knowledge base",
      },
      content_type: {
        type: "string",
        default: "",
        description: "Filter: research, note, briefing, obsidian_note",
      },
    },
    execute: async (input, _ctx) => {
      const { execSync } = await import("child_process");
      
      const typeFlag = input.content_type ? `--type ${input.content_type}` : "";
      
      try {
        const result = execSync(
          `aiw kb search "${input.query}" ${typeFlag} --limit 5`,
          { encoding: "utf-8", maxBuffer: 5 * 1024 * 1024, timeout: 30000 }
        );
        return { success: true, output: result.trim() };
      } catch (e: any) {
        return { success: false, error: e.stderr || e.message };
      }
    },
  });

  // ─── Tool: task management ────────────────────────────
  pi.registerTool({
    name: "aiw_task",
    label: "Task Management",
    description:
      "List, add, or update tasks in the AI Workspace. " +
      "Tasks can be recurring (cron schedule).",
    parameters: {
      action: {
        type: "string",
        description: "list, add, or due",
      },
      title: {
        type: "string",
        default: "",
        description: "Task title (for add action)",
      },
      priority: {
        type: "number",
        default: 5,
        description: "Priority 0-10 (for add action)",
      },
      schedule: {
        type: "string",
        default: "",
        description: "Cron schedule, e.g. '0 9 * * *' (for add action)",
      },
    },
    execute: async (input, _ctx) => {
      const { execSync } = await import("child_process");
      
      try {
        let cmd = "aiw task list --limit 10";
        
        if (input.action === "add" && input.title) {
          cmd = `aiw task add "${input.title}" --priority ${input.priority || 5}`;
          if (input.schedule) cmd += ` --schedule "${input.schedule}"`;
        } else if (input.action === "due") {
          cmd = "aiw task due";
        }
        
        const result = execSync(cmd, {
          encoding: "utf-8", maxBuffer: 1 * 1024 * 1024, timeout: 10000,
        });
        return { success: true, output: result.trim() };
      } catch (e: any) {
        return { success: false, error: e.stderr || e.message };
      }
    },
  });

  // ─── Tool: workflow status ────────────────────────────
  pi.registerTool({
    name: "aiw_wf_status",
    label: "Workflow Status",
    description:
      "Check status of AI Workspace workflows (deep research, briefings, learning).",
    parameters: {
      workflow: {
        type: "string",
        default: "",
        description: "Workflow name (deep_research, daily_briefing, continuous_learning) or empty for all",
      },
    },
    execute: async (input, _ctx) => {
      const { execSync } = await import("child_process");
      
      try {
        const nameFlag = input.workflow ? `--name ${input.workflow}` : "";
        const result = execSync(`aiw wf status ${nameFlag}`, {
          encoding: "utf-8", maxBuffer: 1 * 1024 * 1024, timeout: 10000,
        });
        return { success: true, output: result.trim() };
      } catch (e: any) {
        return { success: false, error: e.stderr || e.message };
      }
    },
  });

  // ─── Tool: run workflow ───────────────────────────────
  pi.registerTool({
    name: "aiw_wf_run",
    label: "Run Workflow",
    description:
      "Execute an AI Workspace workflow (DAG-based). " +
      "deep_research: plan→parallel research→synthesize→store. " +
      "daily_briefing: collect→generate→store.",
    parameters: {
      workflow: {
        type: "string",
        description: "Workflow to run: deep_research, daily_briefing, continuous_learning",
      },
      query: {
        type: "string",
        default: "",
        description: "Research query (for deep_research workflow)",
      },
    },
    execute: async (input, _ctx) => {
      const { execSync } = await import("child_process");
      
      try {
        const result = execSync(
          `aiw wf run ${input.workflow} --query "${input.query}"`,
          { encoding: "utf-8", maxBuffer: 50 * 1024 * 1024, timeout: 600000 }
        );
        return { success: true, output: result.trim() };
      } catch (e: any) {
        return { success: false, error: e.stderr || e.message };
      }
    },
  });

  // ─── Tool: telemetry ──────────────────────────────────
  pi.registerTool({
    name: "aiw_telemetry",
    label: "AI Workspace Telemetry",
    description:
      "Get AI Workspace metrics: research count, tasks, memory usage, confidence scores.",
    parameters: {},
    execute: async (_input, _ctx) => {
      const { execSync } = await import("child_process");
      
      try {
        const result = execSync("aiw telemetry", {
          encoding: "utf-8", maxBuffer: 1 * 1024 * 1024, timeout: 10000,
        });
        return { success: true, output: result.trim() };
      } catch (e: any) {
        return { success: false, error: e.stderr || e.message };
      }
    },
  });

  // ─── Command: /aiw ────────────────────────────────────
  pi.registerCommand({
    name: "aiw",
    description: "AI Workspace operations: /aiw search|task|kb|wf|telemetry",
    execute: async (args, ctx) => {
      if (args.length === 0) {
        ctx.ui.notify(
          "Usage: /aiw search|task|kb|wf|telemetry",
          "info"
        );
        return;
      }

      const { execSync } = await import("child_process");
      const subcommand = args.join(" ");
      
      try {
        const result = execSync(`aiw ${subcommand}`, {
          encoding: "utf-8", maxBuffer: 1 * 1024 * 1024, timeout: 30000,
        });
        ctx.ui.notify(result.trim().split("\n")[0] || "Done", "info");
      } catch (e: any) {
        ctx.ui.notify(`aiw error: ${e.stderr || e.message}`, "error");
      }
    },
  });

  // ─── Periodic telemetry (every 30 min) ────────────────
  let lastTelemetry = 0;
  pi.on("turn_start", async (_event, ctx) => {
    const now = Date.now();
    if (now - lastTelemetry > 30 * 60 * 1000) {
      lastTelemetry = now;
      try {
        const { execSync } = await import("child_process");
        const result = execSync("aiw telemetry 2>/dev/null || true", {
          encoding: "utf-8", timeout: 5000,
        });
        if (result.trim()) {
          ctx.ui.notify("📊 " + result.trim().split("\n").slice(1, 4).join(" | "), "info");
        }
      } catch {
        // Silent fail — aiw might not be initialized yet
      }
    }
  });
}
