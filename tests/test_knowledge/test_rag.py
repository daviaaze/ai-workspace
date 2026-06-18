"""
Tests for RAG (Retrieval Augmented Generation).

Covers: DocumentIndexer chunking, KnowledgeRetriever search,
RRF merge, rerank, setup_schema, convenience functions.

Refs: SPEC_RAG.md, pgvector-python examples
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_workspace.knowledge.rag import (
    Chunk,
    DocumentIndexer,
    KnowledgeRetriever,
    index_workspace,
    retrieve_context,
    search_knowledge,
    setup_schema,
    EMBED_DIM,
    EMBED_MODEL,
)


# ═══════════════════════════════════════════════════════════
# Test fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def tmp_dir():
    """Create a temp directory with test files."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


# ═══════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════

class TestChunk:
    """Chunk dataclass basics."""

    def test_defaults(self):
        """Chunk has sensible defaults."""
        c = Chunk(id="test:1", content="hello", source_file="test.py")
        assert c.id == "test:1"
        assert c.start_line == 0
        assert c.end_line == 0
        assert c.language == "text"
        assert c.chunk_type == "paragraph"

    def test_full_fields(self):
        """All fields can be set."""
        c = Chunk(
            id="src/app.py:L42",
            content="def foo(): pass",
            source_file="src/app.py",
            start_line=42,
            end_line=44,
            language="python",
            chunk_type="FunctionDef",
        )
        assert c.language == "python"
        assert c.chunk_type == "FunctionDef"


# ═══════════════════════════════════════════════════════════
# Chunking strategies
# ═══════════════════════════════════════════════════════════

class TestChunkPython:
    """Python AST-based chunking."""

    def test_functions_and_classes(self):
        """AST chunker extracts top-level functions and classes."""
        indexer = DocumentIndexer()
        code = """
import os

def hello():
    \"\"\"Say hello.\"\"\"
    return "hello"

class Greeter:
    \"\"\"A greeter class.\"\"\"
    def greet(self):
        return "hi"
"""
        chunks = indexer._chunk_python(code, "test.py")
        assert len(chunks) == 2
        assert chunks[0].chunk_type == "FunctionDef"
        assert "def hello" in chunks[0].content
        assert chunks[1].chunk_type == "ClassDef"
        assert "class Greeter" in chunks[1].content

    def test_no_functions_fallback(self):
        """Files without def/class fall back to fixed-size chunks."""
        indexer = DocumentIndexer()
        code = "x = 1\ny = 2\n" * 300  # 600 tokens
        chunks = indexer._chunk_python(code, "test.py")
        assert len(chunks) > 0
        assert chunks[0].language == "python"
        assert chunks[0].chunk_type == "paragraph"

    def test_syntax_error_fallback(self):
        """Invalid Python falls back to generic chunking."""
        indexer = DocumentIndexer()
        code = "this is not valid python !!! }}}"
        chunks = indexer._chunk_python(code, "test.py")
        assert len(chunks) >= 1

    def test_skips_tiny_functions(self):
        """Functions shorter than 50 chars fall to generic chunking."""
        indexer = DocumentIndexer()
        code = "def x(): pass\n"
        chunks = indexer._chunk_python(code, "small.py")
        # AST chunker rejects tiny functions, generic fallback catches them
        # All chunks should have some content (even if small)
        assert len(chunks) == 1
        assert "def x" in chunks[0].content


class TestChunkMarkdown:
    """Markdown heading-based chunking."""

    def test_splits_on_headings(self):
        """Markdown is split on # and ## headings."""
        indexer = DocumentIndexer()
        md = """# Title

## Section One
Content for section one. This is long enough to be a chunk.
" + "extra " * 20 + "

## Section Two
More content here. Also sufficiently long.
" + "padding " * 20
"""
        chunks = indexer._chunk_markdown(md, "doc.md")
        # Should have 2 sections (Title might be sized out)
        assert len(chunks) >= 1
        for c in chunks:
            assert c.language == "markdown"
            assert c.chunk_type == "heading"

    def test_skips_tiny_sections(self):
        """Very short sections (< 50 chars) are skipped."""
        indexer = DocumentIndexer()
        md = """# Short

hi

## Long Section
This is a longer section with enough content to be considered a chunk.
" + "filler " * 30
"""
        chunks = indexer._chunk_markdown(md, "doc.md")
        # Only the long section should be kept
        assert len(chunks) == 1
        assert "Long Section" in chunks[0].content


