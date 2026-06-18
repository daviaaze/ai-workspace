# TUI Design Patterns — Research Summary

## Reference TUIs

### lazygit (Go, gocui) — 2022-present
- **Stars:** 55k+
- **Author:** Jesse Duffield
- **Design doc:** [VISION.md](https://github.com/jesseduffield/lazygit/blob/master/VISION.md)
- **Key takeaway:** 7 principles (discoverability, simplicity, safety, power, speed, conformity, sustainability). Single-purpose screens, contextual help always visible, vim keys as standard.

### Posting (Python, Textual) — 2024-present
- **Stars:** 15k+
- **Author:** Darren Burns
- **Design:** Local-first HTTP client. Filesystem as DB. Reactive state. Panel layout. Configurable keymaps/themes.
- **Key takeaway:** Clean layout, no tab overload, extensible via Python config, help bar with context.

### Open Interpreter (Python, Rich) — 2023-present
- **Stars:** 60k+
- **Design:** REPL-style AI agent. Slash commands for config. Markdown rendering. User approval for code execution.
- **Key takeaway:** Simple input→response loop works better than complex multi-panel for AI interaction.

### k9s (Go) — Kubernetes dashboard
- **Design:** Single-purpose screens (pods, logs, events). Vim navigation. `/` filter. `:command` palette.
- **Key takeaway:** Vim-style slash commands + colon commands are intuitive for developers.

## Anti-Patterns Observed (aiw v1/v2)

### 1. Tab Overload
- 7 tabs, 5 empty → user sees dead screens
- Fix: 1 main screen + modal overlays for secondary actions

### 2. Dashboard with No Data
- 6 stat cards all showing "No data" / zeros
- Fix: Don't show what doesn't exist; show meaningful defaults or hide

### 3. Silent Exception Handling
- `except Exception: pass` on every UI update → bugs invisible
- Fix: Log errors, show Toast notifications for failures

### 4. Premature Feature Complexity
- ContextWorkbench (582 lines), KnowledgeGraph (752 lines) before basic chat works
- Fix: Build the PRIMARY feature first, then add secondary features

### 5. Hard Dependency Chain
- Spawn agent → need PostgreSQL → need session → need crewAI → need Ollama
- Fix: Graceful degradation; allow "offline mode" without DB

## Design Patterns That Work

### Pattern 1: Chat-first Layout
```
[Header: model, cost, time]
[Scrollable conversation]
[Input bar with help hints]
```
Best for: AI agents, coding assistants

### Pattern 2: Card Dashboard
```
[Stat cards row]
[Main content (table/list/graph)]
[Activity feed]
[Bottom bar: keybindings]
```
Best for: Monitoring, multi-agent view

### Pattern 3: Modal Overlay Navigation
```
[Main screen: always visible]
  ├── push_screen(Search)
  ├── push_screen(Files)
  └── push_screen(Settings)
```
Best for: Secondary actions, settings, exploration

## Terminal Constraints

- **Screen size:** 80×24 (minimum), 120×40 (typical), 200×60 (large)
- **Font:** Monospace only (no variable-width text)
- **Colors:** 16 (ANSI), 256 (extended), or 16M (true color — Textual default)
- **No mouse required** — everything must work with keyboard
- **No images** — pure text rendering
- **Scrollback not available** — Textual uses alternate screen buffer
