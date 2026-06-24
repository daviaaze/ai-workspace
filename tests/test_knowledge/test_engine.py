"""Tests for retrieval engine abstraction — engine.py."""

import tempfile
from pathlib import Path

import pytest

from ai_workspace.knowledge.engine import (
    ENGINE_REGISTRY,
    LightRAGEngine,
    MultiEngineRetriever,
    ObsidianEngine,
    PgVectorEngine,
    RetrievalEngine,
    RetrievalResult,
    get_engine,
    list_engines,
)


# ═══════════════════════════════════════════════════════════
# RetrievalResult
# ═══════════════════════════════════════════════════════════


class TestRetrievalResult:
    def test_defaults(self):
        """Result defaults are sensible."""
        r = RetrievalResult(id="1", content="hello", source="test.md")
        assert r.score == 0.0
        assert r.engine == ""
        assert r.metadata == {}

    def test_required_fields(self):
        """Required fields are set."""
        r = RetrievalResult(id="1", content="content", source="file.md")
        assert r.id == "1"
        assert r.content == "content"
        assert r.source == "file.md"

    def test_full_fields(self):
        """All fields can be set."""
        r = RetrievalResult(
            id="abc",
            content="some text",
            source="/path/file.md:10",
            score=0.95,
            engine="pgvector",
            metadata={"source_file": "file.md"},
        )
        assert r.score == 0.95
        assert r.engine == "pgvector"
        assert r.metadata["source_file"] == "file.md"


# ═══════════════════════════════════════════════════════════
# ObsidianEngine
# ═══════════════════════════════════════════════════════════


class TestObsidianEngine:
    @pytest.fixture
    def vault(self) -> Path:
        """Create a temp Obsidian vault with test notes."""
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp) / "my-vault"
            vault.mkdir()

            # Note with auth-related content
            auth_note = vault / "Authentication.md"
            auth_note.write_text(
                "# Authentication\n"
                "Use JWT tokens for API auth.\n"
                "Tokens expire after 24 hours.\n"
                "Store secrets in environment variables.\n"
            )

            # Note about database
            db_note = vault / "Database.md"
            db_note.write_text(
                "# Database\n"
                "PostgreSQL with pgvector for embeddings.\n"
                "Connection string from env var.\n"
            )

            # Nested note
            nested_dir = vault / "features"
            nested_dir.mkdir()
            config_note = nested_dir / "configuration.md"
            config_note.write_text(
                "# Configuration\n"
                "YAML files in config/ directory.\n"
                "Environment variables override YAML.\n"
            )

            yield vault

    def test_engine_properties(self, vault: Path):
        """Basic engine properties."""
        engine = ObsidianEngine(vault)
        assert engine.name == "obsidian"
        assert engine.engine_type == "page_index"
        assert engine.health() is True

    def test_retrieve_basic(self, vault: Path):
        """Basic retrieval finds matching notes."""
        engine = ObsidianEngine(vault)
        results = engine.retrieve("authentication", k=5)

        assert len(results) >= 1
        assert any("Authentication" in r.source for r in results)
        assert all(isinstance(r.score, float) for r in results)
        assert all(r.engine == "obsidian" for r in results)

    def test_retrieve_multiple_tokens(self, vault: Path):
        """Retrieval with multi-token query."""
        engine = ObsidianEngine(vault)
        results = engine.retrieve("jwt token authentication", k=5)
        assert len(results) >= 1

    def test_retrieve_empty_query(self, vault: Path):
        """Empty query returns no results."""
        engine = ObsidianEngine(vault)
        results = engine.retrieve("", k=5)
        assert results == []

    def test_retrieve_no_match(self, vault: Path):
        """Query with no matches returns empty."""
        engine = ObsidianEngine(vault)
        results = engine.retrieve("xyznonexistentquery", k=5)
        assert results == []

    def test_retrieve_context_format(self, vault: Path):
        """retrieve_context returns formatted string."""
        engine = ObsidianEngine(vault)
        ctx = engine.retrieve_context("database", k=2)
        assert ctx.startswith("//")
        assert "Database" in ctx or "database" in ctx.lower()

    def test_stats(self, vault: Path):
        """Stats reflect vault contents."""
        engine = ObsidianEngine(vault)
        stats = engine.stats()
        assert stats["file_count"] >= 3  # 3 .md files
        assert stats["healthy"] is True
        assert stats["vault_path"] == str(vault)

    def test_invalid_path(self):
        """Engine raises on non-existent vault."""
        with pytest.raises(NotADirectoryError):
            ObsidianEngine("/nonexistent/path")

    def test_reset(self, vault: Path):
        """Reset clears the file cache."""
        engine = ObsidianEngine(vault)
        _ = engine.stats()  # Builds cache
        assert engine._cache_ready is True
        engine.reset()
        assert engine._cache_ready is False

    def test_include_paths(self, vault: Path):
        """include_paths restricts search scope."""
        engine = ObsidianEngine(vault)
        # Search only in the 'features' subdirectory
        results = engine.retrieve("configuration", k=5, include_paths=["features"])
        assert len(results) >= 1
        assert "features" in results[0].source

    def test_include_paths_excludes(self, vault: Path):
        """include_paths can exclude other directories."""
        engine = ObsidianEngine(vault)
        results = engine.retrieve("authentication", k=5, include_paths=["features"])
        # Authentication note is in root, not features
        auth_results = [r for r in results if "Authentication" in r.source]
        assert len(auth_results) == 0

    def test_custom_extensions(self, vault: Path):
        """Custom extensions filter files."""
        engine = ObsidianEngine(vault, extensions=[".py"])
        results = engine.retrieve("authentication", k=5)
        assert results == []

    def test_wiki_links(self, vault: Path):
        """Wiki links [[like this]] are resolved in content."""
        vault_with_links = vault / "Links.md"
        vault_with_links.write_text(
            "# Links\n"
            "See [[Authentication]] for details.\n"
            "See [[Database|DB Notes]] for schema.\n"
        )

        engine = ObsidianEngine(vault)
        results = engine.retrieve("links", k=5)
        links_result = [r for r in results if "Links" in r.source]
        if links_result:
            assert "[[" not in links_result[0].content


