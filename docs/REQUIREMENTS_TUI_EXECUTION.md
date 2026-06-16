# TUI Real Execution Architecture

## Goal
Transform the TUI from a "dashboard with fake data" into a real agent operations center where users spawn agents, watch them work live, and interact with them — replacing pi as the primary interface.

## Current State vs Target

```
┌─────────────────────────┐    ┌─────────────────────────┐
│      CURRENT            │    │       TARGET            │
├─────────────────────────┤    ├─────────────────────────┤
│ Demo data               │    │ Real agents executing   │
│ Fake output             │    │ Live stdout streaming   │
│ Spawn creates widget    │    │ Spawn runs crew.kickoff │
│ Quick input = notify    │    │ Quick input = agent msg │
│ Ctrl+S = empty lane     │    │ Ctrl+S = working agent  │
└─────────────────────────┘    └─────────────────────────┘
```

## Requirements

### R1 — Agent Execution in Background
Agents must run in a Textual `@work` coroutine so the TUI remains responsive.
- Output is captured via `contextlib.redirect_stdout` + custom stream
- Each line is pushed to an `asyncio.Queue`
- A `set_interval` consumer drains the queue into the AgentLane

### R2 — Real-Time Output Streaming
- Agent stdout → TUI AgentLane with <100ms latency
- Tool calls shown inline: `> read_file: src/core/cost.py`
- Tool results shown inline: `  ✅ 47 lines read`
- Thinking stream toggleable per lane (Ctrl+T)

### R3 — Agent Lifecycle Management
- Spawn: `Ctrl+S` → select type (coding/research/general) → runs real agent
- Pause: `Space` on focused lane → suspend agent
- Resume: `Space` again → resume
- Kill: `Ctrl+X` on focused lane → abort agent
- Auto-cleanup: agent finishes → lane stays (with final output) + "🟢 Done" status

### R4 — Interactive Chat Mode
- Quick input sends messages to the focused agent
- Agent responds in real-time in its lane
- History preserved (scrollable)
- Supports multi-turn within same lane

### R5 — Command Integration
All CLI commands accessible from TUI without leaving:

| Key | Command | Action |
|-----|---------|--------|
| `:` | Command palette | `:search`, `:cache stats`, `:source check` |
| `Ctrl+R` | Research | Opens research overlay, runs deep_search |
| `Ctrl+P` | Project | Shows worktree panel |
| `Ctrl+M` | Model | Switch active model (qwen3/ministral/gemini) |
| `Ctrl+C` | Cache | Shows cache stats overlay |

### R6 — Project/Worktree Integration
- Left panel shows active worktrees (from `ProjectManager`)
- Spawn dialog includes "project" selector
- Agent works in isolated worktree
- Worktree cleanup visible in panel

### R7 — Multi-Agent Orchestration
- Multiple agents can run simultaneously (each in own lane)
- Agents can delegate to each other via messages
- Human can @mention agent in quick input to route messages

### R8 — Persistent Session State
- TUI layout, agent outputs, task states survive restart
- Stored in SQLite/JSON in `~/.aiw/tui-state.json`
- On reconnect, lanes restored with last output

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AIWorkspaceApp                            │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ TaskPanel│  │ AgentLane(s) │  │  CommandBar              │  │
│  │ (left)   │  │ (center)     │  │  (bottom)                │  │
│  └────┬─────┘  └──────┬───────┘  └────────────┬─────────────┘  │
│       │               │                        │                │
│       │         ┌─────┴─────┐                  │                │
│       │         │AgentWorker│◄─────────────────┘                │
│       │         │(@work)    │   (spawn, message, pause)        │
│       │         └─────┬─────┘                                   │
│       │               │                                         │
│       │         ┌─────┴─────┐                                   │
│       │         │async Queue│  (line-by-line output)            │
│       │         └─────┬─────┘                                   │
│       │               │                                         │
│       └───────────────┘                                         │
│              AgentLane.set_interval(50ms) → drain_queue()       │
└─────────────────────────────────────────────────────────────────┘

