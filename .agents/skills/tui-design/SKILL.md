---
name: tui-design
description: Design and implement Textual TUI interfaces for terminal applications. Use when building terminal dashboards, agent interfaces, chat UIs, or any terminal-based user interface. Covers research-backed design principles, Textual-specific patterns, common pitfalls, and implementation recipes.
compatibility: Requires Textual >= 8.0 Python framework. Works with crewAI agents, PostgreSQL, and async workers.
metadata:
  framework: textual
  language: python
  research_sources: lazygit, Posting.sh, Open Interpreter, Textual docs
  principles: discoverability, simplicity, safety, keyboard-first, reactive
---

# TUI Design — Textual Terminal Interfaces

Systematic process for designing and implementing terminal user interfaces using Python's Textual framework. Based on research of successful TUIs (lazygit, Posting, Open Interpreter) and real-world Textual apps.

## When to Use

- Building a terminal dashboard for AI agents / data
- Designing a chat interface with LLM
- Creating a monitoring/status TUI
- Replacing complex CLI commands with visual interface
- User says "TUI", "terminal dashboard", "Textual app"

## Research: What Makes a TUI Great

### lazygit — 7 Design Principles (Jesse Duffield)
1. **Discoverability** — Users should see what they can do without reading docs
2. **Simplicity** — One screen, one purpose; don't cram everything
3. **Safety** — Confirm destructive actions; never lose user's work
4. **Power** — Keyboard-first; power users should fly
5. **Speed** — < 100ms response on any action
6. **Conformity** — Use established patterns (vim keys, git terminology)
7. **Sustainability** — Codebase must be maintainable

### Posting.sh (Darren Burns, Textual-based, 15k+ stars)
- **Local-first** — Filesystem as database, no server needed
- **Reactive** — State changes auto-trigger UI updates via `reactive()`
- **Panel layout** — Main content + collapsible sidebars, not tabs overload
- **Configurable** — Custom keymaps, themes, Python scripting for extensibility
- **Discoverable** — Help bar always visible with current context actions

### Open Interpreter (CLI AI Agent)
- **REPL-style** — Simple input → response loop, not multi-tab complex UI
- **Slash commands** — `/model`, `/plan`, `/diff` for configuration within flow
- **Markdown rendering** — Rich text for agent responses (code blocks, tables)
- **User approval** — Confirmation before executing code (safety principle)

---

## Phase 1: Understand

### 1.1 Key Questions

- **What's the ONE primary action?** (chat, monitor, browse, configure?)
- **What information must be visible at all times?** (model name, cost, status?)
- **What actions are frequent?** (keyboard shortcuts for top 3 actions)
- **What actions are rare?** (hide in menus/overlays, not permanent tabs)
- **Is it keyboard-first or mouse-friendly?** (TUI = keyboard-first)

### 1.2 Anti-Patterns (from aiw v1/v2 failures)

| Anti-pattern | Why it fails | Fix |
|-------------|-------------|-----|
| **7+ tabs with empty content** | Users see dead screens, lose trust | 1 main screen + overlays |
| **Dashboard with 6 cards, all "No data"** | Wasted space, no value | Show only what has data |
| **Spawning agents requires PostgreSQL + crewAI + Ollama** | Too many failure points | Graceful degradation |
| **Silent `except: pass` everywhere** | Bugs invisible, hard to debug | Log errors, show fallback UI |
| **Complex multi-panel layout** | Terminal space is scarce (80×24) | Single primary panel + bottom bar |

---

## Phase 2: Design

### 2.1 Layout Patterns

**Pattern A: Chat-first (for AI agents)**
```
┌─ Header: workspace, model, cost, time ──────────────────────────┐
│                                                                  │
│  Conversation area (scrollable)                                  │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ User: Research Rust async                                    ││
│  │ Agent: Here's what I found...                                ││
│  │ (markdown, code blocks, tool calls)                          ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  > Input...                                      [Enter] send    │
├──────────────────────────────────────────────────────────────────┤
│  /search  /code  /files  /git  /model  /help      Ctrl+Q quit   │
└──────────────────────────────────────────────────────────────────┘
```
**Best for:** AI agent interaction, coding assistants, research tools

