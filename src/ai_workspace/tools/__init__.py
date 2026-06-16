"""Tools for AI Workspace agents."""

from ai_workspace.tools.web_fetch import WebFetchTool
from ai_workspace.tools.marketplace import MercadoLivreSearchTool, OLXSearchTool
from ai_workspace.tools.headless_browser import HeadlessBrowserTool
from ai_workspace.tools.paginated_scraper import PaginatedScraperTool
from ai_workspace.tools.crawl4ai import Crawl4AITool
from ai_workspace.tools.filesystem import (
    ReadFileTool,
    WriteFileTool,
    EditFileTool,
    ListDirTool,
    SearchCodeTool,
    get_filesystem_tools,
)
from ai_workspace.tools.git import (
    GitStatusTool,
    GitDiffTool,
    GitLogTool,
    GitCommitTool,
    GitBranchTool,
    GhPRCreateTool,
    get_git_tools,
)
from ai_workspace.tools.shell import (
    SafeShellTool,
    get_shell_tool,
    SAFE as SAFE_SHELL_COMMANDS,
    NEVER_ALLOWED as NEVER_ALLOWED_SHELL_COMMANDS,
)

# Optional: browser-use agent tool (only if dependency installed)
try:
    from ai_workspace.tools.browser_agent import BrowserUseAgentTool, get_browser_agent_tool
    _HAS_BROWSER_USE = True
except ImportError:
    BrowserUseAgentTool = None  # type: ignore
    get_browser_agent_tool = None  # type: ignore
    _HAS_BROWSER_USE = False


__all__ = [
    # Web research
    "WebFetchTool",
    "HeadlessBrowserTool",
    "PaginatedScraperTool",
    "Crawl4AITool",
    "MercadoLivreSearchTool",
    "OLXSearchTool",
    # Filesystem
    "ReadFileTool",
    "WriteFileTool",
    "EditFileTool",
    "ListDirTool",
    "SearchCodeTool",
    "get_filesystem_tools",
    # Git
    "GitStatusTool",
    "GitDiffTool",
    "GitLogTool",
    "GitCommitTool",
    "GitBranchTool",
    "GhPRCreateTool",
    "get_git_tools",
    # Shell
    "SafeShellTool",
    "get_shell_tool",
    "SAFE_SHELL_COMMANDS",
    "NEVER_ALLOWED_SHELL_COMMANDS",
    # Browser agent (optional)
    "BrowserUseAgentTool",
    "get_browser_agent_tool",
]