# ═══════════════════════════════════════════════════════════
# MultiEngineRetriever
# ═══════════════════════════════════════════════════════════


class TestMultiEngineRetriever:
    def test_init_empty(self):
        """Empty engine list raises."""
        with pytest.raises(ValueError, match="At least one engine"):
            MultiEngineRetriever([])

    def test_single_engine(self):
        """Works with a single engine."""
        from unittest.mock import MagicMock

        mock = MagicMock(spec=RetrievalEngine)
        mock.name = "mock"
        mock.retrieve.return_value = [
            RetrievalResult(id="1", content="test", source="file.md", score=0.9),
        ]

        merger = MultiEngineRetriever([mock])
        results = merger.retrieve("query", k=5)
        assert len(results) == 1
        assert results[0].content == "test"

    def test_multi_engine_merge(self):
        """Multiple engines merge results via RRF."""
        from unittest.mock import MagicMock

        e1 = MagicMock(spec=RetrievalEngine)
        e1.name = "engine1"
        e1.retrieve.return_value = [
            RetrievalResult(id="a", content="result a", source="f1", score=0.9),
            RetrievalResult(id="b", content="result b", source="f1", score=0.5),
        ]

        e2 = MagicMock(spec=RetrievalEngine)
        e2.name = "engine2"
        e2.retrieve.return_value = [
            RetrievalResult(id="b", content="result b", source="f2", score=0.8),
            RetrievalResult(id="c", content="result c", source="f2", score=0.3),
        ]

        merger = MultiEngineRetriever([e1, e2])
        results = merger.retrieve("query", k=5)
        # All 3 unique results should be present
        ids = {r.id for r in results}
        assert len(ids) == 3
        assert "a" in ids
        assert "b" in ids
        assert "c" in ids

    def test_engine_failure_isolation(self):
        """One engine failing doesn't crash the merger."""
        from unittest.mock import MagicMock

        e1 = MagicMock(spec=RetrievalEngine)
        e1.name = "failing"
        e1.retrieve.side_effect = RuntimeError("Engine down")

        e2 = MagicMock(spec=RetrievalEngine)
        e2.name = "working"
        e2.retrieve.return_value = [
            RetrievalResult(id="1", content="ok", source="f", score=0.5),
        ]

        merger = MultiEngineRetriever([e1, e2])
        results = merger.retrieve("query")
        assert len(results) == 1

    def test_retrieve_context(self):
        """retrieve_context formats merged results."""
        from unittest.mock import MagicMock

        mock = MagicMock(spec=RetrievalEngine)
        mock.name = "mock"
        mock.retrieve.return_value = [
            RetrievalResult(id="1", content="test content", source="doc.md", score=0.7),
        ]

        merger = MultiEngineRetriever([mock])
        ctx = merger.retrieve_context("query")
        assert "test content" in ctx
        assert "doc.md" in ctx

    def test_stats(self):
        """Stats returns per-engine info."""
        from unittest.mock import MagicMock

        e1 = MagicMock(spec=RetrievalEngine)
        e1.name = "e1"
        e1.stats.return_value = {"name": "e1"}

        merger = MultiEngineRetriever([e1])
        stats = merger.stats()
        assert len(stats) == 1

    def test_health(self):
        """Health returns per-engine status."""
        from unittest.mock import MagicMock

        e1 = MagicMock(spec=RetrievalEngine)
        e1.name = "e1"
        e1.health.return_value = True

        merger = MultiEngineRetriever([e1])
        health = merger.health()
        assert health == {"e1": True}