class TestChunkGeneric:
    """Fixed-size generic chunking."""

    def test_fixed_size_chunks(self):
        """Generic chunker creates fixed-size chunks with overlap."""
        indexer = DocumentIndexer()
        content = "word " * 1000  # 1000 words
        chunks = indexer._chunk_generic(content, "data.txt", size=200, overlap=50)
        assert len(chunks) >= 4
        for c in chunks:
            assert c.language == "text"
            assert c.chunk_type == "paragraph"
            assert len(c.content) > 0

    def test_small_content_single_chunk(self):
        """Short content produces a single chunk."""
        indexer = DocumentIndexer()
        content = "short text here"
        chunks = indexer._chunk_generic(content, "small.txt")
        assert len(chunks) == 1

    def test_empty_content(self):
        """Empty content produces no chunks."""
        indexer = DocumentIndexer()
        chunks = indexer._chunk_generic("", "empty.txt")
        assert chunks == []

    def test_custom_language(self):
        """Language parameter is passed through."""
        indexer = DocumentIndexer()
        chunks = indexer._chunk_generic(
            "hello " * 100, "test.json", language="json",
        )
        assert len(chunks) > 0
        assert all(c.language == "json" for c in chunks)


# ═══════════════════════════════════════════════════════════
# Chunk file dispatch
# ═══════════════════════════════════════════════════════════

class TestChunkFile:
    """Document-indexer file dispatch."""

    def test_python_dispatched_to_ast(self, tmp_dir):
        """Python files use AST chunker."""
        f = tmp_dir / "test.py"
        f.write_text("""
def hello():
    \"\"\"A friendly function that greets people.\"\"\"
    return "hello world"
""")
        indexer = DocumentIndexer()
        chunks = indexer._chunk_file(f)
        assert len(chunks) >= 1
        assert chunks[0].language == "python"

    def test_markdown_dispatched_to_heading(self, tmp_dir):
        """Markdown files use heading chunker."""
        f = tmp_dir / "doc.md"
        f.write_text("""# Title

## Section
This is a meaningful section that has enough text to be chunked.
" + "more text " * 20
""")
        indexer = DocumentIndexer()
        chunks = indexer._chunk_file(f)
        assert len(chunks) >= 1
        assert chunks[0].language == "markdown"

    def test_unknown_extension_generic(self, tmp_dir):
        """Unknown extensions use generic chunker."""
        f = tmp_dir / "data.txt"
        f.write_text("line " * 200)
        indexer = DocumentIndexer()
        chunks = indexer._chunk_file(f)
        assert len(chunks) >= 1
        assert chunks[0].language == "text"


# ═══════════════════════════════════════════════════════════
# Should skip
# ═══════════════════════════════════════════════════════════

class TestShouldSkip:
    """File filtering logic."""

    def test_skips_binary_extensions(self, tmp_dir):
        """Image files are skipped."""
        indexer = DocumentIndexer()
        assert indexer._should_skip(tmp_dir / "img.png")
        assert indexer._should_skip(tmp_dir / "img.jpg")
        assert indexer._should_skip(tmp_dir / "font.woff2")

    def test_skips_hidden_dirs(self, tmp_dir):
        """Files in hidden/generated dirs are skipped."""
        indexer = DocumentIndexer()
        assert indexer._should_skip(Path(".git/config"))
        assert indexer._should_skip(Path("node_modules/pkg/index.js"))
        assert indexer._should_skip(Path(".venv/lib/python/site.py"))

    def test_does_not_skip_python_files(self, tmp_dir):
        """Regular Python files are not skipped."""
        f = tmp_dir / "my_code.py"
        f.write_text("x = 1")
        indexer = DocumentIndexer()
        assert not indexer._should_skip(f)

    def test_skips_large_files(self, tmp_dir):
        """Files > MAX_FILE_SIZE are skipped (mocked)."""
        f = tmp_dir / "large.py"
        f.write_text("x" * 100)
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 2_000_000
            indexer = DocumentIndexer()
            assert indexer._should_skip(f)


# ═══════════════════════════════════════════════════════════
# RRF Merge
# ═══════════════════════════════════════════════════════════

