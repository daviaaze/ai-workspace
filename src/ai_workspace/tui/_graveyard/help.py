"""
Help Screen — keyboard shortcut reference for the AI Workspace TUI.

Opened with F1 or ?. Shows all keybindings organized by category.
"""

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label


class HelpScreen(ModalScreen[None]):
    """Modal help overlay showing all keyboard shortcuts."""

    CSS = """
    HelpScreen {
        align: center middle;
    }

    #help-container {
        width: 65;
        height: 85%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
        overflow-y: auto;
    }

    #help-title {
        text-style: bold;
        text-align: center;
        padding: 1;
        background: $boost;
        width: 100%;
    }

    .help-section {
        padding: 1 0;
    }

    .help-section-title {
        text-style: bold;
        color: $primary;
        padding: 1 0 0 0;
        width: 100%;
    }

    .help-row {
        height: 1;
        padding: 0 1;
        width: 100%;
    }

    #help-footer {
        dock: bottom;
        height: 1;
        padding: 0 2;
        text-style: dim;
        text-align: center;
        background: $boost;
    }
    """

    BINDINGS = [
        ("escape", "dismiss_help", "Close"),
        ("f1", "dismiss_help", "Close"),
        ("question_mark", "dismiss_help", "Close"),
        ("q", "dismiss_help", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-container"):
            yield Label("  AI Workspace — Keyboard Shortcuts", id="help-title")

            with VerticalScroll():
                #  Agent Control
                yield Label(" Agent Control", classes="help-section-title")
                for key, desc in [
                    ("Ctrl+S", "Spawn new agent"),
                    ("Ctrl+Enter", "Open chat screen for focused agent"),
                    ("Ctrl+X", "Kill focused agent (press twice)"),
                    ("Space", "Pause / resume focused agent"),
                ]:
                    yield Label(f"  [bold]{key:<16}[/] {desc}", classes="help-row")

                #  Navigation
                yield Label(" Navigation", classes="help-section-title")
                for key, desc in [
                    ("Tab", "Cycle focus (tasks → lanes → input)"),
                    ("Ctrl+D", "Full-screen detail view of focused agent"),
                    ("Ctrl+W", "Workspace switcher"),
                    ("Ctrl+L", "Cycle layout (auto → 1-col → 2-col → grid)"),
                    ("Ctrl+K", "Toggle task panel"),
                ]:
                    yield Label(f"  [bold]{key:<16}[/] {desc}", classes="help-row")

                #  Search & Knowledge
                yield Label(" Search & Knowledge", classes="help-section-title")
                for key, desc in [
                    ("Ctrl+F", "Fuzzy finder (files, tasks, sessions, commands)"),
                    ("Ctrl+G", "Knowledge graph (KB entries, memories, research)"),
                    ("Ctrl+E", "Context workbench (token budget, pin/exclude)"),
                    ("Ctrl+M", "Agent metrics (tokens, cost, runtime)"),
                ]:
                    yield Label(f"  [bold]{key:<16}[/] {desc}", classes="help-row")

                #  Chat Screen
                yield Label(" Chat Screen (Ctrl+Enter)", classes="help-section-title")
                for key, desc in [
                    ("Ctrl+Enter", "Send message"),
                    ("Ctrl+N", "Insert newline"),
                    ("Ctrl+P", "Previous message in history"),
                    ("Ctrl+Shift+P", "Next message in history"),
                    ("Ctrl+T", "Toggle all thinking blocks"),
                    ("Ctrl+E", "Open context workbench"),
                    ("Ctrl+Up/Down", "Scroll conversation"),
                    ("Escape", "Focus input"),
                    ("!prefix", "Interrupt agent (clear context, fresh start)"),
                    ("Ctrl+L / q", "Back to agent lanes"),
                ]:
                    yield Label(f"  [bold]{key:<16}[/] {desc}", classes="help-row")

                #  Commands
                yield Label(" Command Palette (:)", classes="help-section-title")
                for key, desc in [
                    (":spawn <type>", "Spawn agent (coding, research, general)"),
                    (":task \"title\"", "Create a new task"),
                    (":cd <path>", "Change working directory"),
                    (":model <name>", "Switch default model"),
                    (":sessions", "List recent sessions"),
                    (":thinking on/off", "Toggle all thinking panels"),
                    (":quit / :q", "Exit AI Workspace"),
                ]:
                    yield Label(f"  [bold]{key:<16}[/] {desc}", classes="help-row")

                #  Workspace Switcher
                yield Label(" Workspace Switcher (Ctrl+W)", classes="help-section-title")
                for key, desc in [
                    ("Enter", "Switch to selected directory"),
                    ("Escape", "Close"),
                    ("Type to filter", "Filter by path or project name"),
                ]:
                    yield Label(f"  [bold]{key:<16}[/] {desc}", classes="help-row")

                #  Fuzzy Finder
                yield Label(" Fuzzy Finder (Ctrl+F)", classes="help-section-title")
                for key, desc in [
                    ("Enter", "Select result"),
                    ("Escape", "Close"),
                    ("Ctrl+N", "Next source filter"),
                    ("Ctrl+P", "Previous source filter"),
                    ("Type to filter", "Fuzzy match across files, tasks, sessions"),
                ]:
                    yield Label(f"  [bold]{key:<16}[/] {desc}", classes="help-row")

                #  Knowledge Graph
                yield Label(" Knowledge Graph (Ctrl+G)", classes="help-section-title")
                for key, desc in [
                    ("Enter", "Expand/collapse group or view details"),
                    ("p", "Toggle pin on selected node"),
                    ("v", "View full content"),
                    ("/", "Focus filter input"),
                    ("Escape", "Close"),
                ]:
                    yield Label(f"  [bold]{key:<16}[/] {desc}", classes="help-row")

                #  Other
                yield Label(" Other", classes="help-section-title")
                for key, desc in [
                    ("Ctrl+P", "View pending permissions"),
                    ("Ctrl+N", "New task (focuses input with /task)"),
                    ("Ctrl+Shift+N", "Toggle node panel"),
                    ("Escape", "Dismiss modals / overlays"),
                    ("F1 / ?", "This help screen"),
                    ("Ctrl+C / q", "Quit AI Workspace"),
                ]:
                    yield Label(f"  [bold]{key:<16}[/] {desc}", classes="help-row")

            yield Label("[dim]Press Escape, F1, ? or q to close[/]", id="help-footer")

    def action_dismiss_help(self) -> None:
        self.dismiss(None)