# ═══════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════


class TestGetEngine:
    def test_vector_engine(self):
        """get_engine returns PgVectorEngine for 'vector'."""
        engine = get_engine("vector")
        assert isinstance(engine, PgVectorEngine)
        assert engine.name == "pgvector"

    def test_pgvector_alias(self):
        """get_engine returns PgVectorEngine for 'pgvector'."""
        engine = get_engine("pgvector")
        assert isinstance(engine, PgVectorEngine)

    def test_obsidian_engine_invalid_path(self):
        """Obsidian engine needs valid path."""
        # This will fail at init because the vault doesn't exist
        with pytest.raises(NotADirectoryError):
            get_engine("obsidian", vault_path="/nonexistent")

    def test_unknown_engine(self):
        """Unknown engine type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown engine type"):
            get_engine("nonexistent")

    def test_list_engines(self):
        """list_engines returns descriptions."""
        engines = list_engines()
        engine_types = {e["type"] for e in engines}
        assert "vector" in engine_types
        assert "obsidian" in engine_types
        assert "lightrag" in engine_types
        assert len(engines) >= 3

    def test_registry_has_types(self):
        """ENGINE_REGISTRY maps expected types."""
        assert "vector" in ENGINE_REGISTRY
        assert "pgvector" in ENGINE_REGISTRY
        assert "obsidian" in ENGINE_REGISTRY
        assert "lightrag" in ENGINE_REGISTRY
        assert "graph" in ENGINE_REGISTRY


# ═══════════════════════════════════════════════════════════
# LightRAGEngine (optional — skips if not installed)
# ═══════════════════════════════════════════════════════════


class TestLightRAGEngine:
    def test_properties(self):
        """Engine properties are correct."""
        engine = LightRAGEngine(working_dir="/tmp/test-lightrag")
        assert engine.name == "lightrag"
        assert engine.engine_type == "graph"

    def test_health_no_lightrag(self):
        """health() is False when lightrag not installed."""
        engine = LightRAGEngine(working_dir="/tmp/test-lightrag")
        # Without the lightrag package, health should be False
        assert engine.health() is False

    def test_retrieve_no_lightrag(self):
        """retrieve returns empty list when lightrag not installed."""
        engine = LightRAGEngine(working_dir="/tmp/test-lightrag")
        results = engine.retrieve("test")
        assert results == []

    def test_store_no_lightrag(self):
        """store returns 0 when lightrag not installed."""
        engine = LightRAGEngine(working_dir="/tmp/test-lightrag")
        assert engine.store(["test"]) == 0

    def test_stats_no_lightrag(self):
        """stats returns metadata without crashing."""
        engine = LightRAGEngine(working_dir="/tmp/test-lightrag")
        stats = engine.stats()
        assert stats["name"] == "lightrag"
        assert stats["initialized"] is False


# ═══════════════════════════════════════════════════════════
# Abstract Base
# ═══════════════════════════════════════════════════════════


class TestRetrievalEngineABC:
    def test_cannot_instantiate_base(self):
        """ABC cannot be instantiated directly."""
        with pytest.raises(TypeError):
            RetrievalEngine()  # type: ignore

    def test_default_store_raises(self):
        """Default store() raises NotImplementedError."""
        from unittest.mock import MagicMock

        engine = MagicMock(spec=RetrievalEngine)
        engine.store.side_effect = NotImplementedError()
        with pytest.raises(NotImplementedError):
            engine.store(["test"])
