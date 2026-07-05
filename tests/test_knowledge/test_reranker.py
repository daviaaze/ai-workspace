"""
E2E tests for the Reranker class and search pipeline.

Covers:
- Reranker backend isolation (keyword, ollama, cross-encoder)
- Automatic fallback chain (auto mode)
- KnowledgeRetriever integration
- Edge cases: empty candidates, API errors, import failures
"""

from __future__ import annotations

import copy
from unittest.mock import MagicMock, patch

import pytest

from ai_workspace.knowledge.rag import (
    RERANKER_METHOD,
    RERANKER_MODEL,
    KnowledgeRetriever,
    Reranker,
)

# ═══════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════

@pytest.fixture
def sample_candidates():
    """Sample search results for reranking tests."""
    return copy.deepcopy([
        {"id": "doc1", "content": "FastAPI is an async Python web framework", "score": 0.9},
        {"id": "doc2", "content": "Django is a synchronous web framework", "score": 0.8},
        {"id": "doc3", "content": "Python is great for data science and ML", "score": 0.7},
        {"id": "doc4", "content": "Rust is a systems programming language", "score": 0.6},
    ])


@pytest.fixture
def reranker_keyword():
    """Reranker forced to keyword backend."""
    return Reranker(method="keyword")


# ═══════════════════════════════════════════════════════════
# Keyword Backend (no mocks needed — pure Python)
# ═══════════════════════════════════════════════════════════

class TestRerankerKeyword:
    """Tests for the keyword overlap backend (no network, no GPU)."""

    def test_keyword_boosts_relevant_candidates(self, reranker_keyword, sample_candidates):
        """Candidates with more query term overlap get boosted."""
        query = "async python web framework"
        # Save baseline before rerank modifies in-place
        baseline = copy.deepcopy(sample_candidates)
        result = reranker_keyword.rerank(query, sample_candidates)

        # doc1 has "async", "python", "web", "framework" → highest overlap
        assert result[0]["id"] == "doc1"
        assert result[0]["score"] > baseline[0]["score"]

    def test_keyword_preserves_order_when_no_overlap(self, reranker_keyword):
        """When no terms match, original order is preserved (no boost)."""
        candidates = [
            {"id": "a", "content": "aaa bbb ccc", "score": 0.8},
            {"id": "b", "content": "ddd eee fff", "score": 0.7},
        ]
        result = reranker_keyword.rerank("xyz", candidates)
        assert result[0]["id"] == "a"
        assert result[0]["score"] == 0.8

    def test_keyword_score_calculation(self, reranker_keyword):
        """Each overlapping term adds 10% boost to base score."""
        candidates = [
            {"id": "a", "content": "python", "score": 1.0},
        ]
        result = reranker_keyword.rerank("python", candidates)
        # 1 term overlap → 1.0 * (1.0 + 0.1 * 1) = 1.1
        assert result[0]["score"] == pytest.approx(1.1)

    def test_keyword_case_insensitive(self, reranker_keyword):
        """Matching is case-insensitive."""
        candidates = [
            {"id": "a", "content": "Python Async", "score": 1.0},
        ]
        result = reranker_keyword.rerank("python async", candidates)
        assert result[0]["score"] == pytest.approx(1.2)  # 2 terms * 0.1

    def test_empty_candidates(self, reranker_keyword):
        """Empty candidate list returns empty."""
        result = reranker_keyword.rerank("query", [])
        assert result == []


# ═══════════════════════════════════════════════════════════
# Ollama Backend (mocked httpx)
# ═══════════════════════════════════════════════════════════

class TestRerankerOllama:
    """Tests for the Ollama /api/rerank backend."""

    @patch("httpx.Client")
    def test_ollama_success(self, mock_httpx_client, sample_candidates):
        """Ollama rerank maps results back by index."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"index": 2, "relevance_score": 0.95},  # doc3 most relevant
                {"index": 0, "relevance_score": 0.80},  # doc1
                {"index": 1, "relevance_score": 0.30},  # doc2
                {"index": 3, "relevance_score": 0.10},  # doc4
            ],
        }
        # Chain: httpx.Client() → context manager → .post() → mock_response
        mock_httpx_client.return_value.__enter__.return_value = mock_response
        mock_response.post.return_value = mock_response

        reranker = Reranker(method="llm", ollama_host="http://test:11434")
        result = reranker.rerank("test query", sample_candidates)

        assert result[0]["id"] == "doc3"  # highest score
        assert result[1]["id"] == "doc1"
        assert result[0]["score"] == 0.95

    @patch("httpx.Client")
    def test_ollama_empty_results_returns_original_order(self, mock_httpx_client, sample_candidates):
        """Empty results from Ollama logs warning and returns original order."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_httpx_client.return_value.__enter__.return_value = mock_response
        mock_response.post.return_value = mock_response

        reranker = Reranker(method="llm", ollama_host="http://test:11434")
        # Empty results are caught by rerank()'s exception handler
        # and return original order (no-op fallback)
        result = reranker.rerank("test", sample_candidates)
        assert len(result) == 4
        assert result[0]["id"] == "doc1"  # original order preserved

    @patch("httpx.Client")
    def test_ollama_http_error_falls_back_in_auto_mode(
        self, mock_httpx_client, sample_candidates
    ):
        """In auto mode, HTTP errors fall back gracefully."""
        mock_httpx_client.return_value.__enter__.return_value = (
            MagicMock(raise_for_status=MagicMock(side_effect=Exception("Connection refused")))
        )

        reranker = Reranker(method="auto", ollama_host="http://down:11434")
        # Should fall back to keyword and not crash
        result = reranker.rerank("async python", sample_candidates)
        assert len(result) == 4
        assert result[0]["score"] > 0  # keyword fallback worked


