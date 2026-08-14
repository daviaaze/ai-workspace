# AI Workspace ↔ Pi Integration Plan

## Approach: Pi Extension (simplest, most powerful)

pi has a robust extension system. We can create a pi extension at `~/.pi/agent/extensions/aiw/` that registers these tools:

| Tool | What it does | Calls |
|------|-------------|-------|
| `search_knowledge` | Vector/text search the knowledge base | `aiw kb search <query>` |
| `deep_research` | Multi-step LLM research | `aiw search --provider deepseek <query>` |
| `recall_memory` | Search agent memories | `aiw memory recall <query>` |
| `remember_fact` | Store a fact | `aiw memory add <content>` |
| `list_tasks` | Show pending tasks | `aiw task list` |
| `add_task` | Create a task | `aiw task add <title>` |

The extension runs once on pi startup, connects to the DB, and on every `session_start` injects relevant context (recent research, memories) into the system prompt.

## Implementation

```typescript
// ~/.pi/agent/extensions/aiw/index.ts
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";
import { execSync } from "node:child_process";

const AIW_BIN = "aiw";           // from PATH (Nix-installed)
const AIW_DB = "postgresql://ai_workspace:ai_workspace@localhost:2284/ai_workspace";

function aiw(args: string): string {
  return execSync(`AIW_DB_URL=${AIW_DB} ${AIW_BIN} ${args}`, {
    encoding: "utf-8",
    timeout: 120_000,
  });
}

export default function (pi: ExtensionAPI) {
  // 1. Knowledge base search
  pi.registerTool({
    name: "search_knowledge",
    label: "Search Knowledge",
    description: "Search the AI Workspace knowledge base (research, notes, agent memory). Use this to find past research results, stored facts, and project knowledge before answering.",
    parameters: Type.Object({
      query: Type.String({ description: "Search query" }),
      type: Type.Optional(Type.String({ description: "Filter: 'kb' (notes), 'memory' (agent facts), 'research' (past research)" })),
      limit: Type.Optional(Type.Number({ description: "Max results (default 5)" })),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
      const limit = params.limit || 5;

      let results = "";
      if (!params.type || params.type === "research") {
        results += aiw(`kb search "${params.query}" --limit ${limit}`);
      }
      if (!params.type || params.type === "memory") {
        results += aiw(`memory recall "${params.query}" --limit ${limit}`);
      }

      return {
        content: [{ type: "text", text: results || "No results found." }],
        details: { query: params.query, type: params.type },
      };
    },
  });

  // 2. Deep research
  pi.registerTool({
    name: "deep_research",
    label: "Deep Research",
    description: "Run multi-step AI-powered research on a topic. Breaks the question into sub-questions, researches each, and synthesizes a report. Use this for complex topics that require thorough investigation.",
    parameters: Type.Object({
      query: Type.String({ description: "Research question or topic" }),
      depth: Type.Optional(Type.Number({ description: "Research depth 1-4 (default 2)" })),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
      const depth = params.depth || 2;
      const output = aiw(`search --provider deepseek "${params.query}" --depth ${depth} --no-save`);
      return {
        content: [{ type: "text", text: output }],
        details: { depth, query: params.query },
      };
    },
  });

  // 3. Remember facts for future sessions
  pi.registerTool({
    name: "remember",
    label: "Remember",
    description: "Store an important fact, insight, or decision in the AI Workspace memory so future sessions can recall it.",
    parameters: Type.Object({
      content: Type.String({ description: "What to remember" }),
      importance: Type.Optional(Type.Number({ description: "Importance 0.0-1.0 (default 0.5)" })),
    }),
    async execute(_toolCallId, params, _signal, _onUpdate, _ctx) {
      const importance = params.importance || 0.5;
      aiw(`memory add "${params.content}" --importance ${importance}`);
      return {
        content: [{ type: "text", text: `✓ Remembered (importance: ${importance})` }],
        details: {},
      };
    },
  });

  // 4. Telemetry / context injection on session start
  pi.on("session_start", async (_event, ctx) => {
    try {
      const recent = aiw("telemetry");
      // Inject recent activity as context the LLM can see
      pi.sendMessage({
        customType: "aiw-context",
        content: `Recent AI Workspace activity:\n${recent}`,
        display: false,
      }, { triggerTurn: false });
    } catch {
      // aiw not available — skip
    }
  });

  // 5. Register /kb and /research commands
  pi.registerCommand("kb", {
    description: "Search the knowledge base",
    handler: async (args, ctx) => {
      if (!args) return;
      const result = aiw(`kb search "${args}"`);
      ctx.ui.notify(result.slice(0, 500), "info");
    },
  });
}
```

## What this enables

### pi sessions with persistent memory

```
User: "What was the conclusion about crewAI Flows vs our DAG engine?"
pi calls: search_knowledge(query="crewAI Flows DAG engine")
→ Finds past research entry from aiw kb
→ Answers with context from the knowledge base
```

### pi doing research before coding

```
User: "Build a web scraper for the Receita Federal edital page"
pi calls: deep_research(query="Receita Federal scraping approaches")
→ aiw breaks into sub-questions, researches, returns report
pi: uses research to inform code generation
pi calls: remember(content="Receita Federal uses ASP.NET WebForms, requires session cookies")
→ Stored for future sessions
```

### Cross-session context

```
Session 1 (last week):
  pi calls: remember("The edital scraper needs to handle CAPTCHA redirects")
  
Session 2 (today):
  pi: reads aiw context on session_start
  → Already knows about CAPTCHA issue from past session
```

## Installation

```bash
mkdir -p ~/.pi/agent/extensions/aiw
# Create index.ts with the code above
# Restart pi or run /reload
```

## Alternative: Direct PostgreSQL access

If the CLI approach is too slow, the extension could use a Node.js PostgreSQL client (`pg`) to query the database directly:

```typescript
import { Pool } from "pg";

const pool = new Pool({
  connectionString: "postgresql://ai_workspace:ai_workspace@localhost:2284/ai_workspace",
});

// Vector search
const { rows } = await pool.query(
  `SELECT content, title, 1 - (embedding <=> $1) AS similarity
   FROM knowledge_entries
   WHERE embedding IS NOT NULL
   ORDER BY similarity DESC LIMIT 5`,
  [embedding]
);
```

This is faster but requires `npm install pg` in the extension directory, adds a dependency, and requires an embedding model to convert queries to vectors.

## Recommended: Start with the CLI approach

- ✅ Zero additional dependencies
- ✅ Works immediately (aiw is already on PATH)
- ✅ Full access to all aiw features
- ⚠️ ~1-2s overhead per call (spawning process)
- ⚠️ No streaming progress (but we added live output to aiw)