**Pattern B: Dashboard (for monitoring)**
```
┌─ Header: workspace, status, time ───────────────────────────────┐
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │ Agents: 3   │ │ Tasks: 12  │ │ Cost: $0.05│ │ Cache: 85% │   │
│  │ ● running   │ │ ● active   │ │ today      │ │ hit rate   │   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│                                                                  │
│  ┌─ Active Agents ──────────────────────────────────────────┐   │
│  │ coding-1  ● running  Fix auth middleware       80%       │   │
│  │ research  ● running  MCP tools comparison      40%       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─ Recent Activity ────────────────────────────────────────┐   │
│  │ 20:45  ✓ Research completed: "Rust async vs Go"          │   │
│  │ 20:30  ✗ Agent error: Ollama timeout                    │   │
│  └──────────────────────────────────────────────────────────┘   │
├──────────────────────────────────────────────────────────────────┤
│  Ctrl+S spawn  Ctrl+R research  Ctrl+F find  Ctrl+Q quit        │
└──────────────────────────────────────────────────────────────────┘
```
**Best for:** Operations center, system monitoring, multi-agent view

**Pattern C: Single-panel browser (for exploring)**
```
┌─ Header: path, filter ──────────────────────────────────────────┐
│  📁 src/ai_workspace/                                           │
│    📁 agents/                                                   │
│      📄 orchestrator.py      12KB   modified                    │
│      📄 router.py             8KB                               │
│    📁 core/                                                    │
│      📄 cost.py              15KB                               │
│    📁 tui/                                                     │
│      📄 app.py               28KB   modified                    │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│  Enter open  Space select  / filter  Ctrl+Q quit                │
└──────────────────────────────────────────────────────────────────┘
```
**Best for:** File browsers, knowledge graphs, git log

### 2.2 Navigation Architecture

Use a **Router pattern** — one primary screen, overlays for secondary views:

```python
# Main app: ChatScreen (always visible)
# Overlays (ModalScreen): FileBrowser, GitPanel, SearchDialog, HelpScreen

class AIWorkspaceApp(App):
    def action_open_files(self):
        self.push_screen(FileBrowser())

    def action_open_git(self):
        self.push_screen(GitPanel())
```

This is better than tabs+ContentSwitcher because:
- No empty tabs visible
- Context-preserving (chat stays underneath)
- Escape to dismiss (natural mental model)
- Less DOM complexity

---

## Phase 3: Textual Implementation Patterns

### 3.1 Valid CSS Colors (Textual 8.x)

```css
/* ✅ VALID — built-in ANSI colors */
$text, $text-disabled  /* ⚠️ DOES NOT EXIST in 8.x! */
$primary, $secondary, $accent
$error, $warning, $success
$background, $surface, $panel, $boost

/* ✅ VALID — opacity modifiers (CSS only, NOT Python code) */
$text 40%
$primary 20%
$background 80%

/* ✅ VALID — explicit colors */
#888888, #ff0000
rgb(128,128,128)
rgba(255,0,0,0.5)

/* ❌ INVALID — do not use */
$text-muted       # doesn't exist
$text-disabled    # doesn't exist
$dimmed           # doesn't exist

/* ✅ PYTHON CODE — styles.color assignment */
widget.styles.color = "#888888"        # explicit hex
widget.styles.color = "grey"           # color name
widget.styles.color = "rgb(128,128,128)"  # rgb
# ❌ widget.styles.color = "$text 40%"  # CSS syntax >não< funciona em Python!
```

### 3.2 Tab IDs Must Be Explicit

```python
# ❌ WRONG — Textual auto-generates IDs like "tab-1"
Tabs("Dashboard", "Agents", "Tasks")

# ✅ CORRECT — explicit IDs that handlers can match
from textual.widgets import Tab, Tabs
Tabs(
    Tab("Dashboard", id="dashboard"),
    Tab("Agents", id="agents"),
    Tab("Tasks", id="tasks"),
)

# Handler
@on(Tabs.TabActivated, "#main-tabs")
def on_tab(self, event):
    if event.tab.id == "dashboard":  # Now matches!
        ...
```

### 3.3 Reactive State Pattern

```python
from textual.reactive import reactive

class MyWidget(Static):
    data: reactive[list[dict]] = reactive([])

    def update_data(self, new_data):
        self.data = new_data  # Automatically triggers render()

    def render(self):
        if not self.data:
            return "No data yet."
        return "\n".join(str(d) for d in self.data)
```

### 3.4 Worker Thread Pattern

