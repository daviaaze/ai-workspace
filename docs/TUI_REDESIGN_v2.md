# AI Workspace TUI v2 — Redesign Summary

## Overview

The TUI has been completely redesigned from a fixed 3-pane layout to a **tabbed dashboard architecture** with dedicated views for each major concern, plus integrated **git workflow support**.

## Architecture Changes

### Old Layout (v1)
```
┌─ StatusBar ──────────────────────────────────────────────────────────┐
├──────────┬───────────────────────────────┬──────────────────────────┤
│ TASKS    │  AGENT LANE 1  │ AGENT LANE 2 │  (horizontal lanes)      │
│ sidebar  │                               │                          │
├──────────┴───────────────────────────────┴──────────────────────────┤
│ Command bar + keybinding hints                                       │
└──────────────────────────────────────────────────────────────────────┘
```

**Problems:**
- Cramped task sidebar (28 chars)
- Horizontal agent lanes don't scale past 2-3 agents
- Weak visual hierarchy
- Everything crammed into one screen
- No overview/dashboard

### New Layout (v2)
```
┌─ HeaderBar ──────────────────────────────────────────────────────────┐
│ [🏠] [🤖] [📋] [] [💬] [🔍] [📊]  ws:~/project  git:main ↑2  $0.004 │
├─ ContentSwitcher ────────────────────────────────────────────────────┤
│                                                                      │
│  Dashboard / Agents / Tasks / Git / (Chat+Search+Metrics as overlays)│
│                                                                      │
├─ BottomBar ──────────────────────────────────────────────────────────┤
│ ⚡ 2/2 agents  [^S] spawn  [^N] task  [^F] find  [^W] ws  [^Q] quit  │
└──────────────────────────────────────────────────────────────────────┘
```

## New Components

### 1. HeaderBar (`header.py`)
- **Two-row header**: Logo/workspace/git on top, tab navigation below
- **Git info integrated**: branch, ahead/behind arrows (↑↓), modified/staged counts
- **Collapsible**: Would collapse to single row on very narrow terminals
- **7 tabs**: Dashboard, Agents, Tasks, Git, Chat, Search, Metrics

### 2. DashboardView (`dashboard.py`)
The new home screen with **5 cards** in a responsive 2-column grid:

| Card | Content |
|------|---------|
| 🤖 Agents | Compact table of all agents with status, progress, task |
| 📋 Tasks | Recent + active tasks with progress indicators |
| 📊 Quick Stats | Cost, tokens saved, cache hits, active counts |
|  Git | Branch, sync status, change summary |
| 📡 Activity | Unified event log with timestamps and severity |
| ⚡ Quick Actions | Spawn, New Task, Search, Workspace buttons |

### 3. AgentsView (`agent_grid.py`)
Replaces horizontal lanes with a **scalable list+detail layout**:
- **Left (40 cols)**: Sortable DataTable of agents — name, status, progress, task
- **Right**: Detail panel for selected agent (diff view placeholder)
- **Toolbar**: Spawn / Pause / Kill / Chat buttons + filter dropdown
- **Status filters**: All / Running / Done / Blocked / Idle

### 4. TasksView (`task_table.py`)
Full-featured task management:
- **DataTable** with columns: Status, Title, Agent, Progress, Priority, Schedule
- **Toolbar**: New / Toggle / Delete + text filter + status filter
- **Row count**: "Showing X/Y tasks" indicator
- **Inline progress bars**: Visual progress in table cells

### 5. GitPanel (`git_panel.py`) — **NEW**
Complete git workflow integration:
- **Status bar**: Branch, upstream, ahead/behind, commit hash, change counts
- **Working tree**: Modified / Staged / Untracked file tables (click to diff)
- **Diff view**: Right panel showing colored diff for selected file
- **Commit log**: Recent commits with hash, message, author, date
- **Actions**: Pull / Push / Stash / Commit / Refresh buttons
- **Keyboard**: `^R` refresh, `Enter` diff, `p` pull, `P` push, `c` commit

### 6. BottomBar (`bottom_bar.py`)
Context-aware footer:
- **Left**: Live agent status (⚡ 2/2 agents, 📨 pending, 🔒 permissions)
- **Center**: Keybinding hints that change per tab
- **Right**: Quick command input (`/task`, `:command`, or message)