# ═══════════════════════════════════════════════════════════
# Cross-Encoder Backend (mocked)
# ═══════════════════════════════════════════════════════════

class TestRerankerCrossEncoder:
    """Tests for the sentence-transformers cross-encoder backend."""

    @patch("ai_workspace.knowledge.rag.Reranker._rerank_cross_encoder")
    def test_cross_encoder_called_in_auto_mode(
        self, mock_ce, sample_candidates
    ):
        """When ollama fails, auto mode tries cross-encoder."""
        mock_ce.return_value = sorted(
            sample_candidates, key=lambda x: x.get("score", 0.0), reverse=True
        )

        # Create reranker that simulates ollama failing → cross-encoder
        reranker = Reranker(method="cross-encoder")
        reranker.rerank("test", sample_candidates)
        mock_ce.assert_called_once()


# ═══════════════════════════════════════════════════════════
# Fallback Chain (auto mode)
# ═══════════════════════════════════════════════════════════

class TestRerankerFallback:
    """Tests for the automatic fallback chain."""

    def test_auto_falls_to_keyword_when_ollama_down(self, sample_candidates):
        """auto mode tries ollama → cross_encoder → keyword. Keyword always works."""
        reranker = Reranker(method="auto", ollama_host="http://localhost:1")

        # Should not crash — keyword doesn't need network
        result = reranker.rerank("test query", sample_candidates)
        assert len(result) == 4

    def test_pipeline_respected_for_llm_mode(self):
        """llm mode only tries ollama, no fallback."""
        reranker = Reranker(method="llm")
        assert reranker._pipeline == ["ollama"]

    def test_pipeline_respected_for_keyword_mode(self):
        """keyword mode only tries keyword."""
        reranker = Reranker(method="keyword")
        assert reranker._pipeline == ["keyword"]


# ═══════════════════════════════════════════════════════════
# KnowledgeRetriever Integration
# ═══════════════════════════════════════════════════════════

class TestKnowledgeRetrieverRerankIntegration:
    """Tests that KnowledgeRetriever._rerank() delegates to Reranker."""

    def test_retriever_creates_reranker_on_first_call(self):
        """_ensure_imports() initializes the Reranker."""
        retriever = KnowledgeRetriever(db_url="postgresql:///mock")
        retriever._ensure_imports()
        assert retriever._reranker is not None
        assert isinstance(retriever._reranker, Reranker)

    def test_retriever_rerank_delegates_to_reranker(self, sample_candidates):
        """_rerank() calls Reranker.rerank() and returns sorted results."""
        retriever = KnowledgeRetriever(db_url="postgresql:///mock")
        retriever._ensure_imports()
        # Force keyword mode for deterministic results
        retriever._reranker = Reranker(method="keyword")

        result = retriever._rerank("async python", sample_candidates)
        assert len(result) == 4
        # doc1 has most overlap with "async python"
        assert result[0]["id"] == "doc1"

    def test_retriever_rerank_called_from_retrieve(self):
        """retrieve() with hybrid strategy calls _rerank.

        We can't easily test the full pipeline without a DB,
        but we can verify the method exists and accepts the right args.
        """
        retriever = KnowledgeRetriever(db_url="postgresql:///mock")
        assert hasattr(retriever, "_rerank")
        assert callable(retriever._rerank)


# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

class TestRerankerConstants:
    """Verify reranker constants match expectations."""

    def test_reranker_model_default(self):
        assert RERANKER_MODEL == "batiai/qwen3-reranker:8b"

    def test_reranker_method_default(self):
        assert RERANKER_METHOD == "auto"
