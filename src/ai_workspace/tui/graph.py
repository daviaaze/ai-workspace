"""
Knowledge Graph — navigable graph of knowledge entries, memories, and connections.

Opened with Ctrl+G. Shows the AI Workspace knowledge graph as an interactive
tree where each node is a knowledge entry, memory, research result, or session.
Arrows navigate, Enter expands/collapses, and a detail panel shows full content.

Data sources:
- knowledge_entries (KB table)
- agent_memory (memories table)
- research_entries (past research)
- sessions (agent conversations)

Layout:
 Knowledge Graph 
 Filter: [________________]  sort: recent  [12 nodes, 8 connections]      

  Knowledge Base (5)          Type: Memory                           
    auth-pattern (0.8)       Agent: default                            
    ci-setup (0.6)           Importance: 85%                           
    api-design (0.5)                                                   
  Agent Memories (3)          Content                             
    fix: JWT expiry bug      When validating JWT tokens, always        
    convention: use typer    check expiry before decoding claims...    
    learning: crewai 1.0                                               
  Research (2)               Connections:                              
    MCP tools comparison     →  api-design                           
    TUI frameworks 2026      →  TUI frameworks 2026                  
  Sessions (2)                                                         
    Fix auth middleware      [p] pin  [v] view full  [Enter] expand    
    General chat                                                       

 [↑↓] navigate  [Enter] expand  [v] view  [p] pin  [/] filter  [^G/Esc]  

"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Label, Static


class GraphNodeKind(Enum):
    KNOWLEDGE = auto()
    MEMORY = auto()
    RESEARCH = auto()
    SESSION = auto()


NODE_ICONS: dict[GraphNodeKind, str] = {
    GraphNodeKind.KNOWLEDGE: "",
    GraphNodeKind.MEMORY: "",
    GraphNodeKind.RESEARCH: "",
    GraphNodeKind.SESSION: "",
}

NODE_LABELS: dict[GraphNodeKind, str] = {
    GraphNodeKind.KNOWLEDGE: "Knowledge Base",
    GraphNodeKind.MEMORY: "Agent Memories",
    GraphNodeKind.RESEARCH: "Research",
    GraphNodeKind.SESSION: "Sessions",
}


@dataclass
class GraphNode:
    """A node in the knowledge graph."""
    node_id: str
    kind: GraphNodeKind
    title: str
    content: str = ""
    importance: float = 0.5
    date: str = ""
    connections: list[str] = field(default_factory=list)  # IDs of connected nodes
    pinned: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    children: list[str] = field(default_factory=list)  # Child node IDs


class GraphNodeRow(Static):
    """A single row in the graph tree."""

    DEFAULT_CSS = """
    GraphNodeRow {
        height: 1;
        padding: 0 2;
    }
    GraphNodeRow.selected {
        background: $accent 30%;
    }
    GraphNodeRow.pinned {
        border-left: solid $success;
    }
    GraphNodeRow.group-header {
        text-style: bold;
        background: $boost;
    }
    """

    node: GraphNode | None = None
    depth: reactive[int] = reactive(0)
    selected: reactive[bool] = reactive(False)
    is_group_header: reactive[bool] = reactive(False)

    def render(self) -> str:
        if self.is_group_header and self.node:
            kind = self.node.kind
            icon = NODE_ICONS.get(kind, "•")
            label = NODE_LABELS.get(kind, "?")
            count = self.node.metadata.get("count", 0)
            return f"[bold]{icon} {label} ({count})[/]"

        if not self.node:
            return ""

        indent = "  " * self.depth
        icon = NODE_ICONS.get(self.node.kind, "•")
        importance = ""
        if self.node.importance > 0:
            importance = f" [dim]({self.node.importance:.0%})[/]"
        pin = " [green][/]" if self.node.pinned else ""
        conn = f" [dim]→{len(self.node.connections)}[/]" if self.node.connections else ""

        title = self.node.title[:60]
        if self.selected:
            return f"[reverse]{indent}{icon} {title}{importance}{pin}{conn}[/]"
        return f"{indent}{icon} {title}{importance}{pin}{conn}"


class GraphDetail(Static):
    """Right panel showing details of the selected graph node."""

    node: GraphNode | None = None

    DEFAULT_CSS = """
    GraphDetail {
        padding: 1 2;
        height: 1fr;
        overflow-y: auto;
    }
    """

    def render(self) -> str:
        if not self.node:
            return "[dim]Select a node to view details[/]"

        n = self.node
        kind_name = n.kind.name.replace("_", " ").title()
        lines = [
            f"[bold]{NODE_ICONS.get(n.kind, '•')} Type: {kind_name}[/]",
            f"[bold]Title:[/] {n.title}",
            f"[bold]Importance:[/] {n.importance:.0%}",
        ]

        if n.date:
            lines.append(f"[bold]Date:[/] [dim]{n.date}[/]")
        if n.metadata:
            for k, v in n.metadata.items():
                if k not in ("id", "title", "content"):
                    lines.append(f"[bold]{k}:[/] [dim]{str(v)[:60]}[/]")

        # Connections
        if n.connections:
            lines.append("")
            lines.append(f"[bold]Connections:[/] ({len(n.connections)})")
            for c in n.connections[:10]:
                # Show connection IDs (titles would need a lookup table)
                lines.append(f"  → [cyan]{c[:40]}[/]")

        # Content preview
        if n.content:
            lines.append("")
            lines.append("[dim] Content [/]")
            content_lines = n.content.split("\n")[:10]
            for cl in content_lines:
                lines.append(f"[dim]{cl[:100]}[/]")
            if len(n.content.split("\n")) > 10:
                lines.append("[dim]... (more)[/]")

        lines.append("")
        lines.append("[bold][[p]][/] Pin  [bold][[v]][/] Full Content  [bold][[/]][/] Filter")

        return "\n".join(lines)


class KnowledgeGraph(Static):
    """Navigable knowledge graph overlay.

    Shows all knowledge entries, memories, research results, and sessions
    as a tree with connections. Navigate with arrows, expand with Enter,
    view details in the right panel. Dismiss with Escape.
    """

    can_focus = True

    DEFAULT_CSS = """
    KnowledgeGraph {
        display: none;
        layer: overlay;
        background: $surface;
        border: thick $accent;
        padding: 0 0;
        width: 85%;
        height: 80%;
        dock: top;
        offset-x: 7%;
        offset-y: 3;
        overflow: hidden;
    }
    KnowledgeGraph.visible {
        display: block;
    }

    #graph-container {
        height: 1fr;
    }

    #graph-header {
        dock: top;
        height: 2;
        padding: 0 2;
        background: $boost;
        border-bottom: solid $primary 20%;
    }

    #graph-header > Horizontal > Input {
        width: 30;
        background: $surface;
    }

    #graph-header > Horizontal > Label {
        width: 1fr;
        padding: 0 2;
    }

    #graph-body {
        height: 1fr;
    }

    #graph-tree {
        width: 45%;
        height: 1fr;
        border-right: solid $primary 20%;
        overflow-y: auto;
    }

    #graph-detail-container {
        width: 55%;
        height: 1fr;
    }

    #graph-help {
        dock: bottom;
        height: 1;
        padding: 0 2;
        background: $boost;
        border-top: solid $primary 20%;
        text-style: dim;
    }

    #graph-empty {
        padding: 2 4;
        text-style: dim;
        text-align: center;
    }
    """

    class Closed(Message):
        """Posted when the graph is dismissed."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._graph_nodes: dict[str, GraphNode] = {}  # All nodes by ID
        self._visible_nodes: list[GraphNode] = []  # Currently visible (filtered)
        self._selected_idx: int = 0
        self._expanded_groups: set[GraphNodeKind] = {
            GraphNodeKind.KNOWLEDGE, GraphNodeKind.MEMORY,
            GraphNodeKind.RESEARCH, GraphNodeKind.SESSION,
        }
        self._filter_text: str = ""
        self._dismissed: bool = False

    def compose(self) -> ComposeResult:
        with Vertical(id="graph-container"):
            with Container(id="graph-header"):
                with Horizontal():
                    yield Input(
                        placeholder="Filter nodes...",
                        id="graph-filter",
                    )
                    yield Label(
                        "[dim][/] filter  [↑↓] navigate  [Enter] expand[/]",
                    )
            with Horizontal(id="graph-body"):
                yield VerticalScroll(id="graph-tree")
                yield GraphDetail(id="graph-detail-container", classes="hidden")
            yield Label(
                "[dim][↑↓] navigate  [Enter] expand/collapse  [v] view  "
                "[p] pin  [/] filter  [^G/Esc] close[/]",
                id="graph-help",
            )

    def show(self) -> None:
        """Open the knowledge graph and load all data."""
        self._dismissed = False
        self.set_class(True, "visible")
        # Show loading state before potentially slow DB call
        try:
            container = self.query_one("#graph-tree", VerticalScroll)
            container.mount(Label("Loading knowledge graph…", id="graph-loading"))
        except NoMatches:
            pass
        # Load data (may take a moment if DB is slow)
        self.call_later(self._do_load)

    def hide(self) -> None:
        """Close the knowledge graph."""
        self._dismissed = True
        self.set_class(False, "visible")
        self.post_message(self.Closed())

    def _do_load(self) -> None:
        """Perform the actual data loading (deferred for smooth UX)."""
        if self._dismissed:
            return
        # Remove loading indicator
        try:
            container = self.query_one("#graph-tree", VerticalScroll)
            for child in list(container.children):
                if hasattr(child, 'id') and child.id == "graph-loading":
                    child.remove()
        except NoMatches:
            pass
        self._load_data()
        self._apply_filter()
        self.focus()


    def _load_data(self) -> None:
        """Load all nodes from the database, memory files, or demo data."""
        self._graph_nodes = {}

        # 1. Try loading from DB
        try:
            self._load_from_db()
        except Exception:
            pass

        # 2. If no DB data, try loading from memory/ markdown files
        if not self._graph_nodes:
            self._load_from_memory_files()

        # 3. Last resort: hardcoded demo
        if not self._graph_nodes:
            self._load_demo_data()

    def _load_from_db(self) -> None:
        """Load nodes from PostgreSQL."""
        try:
            from ai_workspace.knowledge import KnowledgeStore
            store = KnowledgeStore()
            store.initialize()
            c = store.conn.cursor()

            # Knowledge entries
            c.execute(
                "SELECT id, title, content, content_type, created_at "
                "FROM knowledge_entries ORDER BY created_at DESC LIMIT 100"
            )
            for row in c.fetchall():
                nid = f"kb-{row[0]}"
                self._graph_nodes[nid] = GraphNode(
                    node_id=nid,
                    kind=GraphNodeKind.KNOWLEDGE,
                    title=row[1] or f"Entry #{row[0]}",
                    content=row[2] or "",
                    importance=0.5,
                    date=str(row[4])[:19] if row[4] else "",
                    metadata={"type": row[3] or "note"},
                )

            # Agent memories
            c.execute(
                "SELECT id, content, memory_type, importance, agent_name, created_at "
                "FROM agent_memory ORDER BY importance DESC LIMIT 100"
            )
            for row in c.fetchall():
                nid = f"mem-{row[0]}"
                self._graph_nodes[nid] = GraphNode(
                    node_id=nid,
                    kind=GraphNodeKind.MEMORY,
                    title=(row[1] or f"Memory #{row[0]}")[:80],
                    content=row[1] or "",
                    importance=float(row[3]) if row[3] else 0.5,
                    date=str(row[5])[:19] if row[5] else "",
                    metadata={
                        "type": row[2] or "fact",
                        "agent": row[4] or "default",
                    },
                )

            # Research entries
            c.execute(
                "SELECT id, query, summary, confidence, created_at "
                "FROM research_entries ORDER BY created_at DESC LIMIT 50"
            )
            for row in c.fetchall():
                nid = f"research-{row[0]}"
                self._graph_nodes[nid] = GraphNode(
                    node_id=nid,
                    kind=GraphNodeKind.RESEARCH,
                    title=row[1] or f"Research #{row[0]}",
                    content=row[2] or "",
                    importance=float(row[3]) if row[3] else 0.5,
                    date=str(row[4])[:19] if row[4] else "",
                )

            c.close()

            # Build connections (simple title overlap matching)
            self._build_connections()

            store.close()
        except Exception:
            pass

    def _load_from_memory_files(self) -> None:
        """Load nodes from workspace memory/ markdown files."""
        import os
        from pathlib import Path

        workspace = Path(os.environ.get(
            "AIW_WORKSPACE",
            Path.home() / "Projects" / "pessoal" / "ai-workspace"
        ))

        # Load from learning-log.md
        learning_path = workspace / "memory" / "learning-log.md"
        if learning_path.exists():
            content = learning_path.read_text()
            entries = content.split("\n## ")
            for i, entry in enumerate(entries[1:11], 1):
                lines = entry.strip().split("\n")
                title = lines[0].strip()[:80] if lines else f"Learning #{i}"
                body = "\n".join(lines[1:])[:500] if len(lines) > 1 else ""
                nid = f"learn-{i}"
                self._graph_nodes[nid] = GraphNode(
                    node_id=nid,
                    kind=GraphNodeKind.MEMORY,
                    title=title,
                    content=body,
                    importance=0.7,
                    metadata={"type": "learning", "source": "memory/learning-log.md"},
                )

        # Load from project-patterns.md if exists
        patterns_path = workspace / "memory" / "project-patterns.md"
        if patterns_path.exists():
            content = patterns_path.read_text()
            entries = content.split("\n## ")
            for i, entry in enumerate(entries[1:6], 1):
                lines = entry.strip().split("\n")
                title = lines[0].strip()[:80] if lines else f"Pattern #{i}"
                body = "\n".join(lines[1:])[:500] if len(lines) > 1 else ""
                nid = f"pattern-{i}"
                self._graph_nodes[nid] = GraphNode(
                    node_id=nid,
                    kind=GraphNodeKind.KNOWLEDGE,
                    title=title,
                    content=body,
                    importance=0.6,
                    metadata={"type": "pattern", "source": "memory/project-patterns.md"},
                )

        # Load from conventions.md if exists
        conventions_path = workspace / "memory" / "conventions.md"
        if conventions_path.exists():
            content = conventions_path.read_text()
            entries = content.split("\n## ")
            for i, entry in enumerate(entries[1:6], 1):
                lines = entry.strip().split("\n")
                title = lines[0].strip()[:80] if lines else f"Convention #{i}"
                body = "\n".join(lines[1:])[:500] if len(lines) > 1 else ""
                nid = f"conv-{i}"
                self._graph_nodes[nid] = GraphNode(
                    node_id=nid,
                    kind=GraphNodeKind.KNOWLEDGE,
                    title=title,
                    content=body,
                    importance=0.5,
                    metadata={"type": "convention", "source": "memory/conventions.md"},
                )

        # Build connections between loaded nodes
        if self._graph_nodes:
            self._build_connections()

    def _build_connections(self) -> None:
        """Build connections between nodes based on title/content overlap."""
        nodes_list = list(self._graph_nodes.values())
        for i, n1 in enumerate(nodes_list):
            for n2 in nodes_list[i + 1:]:
                # Skip same-type connections (too noisy)
                if n1.kind == n2.kind:
                    continue
                # Check title overlap
                words1 = set(n1.title.lower().split())
                words2 = set(n2.title.lower().split())
                common = words1 & words2
                if len(common) >= 2:  # At least 2 common words
                    n1.connections.append(n2.title[:60])
                    n2.connections.append(n1.title[:60])

    def _load_demo_data(self) -> None:
        """Load demo nodes when database is unavailable."""
        demo_nodes = [
            GraphNode("kb-1", GraphNodeKind.KNOWLEDGE, "Auth middleware patterns",
                      "JWT validation, session refresh, and rate limiting patterns for FastAPI.",
                      importance=0.8),
            GraphNode("kb-2", GraphNodeKind.KNOWLEDGE, "CI/CD with Nix flakes",
                      "Setting up GitHub Actions with Nix for reproducible builds.",
                      importance=0.6),
            GraphNode("mem-1", GraphNodeKind.MEMORY, "Fix: JWT expiry in auth middleware",
                      "When validating JWT tokens, always check expiry before decoding claims. The validate_jwt function was raising instead of returning False.",
                      importance=0.9),
            GraphNode("mem-2", GraphNodeKind.MEMORY, "Convention: Use typer for CLI",
                      "All CLI commands should use typer with Rich for output formatting.",
                      importance=0.7),
            GraphNode("research-1", GraphNodeKind.RESEARCH, "MCP tool marketplace comparison",
                       "Compared 5 MCP tool registries. Smithery has the most tools (1200+), but MCPHub has better curation.",
                       importance=0.75),
            GraphNode("research-2", GraphNodeKind.RESEARCH, "TUI frameworks 2026",
                       "Textual, Bubble Tea, Ratatui, Ink comparison. Textual wins for Python with 28k stars.",
                       importance=0.85),
        ]
        for n in demo_nodes:
            self._graph_nodes[n.node_id] = n

        # Demo connections
        self._graph_nodes["kb-1"].connections = ["Fix: JWT expiry in auth middleware"]
        self._graph_nodes["mem-1"].connections = ["Auth middleware patterns"]
        self._graph_nodes["research-2"].connections = ["Auth middleware patterns"]


    def _apply_filter(self) -> None:
        """Apply current filter and rebuild visible node list."""
        q = self._filter_text.lower()

        # Group nodes by kind
        self._visible_nodes = []

        for kind in GraphNodeKind:
            kind_nodes = [n for n in self._graph_nodes.values() if n.kind == kind]

            if q:
                # Fuzzy filter within this group
                filtered = []
                for n in kind_nodes:
                    search = f"{n.title} {n.content} {' '.join(n.metadata.values())}".lower()
                    if difflib.SequenceMatcher(None, q, search).ratio() > 0.2 or q in search:
                        filtered.append(n)
                kind_nodes = filtered

            if kind_nodes:
                # Group header (virtual node)
                if kind in self._expanded_groups:
                    header = GraphNode(
                        node_id=f"group-{kind.name}",
                        kind=kind,
                        title=NODE_LABELS.get(kind, "?"),
                        metadata={"count": len(kind_nodes)},
                    )
                    self._visible_nodes.append(header)
                    self._visible_nodes.extend(sorted(kind_nodes, key=lambda n: -n.importance))
                else:
                    header = GraphNode(
                        node_id=f"group-{kind.name}",
                        kind=kind,
                        title=NODE_LABELS.get(kind, "?"),
                        metadata={"count": len(kind_nodes)},
                    )
                    self._visible_nodes.append(header)

        self._selected_idx = 0
        self._render_tree()
        self._render_detail()

    def _render_tree(self) -> None:
        """Render the tree view."""
        try:
            container = self.query_one("#graph-tree", VerticalScroll)
        except NoMatches:
            return

        # Remove old rows
        for child in list(container.children):
            if isinstance(child, GraphNodeRow):
                child.remove()

        try:
            container.query_one("#graph-empty").remove()
        except NoMatches:
            pass

        if not self._visible_nodes:
            container.mount(Label(
                "No nodes found. Run 'aiw kb seed' to index the codebase, "
                "or create memories with 'aiw memory add'.",
                id="graph-empty",
            ))
            # Update header count
            self._update_header(0, 0)
            return

        for i, node in enumerate(self._visible_nodes[:200]):
            row = GraphNodeRow()
            row.node = node
            row.selected = (i == self._selected_idx)
            row.is_group_header = node.node_id.startswith("group-")
            row.depth = 0 if row.is_group_header else 1
            if row.is_group_header:
                row.add_class("group-header")
            if node.pinned:
                row.add_class("pinned")
            container.mount(row)

        total = len([n for n in self._visible_nodes if not n.node_id.startswith("group-")])
        conn_count = sum(len(n.connections) for n in self._graph_nodes.values())
        self._update_header(total, conn_count)

    def _render_detail(self) -> None:
        """Update the detail panel."""
        try:
            detail = self.query_one(GraphDetail)
        except NoMatches:
            return

        if 0 <= self._selected_idx < len(self._visible_nodes):
            node = self._visible_nodes[self._selected_idx]
            if node.node_id.startswith("group-"):
                detail.node = None
                detail.set_class(True, "hidden")
            else:
                detail.node = node
                detail.set_class(False, "hidden")
        else:
            detail.node = None
            detail.set_class(True, "hidden")

        detail.refresh()

    def _update_header(self, total: int, connections: int) -> None:
        """Update the header label with counts."""
        try:
            # Find the Label in graph-header
            header = self.query_one("#graph-header")
            for child in header.query(Label):
                child.update(
                    f"[dim]{total} nodes, {connections} connections  "
                    f"[↑↓] navigate  [Enter] expand[/]"
                )
                break
        except NoMatches:
            pass


    @on(Input.Changed, "#graph-filter")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self._filter_text = event.value
        self._apply_filter()

    def key_up(self) -> None:
        if self._visible_nodes:
            self._selected_idx = max(0, self._selected_idx - 1)
            self._render_tree()
            self._render_detail()

    def key_down(self) -> None:
        if self._visible_nodes:
            self._selected_idx = min(
                len(self._visible_nodes) - 1, self._selected_idx + 1
            )
            self._render_tree()
            self._render_detail()

    def key_enter(self) -> None:
        """Expand/collapse a group or view node details."""
        if not self._visible_nodes:
            return

        node = self._visible_nodes[self._selected_idx]
        if node.node_id.startswith("group-"):
            # Toggle group expansion
            kind = node.kind
            if kind in self._expanded_groups:
                self._expanded_groups.discard(kind)
            else:
                self._expanded_groups.add(kind)
            self._apply_filter()
        else:
            # Toggle detail panel
            try:
                detail = self.query_one(GraphDetail)
                detail.set_class(not detail.has_class("hidden"), "hidden")
            except NoMatches:
                pass

    def key_v(self) -> None:
        """View full content of selected node."""
        try:
            detail = self.query_one(GraphDetail)
            detail.set_class(False, "hidden")
            self._render_detail()
        except NoMatches:
            pass

    def key_p(self) -> None:
        """Toggle pin on selected node."""
        if 0 <= self._selected_idx < len(self._visible_nodes):
            node = self._visible_nodes[self._selected_idx]
            if not node.node_id.startswith("group-"):
                node.pinned = not node.pinned
                self._render_tree()

    def key_slash(self) -> None:
        """Focus the filter input."""
        try:
            inp = self.query_one("#graph-filter", Input)
            inp.focus()
        except NoMatches:
            pass

    def key_escape(self) -> None:
        """Close the graph."""
        self.hide()

    def key_f3(self) -> None:
        """Alternative close (F3)."""
        self.hide()
