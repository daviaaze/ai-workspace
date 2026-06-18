# TUI Graveyard

These files were part of TUI v2, v3, and v4 experiments. They are kept for reference.

Some will be resurrected as overlays (ModalScreen) in TUI v5:
- `dashboard.py` → DashboardScreen (F3 overlay)
- `git_panel.py` → GitScreen (Ctrl+G overlay)
- `task_table.py` → TasksScreen (overlay)
- `agent_grid.py` → AgentGrid component

Others are replaced by new specs:
- `header.py` → replaced by SPEC_TUI_V5 Header component
- `bottom_bar.py` → replaced by HelpBar
- `help.py` → replaced by HelpScreen overlay
- `metrics.py` → replaced by MetricsBar
- `context_graph_panel.py` → replaced by Context Inspector (F4)
- `side_panel.py` → replaced by overlays
- `research_queue.py` → replaced by SPEC_DEEP_RESEARCH_V2
- `agent_inventory.py` → replaced by AgentMonitor
- `data.py` → data layer, no longer used
- `cyberdeck.tcss` → v4 theme, replaced by v5 professional theme

**Do NOT import from this directory. These files are not maintained.**
