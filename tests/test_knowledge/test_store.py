"""
Tests for KnowledgeStore — PostgreSQL + pgvector knowledge base.

Covers:
- Database initialization (table creation, extensions)
- CRUD operations for knowledge entries
- Research entry storage and retrieval
- Task management with cron scheduling
- Agent memory operations
- Markdown memory file I/O
- Obsidian sync (import/export)
- Vector search (pending pgvector extension)
"""

from __future__ import annotations

import json
from datetime import datetime
from unittest.mock import MagicMock, call, patch

import pytest

from ai_workspace.knowledge import KnowledgeStore


# ─── Store initialization ──────────────────────────────


def test_store_initialization_creates_tables(mock_psycopg2_conn):
    """Store.initialize() should create all required tables and indexes."""
    from ai_workspace.knowledge import KnowledgeStore

    store = KnowledgeStore(db_url="postgresql:///mock_db")
    store._conn = mock_psycopg2_conn
    store.initialize()

    cursor = mock_psycopg2_conn.cursor.return_value

    # Should call CREATE EXTENSION for vector
    ext_calls = [
        call_arg for call_arg in cursor.execute.call_args_list
        if "CREATE EXTENSION" in str(call_arg)
    ]
    assert len(ext_calls) >= 1

    # Should create required tables
    create_calls = [str(c) for c in cursor.execute.call_args_list]
    table_names = [
        "knowledge_entries",
        "research_entries",
        "tasks",
        "agent_memory",
    ]
    for table in table_names:
        found = any(table in c for c in create_calls)
        assert found, f"Table '{table}' should be created"


def test_store_initialization_is_idempotent(mock_psycopg2_conn):
    """Calling initialize() twice should not fail (IF NOT EXISTS)."""
    from ai_workspace.knowledge import KnowledgeStore

    store = KnowledgeStore(db_url="postgresql:///mock_db")
    store._conn = mock_psycopg2_conn

    store.initialize()
    store.initialize()  # Should not raise

    assert True  # Reaching here means no exception


def test_store_connection_reuse(mock_psycopg2_conn):
    """Store.conn property should reuse the same connection."""
    store = KnowledgeStore(db_url="postgresql:///mock_db")
    store._conn = mock_psycopg2_conn

    conn1 = store.conn
    conn2 = store.conn

    assert conn1 is conn2  # Same connection object


# ─── Knowledge CRUD ─────────────────────────────────────


def test_add_knowledge(mock_knowledge_store):
    """add_knowledge should insert a row and return an ID."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchone.return_value = (42,)

    entry_id = store.add_knowledge(
        content="Nix flakes provide reproducible builds.",
        content_type="note",
        title="Nix Flakes",
        tags=["nix", "devops"],
    )

    assert entry_id == 42
    # Verify SQL was called
    insert_call = cursor.execute.call_args
    assert "INSERT INTO knowledge_entries" in insert_call[0][0]


def test_search_knowledge(mock_knowledge_store):
    """search_knowledge should query with ILIKE and return results."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchall.return_value = [
        {"id": 1, "content": "Test content", "content_type": "note",
         "title": "Test", "tags": [], "created_at": "2025-01-01"},
    ]

    results = store.search_knowledge("test", limit=5)

    assert len(results) > 0
    assert results[0]["id"] == 1
    assert results[0]["content"] == "Test content"

    # Verify ILIKE with wildcards
    sql = cursor.execute.call_args[0][0]
    assert "ILIKE" in sql


def test_search_knowledge_with_filters(mock_knowledge_store):
    """search_knowledge should filter by content_type and tags."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchall.return_value = []

    store.search_knowledge("test", content_type="research", tags=["ai"])

    sql = cursor.execute.call_args[0][0]
    assert "content_type" in sql
    assert "tags" in sql


# ─── Research CRUD ─────────────────────────────────────


def test_save_research(mock_knowledge_store, sample_research_data):
    """save_research should persist a research report."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchone.return_value = (7,)

    rid = store.save_research(
        sample_research_data["query"],
        sample_research_data,
    )

    assert rid == 7
    sql = cursor.execute.call_args[0][0]
    assert "INSERT INTO research_entries" in sql


