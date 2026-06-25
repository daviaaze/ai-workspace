"""
Integration Catalog — Categorized registry of all tools, providers, and MCP integrations.

Inspired by OpenSRE's 60+ tool integration catalog pattern.
Provides:
  - Categorized listing of all integrations
  - Health/connectivity verification
  - Rich formatted output for TUI and CLI
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ═══════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════

@dataclass
class Integration:
    """A single integration (tool, provider, or service connection).

    Attributes:
        name: Display name.
        category: Grouping category.
        description: One-line summary.
        status: Current connectivity status (unknown, available, configured, unconfigured, error).
        version: Optional version string.
        docs_url: Optional link to documentation.
        type: Integration type: "provider", "tool", "mcp", "observability", "database", etc.
    """
    name: str
    category: str
    description: str = ""
    status: str = "unknown"
    version: str = ""
    docs_url: str = ""
    type: str = "tool"
    metadata: dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════
# Categories
# ═══════════════════════════════════════════════════════════

CATEGORIES: dict[str, str] = {
    "llm_provider": "LLM Providers",
    "embedding": "Embedding Models",
    "tool": "Built-in Tools",
    "mcp": "MCP Servers",
    "observability": "Observability",
    "database": "Databases",
    "search": "Search Engines",
    "knowledge": "Knowledge Bases",
    "automation": "Automation",
    "communication": "Communication",
}


# ═══════════════════════════════════════════════════════════
# Catalog
# ═══════════════════════════════════════════════════════════

class IntegrationCatalog:
    """Categorized registry of all integrations.

    Usage::

        catalog = IntegrationCatalog()
        catalog.scan()                    # Auto-detect available integrations
        catalog.verify("ollama")          # Check connectivity
        catalog.by_category()             # Group for display
        print(catalog.format_table())     # Rich formatted table
    """

    def __init__(self) -> None:
        self.integrations: list[Integration] = []
        self._scanned = False

    def register(self, integration: Integration) -> None:
        """Register a single integration."""
        self.integrations.append(integration)

    def scan(self) -> None:
        """Auto-discover all available integrations from the current environment."""
        self.integrations.clear()
        self._scan_llm_providers()
        self._scan_tools()
        self._scan_mcp()
        self._scan_databases()
        self._scan_observability()
        self._scanned = True

    def by_category(self) -> dict[str, list[Integration]]:
        """Return integrations grouped by display category."""
        result: dict[str, list[Integration]] = {}
        for integration in self.integrations:
            cat = CATEGORIES.get(integration.category, integration.category)
            result.setdefault(cat, []).append(integration)
        return result

    def get(self, name: str) -> Integration | None:
        """Find an integration by name (case-insensitive)."""
        name_lower = name.lower()
        for integration in self.integrations:
            if integration.name.lower() == name_lower:
                return integration
        return None

    def verify(self, name: str) -> str:
        """Check connectivity for a specific integration.

        Returns a status string.
        """
        integration = self.get(name)
        if integration is None:
            return f"Unknown integration: {name}"

        if integration.type == "provider":
            return self._verify_provider(integration.name)
        elif integration.type == "database":
            return self._verify_database()
        elif integration.type == "search":
            return self._verify_search()
        else:
            return f"{integration.name}: status unknown (no verification handler)"

    def verify_all(self) -> dict[str, str]:
        """Verify all configured integrations.

        Returns dict of integration_name -> status_message.
        """
        results: dict[str, str] = {}
        for integration in self.integrations:
            if integration.status in ("configured", "available"):
                results[integration.name] = self.verify(integration.name)
        return results

    def summary(self) -> dict[str, Any]:
        """Return summary statistics about the catalog."""
        if not self._scanned:
            self.scan()

        total = len(self.integrations)
        by_status: dict[str, int] = {}
        by_category: dict[str, int] = {}

        for integration in self.integrations:
            by_status[integration.status] = by_status.get(integration.status, 0) + 1
            cat = CATEGORIES.get(integration.category, integration.category)
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
            "categories": len(by_category),
        }

    def format_table(self) -> str:
        """Return a rich-formatted table string of all integrations."""
        from rich.console import Console
        from rich.table import Table
        from rich.text import Text

        console = Console(width=120)
        table = Table(title=" Integration Catalog")

        table.add_column("Category", style="cyan", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("Type", style="dim")
        table.add_column("Status")
        table.add_column("Description")

        for cat_name, integrations in self.by_category().items():
            for i, integration in enumerate(integrations):
                cat_display = cat_name if i == 0 else ""

                status_style = {
                    "available": "[green]Available[/]",
                    "configured": "[green]Configured[/]",
                    "unconfigured": "[yellow]No key[/]",
                    "error": "[red]Error[/]",
                    "unknown": "[dim]Unknown[/]",
                }.get(integration.status, f"[dim]{integration.status}[/]")

                table.add_row(
                    cat_display,
                    integration.name,
                    integration.type,
                    status_style,
                    integration.description[:80],
                )

        # Render to string
        with console.capture() as capture:
            console.print(table)
        return capture.get()

    # ── Internal scanners ────────────────────────────────

    def _scan_llm_providers(self) -> None:
        """Scan for available LLM providers from ProviderRegistry."""
        try:
            from ai_workspace.providers import ProviderRegistry
            registry = ProviderRegistry()
            for name, cfg in registry.providers.items():
                status = "configured" if cfg.api_key else "unconfigured"
                self.register(Integration(
                    name=name,
                    category="llm_provider",
                    description=f"{cfg.default_model or 'default'} via {cfg.base_url[:50]}",
                    status=status,
                    type="provider",
                    metadata={
                        "base_url": cfg.base_url,
                        "default_model": cfg.default_model,
                        "provider_type": cfg.provider.value,
                    },
                ))
        except Exception as exc:
            self.register(Integration(
                name="providers",
                category="llm_provider",
                description=f"Could not scan: {exc}",
                status="error",
                type="provider",
            ))

    def _scan_tools(self) -> None:
        """Scan for available built-in tools."""
        tool_descriptions: list[tuple[str, str, str]] = [
            ("web_fetch", "tool", "Fetch and extract content from URLs"),
            ("headless_browser", "tool", "Browser automation via Playwright"),
            ("crawl4ai", "tool", "Deep website crawling and content extraction"),
            ("paginated_scraper", "tool", "Scrape paginated listings"),
            ("scraping_chain", "tool", "Chained scraping workflow"),
            ("shell", "tool", "Execute shell commands"),
            ("filesystem", "tool", "File read/write/list operations"),
            ("git", "tool", "Git operations (commit, diff, log)"),
            ("diff_edit", "tool", "Precise text replacement edits"),
            ("code_tools", "tool", "Code analysis and manipulation"),
            ("code_graph", "tool", "Code dependency analysis"),
            ("skill_tool", "tool", "Load and execute SKILL.md files"),
            ("auto_fix", "tool", "Auto-fix code issues"),
            ("browser_agent", "tool", "Autonomous browser agent"),
            ("marketplace_search", "tool", "Search Mercado Livre and OLX"),
        ]

        for name, type_, desc in tool_descriptions:
            try:
                module = __import__(f"ai_workspace.tools.{name.replace('_search', '')}", fromlist=[""])
                status = "available"
            except Exception:
                status = "unknown"
            self.register(Integration(
                name=name,
                category="tool",
                description=desc,
                status=status,
                type=type_,
            ))

    def _scan_mcp(self) -> None:
        """Scan for available MCP servers from .mcp.json config."""
        mcp_config_path = None
        for candidate in [".mcp.json", ".mcp_config.json", "mcp.json"]:
            p = Path.cwd() / candidate
            if p.exists():
                mcp_config_path = p
                break

        if mcp_config_path:
            try:
                import json
                config = json.loads(mcp_config_path.read_text())
                servers = config.get("mcpServers", config.get("servers", {}))
                for name, _ in servers.items():
                    self.register(Integration(
                        name=name,
                        category="mcp",
                        description=f"MCP server from {mcp_config_path.name}",
                        status="available",
                        type="mcp",
                    ))
            except Exception as exc:
                self.register(Integration(
                    name="mcp_config",
                    category="mcp",
                    description=f"Could not read config: {exc}",
                    status="error",
                    type="mcp",
                ))

        # Also scan from the aiw MCP server
        try:
            from ai_workspace.mcp_server.server import TOOL_REGISTRY
            for tool_name in TOOL_REGISTRY:
                self.register(Integration(
                    name=f"aiw-mcp:{tool_name}",
                    category="mcp",
                    description=f"aiw MCP tool",
                    status="available",
                    type="mcp",
                ))
        except Exception:
            pass

    def _scan_databases(self) -> None:
        """Scan for available database connections."""
        import os
        db_url = os.getenv("AIW_DB_URL", "")
        if db_url:
            status = "configured" if "postgresql" in db_url else "unconfigured"
        else:
            db_url = os.getenv("DATABASE_URL", "")
            status = "configured" if db_url else "unconfigured"

        self.register(Integration(
            name="PostgreSQL",
            category="database",
            description=f"Vector DB via pgvector" if status == "configured" else "No database configured",
            status=status,
            type="database",
            metadata={"url": db_url[:60] if db_url else ""},
        ))

    def _scan_observability(self) -> None:
        """Scan for observability integrations."""
        import os
        otel_endpoint = os.getenv("CATALYST_OTLP_ENDPOINT", "")
        otel_token = os.getenv("CATALYST_OTLP_TOKEN", "")

        if otel_token:
            status = "configured"
        elif otel_endpoint:
            status = "configured"
        else:
            status = "unconfigured"

        self.register(Integration(
            name="OpenTelemetry",
            category="observability",
            description="OTel trace export (HALO-compatible)" if status == "configured" else "No OTel configured",
            status=status,
            type="observability",
        ))

        # Check if trace store is accessible
        try:
            from ai_workspace.observability import TraceStore
            store = TraceStore()
            traces = store.list_sessions(limit=1)
            trace_count = len(traces)
        except Exception:
            trace_count = 0

        self.register(Integration(
            name="TraceStore",
            category="observability",
            description=f"Local trace storage ({trace_count} sessions available)",
            status="available" if trace_count > 0 else "unconfigured",
            type="observability",
        ))

    # ── Verifiers ─────────────────────────────────────────

    def _verify_provider(self, name: str) -> str:
        """Check a provider's connectivity by listing models."""
        try:
            from ai_workspace.providers import ProviderRegistry
            registry = ProviderRegistry()
            cfg = registry.providers.get(name)
            if cfg is None:
                return f"Provider '{name}' not found in registry"

            import httpx
            with httpx.Client(timeout=10.0) as client:
                headers = {
                    "Authorization": f"Bearer {cfg.api_key}",
                    "Content-Type": "application/json",
                }
                models_url = cfg.base_url.rstrip("/") + "/models"
                response = client.get(models_url, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    models = data.get("data", [])
                    return f"[green]Connected[/] — {len(models)} models available"
                else:
                    return f"[yellow]Responded with status {response.status_code}[/]"

        except ImportError:
            return "[yellow]Provider module not available[/]"
        except httpx.ConnectError:
            return "[red]Connection refused[/]"
        except Exception as exc:
            return f"[red]Error: {exc}[/]"

    def _verify_database(self) -> str:
        """Check database connectivity."""
        try:
            from ai_workspace.core.db import get_store
            store = get_store()
            store.initialize()
            store.close()
            return "[green]Connected[/]"
        except Exception as exc:
            return f"[red]Error: {exc}[/]"

    def _verify_search(self) -> str:
        """Check search engine availability."""
        try:
            from ai_workspace.search.research_engine import DeepResearchEngine
            return "[green]Module available[/]"
        except Exception as exc:
            return f"[yellow]Search module unavailable: {exc}[/]"


# ═══════════════════════════════════════════════════════════
# Convenience
# ═══════════════════════════════════════════════════════════

def create_catalog() -> IntegrationCatalog:
    """Create and scan a catalog in one step."""
    catalog = IntegrationCatalog()
    catalog.scan()
    return catalog
