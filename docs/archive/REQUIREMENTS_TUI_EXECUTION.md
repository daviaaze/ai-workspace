# TUI Architecture & Status

## ✅ IMPLEMENTED

### Agent Execution
- **AgentWorker** (`tui/worker.py`): background crew execution via ThreadPoolExecutor
- **QueueStream**: captures stdout line-by-line → asyncio.Queue → AgentLane
- **AgentLane.attach_worker()**: drains queue every 50ms, updates status live
- **Lifecycle**: Space = pause/resume, Ctrl+X = kill
- **Agent types**: coding (crew), research (deep_search), general (unified agent)

### Session Persistence
- **SessionStore** (`core/sessions.py`): PostgreSQL-backed, pi-compatible JSONL format
- **PersistentAgentSession** (`agents/session.py`): multi-turn conversation with history injection
- **Auto-compaction**: detects context overflow, summarizes older messages
- **TUI integration**: SpawnDialog auto-creates session, AgentWorker injects history
- **CLI**: `aiw session start|chat|list|export|import`

### TUI Redesign (pi-like experience)
- **StatusBar**: shows CWD (abbreviated), git branch, cache, cost, sources
- **Quick Input**: typing a task auto-spawns agent (no dialog needed)
- **`:cd ~/dir`**: changes TUI working directory, updates status bar
- **`:sessions`**: lists recent sessions
- **`:model X`**: switch model for next spawn
- **SpawnDialog**: simplified (type, model, dir, task) with smart defaults

### Directory Navigation
- AgentWorker does `os.chdir()` to configured CWD
- All filesystem tools use relative/absolute paths
- `list_dir` + `read_file` for project exploration
- Git branch auto-detected in status bar

## ⏳ NEXT (priority order)

### 1. Permission Preview Gate
- Intercept `edit_file`, `write_file`, `shell_exec` in AgentWorker
- Show diff/command preview in TUI PermissionModal
- Human approves with a/A/d keys
- **Impact**: Safety — no blind file edits
- **Estimate**: 2h

### 2. Token Streaming
- Use Ollama streaming API (`stream=True`) directly
- Tokens appear in AgentLane in real-time (not after completion)
- Thinking token stream separate from response stream
- **Impact**: UX — see agent "thinking" live
- **Estimate**: 2h

### 3. SmartRouter (Model Fallback)
- qwen3:14b → ministral-3:8b → Gemini free tier
- Cost-based routing rules
- Auto-retry with different model on error
- **Impact**: Reliability + cost optimization
- **Estimate**: 2h

### 4. Session Picker (TUI overlay)
- `:sessions` shows pickable list (not just text)
- Enter selects, spawns agent with full history
- Visual: list with labels, entry counts, dates
- **Impact**: Usability — no UUID typing
- **Estimate**: 1h

### 5. ContextBundle (Auto Context Injection)
- Inject git status, project tree, recent commits into system prompt
- Agent knows "where it is" automatically
- **Impact**: Agent effectiveness
- **Estimate**: 1h

## Architecture (current)

```
┌─────────────────────────────────────────────────────────────────┐
│                        AIWorkspaceApp (TUI)                      │
│                                                                  │
│  StatusBar: ~/project git:main  qwen3:14b  💾 4e  $0.001       │
│                                                                  │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ TaskPanel│  │ AgentLane(s) │  │  CommandBar              │  │
│  │ (left)   │  │ (center)     │  │  Type task → auto-spawn  │  │
│  └──────────┘  └──────┬───────┘  └──────────────────────────┘  │
│                       │                                         │
│                  ┌────┴─────┐                                   │
│                  │AgentWorker│  ThreadPoolExecutor              │
│                  │ (@work)   │  ┌─────────────────┐            │
│                  └────┬─────┘  │ crew.kickoff()   │            │
│                       │        │ + stdout capture │            │
│                  ┌────┴─────┐  │ + session inject │            │
│                  │asyncio   │  └─────────────────┘            │
│                  │Queue     │                                   │
│                  └──────────┘                                   │
│                                                                  │
│  Overlays: SpawnDialog, CommandPalette, PermissionModal, Toast  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PersistentAgentSession                         │
│                                                                  │
│  SessionStore (PostgreSQL)                                       │
│  ├── sessions table                                              │
│  ├── session_entries (id/parentId tree)                         │
│  └── JSONL import/export (pi-compatible)                        │
│                                                                  │
│  Compaction: auto-summarize when context window nears limit     │
└─────────────────────────────────────────────────────────────────┘
```
