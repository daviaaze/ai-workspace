# GAP Analysis — aiw vs pi

## Pi Capabilities (target)

| # | Feature | Description |
|---|---------|-------------|
| 1 | Interactive persistent session | Multi-turn chat with memory, agent self-improves |
| 2 | Streaming token output | Real-time token-by-token response (not just prints) |
| 3 | Automatic tool selection | Auto-detects intent, picks right tools |
| 4 | Permission/preview system | Shows file edits before applying, asks for approval |
| 5 | Safe execution sandbox | Shell runs in sandbox, git changes reversible |
| 6 | Multi-agent orchestration | Can delegate subtasks to specialized agents |
| 7 | Context awareness | Understands project structure, git state, open files |
| 8 | Model fallback/retry | Tries different providers/models on failure |
| 9 | Session persistence | Remembers across restarts, restores state |
| 10 | MCP server integration | Connects to external MCP tool servers |

## AIW Current State

| # | Feature | Status |
|---|---------|--------|
| 1 | Interactive persistent session | ❌ Missing — `aiw agent` is one-shot |
| 2 | Streaming token output | ⚠️ Partial — captures print() lines, not LLM tokens |
| 3 | Automatic tool selection | ⚠️ Partial — agent has all tools, model chooses |
| 4 | Permission/preview system | ❌ Missing — PermissionModal exists but unused |
| 5 | Safe execution sandbox | ⚠️ Partial — shell_exec is sandboxed, no edit preview |
| 6 | Multi-agent orchestration | ⚠️ Partial — worktrees isolate, no delegation |
| 7 | Context awareness | ❌ Missing — no automatic project context injection |
| 8 | Model fallback/retry | ❌ Missing — SmartRouter planned, not built |
| 9 | Session persistence | ❌ Missing — TUI state lost on exit |
| 10 | MCP server integration | ❌ Missing — MCP framework installed, not wired |

## Gap Prioritization

### 🔥 Phase 1 — Interactive Persistent Session (1-2 days)
**What:** Continuous agent loop that maintains context across messages.
**Why:** This is the CORE pi experience — you talk, agent acts, you reply, it continues.
**How:**
- `PersistentAgentSession` class wrapping AgentWorker
- Maintains conversation history (list of messages)
- Each user message → append to task context → re-run agent
- Agent sees full history, continues where it left off
- Session saves/restores to DB

### 🔥 Phase 2 — Streaming Token Output (1 day)
**What:** Real-time token streaming into TUI lanes, not just print() capture.
**Why:** pi streams token-by-token. Current AgentWorker captures stdout lines only.
**How:**
- Use Ollama streaming API (`stream=True`) directly
- `QueueStream` receives tokens, not lines
- TUI renders partial responses in AgentLane
- Thinking stream separate from response stream

### 🟡 Phase 3 — Permission/Preview System (1 day)
**What:** Show file edits before applying, require human approval for destructive ops.
**Why:** Safety layer. pi previews edits.
**How:**
- Intercept `edit_file`, `write_file`, `shell_exec` tool calls
- PermissionModal shows diff/command preview
- Human approves (a/A/d keys) → tool executes
- Configurable auto-approve for trusted operations

### 🟡 Phase 4 — Context Awareness (1 day)
**What:** Agent automatically knows project structure, git state, recent changes.
**Why:** pi understands "where you are" in the project.
**How:**
- `ContextBundle`: project tree, git status, open files, recent commits
- Injected into agent system prompt automatically
- Updates on each iteration

### 🟡 Phase 5 — Smart Router / Model Fallback (1 day)
**What:** Auto-select best model, fallback on failure.
**Why:** Cost optimization + reliability.
**How:**
- `SmartRouter`: qwen3:14b for coding → deepseek for complex → gemini for fallback
- Cost-based routing rules in config
- Auto-retry with different model on error

### 🟢 Phase 6 — Session Persistence (1 day)
**What:** TUI state survives restart.
**Why:** Don't lose agent outputs when you quit.
**How:**
- Save TUI state to JSON/SQLite on exit
- Restore lanes, outputs, task status on start
- Reconnect to running agents (via PID/socket)

### 🟢 Phase 7 — MCP Integration (1 day)
**What:** Connect to external MCP servers for additional tools.
**Why:** Expand tool ecosystem beyond built-in tools.
**How:**
- MCP client in AgentWorker
- Discover servers via mcp.directory or registry
- Tools appear in agent tool list dynamically

### ⚪ Phase 8 — Multi-Agent with Delegation (2 days)
**What:** One agent can spawn subtasks to other agents.
**Why:** Complex tasks need specialization.
**How:**
- `delegate(agent_type, subtask)` tool
- Sub-agent runs in separate worktree
- Results merged back to parent agent
- TUI shows sub-agent lanes nested

## Architecture for the Complete Agent

```
┌─────────────────────────────────────────────────────────────────┐
│                   PersistentAgentSession                          │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────────┐ │
│  │ Context  │   │  History │   │  Tools   │   │   Permissions │ │
│  │ Bundle   │   │  (msg[] │   │  (18+)   │   │   (gate)      │ │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └──────┬───────┘ │
│       │              │              │                 │          │
│       └──────────────┴──────────────┴─────────────────┘          │
│                              │                                    │
│                     ┌────────▼────────┐                          │
│                     │  SmartRouter    │                          │
│                     │  ├ qwen3:14b    │                          │
│                     │  ├ deepseek-v4  │                          │
│                     │  └ gemini (fb)  │                          │
│                     └────────┬────────┘                          │
│                              │                                    │
│                     ┌────────▼────────┐                          │
│                     │  LLM (Ollama/API)│                          │
│                     │  stream=True     │                          │
│                     │  token → Queue   │                          │
│                     └────────┬────────┘                          │
│                              │                                    │
│              ┌───────────────┼───────────────┐                   │
│              │               │               │                    │
│         ┌────▼────┐   ┌─────▼──────┐  ┌─────▼─────┐             │
│         │ Tool    │   │ Permission │  │ Delegation│             │
│         │ Executor│   │ Gate       │  │ Manager   │             │
│         │         │   │ (preview)  │  │ (subtasks)│             │
│         └────┬────┘   └─────┬──────┘  └─────┬─────┘             │
│              │              │               │                    │
│         ┌────▼────┐   ┌─────▼──────┐  ┌─────▼─────┐             │
│         │ Files   │   │ TUI Modal  │  │ AgentWorker│             │
│         │ Git     │   │ (approve)  │  │ (background)│            │
│         │ Shell   │   │            │  │             │            │
│         │ Web     │   │            │  │             │            │
│         └─────────┘   └────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Order (next 5 sessions)

| Session | Phase | Deliverable |
|---------|-------|-------------|
| Now | 1 | `PersistentAgentSession` — continuous chat agent |
| Next | 2 | Token streaming into TUI AgentLane |
| Next | 3 | Permission preview for file/shell ops |
| Next | 4 | ContextBundle auto-injection |
| Next | 5 | SmartRouter with model fallback |
| Future | 6-8 | Persistence, MCP, multi-agent delegation |