```python
from textual import work

class MyApp(App):
    @work(thread=True)
    async def heavy_task(self):
        # Runs in background thread
        result = slow_api_call()
        self.call_from_thread(self.update_ui, result)

    def update_ui(self, result):
        # Runs on main thread — safe to modify UI
        self.query_one("#output").update(str(result))
```

### 3.5 ModalScreen for Dialogs

```python
from textual.screen import ModalScreen

class ConfirmDialog(ModalScreen):
    CSS = """
    ConfirmDialog {
        align: center middle;
    }
    #dialog {
        width: 40;
        height: auto;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }
    """

    def compose(self):
        with Static(id="dialog"):
            yield Static("Are you sure?")
            with Horizontal():
                yield Button("Yes", variant="primary")
                yield Button("No", variant="error")

# Usage
self.push_screen(ConfirmDialog(), callback=self.on_confirm)
```

### 3.6 Debugging Textual Apps

```python
# Enable devtools (Ctrl+P for command palette)
import os
os.environ["TEXTUAL_DEVTOOLS"] = "1"

# Enable logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Run with textual CLI for hot-reload
# textual run --dev app.py

# NEVER do this — hides all bugs:
try:
    self.query_one("#widget").update(data)
except Exception:
    pass  # ❌ Bug invisible!

# DO this instead:
import logging
log = logging.getLogger(__name__)
try:
    self.query_one("#widget").update(data)
except Exception as e:
    log.warning("Failed to update widget: %s", e)
    # Show fallback in UI
    self.notify(f"Error loading data: {e}", severity="error")
```

---

## Phase 4: Common Pitfalls & Solutions

| Pitfall | Symptom | Solution |
|---------|---------|----------|
| `$text-muted` / `$text-disabled` | `ColorParseError` crash | Use `#888888` or `$text 40%` (CSS only) |
| Tab IDs auto-generated | Tabs don't switch content | Use `Tab("Label", id="explicit-id")` |
| `PYTHONPATH=src` replaces all paths | `ModuleNotFoundError` | Use `sys.path.insert(0, "src")` instead |
| `nix build` uses git HEAD | Old code in binary | Commit before building |
| ContentSwitcher children not mounted | Empty screens on tab switch | All children mount; check CSS `height: 1fr` |
| `asyncio.create_task` fail silent | Agent spawns but doesn't run | Add logging to worker.start_loop |
| crewAI import fails (no libstdc++) | Agent crashes on spawn | Use nix-shell for LD_LIBRARY_PATH |
| `app.run()` exits immediately | No terminal output | Check `isatty()` — needs real terminal |

---

## Phase 5: Testing TUI Apps

```python
# Unit test — verify widget renders
def test_widget_render():
    widget = MyWidget()
    widget.data = [{"name": "test"}]
    result = widget.render()
    assert "test" in str(result)

# Integration test — verify compose
from textual.app import App
async def test_app_compose():
    app = MyApp()
    async with app.run_test() as pilot:
        assert pilot.app.query_one("#header")
        await pilot.press("ctrl+q")

# CSS validation
def test_css_valid():
    app = MyApp()
    # Textual validates CSS on mount
    # If invalid colors, raises ColorParseError
```

---

## Quick Recipes

### Chat Interface
```
Phase 1 → One primary action: chat with agent
Phase 2 → Header + ScrollableChat + InputBar + HelpBar
Phase 3 → ChatMessage (user/agent/thinking/tool), ChatInput, HelpBar
Phase 4 → Textual Static + Input + reactive message list
```

### Agent Monitor
```
Phase 1 → Show running agents, tasks, costs
Phase 2 → StatsRow + AgentList + ActivityFeed + BottomBar
Phase 3 → AgentCard, StatBadge, ActivityItem
Phase 4 → Reactive data from AgentWorker queues
```

### File Browser
```
Phase 1 → Browse project files with git status
Phase 2 → Header + FileTree + DetailPanel
Phase 3 → FileNode, GitBadge, PreviewPane
Phase 4 → Directory listing + syntax highlight
```

---

## Resources

- [Textual Documentation](https://textual.textualize.io/) — Official docs
- [Textual CSS Reference](https://textual.textualize.io/guide/CSS/) — Valid properties
- [Posting.sh Source](https://github.com/darrenburns/posting) — Production Textual app
- [lazygit VISION.md](https://github.com/jesseduffield/lazygit/blob/master/VISION.md) — Design philosophy
- [Textual Colors](https://textual.textualize.io/guide/design/#colors) — Built-in color names