## Git Integration Details

### Header Bar Git Info
```
 main  ↑2  ↓1  ~3  +1        (branch, ahead, behind, modified, staged)
```

### Git Dashboard Card
Shows at-a-glance:
- Current branch with sync arrows
- Commit hash (short)
- Change summary: "3 modified  1 staged  0 untracked"
- Or "Working tree clean" when clean

### Git Tab (Full View)
```
┌─  main ↑2 ↓1  abc1234  [Pull] [Push] [Stash] [Commit] [Refresh] ──┐
├──────────────────────────┬──────────────────────────────────────────┤
│ Modified                 │ Diff: src/auth.py                        │
│  M  src/auth.py          │ ─────────────────────────────────────    │
│  M  src/middleware.py    │  - raise ExpiredTokenError               │
│                          │  + return False                          │
│ Staged                   │                                          │
│  A  README.md            │                                          │
│                          │                                          │
│ Recent Commits           │                                          │
│  abc1234 Fix auth bug    │                                          │
│  def5678 Add tests       │                                          │
└──────────────────────────┴──────────────────────────────────────────┘
```

## Data Flow

```
_load_data()
    ├── HeaderBar (workspace, git, model, tasks, agents, cost)
    ├── DashboardView (agents, tasks, stats, git, activity)
    ├── AgentsView (agent list)
    ├── TasksView (task table)
    ├── GitPanel (branch, status, commits)  ← NEW
    └── BottomBar (agent status)
```

## Keybindings (Preserved + Added)

| Key | Action |
|-----|--------|
| `Tab` | Cycle focus / switch tabs |
| `^S` | Spawn agent dialog |
| `^N` | New task |
| `^D` | Detail view (focused agent) |
| `^W` | Workspace switcher |
| `^P` | Permissions |
| `^F` | Fuzzy finder |
| `^G` | Knowledge graph |
| `^E` | Context workbench |
| `^M` | Metrics overlay |
| `^L` | Cycle layout |
| `^R` | **Refresh git status** ← NEW |
| `Space` | Pause/resume agent |
| `^X` | Kill agent (double-press) |
| `^Enter` | Chat screen |
| `:` | Command palette |
| `q` | Quit |
| `F1` / `?` | Help |

## Files Changed

### New Files
- `src/ai_workspace/tui/header.py` — HeaderBar with tabs
- `src/ai_workspace/tui/dashboard.py` — DashboardView + cards
- `src/ai_workspace/tui/agent_grid.py` — AgentsView (list+detail)
- `src/ai_workspace/tui/task_table.py` — TasksView (DataTable)
- `src/ai_workspace/tui/git_panel.py` — GitPanel (status, diff, log)
- `src/ai_workspace/tui/bottom_bar.py` — BottomBar (context hints)

### Modified Files
- `src/ai_workspace/tui/app.py` — Complete rewrite with tabbed layout
- `src/ai_workspace/tui/__init__.py` — Export new components
- `tests/test_tui/test_app.py` — Updated for new widgets

### Backed Up
- `src/ai_workspace/tui/app_legacy.py` — Original app.py preserved

## Running the New TUI

```bash
# From project root
python -m ai_workspace.tui.app

# Or if installed
aiw tui
```

## Migration Notes

1. **Screens preserved**: ChatScreen, DetailScreen, SpawnDialog, HelpScreen, ContextWorkbench, KnowledgeGraph all work unchanged
2. **Overlays preserved**: PermissionModal, CommandPalette, FuzzyFinder, AgentMetrics, WorkspaceSwitcher, Toast all still functional
3. **AgentLane widget preserved**: Still used internally for agent output streams
4. **Data layer unchanged**: `load_tasks()`, `load_metrics()`, `load_agent_status()` still used
5. **Worker system unchanged**: AgentWorker, AgentConfig, context_manager all preserved

## Future Enhancements

- [ ] Git commit dialog with message input
- [ ] Git branch creation/switching UI
- [ ] Interactive rebase visualization
- [ ] Stash list with apply/pop
- [ ] Agent output streaming in the new AgentsView detail panel
- [ ] Task detail view (click task to see full info)
- [ ] Dark/light theme toggle
- [ ] Customizable dashboard card layout
