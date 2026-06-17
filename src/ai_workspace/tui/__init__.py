"""TUI module — Agent Operations Center (Textual)."""

from ai_workspace.tui.app import AIWorkspaceApp, run_tui
from ai_workspace.tui.header import HeaderBar
from ai_workspace.tui.dashboard import DashboardView
from ai_workspace.tui.agent_grid import AgentsView
from ai_workspace.tui.task_table import TasksView
from ai_workspace.tui.git_panel import GitPanel
from ai_workspace.tui.bottom_bar import BottomBar
from ai_workspace.tui.widgets import (
    AgentLane,
    CommandPalette,
    NodePanel,
    PermissionModal,
    StatusBar,
    TaskItem,
    TaskPanel,
    Toast,
)

from ai_workspace.tui.chat import ChatScreen, push_chat_screen
from ai_workspace.tui.detail import DetailScreen
from ai_workspace.tui.fuzzy import FuzzyFinder
from ai_workspace.tui.metrics import AgentMetrics
from ai_workspace.tui.workspace import WorkspaceSwitcher
from ai_workspace.tui.graph import KnowledgeGraph

__all__ = [
    "AIWorkspaceApp",
    "run_tui",
    "HeaderBar",
    "DashboardView",
    "AgentsView",
    "TasksView",
    "GitPanel",
    "BottomBar",
    "AgentLane",
    "AgentMetrics",
    "ChatScreen",
    "push_chat_screen",
    "CommandPalette",
    "DetailScreen",
    "FuzzyFinder",
    "KnowledgeGraph",
    "NodePanel",
    "PermissionModal",
    "StatusBar",
    "TaskPanel",
    "Toast",
    "WorkspaceSwitcher",
]
