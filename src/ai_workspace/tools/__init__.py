"""Tools for AI Workspace agents.

Uses lazy imports (PEP 562) to avoid pulling heavy dependencies
at import time. Each tool is loaded only when first accessed.
"""

import importlib

_imports: dict[str, str] = {
    # Web research
    "WebFetchTool": "ai_workspace.tools.web_fetch",
    "HeadlessBrowserTool": "ai_workspace.tools.headless_browser",
    "PaginatedScraperTool": "ai_workspace.tools.paginated_scraper",
    "Crawl4AITool": "ai_workspace.tools.crawl4ai",
    "MercadoLivreSearchTool": "ai_workspace.tools.marketplace",
    "OLXSearchTool": "ai_workspace.tools.marketplace",
    # Filesystem
    "ReadFileTool": "ai_workspace.tools.filesystem",
    "WriteFileTool": "ai_workspace.tools.filesystem",
    "EditFileTool": "ai_workspace.tools.filesystem",
    "ListDirTool": "ai_workspace.tools.filesystem",
    "SearchCodeTool": "ai_workspace.tools.filesystem",
    "get_filesystem_tools": "ai_workspace.tools.filesystem",
    # Git
    "GitStatusTool": "ai_workspace.tools.git",
    "GitDiffTool": "ai_workspace.tools.git",
    "GitLogTool": "ai_workspace.tools.git",
    "GitCommitTool": "ai_workspace.tools.git",
    "GitBranchTool": "ai_workspace.tools.git",
    "GhPRCreateTool": "ai_workspace.tools.git",
    "get_git_tools": "ai_workspace.tools.git",
    # Shell
    "SafeShellTool": "ai_workspace.tools.shell",
    "get_shell_tool": "ai_workspace.tools.shell",
    "SAFE_SHELL_COMMANDS": "ai_workspace.tools.shell",
    "NEVER_ALLOWED_SHELL_COMMANDS": "ai_workspace.tools.shell",
    # Browser agent (optional — may fail on systems without browser-use)
    "BrowserUseAgentTool": "ai_workspace.tools.browser_agent",
    "get_browser_agent_tool": "ai_workspace.tools.browser_agent",
    # Code graph (optional)
    "CodeReviewGraphTool": "ai_workspace.tools.code_graph",
    # Code agent tools (research-backed: OpenHands CodeAct + Aider + SWE-agent)
    "ReadCodeFileTool": "ai_workspace.tools.code_tools",
    "WriteCodeFileTool": "ai_workspace.tools.code_tools",
    "EditCodeFileTool": "ai_workspace.tools.code_tools",
    "SandboxShellTool": "ai_workspace.tools.code_tools",
    "SafeGitTool": "ai_workspace.tools.code_tools",
    "UndoEditCodeTool": "ai_workspace.tools.code_tools",
    "get_code_tools": "ai_workspace.tools.code_tools",
    # Skill tools (pi-compatible)
    "RunSkillTool": "ai_workspace.tools.skill_tool",
    "ListSkillsTool": "ai_workspace.tools.skill_tool",
    "get_skill_tools": "ai_workspace.tools.skill_tool",
    # Diff edit (legacy)
    "DiffEditTool": "ai_workspace.tools.diff_edit",
    # Auto-fix
    "AutoFixLoop": "ai_workspace.tools.auto_fix",
    "FixReport": "ai_workspace.tools.auto_fix",
    "classify_error": "ai_workspace.tools.auto_fix",
    "ErrorClass": "ai_workspace.tools.auto_fix",
    "FixResult": "ai_workspace.tools.auto_fix",
    # Scraping
    "ScrapingChainTool": "ai_workspace.tools.scraping_chain",
    "LeilaoScraperTool": "ai_workspace.tools.leilao_scraper",
    "LeilaoScraperEngine": "ai_workspace.tools.leilao_scraper",
    "ReceitaFederalSLE": "ai_workspace.tools.leilao_scraper",
    "CaixaImoveis": "ai_workspace.tools.leilao_scraper",
    "BancoDoBrasilLeiloes": "ai_workspace.tools.leilao_scraper",
    "PoliciaFederalLeiloes": "ai_workspace.tools.leilao_scraper",
    "PRFLeiloes": "ai_workspace.tools.leilao_scraper",
    "LeiloesJudiciais": "ai_workspace.tools.leilao_scraper",
    "SefazLeiloes": "ai_workspace.tools.leilao_scraper",
    "get_source": "ai_workspace.tools.leilao_scraper",
    "get_all_sources": "ai_workspace.tools.leilao_scraper",
    "SOURCES": "ai_workspace.tools.leilao_scraper",
}


def __getattr__(name: str):
    if name in _imports:
        mod = importlib.import_module(_imports[name])
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    # Code graph (optional)
    "CodeReviewGraphTool",
    # Code agent tools (research-backed: OpenHands CodeAct + Aider + SWE-agent)
    "ReadCodeFileTool",
    "WriteCodeFileTool",
    "EditCodeFileTool",
    "SandboxShellTool",
    "SafeGitTool",
    "UndoEditCodeTool",
    "get_code_tools",
    # Skill tools (pi-compatible)
    "RunSkillTool",
    "ListSkillsTool",
    "get_skill_tools",
    # Diff edit (legacy)
    "DiffEditTool",
    # Auto-fix
    "AutoFixLoop",
    "FixReport",
    "classify_error",
    "ErrorClass",
    "FixResult",
    # Scraping
    "ScrapingChainTool",
    "LeilaoScraperTool",
    "LeilaoScraperEngine",
    "ReceitaFederalSLE",
    "CaixaImoveis",
    "BancoDoBrasilLeiloes",
    "PoliciaFederalLeiloes",
    "PRFLeiloes",
    "LeiloesJudiciais",
    "SefazLeiloes",
    "get_source",
    "get_all_sources",
    "SOURCES",
]