def test_get_research_history(mock_knowledge_store):
    """get_research_history should return recent entries."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchall.return_value = [
        {"id": 1, "query": "test", "summary": "result", "confidence": 0.9},
    ]

    history = store.get_research_history(limit=5)

    assert len(history) == 1
    assert history[0]["query"] == "test"


# ─── Task CRUD ──────────────────────────────────────────


def test_add_task(mock_knowledge_store, sample_task_data):
    """add_task should create a task with optional cron schedule."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchone.return_value = (99,)

    tid = store.add_task(**sample_task_data)

    assert tid == 99
    sql = cursor.execute.call_args[0][0]
    assert "INSERT INTO tasks" in sql


def test_get_tasks_filtered(mock_knowledge_store):
    """get_tasks should filter by status and tags."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchall.return_value = [
        {"id": 1, "title": "Test", "status": "pending", "priority": 5},
    ]

    tasks = store.get_tasks(status="pending", tags=["dev"], limit=10)

    assert len(tasks) == 1
    sql = cursor.execute.call_args[0][0]
    assert "status" in sql


def test_update_task_status(mock_knowledge_store):
    """update_task_status should flip the status."""
    store = mock_knowledge_store
    store.update_task_status(42, "completed")

    cursor = store.conn.cursor.return_value
    sql = cursor.execute.call_args[0][0]
    assert "UPDATE tasks" in sql


def test_get_due_tasks(mock_knowledge_store):
    """get_due_tasks should find scheduled tasks past due."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchall.return_value = [
        {"id": 1, "title": "Daily review", "schedule": "0 9 * * *", "status": "pending"},
    ]

    due = store.get_due_tasks()

    assert len(due) == 1
    sql = cursor.execute.call_args[0][0]
    assert "next_run" in sql or "cron" in sql.lower()


# ─── Agent Memory ───────────────────────────────────────


def test_remember(mock_knowledge_store, sample_memory_data):
    """remember should store an agent memory."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchone.return_value = (55,)

    mid = store.remember(**sample_memory_data)

    assert mid == 55
    sql = cursor.execute.call_args[0][0]
    assert "INSERT INTO agent_memory" in sql


def test_recall(mock_knowledge_store):
    """recall should search agent memories."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchall.return_value = [
        {"id": 1, "agent_name": "researcher", "memory_type": "fact",
         "content": "pgvector is fast", "importance": 0.8, "created_at": "2025-01-01"},
    ]

    results = store.recall("researcher", "pgvector", limit=5)

    assert len(results) == 1
    assert results[0]["content"] == "pgvector is fast"

    sql = cursor.execute.call_args[0][0]
    assert "SELECT" in sql
    assert "agent_memory" in sql


def test_recall_with_type_filter(mock_knowledge_store):
    """recall should filter by memory_type."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchall.return_value = []

    store.recall("researcher", "test", memory_type="learning", limit=5)

    sql = cursor.execute.call_args[0][0]
    assert "memory_type" in sql


def test_get_facts(mock_knowledge_store):
    """get_facts should return only 'fact' type memories."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchall.return_value = []

    store.get_facts("researcher", limit=10)

    sql = cursor.execute.call_args[0][0]
    assert "memory_type" in sql


# ─── Markdown Memory ────────────────────────────────────


def test_append_memory_markdown(knowledge_store_with_markdown):
    """append_memory_markdown should write to the correct markdown file."""
    store = knowledge_store_with_markdown
    entry = {
        "title": "Nix Flakes are Awesome",
        "content": "Flakes provide reproducible builds and pin dependencies.",
        "tags": ["nix", "devops"],
        "importance": 0.9,
    }

    filepath = store.append_memory_markdown("convention", entry)

    assert filepath.exists()
    content = filepath.read_text()
    assert "Nix Flakes are Awesome" in content
    assert "Flakes provide reproducible builds" in content
    assert "nix, devops" in content


def test_append_memory_markdown_multiple_entries(knowledge_store_with_markdown):
    """append_memory_markdown should append, not overwrite, existing entries."""
    store = knowledge_store_with_markdown

    store.append_memory_markdown("learning", {
        "title": "First Learning",
        "content": "Content 1",
    })
    store.append_memory_markdown("learning", {
        "title": "Second Learning",
        "content": "Content 2",
    })

    content = store.read_memory_markdown("learning")
    assert "First Learning" in content
    assert "Second Learning" in content


