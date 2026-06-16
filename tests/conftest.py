"""
Shared test fixtures for AI Workspace.

Provides:
- PostgreSQL test database (if AIW_TEST_DB_URL is set)
- Mock KnowledgeStore for unit tests (no DB required)
- Temp directories for markdown memory tests
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ─── Database fixtures ──────────────────────────────────


@pytest.fixture(scope="session")
def db_url():
    """PostgreSQL database URL for tests.

    Set AIW_TEST_DB_URL env var to run integration tests against a real DB.
    Defaults to a non-existent DB so tests requiring real DB are skipped.
    """
    return os.environ.get("AIW_TEST_DB_URL", "postgresql:///ai_workspace_test")


@pytest.fixture
def mock_psycopg2_conn():
    """Mock a psycopg2 connection with cursor support."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.description = []
    mock_cursor.__enter__ = lambda self: self
    mock_cursor.__exit__ = lambda *_: None

    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__ = lambda self: self
    mock_conn.__exit__ = lambda *_: None

    return mock_conn


@pytest.fixture
def mock_knowledge_store(mock_psycopg2_conn, tmp_path):
    """Create a KnowledgeStore with mocked PostgreSQL connection.

    Uses the actual initialization logic but replaces psycopg2.connect
    with a mock so no real DB is needed. Tests CRUD logic and SQL correctness.
    """
    with patch("psycopg2.connect", return_value=mock_psycopg2_conn):
        from ai_workspace.knowledge import KnowledgeStore

        store = KnowledgeStore(db_url="postgresql:///mock_db")
        store._conn = mock_psycopg2_conn
        store.initialize()
        yield store
        store.close()


@pytest.fixture
def temp_workspace(tmp_path):
    """Temporary workspace directory for markdown memory tests."""
    mem_dir = tmp_path / "memory"
    mem_dir.mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def knowledge_store_with_markdown(tmp_path, monkeypatch):
    """KnowledgeStore with temp workspace for markdown memory tests."""
    # Override the workspace root
    monkeypatch.setenv("AIW_WORKSPACE", str(tmp_path))

    with patch("psycopg2.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_conn.closed = False
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.fetchall.return_value = []
        mock_cursor.description = []
        mock_cursor.__enter__ = lambda self: self
        mock_cursor.__exit__ = lambda *_: None
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore(db_url="postgresql:///mock_db")
        store._conn = mock_conn
        store.initialize()
        yield store
        store.close()


# ─── Mock fixtures for common dependencies ────────────────


@pytest.fixture
def mock_crewai_agent():
    """Mock a crewai Agent."""
    with patch("crewai.Agent") as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture
def mock_crewai_crew():
    """Mock a crewai Crew."""
    with patch("crewai.Crew") as mock:
        instance = MagicMock()
        instance.kickoff.return_value = '{"answer": "test answer", "confidence": 0.9}'
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_crewai_llm():
    """Mock a crewai LLM."""
    with patch("crewai.LLM") as mock:
        mock.return_value = MagicMock()
        yield mock


@pytest.fixture
def mock_provider_registry():
    """Mock ProviderRegistry with fake clients."""
    with patch("ai_workspace.providers.ProviderRegistry") as mock:
        instance = MagicMock()
        mock.return_value = instance
        yield instance


@pytest.fixture
def sample_research_data():
    """Sample research entry data for tests."""
    return {
        "query": "What is the best async framework in Python?",
        "summary": "FastAPI and asyncio are top choices.",
        "detailed_report": "Detailed analysis of async frameworks...",
        "sources": ["https://fastapi.tiangolo.com"],
        "confidence": 0.85,
        "sub_questions": [
            {"question": "How does FastAPI compare to aiohttp?", "answer": "..."},
        ],
    }


@pytest.fixture
def sample_task_data():
    """Sample task data for tests."""
    return {
        "title": "Write unit tests",
        "description": "Create comprehensive tests for the knowledge module",
        "priority": 8,
        "tags": ["testing", "development"],
        "schedule": "0 9 * * *",
    }


@pytest.fixture
def sample_memory_data():
    """Sample agent memory data."""
    return {
        "agent_name": "researcher",
        "content": "pgvector HNSW indexes are faster than IVFFlat for most workloads",
        "memory_type": "fact",
        "importance": 0.8,
        "metadata": {"source": "research", "topic": "postgresql"},
    }
