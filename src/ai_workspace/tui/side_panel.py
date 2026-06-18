"""
Side Panel System — collapsible docked panels for the cyberdeck layout.

Provides:
  - SidePanel: a docked panel that collapses to a narrow icon-tab
  - SidePanelStack: a vertical stack of multiple collapsible panels
  - BottomPanel: a docked-bottom panel with collapsible behavior

Design (inspired by VSCode sidebars + Borland Turbo Vision):
  Collapsed state: narrow tab (2-3 chars) showing icon only
  Expanded state: full-width panel (25-40%) with content
  Click the icon-tab or press a hotkey to toggle

Example layout:
[ Collapsed left tabs ][ Main content ][ Collapsed right tabs ]
                                                                      
                                                                          
                            Agent lanes,                                
                              code, output                                
                                                                        
                                                                          
                                                                        

  Research Queue (collapsed)                                               


Expanded left panel:
[ Agents ][ Main content ]
  coding-1  80%                                                          
  research   40%           Agent lanes, code, output                     
                                                                            
 Skills: [web] [code]                                                      
 MCPs:   [fs] [git] [db]                                                   
                                                                            
 [^S New] [^X Kill]                                                        

"""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static


# Side Panel — single collapsible docked panel

class SidePanel(Static):
    """A collapsible panel docked to one side of the screen.

    Shows an icon-tab when collapsed (2-3 chars wide).
    Expands to full content when toggled.
    """

    can_focus = True
    DEFAULT_CSS = """
    SidePanel {
        height: 1fr;
        border: solid $primary 20%;
        background: $panel;
        overflow: hidden;
    }

    SidePanel.-collapsed {
        width: 3;
        overflow: hidden;
    }

    SidePanel.-expanded {
        width: 30%;
    }

    SidePanel.-dock-right {
        border-left: solid $primary 20%;
    }

    SidePanel.-dock-left {
        border-right: solid $primary 20%;
    }

    SidePanel #sp-tab {
        height: 1fr;
        padding: 2 1;
        text-align: center;
        background: $surface;
        border-right: solid $primary 20%;
    }

    SidePanel.-dock-right #sp-tab {
        border-right: none;
        border-left: solid $primary 20%;
    }

    SidePanel #sp-tab:hover {
        background: $boost;
    }

    SidePanel #sp-header {
        dock: top;
        height: 1;
        padding: 0 2;
        background: $boost;
        border-bottom: solid $primary 20%;
        text-style: bold;
    }

    SidePanel #sp-body {
        height: 1fr;
        overflow-y: auto;
        padding: 0;
    }

    SidePanel .sp-empty {
        padding: 2 2;
        text-style: dim;
        text-align: center;
    }

    SidePanel #sp-toggle {
        dock: top;
        width: auto;
        padding: 0 1;
        text-align: right;
    }
    """

    class Toggled(Message):
        """Posted when panel is toggled open/closed."""

        def __init__(self, panel_id: str, expanded: bool) -> None:
            super().__init__()
            self.panel_id = panel_id
            self.expanded = expanded

    collapsed: reactive[bool] = reactive(True)

    def __init__(
        self,
        panel_id: str = "",
        title: str = "",
        icon: str = "•",
        dock_side: str = "left",
        collapsed_width: int = 3,
        expanded_width: str = "30%",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.panel_id = panel_id or self.id or f"panel-{id(self)}"
        self._title = title
        self._icon = icon
        self._dock_side = dock_side
        self._collapsed_width = collapsed_width
        self._expanded_width = expanded_width

    def compose(self) -> ComposeResult:
        """Yield the panel's internal structure.

        Subclasses should override `compose_content()` instead.
        """
        # Content area — subclasses yield into this
        with Vertical(id="sp-body"):
            yield from self.compose_content()

    def compose_content(self) -> ComposeResult:
        """Override in subclasses to add panel-specific content.

        Example:
            yield Label("Agent list goes here")
            yield AgentCardList()
        """
        yield Label(
            f"[dim]{self._title} content[/]",
            classes="sp-empty",
        )

    def on_mount(self) -> None:
        """Apply initial collapsed state and dock position."""
        self._apply_collapsed()
        self._apply_dock()

    def _apply_collapsed(self) -> None:
        """Set CSS classes based on collapsed state."""
        if self.collapsed:
            self.add_class("-collapsed")
            self.remove_class("-expanded")
        else:
            self.remove_class("-collapsed")
            self.add_class("-expanded")

    def _apply_dock(self) -> None:
        """Set CSS classes based on dock side."""
        if self._dock_side == "right":
            self.add_class("-dock-right")
        else:
            self.add_class("-dock-left")

    def toggle(self) -> None:
        """Toggle between collapsed and expanded."""
        self.collapsed = not self.collapsed
        self._apply_collapsed()
        self.post_message(self.Toggled(self.panel_id, not self.collapsed))

    def expand(self) -> None:
        """Expand the panel."""
        if self.collapsed:
            self.toggle()

    def collapse(self) -> None:
        """Collapse the panel."""
        if not self.collapsed:
            self.toggle()

    def watch_collapsed(self, value: bool) -> None:
        """React to collapsed state changes from outside."""
        self._apply_collapsed()

    def render(self) -> str:
        """Render the collapsed tab icon. When expanded, child widgets handle display."""
        if not self.collapsed:
            return ""  # Children handle expanded display
        # Build a vertical label for collapsed state
        lines = [f"[bold]{self._icon}[/]"]
        for ch in self._title[:5]:
            lines.append(f"[dim]{ch}[/]")
        return "\n".join(lines)

    # Keyboard handlers
    def on_click(self) -> None:
        """Click the collapsed tab to toggle."""
        if self.collapsed:
            self.expand()

    def key_escape(self) -> None:
        """Escape collapses the panel."""
        if not self.collapsed:
            self.collapse()


# Side Panel Stack — multiple collapsible panels in a column

class SidePanelStack(Vertical):
    """A vertical stack of collapsible side panels.

    Only one panel can be expanded at a time. Expanding one panel
    collapses all others. Shows collapsed icon-tabs for all panels.

    Usage:
        stack = SidePanelStack(id="left-stack", dock_side="left")
        stack.add_panel("agents", "Agents", "", AgentPanelContent())
        stack.add_panel("files", "Files", "", FileBrowserContent())
        stack.add_panel("tasks", "Tasks", "", TaskListContent())
    """

    DEFAULT_CSS = """
    SidePanelStack {
        height: 1fr;
        width: auto;
    }

    SidePanelStack.-empty {
        width: 0;
    }
    """

    def __init__(
        self,
        dock_side: str = "left",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._dock_side = dock_side
        self._panels: list[SidePanel] = []
        self._expanded_panel: str | None = None

    def compose(self) -> ComposeResult:
        """Content is added via add_panel() after mount."""
        return []

    def add_panel(
        self,
        panel_id: str,
        title: str,
        icon: str,
        content_widget: str | None = None,
    ) -> SidePanel:
        """Add a new panel to the stack.

        Args:
            panel_id: Unique ID for the panel
            title: Panel title (shown when expanded)
            icon: Icon character(s) for collapsed tab
            content_widget: Optional text for placeholder content

        Returns:
            The created SidePanel widget
        """
        panel = SidePanel(
            panel_id=panel_id,
            title=title,
            icon=icon,
            dock_side=self._dock_side,
            id=f"sp-{panel_id}",
        )
        self._panels.append(panel)
        return panel

    def mount_panels(self) -> None:
        """Mount all panels into the stack. Call after compose."""
        for panel in self._panels:
            self.mount(panel)

    def expand(self, panel_id: str) -> None:
        """Expand a specific panel, collapsing all others."""
        for panel in self._panels:
            if panel.panel_id == panel_id:
                panel.collapsed = False
                panel._apply_collapsed()
                self._expanded_panel = panel_id
            else:
                panel.collapsed = True
                panel._apply_collapsed()

    def collapse_all(self) -> None:
        """Collapse all panels in the stack."""
        self._expanded_panel = None
        for panel in self._panels:
            panel.collapsed = True
            panel._apply_collapsed()

    def toggle(self, panel_id: str) -> None:
        """Toggle a specific panel."""
        for panel in self._panels:
            if panel.panel_id == panel_id:
                if panel.collapsed:
                    self.expand(panel_id)
                else:
                    self.collapse_all()
                return

    def get_expanded(self) -> str | None:
        """Get the currently expanded panel ID."""
        return self._expanded_panel

    @on(SidePanel.Toggled)
    def on_panel_toggled(self, event: SidePanel.Toggled) -> None:
        """When any panel is toggled, collapse others."""
        if event.expanded:
            self.expand(event.panel_id)
        else:
            self._expanded_panel = None


# Bottom Panel — collapsible bottom-docked panel

class BottomPanel(Static):
    """A collapsible panel docked to the bottom of the screen.

    Shows a thin handle bar when collapsed (1 line).
    Expands upward to show content (e.g., research queue, terminal).
    """

    DEFAULT_CSS = """
    BottomPanel {
        dock: bottom;
        border-top: solid $primary 20%;
        background: $panel;
        overflow: hidden;
    }

    BottomPanel.-collapsed {
        height: 1;
    }

    BottomPanel.-expanded {
        height: 30%;
    }

    BottomPanel #bp-handle {
        height: 1;
        padding: 0 2;
        background: $boost;
        text-style: dim;
        border-bottom: solid $primary 20%;
    }

    BottomPanel #bp-handle:hover {
        background: $surface;
        text-style: bold;
    }

    BottomPanel.-expanded #bp-header {
        dock: top;
        height: 1;
        padding: 0 2;
        background: $boost;
        text-style: bold;
    }

    BottomPanel #bp-body {
        height: 1fr;
        overflow-y: auto;
        padding: 0;
    }

    BottomPanel .bp-empty {
        padding: 1 2;
        text-style: dim;
    }
    """

    collapsed: reactive[bool] = reactive(True)

    def __init__(
        self,
        panel_id: str = "",
        title: str = "",
        icon: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.panel_id = panel_id or f"bp-{id(self)}"
        self._title = title
        self._icon = icon

    def compose(self) -> ComposeResult:
        with Vertical(id="bp-body"):
            yield from self.compose_content()

    def compose_content(self) -> ComposeResult:
        """Override in subclasses."""
        yield Label(
            f"[dim]{self._title} content[/]",
            classes="bp-empty",
        )

    def on_mount(self) -> None:
        self._apply_collapsed()

    def _apply_collapsed(self) -> None:
        if self.collapsed:
            self.add_class("-collapsed")
            self.remove_class("-expanded")
        else:
            self.remove_class("-collapsed")
            self.add_class("-expanded")

    def toggle(self) -> None:
        self.collapsed = not self.collapsed
        self._apply_collapsed()

    def watch_collapsed(self, value: bool) -> None:
        self._apply_collapsed()

    def render(self) -> str:
        if self.collapsed:
            return f"[dim]{self._icon} {self._title}  [^B] toggle[/]"
        return f"[bold]{self._icon} {self._title}[/]  [^B] collapse  [Esc] close"

    def on_click(self) -> None:
        self.toggle()


# Layout Container — orchestrates the full 3-panel cyberdeck layout

class CyberdeckLayout(Vertical):
    """Master layout container for the AI Workstation.

    Orchestrates:
      - Left stack: collapsible panels (agents, files, tasks)
      - Center: main content area (agent lanes, code pane)
      - Right stack: collapsible panels (context graph, knowledge)
      - Bottom: collapsible panel (research queue, terminal)

    Keybindings (handled by parent app, forwarded here):
      ^1-^4  — toggle left panels 1-4
      ^5-^8  — toggle right panels 1-4
      ^B     — toggle bottom panel
      ^\\    — collapse all side panels (zen mode)
      Tab    — cycle focus: left → center → right → bottom
    """

    DEFAULT_CSS = """
    CyberdeckLayout {
        height: 1fr;
    }

    CyberdeckLayout #cyberdeck-body {
        height: 1fr;
    }

    CyberdeckLayout #cyberdeck-left {
        dock: left;
        width: auto;
        height: 1fr;
    }

    CyberdeckLayout #cyberdeck-center {
        height: 1fr;
        background: $background;
    }

    CyberdeckLayout #cyberdeck-right {
        dock: right;
        width: auto;
        height: 1fr;
    }
    """

    def __init__(
        self,
        left_stack: SidePanelStack | None = None,
        right_stack: SidePanelStack | None = None,
        bottom_panel: BottomPanel | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.left_stack = left_stack
        self.right_stack = right_stack
        self.bottom_panel = bottom_panel

    def compose(self) -> ComposeResult:
        with Horizontal(id="cyberdeck-body"):
            # Left dock area
            if self.left_stack:
                yield self.left_stack

            # Center — main content
            yield VerticalScroll(id="cyberdeck-center")

            # Right dock area
            if self.right_stack:
                yield self.right_stack

        # Bottom panel
        if self.bottom_panel:
            yield self.bottom_panel

    def on_mount(self) -> None:
        """Mount panels into their stacks."""
        if self.left_stack:
            self.left_stack.mount_panels()
        if self.right_stack:
            self.right_stack.mount_panels()

    def get_center(self) -> VerticalScroll:
        """Get the center content area for mounting widgets."""
        return self.query_one("#cyberdeck-center", VerticalScroll)

    def toggle_left(self, panel_id: str) -> None:
        """Toggle a left stack panel."""
        if self.left_stack:
            self.left_stack.toggle(panel_id)

    def toggle_right(self, panel_id: str) -> None:
        """Toggle a right stack panel."""
        if self.right_stack:
            self.right_stack.toggle(panel_id)

    def toggle_bottom(self) -> None:
        """Toggle the bottom panel."""
        if self.bottom_panel:
            self.bottom_panel.toggle()

    def collapse_all(self) -> None:
        """Collapse all side panels (zen mode)."""
        if self.left_stack:
            self.left_stack.collapse_all()
        if self.right_stack:
            self.right_stack.collapse_all()
        if self.bottom_panel:
            self.bottom_panel.collapsed = True
            self.bottom_panel._apply_collapsed()

    def expand_left(self, panel_id: str) -> None:
        """Expand a specific left panel."""
        if self.left_stack:
            self.left_stack.expand(panel_id)

    def expand_right(self, panel_id: str) -> None:
        """Expand a specific right panel."""
        if self.right_stack:
            self.right_stack.expand(panel_id)

    def key_escape(self) -> None:
        """Escape collapses all panels and focuses center."""
        self.collapse_all()
        try:
            self.query_one("#cyberdeck-center", VerticalScroll).focus()
        except NoMatches:
            pass