class TestRRFMerge:
    """Reciprocal Rank Fusion algorithm."""

    def test_empty_lists(self):
        """Empty inputs produce empty output."""
        result = KnowledgeRetriever._rrf_merge([], [])
        assert result == []

    def test_single_list(self):
        """Single populated list preserves order."""
        items = [
            {"id": "a", "score": 1.0, "content": "A"},
            {"id": "b", "score": 0.8, "content": "B"},
        ]
        result = KnowledgeRetriever._rrf_merge(items, [])
        assert len(result) == 2
        # Order should be preserved (higher rank = higher RRF score)
        assert result[0]["id"] == "a"
        assert result[1]["id"] == "b"

    def test_merged_lists(self):
        """Two lists with overlap are correctly merged."""
        a = [
            {"id": "a", "score": 1.0, "content": "A"},
            {"id": "b", "score": 0.8, "content": "B"},
        ]
        b = [
            {"id": "b", "score": 0.9, "content": "B"},
            {"id": "c", "score": 0.7, "content": "C"},
        ]
        result = KnowledgeRetriever._rrf_merge(a, b)
        # b appears in both, should rank highest
        assert result[0]["id"] == "b"
        # All three unique IDs should be present
        ids = {r["id"] for r in result}
        assert ids == {"a", "b", "c"}

    def test_rrf_score_present(self):
        """Each result has a non-zero RRF score."""
        a = [{"id": "x", "score": 1.0, "content": "X"}]
        b = [{"id": "x", "score": 1.0, "content": "X"}]
        result = KnowledgeRetriever._rrf_merge(a, b)
        assert len(result) == 1
        assert result[0]["score"] > 0.0


# ═══════════════════════════════════════════════════════════
# Rerank
# ═══════════════════════════════════════════════════════════

class TestRerank:
    """Score-based reranking with keyword boost."""

    def test_boost_exact_matches(self):
        """Exact keyword matches get a score boost."""
        candidates = [
            {"id": "a", "score": 1.0, "content": "this is about auth middleware"},
            {"id": "b", "score": 1.0, "content": "unrelated topic text"},
        ]
        result = KnowledgeRetriever._rerank("auth middleware", candidates)
        # "a" should rank higher because of keyword overlap
        assert result[0]["id"] == "a"
        assert result[0]["score"] > result[1]["score"]

    def test_preserves_items(self):
        """Reranking does not drop items."""
        candidates = [
            {"id": "a", "score": 0.5, "content": "x"},
            {"id": "b", "score": 0.3, "content": "y"},
        ]
        result = KnowledgeRetriever._rerank("query", candidates)
        assert len(result) == 2

    def test_empty_input(self):
        """Empty input returns empty list."""
        result = KnowledgeRetriever._rerank("query", [])
        assert result == []


# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

class TestConstants:
    """Module-level constants are correct."""

    def test_embed_model(self):
        """EMBED_MODEL is nomic-embed-text."""
        assert EMBED_MODEL == "nomic-embed-text"

    def test_embed_dim(self):
        """EMBED_DIM matches nomic-embed-text output."""
        assert EMBED_DIM == 768


# ═══════════════════════════════════════════════════════════
# Convenience functions (mocked)
# ═══════════════════════════════════════════════════════════

class TestConvenienceFunctions:
    """Top-level convenience functions with mocked DB."""

    def test_retrieve_context_empty_results(self):
        """retrieve_context returns empty string when no results."""
        with patch.object(KnowledgeRetriever, "retrieve", return_value=[]):
            result = retrieve_context("query")
            assert result == ""

    def test_retrieve_context_formatted(self):
        """retrieve_context formats results with source references."""
        mock_results = [
            {
                "id": "f:L1",
                "content": "def foo(): pass",
                "source_file": "src/foo.py",
                "start_line": 1,
                "end_line": 3,
                "score": 0.9,
            },
        ]
        with patch.object(KnowledgeRetriever, "retrieve", return_value=mock_results):
            result = retrieve_context("query", k=3)
            assert "RELEVANT CONTEXT" in result
            assert "src/foo.py" in result
            assert "def foo" in result

    def test_index_workspace_with_invalid_path(self):
        """index_workspace with a nonexistent path returns 0."""
        with patch(
            "ai_workspace.knowledge.rag.setup_schema",
        ), patch.object(
            DocumentIndexer, "index_directory", return_value=0,
        ):
            count = index_workspace(Path("/nonexistent/path"))
            assert count == 0
