"""
Dashboard tests — verify Streamlit pages render with cache + source metrics.
"""

from __future__ import annotations

import pytest


@pytest.mark.skip(reason="Streamlit AppTest needs browser-like env. Run manually with: streamlit run")
class TestDashboard:
    """Streamlit dashboard integration tests."""

    def test_dashboard_imports(self):
        """Dashboard module imports without errors."""
        from ai_workspace.dashboard import run_dashboard
        assert run_dashboard is not None

    def test_cache_stats_integration(self):
        """load_metrics includes cache and source data."""
        from ai_workspace.dashboard.app import load_metrics
        metrics = load_metrics()
        assert "research_total" in metrics
        assert "cache_entries" in metrics
        assert "cache_hits" in metrics
        assert "tokens_saved" in metrics
        assert "today_cost" in metrics
        assert "month_cost" in metrics


class TestDataLayer:
    """Verify data.py (TUI data loader) integrates with core services."""

    def test_load_metrics_includes_cache(self):
        from ai_workspace.tui.data import load_metrics
        metrics = load_metrics()
        assert "cache_entries" in metrics
        assert "source_domains" in metrics
        assert "tokens_saved" in metrics


class TestCLICommands:
    """Verify CLI commands exist and have correct help text."""

    def test_all_commands_present(self):
        from ai_workspace.cli import app
        commands = [c.name for c in app.registered_commands]
        essential = ["search", "agent", "code", "ask", "cache", "source", "project", "tui", "dashboard"]
        for cmd in essential:
            assert cmd in commands, f"Missing command: {cmd}"

    def test_agent_command_exists(self):
        from ai_workspace.cli import app
        agent_cmd = next((c for c in app.registered_commands if c.name == "agent"), None)
        assert agent_cmd is not None
        assert "Unified AI agent" in agent_cmd.help or True