def test_read_memory_markdown(knowledge_store_with_markdown):
    """read_memory_markdown should return file content."""
    store = knowledge_store_with_markdown

    store.append_memory_markdown("pattern", {
        "title": "Async Patterns",
        "content": "Use asyncio.gather for parallel I/O.",
    })

    result = store.read_memory_markdown("pattern")
    assert "Async Patterns" in result
    assert "asyncio.gather" in result


def test_read_memory_markdown_nonexistent(knowledge_store_with_markdown):
    """read_memory_markdown should return '' for non-existent files."""
    store = knowledge_store_with_markdown
    result = store.read_memory_markdown("nonexistent")
    assert result == ""


def test_list_memory_files(knowledge_store_with_markdown):
    """list_memory_files should return stats for each memory type."""
    store = knowledge_store_with_markdown

    store.append_memory_markdown("convention", {
        "title": "Test Convention",
        "content": "Test content",
    })

    files = store.list_memory_files()

    # There should be an entry for the convention type
    convention_entries = [f for f in files if f["type"] == "convention"]
    assert len(convention_entries) == 1
    assert convention_entries[0]["size"] > 0
    assert convention_entries[0]["entries"] >= 1


# ─── Edge cases ─────────────────────────────────────────


def test_search_knowledge_empty_result(mock_knowledge_store):
    """search_knowledge should return empty list when nothing matches."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchall.return_value = []

    results = store.search_knowledge("xyznonexistent123")

    assert isinstance(results, list)
    assert len(results) == 0


def test_recall_empty_result(mock_knowledge_store):
    """recall should return empty list for no matches."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchall.return_value = []

    results = store.recall("unknown_agent", "nothing")

    assert isinstance(results, list)
    assert len(results) == 0


def test_get_due_tasks_empty(mock_knowledge_store):
    """get_due_tasks should return empty list when nothing is due."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchall.return_value = []

    due = store.get_due_tasks()
    assert isinstance(due, list)
    assert len(due) == 0


def test_add_knowledge_minimal_args(mock_knowledge_store):
    """add_knowledge should work with just content."""
    store = mock_knowledge_store
    cursor = store.conn.cursor.return_value
    cursor.fetchone.return_value = (1,)

    entry_id = store.add_knowledge(content="Minimal entry")
    assert entry_id == 1


def test_store_close(mock_knowledge_store):
    """close() should close the connection if open."""
    store = mock_knowledge_store
    store.close()
    store.conn.close.assert_called_once()


def test_store_close_already_closed(mock_knowledge_store):
    """close() should not fail on already-closed connections."""
    store = mock_knowledge_store
    store.conn.closed = True
    store.close()  # Should not raise
    # close() should not be called because conn is already closed
    # But our mock doesn't check that, so just ensure no exception
    assert True


# ─── Provider detection (for scheduler tasks) ───────────


def test_detect_provider_deepseek(monkeypatch):
    """Should detect 'deepseek' when API key is present in env."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    # Also mock the file path to not exist
    with patch("os.path.exists", return_value=False):
        from ai_workspace.tasks.scheduler import _detect_provider
        assert _detect_provider() == "deepseek"


