"""Tests — P2: DB-task scheduling pipeline.

Covers:
1. ``Database.get_due_sources()`` — SQLite due-check query
2. ``leilao_pipeline_task`` — dispatch routing
3. Scheduler ``run_scheduled_db_task`` — type routing
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest import mock

import pytest


# ──────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────

@pytest.fixture
def in_memory_db(tmp_path):
    """Create a leilão Database backed by a temp SQLite file with a seeded
    ``sources`` table so we can test ``get_due_sources()``."""
    from pathlib import Path

    from ai_workspace.leilao_radar.config import Config
    from ai_workspace.leilao_radar.storage.database import Database

    db_path = tmp_path / "leiloes.db"
    config = Config(db_path=db_path)
    db = Database(config)

    # Log scrape method needed by pipeline (mock out)
    db.log_scrape = mock.MagicMock()

    with db.conn() as c:
        c.executescript("""
            DELETE FROM sources;

            INSERT INTO sources (id, name, is_active, check_interval_hours, last_scraped_at)
            VALUES (1, 'receita_federal_sle', 1, 3, NULL);

            INSERT INTO sources (id, name, is_active, check_interval_hours, last_scraped_at)
            VALUES (2, 'leilao_net', 1, 6, datetime('now', '-7 hours'));

            INSERT INTO sources (id, name, is_active, check_interval_hours, last_scraped_at)
            VALUES (3, 'recent_source', 1, 4, datetime('now', '-2 hours'));

            INSERT INTO sources (id, name, is_active, check_interval_hours, last_scraped_at)
            VALUES (4, 'inactive_source', 0, 3, NULL);
        """)

    return db

    # Populate sources table (normally created by _init_db)
    db.log_scrape = mock.MagicMock()

    with db.conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_active INTEGER NOT NULL DEFAULT 1,
                check_interval_hours INTEGER NOT NULL DEFAULT 3,
                last_scraped_at TEXT
            );

            INSERT INTO sources (id, name, is_active, check_interval_hours, last_scraped_at)
            VALUES (1, 'receita_federal_sle', 1, 3, NULL);

            INSERT INTO sources (id, name, is_active, check_interval_hours, last_scraped_at)
            VALUES (2, 'leilao_net', 1, 6, datetime('now', '-7 hours'));

            INSERT INTO sources (id, name, is_active, check_interval_hours, last_scraped_at)
            VALUES (3, 'recent_source', 1, 4, datetime('now', '-2 hours'));

            INSERT INTO sources (id, name, is_active, check_interval_hours, last_scraped_at)
            VALUES (4, 'inactive_source', 0, 3, NULL);
        """)

    return db


# ──────────────────────────────────────────────────────────────────────────
# 1. get_due_sources
# ──────────────────────────────────────────────────────────────────────────

class TestGetDueSources:
    """Validate the SQLite due-check query logic."""

    def test_never_scraped_is_due(self, in_memory_db):
        """A source that has never been scraped (NULL last_scraped_at) is due."""
        due = in_memory_db.get_due_sources()
        assert any(s["name"] == "receita_federal_sle" for s in due)

    def test_past_interval_is_due(self, in_memory_db):
        """A source scraped 7h ago with a 6h cadence is due."""
        due = in_memory_db.get_due_sources()
        assert any(s["name"] == "leilao_net" for s in due)

    def test_within_interval_not_due(self, in_memory_db):
        """A source scraped 2h ago with a 4h cadence is NOT due."""
        due = in_memory_db.get_due_sources()
        assert not any(s["name"] == "recent_source" for s in due)

    def test_inactive_not_due(self, in_memory_db):
        """An inactive source is never due even if never scraped."""
        due = in_memory_db.get_due_sources()
        assert not any(s["name"] == "inactive_source" for s in due)

    def test_returns_sorted_by_interval(self, in_memory_db):
        """Due sources are sorted by check_interval_hours ascending."""
        due = in_memory_db.get_due_sources()
        intervals = [s["check_interval_hours"] for s in due]
        assert intervals == sorted(intervals)


# ──────────────────────────────────────────────────────────────────────────
# 2. leilao_pipeline_task — dispatch routing
# ──────────────────────────────────────────────────────────────────────────

class TestPipelineTask:
    """Verify that ``leilao_pipeline_task`` correctly calls sources.

    Uses a real in-memory DB but mocks the source ``.scrape()`` methods
    to avoid hitting the network.
    """

    def test_pipeline_routes_to_sources(self):
        """When due sources exist, the pipeline calls .scrape() on each."""
        from ai_workspace.leilao_radar.tasks import leilao_pipeline_task

        with (
            mock.patch("ai_workspace.leilao_radar.storage.database.Database.get_due_sources") as m_due,
            mock.patch("ai_workspace.leilao_radar.sources.LeilaoNet") as m_ln,
        ):
            m_due.return_value = [
                {"id": 1, "name": "leilao_net"},
            ]

            fake_result = mock.MagicMock()
            fake_result.editais = []
            fake_result.lotes = []
            fake_result.errors = []
            m_ln.return_value.scrape.return_value = fake_result

            result = leilao_pipeline_task()

            assert result["status"] == "completed"
            assert result["sources_scraped"] == 1
            assert result["total_lots"] == 0
            assert result["total_errors"] == 0
            m_ln.return_value.scrape.assert_called_once()

    def test_pipeline_handles_scrape_exception(self):
        """When a source raises, the pipeline catches it and logs an error."""
        from ai_workspace.leilao_radar.tasks import leilao_pipeline_task

        with (
            mock.patch("ai_workspace.leilao_radar.storage.database.Database.get_due_sources") as m_due,
            mock.patch("ai_workspace.leilao_radar.sources.LeilaoNet") as m_ln,
        ):
            m_due.return_value = [
                {"id": 1, "name": "leilao_net"},
            ]
            m_ln.return_value.scrape.side_effect = ValueError("Network error")

            result = leilao_pipeline_task()

            assert result["status"] == "completed"
            assert result["total_errors"] == 1
            assert result["details"][0]["status"] == "error"


# ──────────────────────────────────────────────────────────────────────────
# 3. Scheduler dispatch routing
# ──────────────────────────────────────────────────────────────────────────

class TestSchedulerDispatch:
    """Verify that ``run_scheduled_db_task`` routes to ``leilao_pipeline_task``
    when ``metadata.type == "leilao_pipeline"``."""

    def test_dispatch_calls_pipeline_task_with_task_id(self):
        """The scheduler should call leilao_pipeline_task for the right type."""
        from ai_workspace.tasks.scheduler import run_scheduled_db_task

        # Use .func to get the original function (not @huey.task wrapper)
        orig = run_scheduled_db_task.func

        with (
            mock.patch("ai_workspace.knowledge.KnowledgeStore") as m_store,
            mock.patch("ai_workspace.leilao_radar.tasks.leilao_pipeline_task") as m_pipeline,
        ):
            instance = m_store.return_value
            instance.initialize.return_value = None
            instance.get_tasks.return_value = [
                {
                    "id": 42,
                    "title": "Leilão Pipeline",
                    "description": "",
                    "metadata": {"type": "leilao_pipeline"},
                    "schedule": "0 */3 * * *",
                },
            ]

            orig(42)

            m_pipeline.assert_called_once_with(db_url=None)