AgentWorker.run_agent(task, project, model):
  1. Create worktree if project specified
  2. Build crew with tools based on agent_type
  3. Redirect stdout to QueueStream
  4. crew.kickoff() in executor
  5. Push each line to queue
  6. On finish: push "✅ Done" to queue
  7. Cleanup worktree if auto_cleanup
```

## Data Flow

```
User presses Ctrl+S
  → SpawnDialog opens
  → User fills: type=coding, project=main, task="fix auth"
  → on_spawn:
    - Create AgentLane in UI
    - Create AgentWorker
    - worker.run_agent(task, project, model)
    
AgentWorker
  → Starts crew in executor
  → Crew uses tools (read_file, edit_file, git_commit)
  → Each print/stdout → QueueStream.write() → queue.put()
  
AgentLane (set_interval 50ms)
  → drain_queue()
  → For each line: append_output(line)
  → _refresh_output() updates Label widget
  
User types in quick input + Enter
  → on_quick_input()
  → If agent focused: worker.send_message(text)
  → Message appended to agent's task context
  → Agent continues with new context
```

## Implementation Plan

### Phase 1 — AgentWorker Foundation (1-2h)
- [ ] Create `AgentWorker` class in `tui/worker.py`
  - `__init__(lane_id, agent_type, project, model)`
  - `QueueStream` class that wraps `asyncio.Queue`
  - `run_agent(task)` coroutine with `asyncio.to_thread()`
  - `send_message(text)` to inject user messages
  - `pause()`, `resume()`, `kill()` lifecycle methods
- [ ] Modify `AgentLane` to:
  - Accept `AgentWorker` reference
  - `set_interval(0.05, self._drain_queue)`
  - `_drain_queue()` pops from worker.queue, appends to output
  - Show status: "⏳ Running", "⏸ Paused", "🟢 Done", "🔴 Error"

### Phase 2 — Spawn Real Agents (1h)
- [ ] Update `SpawnDialog.Spawn` handler:
  - Create `AgentWorker` with actual `coding_crew()` or `create_agent()`
  - Route output to AgentLane via queue
  - Set lane status to "ongoing"
- [ ] Remove `_add_demo_output()` entirely
- [ ] Add `AgentLane` lifecycle: paused, killed, completed

### Phase 3 — Interactive Quick Input (30min)
- [ ] Route quick input to focused agent's worker
- [ ] `worker.send_message(text)` appends to ongoing task
- [ ] Multi-turn chat preserved in lane output

### Phase 4 — Command Palette Integration (1h)
- [ ] Add commands: `:search`, `:cache`, `:source`, `:project`
- [ ] `:search "query"` → opens overlay with DeepSearchEngine
- [ ] Results shown in new "research" lane or panel
- [ ] `:cache stats` → overlay with cache metrics

### Phase 5 — Project Panel (1h)
- [ ] New panel `ProjectPanel` (left, below TaskPanel)
- [ ] Shows `ProjectManager.list_projects()`
- [ ] Shows active worktrees
- [ ] Spawn dialog includes project dropdown

### Phase 6 — State Persistence (1h)
- [ ] Save `tui-state.json` on exit
- [ ] Restore lanes on startup (without re-running agents)
- [ ] Save output lines, status, task name

## Files to Create/Modify

```
NEW:
  src/ai_workspace/tui/worker.py       — AgentWorker, QueueStream
  src/ai_workspace/tui/commands.py     — Command router for palette
  src/ai_workspace/tui/persistence.py  — State save/restore
  
MODIFY:
  src/ai_workspace/tui/widgets.py      — AgentLane: queue drain, status
  src/ai_workspace/tui/app.py          — Spawn real agents, quick input route
  src/ai_workspace/tui/data.py         — Project/worktree data loaders
```

## Success Criteria

- [ ] User spawns coding agent via Ctrl+S → agent actually edits files
- [ ] User sees real-time output in lane (file reads, edits, test runs)
- [ ] User can pause/resume agent with Space
- [ ] User can send messages to running agent via quick input
- [ ] `:search "topic"` runs deep research and shows results
- [ ] All without TUI freezing
- [ ] Output persists after agent completes
