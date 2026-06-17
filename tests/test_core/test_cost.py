"""
Tests for the cost optimization layer (Fase 0).

Covers:
- CircuitBreaker state machine
- BudgetEnforcer: per-call, daily, monthly limits
- BudgetEnforcer: circuit breaker integration
- SemanticCache: hash hit, semantic miss, set+get cycle
- CostService: facade integration
- BudgetExceededError

All tests are pure Python — no real DB connections, no LLM calls.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from ai_workspace.core.cost import (
    CircuitBreaker,
    BudgetEnforcer,
    BudgetExceededError,
    SemanticCache,
    CostLog,
    CostService,
)


# ═══════════════════════════════════════════════════════════════
# CircuitBreaker
# ═══════════════════════════════════════════════════════════════


class TestCircuitBreakerStateMachine:
    """Circuit breaker transitions: closed → open → half_open → closed."""

    def test_initial_state_is_closed(self):
        cb = CircuitBreaker("test")
        assert cb.state == "closed"
        assert cb.failure_count == 0
        assert cb.allow_request() is True

    def test_open_after_threshold_failures(self):
        cb = CircuitBreaker("deepseek", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"  # not yet
        cb.record_failure()          # 3rd → opens
        assert cb.state == "open"
        assert cb.failure_count == 3

    def test_open_circuit_blocks_requests(self):
        cb = CircuitBreaker("deepseek", failure_threshold=1)
        cb.record_failure()
        assert cb.state == "open"
        assert cb.allow_request() is False

    def test_half_open_after_timeout(self):
        cb = CircuitBreaker("deepseek", failure_threshold=1, reset_timeout=0.05)
        cb.record_failure()
        assert cb.state == "open"
        time.sleep(0.06)
        # Now should allow a probe request → half_open
        assert cb.allow_request() is True
        assert cb.state == "half_open"

    def test_half_open_probe_success_closes_circuit(self):
        cb = CircuitBreaker("deepseek", failure_threshold=1, reset_timeout=0.05)
        cb.record_failure()
        time.sleep(0.06)
        cb.allow_request()      # transition to half_open
        cb.record_success()      # probe succeeds → closed
        assert cb.state == "closed"
        assert cb.failure_count == 0

    def test_half_open_probe_failure_reopens_circuit(self):
        cb = CircuitBreaker("deepseek", failure_threshold=1, reset_timeout=0.05)
        cb.record_failure()
        time.sleep(0.06)
        cb.allow_request()      # half_open
        cb.record_failure()      # probe fails → open again
        assert cb.state == "open"

    def test_multiple_successes_reset_counter(self):
        cb = CircuitBreaker("deepseek", failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        # 2 more failures won't open (counter reset)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "closed"

    def test_default_thresholds_per_provider(self):
        """Verify that default circuit breakers have their configured thresholds."""
        budget = BudgetEnforcer()
        assert budget._circuits["deepseek"].failure_threshold == 3
        assert budget._circuits["deepseek"].reset_timeout == 60
        assert budget._circuits["gemini"].failure_threshold == 5
        assert budget._circuits["gemini"].reset_timeout == 30
        assert budget._circuits["ollama"].failure_threshold == 2
        assert budget._circuits["ollama"].reset_timeout == 120


# ═══════════════════════════════════════════════════════════════
# BudgetEnforcer — limits
# ═══════════════════════════════════════════════════════════════


class TestBudgetEnforcerLimits:
    """Budget enforcement without DB — pure limit checks."""

    def test_very_small_cost_allowed(self):
        budget = BudgetEnforcer()
        allowed, reason = budget.can_call(0.0001, "deepseek")
        assert allowed is True
        assert reason == "ok"

    def test_per_call_limit_exceeded(self):
        budget = BudgetEnforcer()
        allowed, reason = budget.can_call(0.02, "deepseek")
        assert allowed is False
        assert "per-call" in reason.lower()

    def test_daily_limit_exceeded(self):
        budget = BudgetEnforcer()
        # Simulate already spent near daily limit
        with patch.object(budget.logger, "today_cost", return_value=0.999):
            allowed, reason = budget.can_call(0.01, "deepseek")
            assert allowed is False
            assert "daily" in reason.lower()

    def test_daily_limit_exact_boundary_allowed(self):
        budget = BudgetEnforcer()
        with patch.object(budget.logger, "today_cost", return_value=0.99):
            allowed, reason = budget.can_call(0.01, "deepseek")
            assert allowed is True  # exactly at budget

    def test_monthly_limit_exceeded(self):
        budget = BudgetEnforcer()
        with patch.object(budget.logger, "month_cost", return_value=9.995):
            allowed, reason = budget.can_call(0.01, "deepseek")
            assert allowed is False
            assert "monthly" in reason.lower()

    def test_circuit_open_blocks_call(self):
        budget = BudgetEnforcer()
        # Manually open the deepseek circuit
        cb = budget._circuits["deepseek"]
        for _ in range(cb.failure_threshold):
            cb.record_failure()
        assert cb.state == "open"

        allowed, reason = budget.can_call(0.0001, "deepseek")
        assert allowed is False
        assert "circuit open" in reason.lower()

    def test_ollama_no_cost_always_allowed(self):
        """Ollama has $0 cost — budget check should pass without DB queries."""
        budget = BudgetEnforcer()
        allowed, reason = budget.can_call(0.0, "ollama")
        assert allowed is True

    def test_unknown_provider_not_blocked(self):
        """Providers without a circuit breaker should not be blocked."""
        budget = BudgetEnforcer()
        allowed, reason = budget.can_call(0.0001, "openrouter")
        assert allowed is True


# ═══════════════════════════════════════════════════════════════
# BudgetEnforcer — recording
# ═══════════════════════════════════════════════════════════════


class TestBudgetEnforcerRecording:
    """Recording calls updates budgets and circuits."""

    def test_record_success_closes_half_open_circuit(self):
        budget = BudgetEnforcer()
        cb = budget._circuits["deepseek"]
        # Force open → half_open
        for _ in range(cb.failure_threshold):
            cb.record_failure()
        time.sleep(0.001)  # tiny sleep so timeout doesn't accidentally trip
        # Manually advance to half_open via timeout
        cb.state = "half_open"

        # Record a success — should close
        with patch.object(budget.logger, "log", return_value=1):
            budget.record_success(
                provider="deepseek", model="deepseek-chat",
                task_type="research", input_tokens=100, output_tokens=50,
                cost=0.0001,
            )
        assert cb.state == "closed"
        assert cb.failure_count == 0

    def test_record_failure_increments_circuit(self):
        budget = BudgetEnforcer()
        cb = budget._circuits["deepseek"]
        with patch.object(budget.logger, "log", return_value=1):
            budget.record_failure(
                provider="deepseek", model="deepseek-chat",
                task_type="research", error="timeout",
            )
        assert cb.failure_count == 1

    def test_record_success_resets_failure_count(self):
        budget = BudgetEnforcer()
        cb = budget._circuits["deepseek"]
        with patch.object(budget.logger, "log", return_value=1):
            budget.record_failure(provider="deepseek", model="x", task_type="t", error="e")
            budget.record_failure(provider="deepseek", model="x", task_type="t", error="e")
            budget.record_success(provider="deepseek", model="x", task_type="t")
        assert cb.failure_count == 0
        assert cb.state == "closed"

    def test_budget_summary_structure(self):
        budget = BudgetEnforcer()
        with patch.object(budget.logger, "today_cost", return_value=0.0042):
            with patch.object(budget.logger, "month_cost", return_value=0.1337):
                summary = budget.budget_summary()

        assert summary["today_spent"] == 0.0042
        assert summary["today_budget"] == 1.00
        assert summary["month_budget"] == 10.00
        assert "circuits" in summary
        assert summary["circuits"]["deepseek"] == "closed"

    def test_reset_circuits_clears_all(self):
        budget = BudgetEnforcer()
        for cb in budget._circuits.values():
            cb.record_failure()
            cb.record_failure()
            cb.record_failure()
        budget.reset_circuits()
        for cb in budget._circuits.values():
            assert cb.state == "closed"
            assert cb.failure_count == 0


# ═══════════════════════════════════════════════════════════════
# SemanticCache — hash lookups
# ═══════════════════════════════════════════════════════════════


class TestSemanticCacheHashLookup:
    """Exact hash match (no embedding needed)."""

    @pytest.fixture
    def cache(self):
        """SemanticCache with mocked psycopg2 connection."""
        with patch("psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_conn.closed = False
            mock_conn.autocommit = True

            mock_cursor = MagicMock()
            mock_cursor.__enter__ = lambda s: s
            mock_cursor.__exit__ = lambda *_: None

            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            sc = SemanticCache(db_url="postgresql:///mock")
            sc._conn = mock_conn
            yield sc

    def test_hash_hit_returns_cached(self, cache):
        """When the exact query hash exists, return cached response."""
        mock_cursor = cache.conn.cursor()
        # Simulate exact match in DB
        mock_cursor.fetchone.return_value = {
            "id": 1,
            "response_text": "cached answer",
            "similarity": 1.0,
            "query_text": "test query",
            "hit_count": 3,
            "model_used": "deepseek-chat",
        }

        result = cache.get("test query", "chat")
        assert result is not None
        assert result["response_text"] == "cached answer"
        assert result["similarity"] == 1.0
        assert result["source"] == "cache_exact"

    def test_hash_miss_no_embedding_model_returns_none(self, cache):
        """When no embedding model is available, hash miss returns None gracefully."""
        mock_cursor = cache.conn.cursor()
        mock_cursor.fetchone.return_value = None  # no exact match

        # Override _embed to return None (simulating no model available)
        cache._embed = lambda _: None

        result = cache.get("completely new query", "chat")
        assert result is None

    def test_cache_key_uniqueness(self, cache):
        """Different queries produce different hash keys."""
        hash1 = cache._hash_query("hello")
        hash2 = cache._hash_query("world")
        hash3 = cache._hash_query("hello")  # same → same hash
        assert hash1 != hash2
        assert hash1 == hash3
        assert len(hash1) == 32  # MD5 hex


# ═══════════════════════════════════════════════════════════════
# SemanticCache — set/get cycle
# ═══════════════════════════════════════════════════════════════


class TestSemanticCacheSetGet:
    """Set and get cycle with mocked embedding."""

    @pytest.fixture
    def cache_with_embed(self):
        """SemanticCache with mocked embedding (always returns same vector)."""
        with patch("psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_conn.closed = False
            mock_conn.autocommit = True

            mock_cursor = MagicMock()
            mock_cursor.__enter__ = lambda s: s
            mock_cursor.__exit__ = lambda *_: None

            mock_conn.cursor.return_value = mock_cursor
            mock_connect.return_value = mock_conn

            sc = SemanticCache(db_url="postgresql:///mock")
            sc._conn = mock_conn
            # Mock the embedding to return a fixed vector
            sc._embed = lambda _: [0.1] * 768
            sc._embedding_dim = 768
            yield sc

    def test_set_returns_id(self, cache_with_embed):
        """set() stores the response and returns the cache ID."""
        mock_cursor = cache_with_embed.conn.cursor()
        mock_cursor.fetchone.return_value = [42]

        cache_id = cache_with_embed.set(
            "test query", "test response", "chat", "deepseek-chat",
            tokens_used=100, cost=0.0001,
        )
        assert cache_id == 42

    def test_set_returns_none_when_embedding_unavailable(self, cache_with_embed):
        """When embedding model is not available, set() returns None gracefully."""
        cache_with_embed._embed = lambda _: None
        result = cache_with_embed.set("query", "response", "chat")
        assert result is None

    def test_set_upserts_on_conflict(self, cache_with_embed):
        """When query_hash already exists, update instead of inserting."""
        mock_cursor = cache_with_embed.conn.cursor()
        mock_cursor.fetchone.return_value = [99]

        cache_id = cache_with_embed.set("duplicate query", "new response", "chat")
        assert cache_id == 99


# ═══════════════════════════════════════════════════════════════
# SemanticCache — stats
# ═══════════════════════════════════════════════════════════════


class TestSemanticCacheStats:
    """Stats and maintenance operations."""

    @pytest.fixture
    def cache(self):
        with patch("psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_conn.closed = False
            mock_conn.autocommit = True
            mock_connect.return_value = mock_conn
            sc = SemanticCache(db_url="postgresql:///mock")
            sc._conn = mock_conn
            yield sc

    def test_stats_returns_structure(self, cache):
        """stats() returns the expected keys."""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = lambda *_: None

        # Simule 3 queries: total, hits, savings
        fetch_results = [
            {"total": 42},              # COUNT(*)
            {"hits": 128},              # SUM(hit_count)
            {"tokens": 50000, "cost": 0.75},  # SUM(tokens_saved), SUM(cost_saved)
        ]
        mock_cursor.fetchone.side_effect = fetch_results

        cache.conn.cursor = MagicMock(return_value=mock_cursor)

        stats = cache.stats()
        assert stats["total_entries"] == 42
        assert stats["total_hits"] == 128
        assert stats["tokens_saved"] == 50000
        assert stats["cost_saved"] == 0.75

    def test_clear_by_type(self, cache):
        """clear(type) deletes only matching entries."""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = lambda *_: None
        mock_cursor.rowcount = 15
        cache.conn.cursor = MagicMock(return_value=mock_cursor)

        deleted = cache.clear(response_type="search")
        assert deleted == 15

    def test_clear_all(self, cache):
        """clear() without type deletes everything."""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = lambda *_: None
        mock_cursor.rowcount = 42
        cache.conn.cursor = MagicMock(return_value=mock_cursor)

        deleted = cache.clear()
        assert deleted == 42

    def test_cleanup_expired(self, cache):
        """cleanup_expired() removes old entries."""
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = lambda *_: None
        mock_cursor.rowcount = 7
        cache.conn.cursor = MagicMock(return_value=mock_cursor)

        deleted = cache.cleanup_expired(max_age_days=30)
        assert deleted == 7


# ═══════════════════════════════════════════════════════════════
# CostService — facade integration
# ═══════════════════════════════════════════════════════════════


class TestCostService:
    """CostService bundles cache + log + budget."""

    def test_cost_service_exposes_all_components(self):
        cost = CostService(db_url="postgresql:///mock")
        assert hasattr(cost, "cache")
        assert hasattr(cost, "logger")
        assert hasattr(cost, "budget")
        assert isinstance(cost.cache, SemanticCache)
        assert isinstance(cost.logger, CostLog)
        assert isinstance(cost.budget, BudgetEnforcer)

    def test_cost_service_components_share_db_url(self):
        cost = CostService(db_url="postgresql:///custom_db")
        assert cost.cache.db_url == "postgresql:///custom_db"
        assert cost.budget.logger.db_url == "postgresql:///custom_db"


# ═══════════════════════════════════════════════════════════════
# BudgetExceededError
# ═══════════════════════════════════════════════════════════════


class TestBudgetExceededError:
    """BudgetExceededError is a standard exception."""

    def test_is_exception(self):
        with pytest.raises(BudgetExceededError):
            raise BudgetExceededError("Daily budget exceeded: $1.00/1.00")

    def test_message_preserved(self):
        try:
            raise BudgetExceededError("custom reason")
        except BudgetExceededError as e:
            assert "custom reason" in str(e)

    def test_caught_by_broad_exception(self):
        """BudgetExceededError can be caught as Exception."""
        try:
            raise BudgetExceededError("test")
        except Exception as e:
            assert isinstance(e, BudgetExceededError)


# ═══════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_circuit_breaker_with_zero_threshold_opens_immediately(self):
        """A threshold of 0 means open on first failure."""
        cb = CircuitBreaker("test", failure_threshold=0)
        cb.record_failure()
        assert cb.state == "open"

    def test_budget_with_zero_daily_limit_blocks_everything(self):
        budget = BudgetEnforcer()
        budget.DAILY_BUDGET = 0.0
        allowed, _ = budget.can_call(0.000001, "deepseek")
        assert allowed is False

    def test_reset_timeout_zero_opens_immediately(self):
        """With reset_timeout=0, circuit transitions to half_open immediately."""
        cb = CircuitBreaker("test", failure_threshold=1, reset_timeout=0)
        cb.record_failure()
        assert cb.state == "open"
        # Should allow immediately since timeout is 0
        assert cb.allow_request() is True
        assert cb.state == "half_open"

    def test_multiple_providers_independent_circuits(self):
        """Each provider has its own independent circuit breaker."""
        budget = BudgetEnforcer()
        # Break deepseek only
        for _ in range(budget._circuits["deepseek"].failure_threshold):
            budget._circuits["deepseek"].record_failure()

        # deepseek blocked
        allowed, _ = budget.can_call(0.0001, "deepseek")
        assert allowed is False
        # ollama still allowed
        allowed, _ = budget.can_call(0.0, "ollama")
        assert allowed is True
        # gemini still allowed
        allowed, _ = budget.can_call(0.0, "gemini")
        assert allowed is True