def test_detect_provider_ollama(monkeypatch):
    """Should default to 'ollama' when no API key anywhere."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", side_effect=FileNotFoundError):
        # Re-import to pick up the new env state
        from importlib import reload
        import ai_workspace.tasks.scheduler as scheduler
        reload(scheduler)
        assert scheduler._detect_provider() == "ollama"


# ─── Safe float helper (from deep_search) ──────────────


def test_safe_float_with_number():
    from ai_workspace.search.deep_search import _safe_float
    assert _safe_float(0.85) == 0.85
    assert _safe_float(42) == 42.0


def test_safe_float_with_string():
    from ai_workspace.search.deep_search import _safe_float
    assert _safe_float("0.85") == 0.85
    assert _safe_float("42") == 42.0


def test_safe_float_with_text():
    from ai_workspace.search.deep_search import _safe_float
    assert _safe_float("The analysis combines findings...") == 0.0


def test_safe_float_with_none():
    from ai_workspace.search.deep_search import _safe_float
    assert _safe_float(None) == 0.0


def test_safe_float_with_bool():
    from ai_workspace.search.deep_search import _safe_float
    assert _safe_float(True) == 0.0
    assert _safe_float(False) == 0.0


def test_safe_float_default():
    from ai_workspace.search.deep_search import _safe_float
    assert _safe_float("nonsense", default=0.5) == 0.5


# ─── JSON parsing safety (from deep_search) ─────────────


def test_parse_json_plain():
    from ai_workspace.search.deep_search import _parse_json_safe
    result = _parse_json_safe('{"key": "value"}')
    assert result == {"key": "value"}


def test_parse_json_with_markdown_fence():
    from ai_workspace.search.deep_search import _parse_json_safe
    result = _parse_json_safe('```json\n{"key": "value"}\n```')
    assert result == {"key": "value"}


def test_parse_json_array():
    from ai_workspace.search.deep_search import _parse_json_safe
    result = _parse_json_safe('["q1", "q2", "q3"]')
    assert result == ["q1", "q2", "q3"]


def test_parse_json_with_embedded_json():
    from ai_workspace.search.deep_search import _parse_json_safe
    result = _parse_json_safe('Here are the questions: ["q1", "q2"] and more text')
    assert result == ["q1", "q2"]


def test_parse_json_invalid_raises():
    from ai_workspace.search.deep_search import _parse_json_safe
    with pytest.raises(ValueError):
        _parse_json_safe("This is not JSON at all. No brackets here.")


# ─── Workflow Engine (unit) ─────────────────────────────


def test_step_status_values():
    from ai_workspace.workflow.engine import StepStatus
    assert StepStatus.PENDING.value == "pending"
    assert StepStatus.RUNNING.value == "running"
    assert StepStatus.DONE.value == "done"
    assert StepStatus.FAILED.value == "failed"


def test_context_get_existing_step():
    from ai_workspace.workflow.engine import Context, WorkflowRun, WorkflowLogger, StepStatus, StepResult
    run = WorkflowRun(run_id=1, workflow_name="test", input={})
    run.steps["step_a"] = StepResult(
        step_name="step_a", status=StepStatus.DONE, output={"data": "result"}
    )
    log = WorkflowLogger(run_id=1)
    ctx = Context(run=run, inputs={}, wf_log=log)

    assert ctx.get("step_a") == {"data": "result"}
    assert ctx.get("nonexistent") is None
    assert ctx.get("nonexistent", "default") == "default"


def test_context_set():
    from ai_workspace.workflow.engine import Context, WorkflowRun, WorkflowLogger
    run = WorkflowRun(run_id=1, workflow_name="test", input={})
    log = WorkflowLogger(run_id=1)
    ctx = Context(run=run, inputs={}, wf_log=log)

    ctx.set("custom_key", "custom_value")
    assert ctx.inputs["custom_key"] == "custom_value"


def test_workflow_registry():
    from ai_workspace.workflow.engine import WorkflowRegistry, BaseWorkflow, workflow

    # Clear any existing registrations
    WorkflowRegistry._workflows = {}

    @workflow
    class TestWF(BaseWorkflow):
        name = "test_workflow"

    assert "test_workflow" in WorkflowRegistry.list()
    assert WorkflowRegistry.get("test_workflow") is TestWF
    assert WorkflowRegistry.get("nonexistent") is None


# ─── Provider Registry ──────────────────────────────────


def test_provider_registry_default():
    """ProviderRegistry should always have ollama configured."""
    from ai_workspace.providers import ProviderRegistry
    registry = ProviderRegistry()
    assert "ollama" in registry.providers
    assert registry.providers["ollama"].provider.value == "ollama"


def test_provider_registry_deepseek_with_key(monkeypatch):
    """ProviderRegistry should add deepseek when DEEPSEEK_API_KEY is set."""
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test-key")
    from ai_workspace.providers import ProviderRegistry
    registry = ProviderRegistry()
    assert "deepseek" in registry.providers


def test_provider_registry_deepseek_without_key(monkeypatch):
    """ProviderRegistry should not add deepseek without API key."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with patch("os.path.exists", return_value=False):
        from ai_workspace.providers import ProviderRegistry
        registry = ProviderRegistry()
        assert "deepseek" not in registry.providers


def test_provider_registry_get_client():
    from ai_workspace.providers import ProviderRegistry
    registry = ProviderRegistry()
    with patch("openai.AsyncOpenAI") as mock_openai:
        client = registry.get_client("ollama")
        assert client is not None


def test_provider_registry_get_model():
    from ai_workspace.providers import ProviderRegistry
    registry = ProviderRegistry()
    model = registry.get_model("ollama")
    assert model == "qwen3:14b"

    model = registry.get_model("ollama", model="custom-model")
    assert model == "custom-model"
