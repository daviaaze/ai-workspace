"""
AI Workspace TUI — Rich terminal dashboard built with Textual.

Features:
- Tabbed interface: Overview, Research, Tasks, Workflows, Logs
- Live metrics (research count, tasks, confidence)
- Keyboard navigation (vim-style: j/k, tab, /)
- Inline markdown rendering
- Auto-refresh (configurable interval)
- Color themes based on status

Run: aiw tui
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table as RichTable
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Log,
    ProgressBar,
    Static,
    TabbedContent,
    TabPane,
)
from textual.worker import Worker, WorkerState


class MetricWidget(Static):
    """A single metric display (value + label)."""

    def __init__(self, label: str, value: str = "—", color: str = "cyan"):
        super().__init__()
        self.metric_label = label
        self.metric_value = value
        self.color = color

    def render(self) -> Panel:
        return Panel(
            f"[bold {self.color}]{self.metric_value}[/]",
            title=self.metric_label,
            border_style="dim",
        )


class AIWorkspaceTUI(App):
    """Main TUI application for AI Workspace."""

    CSS = """
    MetricWidget {
        width: 1fr;
        height: 5;
        margin: 1;
    }
    
    #metrics-row {
        height: 6;
        margin-bottom: 1;
    }
    
    DataTable {
        height: 1fr;
    }
    
    #log-output {
        height: 1fr;
        background: $surface;
    }
    
    #command-input {
        dock: bottom;
        margin: 1;
    }
    
    .status-done { color: green; }
    .status-failed { color: red; }
    .status-running { color: yellow; }
    .status-pending { color: gray; }
    """

    TITLE = "AI Workspace"
    SUB_TITLE = "Deep Search • Agent Swarm • Knowledge Base"

    refresh_interval = reactive(5)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

        with TabbedContent():
            # ─── Tab 1: Overview ───
            with TabPane("📊 Overview", id="overview"):
                with Horizontal(id="metrics-row"):
                    yield MetricWidget("Research (24h)", "—", "cyan")
                    yield MetricWidget("Tasks Pending", "—", "yellow")
                    yield MetricWidget("Avg Confidence", "—", "green")
                    yield MetricWidget("Agent Memories", "—", "magenta")

                with Horizontal():
                    with Vertical(id="recent-research"):
                        yield Static("[bold]Recent Research[/]", id="research-title")
                        yield DataTable(id="research-table", cursor_type="row")
                    
                    with Vertical(id="recent-tasks"):
                        yield Static("[bold]Pending Tasks[/]", id="tasks-title")
                        yield DataTable(id="tasks-table", cursor_type="row")

            # ─── Tab 2: Research ───
            with TabPane("🔍 Research", id="research"):
                yield Input(
                    placeholder="Enter research query...",
                    id="research-query",
                )
                with Horizontal():
                    yield Button("Deep Search (depth 2)", id="btn-search", variant="primary")
                    yield Button("Quick Research (depth 1)", id="btn-quick")
                
                yield DataTable(id="history-table", cursor_type="row")

            # ─── Tab 3: Tasks ───
            with TabPane("📋 Tasks", id="tasks"):
                with Horizontal():
                    yield Input(placeholder="New task title...", id="task-input")
                    yield Button("Add Task", id="btn-add-task", variant="primary")
                
                yield DataTable(id="all-tasks-table", cursor_type="row")

            # ─── Tab 4: Workflows ───
            with TabPane("🔄 Workflows", id="workflows"):
                yield DataTable(id="workflow-runs-table", cursor_type="row")
                with Horizontal():
                    yield Button("Refresh", id="btn-refresh-wf")
                    yield Button("Run Deep Research", id="btn-run-research")
                    yield Button("Run Briefing", id="btn-run-briefing")

            # ─── Tab 5: Logs ───
            with TabPane("📜 Logs", id="logs"):
                yield Log(id="log-output", highlight=True)

    # ─── Lifecycle ───────────────────────────────────────

    def on_mount(self) -> None:
        """Called when app starts."""
        self.set_interval(self.refresh_interval, self.refresh_all)
        self.refresh_all()

    # ─── Data fetching ───────────────────────────────────

    def _fetch_metrics(self) -> dict[str, Any]:
        """Fetch current metrics from DB."""
        try:
            from ai_workspace.knowledge import KnowledgeStore
            store = KnowledgeStore()
            store.initialize()
            c = store.conn.cursor()

            c.execute("SELECT COUNT(*) FROM research_entries WHERE created_at > NOW() - INTERVAL '24 hours'")
            r24 = c.fetchone()[0]

            c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
            tp = c.fetchone()[0]

            c.execute("SELECT ROUND(AVG(confidence)::numeric, 2) FROM research_entries WHERE confidence > 0")
            ac = c.fetchone()[0] or 0

            c.execute("SELECT COUNT(*) FROM agent_memory")
            am = c.fetchone()[0]

            c.close()
            store.close()
            return {"research_24h": r24, "tasks_pending": tp, "avg_confidence": ac, "memories": am}
        except Exception:
            return {"research_24h": 0, "tasks_pending": 0, "avg_confidence": 0, "memories": 0}

    def _fetch_recent_research(self, limit: int = 10) -> list[dict]:
        try:
            from ai_workspace.knowledge import KnowledgeStore
            store = KnowledgeStore()
            store.initialize()
            results = store.get_research_history(limit=limit)
            store.close()
            return results
        except Exception:
            return []

    def _fetch_tasks(self, limit: int = 20) -> list[dict]:
        try:
            from ai_workspace.knowledge import KnowledgeStore
            store = KnowledgeStore()
            store.initialize()
            tasks = store.get_tasks(status="pending", limit=limit)
            store.close()
            return tasks
        except Exception:
            return []

    def _fetch_workflow_runs(self, limit: int = 20) -> list[dict]:
        try:
            from ai_workspace.workflow import WorkflowRegistry
            runs = []
            for name in WorkflowRegistry.list():
                wf_cls = WorkflowRegistry.get(name)
                if wf_cls:
                    runs.extend(wf_cls.get_runs(limit=5))
            runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)
            return runs[:limit]
        except Exception:
            return []

    # ─── Refresh ─────────────────────────────────────────

    def refresh_all(self) -> None:
        """Refresh all UI data."""
        self._refresh_metrics()
        self._refresh_research_table()
        self._refresh_tasks_table()
        self._refresh_workflow_table()
        self._refresh_all_tasks_table()

    def _refresh_metrics(self) -> None:
        metrics = self._fetch_metrics()
        
        widgets = self.query(MetricWidget)
        if len(widgets) >= 4:
            widgets[0].metric_value = str(metrics["research_24h"])
            widgets[1].metric_value = str(metrics["tasks_pending"])
            widgets[2].metric_value = f"{metrics['avg_confidence']:.0%}"
            widgets[3].metric_value = str(metrics["memories"])
            for w in widgets:
                w.refresh()

    def _refresh_research_table(self) -> None:
        table = self.query_one("#research-table", DataTable)
        if not table.columns:
            table.add_columns("Query", "Summary", "Confidence")

        table.clear()
        for r in self._fetch_recent_research():
            conf = r.get("confidence", 0) or 0
            conf_str = f"[green]{conf:.0%}[/]" if conf > 0.7 else f"[yellow]{conf:.0%}[/]" if conf > 0.4 else f"[red]{conf:.0%}[/]"
            table.add_row(
                str(r.get("query", "?"))[:60],
                str(r.get("summary", ""))[:80],
                conf_str,
            )

    def _refresh_tasks_table(self) -> None:
        table = self.query_one("#tasks-table", DataTable)
        if not table.columns:
            table.add_columns("Title", "Priority", "Schedule")

        table.clear()
        for t in self._fetch_tasks(limit=10):
            prio = "🔴" if t.get("priority", 0) > 7 else "🟡" if t.get("priority", 0) > 3 else "🟢"
            table.add_row(
                str(t.get("title", "?"))[:60],
                prio,
                str(t.get("schedule") or "-"),
            )

    def _refresh_workflow_table(self) -> None:
        table = self.query_one("#workflow-runs-table", DataTable)
        if not table.columns:
            table.add_columns("Run ID", "Workflow", "Status", "Duration", "When")

        table.clear()
        for r in self._fetch_workflow_runs(limit=15):
            status = r.get("status", "?")
            created = str(r.get("created_at", ""))[:16].replace("T", " ")
            table.add_row(
                str(r.get("run_id", "?")),
                str(r.get("workflow_name", "?")),
                f"[{status}]{status}[/]",
                f"{r.get('duration_ms', 0):.0f}ms",
                created,
            )

    def _refresh_all_tasks_table(self) -> None:
        table = self.query_one("#all-tasks-table", DataTable)
        if not table.columns:
            table.add_columns("ID", "Status", "Title", "Priority", "Schedule")

        table.clear()
        try:
            from ai_workspace.knowledge import KnowledgeStore
            store = KnowledgeStore()
            store.initialize()
            tasks = store.get_tasks(limit=50)
            store.close()

            for t in tasks:
                table.add_row(
                    str(t["id"]),
                    t.get("status", "?"),
                    str(t.get("title", "?"))[:60],
                    str(t.get("priority", 0)),
                    str(t.get("schedule") or "-"),
                )
        except Exception:
            pass

    # ─── Actions ─────────────────────────────────────────

    @on(Button.Pressed, "#btn-search")
    async def action_deep_search(self) -> None:
        query = self.query_one("#research-query", Input).value
        if not query:
            self.notify("Enter a research query", severity="warning")
            return

        self.notify(f"Researching: {query}...", timeout=3)
        
        @work(thread=True)
        def run_search():
            from ai_workspace.search import DeepSearchEngine
            engine = DeepSearchEngine(max_depth=2)
            result = asyncio.run(engine.research(query))
            return result

        worker = run_search()
        
        def on_done(worker: Worker):
            if worker.state == WorkerState.SUCCESS:
                result = worker.result
                self.notify(
                    f"✓ Research complete: {len(result.sub_questions)} sub-questions, "
                    f"confidence {result.confidence:.0%}"
                )
                self._refresh_research_table()
                self._refresh_metrics()
        
        worker.callback = on_done

    @on(Button.Pressed, "#btn-quick")
    async def action_quick_research(self) -> None:
        query = self.query_one("#research-query", Input).value
        if not query:
            self.notify("Enter a research query", severity="warning")
            return
        
        self.notify(f"Quick research: {query}...", timeout=2)
        # Quick = depth 1
        @work(thread=True)
        def run_search():
            from ai_workspace.search import DeepSearchEngine
            engine = DeepSearchEngine(max_depth=1)
            result = asyncio.run(engine.research(query))
            return result
        
        worker = run_search()
        worker.callback = lambda w: self.notify("✓ Quick research done") if w.state == WorkerState.SUCCESS else None

    @on(Button.Pressed, "#btn-add-task")
    def action_add_task(self) -> None:
        title = self.query_one("#task-input", Input).value
        if not title:
            self.notify("Enter a task title", severity="warning")
            return
        
        try:
            from ai_workspace.knowledge import KnowledgeStore
            store = KnowledgeStore()
            store.initialize()
            store.add_task(title)
            store.close()
            self.notify(f"✓ Task added: {title}")
            self.query_one("#task-input", Input).value = ""
            self._refresh_tasks_table()
            self._refresh_all_tasks_table()
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(Button.Pressed, "#btn-run-research")
    async def action_run_workflow_research(self) -> None:
        self.notify("Starting deep_research workflow...")
        
        @work(thread=True)
        def run_wf():
            from ai_workspace.workflow import DeepResearchWorkflow
            wf = DeepResearchWorkflow()
            return wf.run_sync(query="Latest AI developments 2025")
        
        worker = run_wf()
        worker.callback = lambda w: (
            self.notify("✓ Workflow complete") if w.state == WorkerState.SUCCESS 
            else self.notify(f"✗ Failed: {w.error}", severity="error")
        )

    @on(Button.Pressed, "#btn-run-briefing")
    async def action_run_workflow_briefing(self) -> None:
        self.notify("Generating daily briefing...")
        
        @work(thread=True)
        def run_wf():
            from ai_workspace.workflow import DailyBriefingWorkflow
            wf = DailyBriefingWorkflow()
            return wf.run_sync()
        
        worker = run_wf()
        worker.callback = lambda w: (
            self.notify("✓ Briefing generated") if w.state == WorkerState.SUCCESS 
            else self.notify(f"✗ Failed: {w.error}", severity="error")
        )

    @on(Button.Pressed, "#btn-refresh-wf")
    def action_refresh_workflows(self) -> None:
        self._refresh_workflow_table()
        self.notify("Refreshed", timeout=1)

    # ─── Hotkeys ─────────────────────────────────────────

    BINDINGS = [
        ("r", "focus_tab('research')", "Research"),
        ("t", "focus_tab('tasks')", "Tasks"),
        ("w", "focus_tab('workflows')", "Workflows"),
        ("o", "focus_tab('overview')", "Overview"),
        ("l", "focus_tab('logs')", "Logs"),
        ("q", "quit", "Quit"),
        ("/", "focus_input", "Search"),
    ]

    def action_focus_tab(self, tab_id: str) -> None:
        self.query_one(TabbedContent).active = tab_id

    def action_focus_input(self) -> None:
        try:
            self.query_one("#research-query", Input).focus()
        except Exception:
            pass


def run_tui():
    """Entry point for `aiw tui` command."""
    app = AIWorkspaceTUI()
    app.run()
