"""Smoke tests for LightRAGEngine and SyncManager."""

from __future__ import annotations

import tempfile
from unittest.mock import patch

# ═══════════════════════════════════════════════════════
# LightRAGEngine
# ═══════════════════════════════════════════════════════


class TestLightRAGEngine:
    def test_engine_type_is_graph(self):
        from ai_workspace.knowledge.engine import LightRAGEngine
        engine = LightRAGEngine()
        assert engine.engine_type == "graph"

    def test_name_is_lightrag(self):
        from ai_workspace.knowledge.engine import LightRAGEngine
        engine = LightRAGEngine()
        assert engine.name == "lightrag"

    def test_initialize_returns_false_when_lightrag_missing(self):
        """When lightrag is not installed, _initialize returns False gracefully."""
        from ai_workspace.knowledge.engine import LightRAGEngine
        with patch("builtins.__import__", side_effect=ImportError("no lightrag")):
            engine = LightRAGEngine()
            assert engine._initialize() is False

    def test_initialize_with_temp_dir_does_not_crash(self):
        """_initialize creates the working directory if needed."""
        from ai_workspace.knowledge.engine import LightRAGEngine
        with tempfile.TemporaryDirectory() as td:
            engine = LightRAGEngine(working_dir=td)
            try:
                engine._initialize()
            except Exception as exc:
                assert isinstance(exc, ImportError)

    def test_retrieve_returns_empty_when_not_initialized(self):
        """Retrieve returns [] when LightRAG is not available."""
        from ai_workspace.knowledge.engine import LightRAGEngine
        with patch.object(LightRAGEngine, "_initialize", return_value=False):
            engine = LightRAGEngine()
            result = engine.retrieve("test query", k=3)
            assert result == []

    def test_store_returns_zero_when_not_initialized(self):
        """Store returns 0 when LightRAG is not available."""
        from ai_workspace.knowledge.engine import LightRAGEngine
        with patch.object(LightRAGEngine, "_initialize", return_value=False):
            engine = LightRAGEngine()
            result = engine.store(["chunk 1", "chunk 2"])
            assert result == 0

    def test_retrieve_context_returns_empty_string(self):
        """retrieve_context returns '' when LightRAG is unavailable."""
        from ai_workspace.knowledge.engine import LightRAGEngine
        with patch.object(LightRAGEngine, "_initialize", return_value=False):
            engine = LightRAGEngine()
            result = engine.retrieve_context("query")
            assert result == ""


# ═══════════════════════════════════════════════════════
# SyncManager
# ═══════════════════════════════════════════════════════


class TestSyncManager:
    def test_sync_manager_importable(self):
        """SyncManager class is importable and instantiable."""
        from ai_workspace.knowledge.sync import SyncManager
        sm = SyncManager()
        assert sm is not None

    def test_sync_knowledge_returns_dict(self):
        """sync_knowledge returns a status dict even without DB."""
        import asyncio

        from ai_workspace.knowledge.sync import SyncManager
        sm = SyncManager()
        result = asyncio.run(sm.sync_knowledge(direction="both"))
        assert isinstance(result, dict)
        assert "synced" in result or "error" in result

    def test_sync_vault_returns_dict(self):
        """sync_vault returns a status dict."""
        import asyncio

        from ai_workspace.knowledge.sync import SyncManager
        sm = SyncManager()
        result = asyncio.run(sm.sync_vault())
        assert isinstance(result, dict)
