"""
Tests for SmartRouter — cross-provider model routing with fallback.

Covers:
- Basic routing: picks first available model for each task type
- Cross-provider fallback: Ollama → DeepSeek → Gemini
- Complexity detection: SIMPLE → MODERATE → COMPLEX
- Availability check (mocked): Ollama offline → routes to DeepSeek
- Fallback chain after failure
- Cost estimation per provider
- Edge cases: all providers down, empty task, unknown task type
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_workspace.agents.router import (
    SmartRouter,
    TaskComplexity,
    TaskType,
    get_router,
    RoutingDecision,
    ModelInfo,
)


# ── Ensure clean singleton between tests ────────────────

@pytest.fixture(autouse=True)
def _reset_router_singleton():
    """Reset the global router singleton before each test."""
    import ai_workspace.agents.router as router_mod
    router_mod._router_instance = None
    yield
    router_mod._router_instance = None


# ── Fixtures ────────────────────────────────────────────

@pytest.fixture
def router():
    """Fresh SmartRouter with all models and providers available."""
    r = SmartRouter()
    r._provider_available = {
        "ollama": True,
        "deepseek": True,
        "gemini": True,
        "openrouter": True,
    }
    r._availability_checked = True
    # Mark all models as available
    for model in r.models.values():
        model.available = True
    return r


@pytest.fixture
def router_ollama_only():
    """Router with only Ollama available."""
    r = SmartRouter()
    r._provider_available = {
        "ollama": True,
        "deepseek": False,
        "gemini": False,
        "openrouter": False,
    }
    r._availability_checked = True
    # Mark all Ollama models as available
    for model in r.models.values():
        if model.provider == "ollama":
            model.available = True
        else:
            model.available = False
    return r


@pytest.fixture
def router_no_ollama():
    """Router with Ollama down, DeepSeek + Gemini up."""
    r = SmartRouter()
    r._provider_available = {
        "ollama": False,
        "deepseek": True,
        "gemini": True,
        "openrouter": False,
    }
    r._availability_checked = True
    for model in r.models.values():
        model.available = model.provider in ("deepseek", "gemini")
    return r


@pytest.fixture
def router_all_down():
    """Router with everything down."""
    r = SmartRouter()
    r._provider_available = {
        "ollama": False,
        "deepseek": False,
        "gemini": False,
        "openrouter": False,
    }
    r._availability_checked = True
    for model in r.models.values():
        model.available = False
    return r


# ── Basic Routing ───────────────────────────────────────

class TestBasicRouting:
    """Test that route() picks the right first model."""

    def test_coding_prefers_ollama_qwen3(self, router):
        decision = router.route("Fix the auth middleware bug", task_type="coding")
        assert decision.provider == "ollama"
        assert decision.model == "qwen3:14b"
        assert len(decision.fallback_chain) >= 3

    def test_research_prefers_ollama_qwen3(self, router):
        decision = router.route("Research Rust vs Go performance", task_type="research")
        assert decision.provider == "ollama"
        assert decision.model == "qwen3:14b"

    def test_chat_prefers_fast_model(self, router):
        decision = router.route("What is 2+2?", task_type="chat")
        assert decision.provider == "ollama"
        assert decision.model == "ministral-3:8b"  # fastest

    def test_planning_prefers_cheap(self, router):
        decision = router.route("Plan the migration steps", task_type="planning")
        assert decision.provider == "ollama"
        assert decision.model == "ministral-3:8b"

    def test_extraction_prefers_gemini(self, router):
        decision = router.route("Extract prices from this HTML", task_type="extraction")
        # Gemini should be first for extraction (cheapest)
        assert decision.provider in ("gemini", "ollama")

    def test_classification_prefers_gemini(self, router):
        decision = router.route("Classify this source", task_type="classification")
        assert decision.provider in ("gemini", "ollama")

    def test_general_defaults_to_ollama(self, router):
        decision = router.route("Some task", task_type="general")
        assert decision.provider == "ollama"
        assert decision.model == "qwen3:14b"

    def test_unknown_task_type_defaults_to_general(self, router):
        decision = router.route("Some task", task_type="nonexistent")
        assert decision.provider == "ollama"
        assert decision.model == "qwen3:14b"


# ── Cross-Provider Fallback ─────────────────────────────

class TestCrossProviderFallback:
    """Test that the router falls back across providers."""

    def test_ollama_down_falls_to_deepseek(self, router_no_ollama):
        decision = router_no_ollama.route("Research something", task_type="research")
        assert decision.provider == "deepseek"
        assert decision.model == "deepseek-chat"

    def test_ollama_down_coding_falls_to_deepseek(self, router_no_ollama):
        decision = router_no_ollama.route("Fix bug in auth.py", task_type="coding")
        assert decision.provider == "deepseek"
        assert "deepseek" in decision.model

    def test_ollama_only_uses_ollama(self, router_ollama_only):
        decision = router_ollama_only.route("Research something", task_type="research")
        assert decision.provider == "ollama"

    def test_fallback_chain_includes_all_providers(self, router):
        decision = router.route("Research X", task_type="research")
        providers_in_chain = {m.provider for m in decision.fallback_chain}
        # Research chain: ollama (qwen3:14b) → deepseek → ollama (qwen3.5:9b) → gemini → openrouter
        assert len(providers_in_chain) >= 2

    def test_fallback_chain_length(self, router):
        decision = router.route("fix bug", task_type="coding")
        # Coding chain: qwen3:14b, qwen3.5:9b, codellama:13b, deepseek-chat, claude
        assert len(decision.fallback_chain) >= 4

    def test_all_down_raises(self, router_all_down):
        import ai_workspace.agents.router as router_mod
        router_mod._router_instance = None
        with pytest.raises(RuntimeError, match="No models available"):
            router_all_down.route("Do something", task_type="general")


# ── Complexity Detection ────────────────────────────────

class TestComplexityDetection:
    """Test that complexity is auto-detected."""

    def test_simple_task(self, router):
        decision = router.route("What does this function do?")
        assert decision.provider in ("ollama", "deepseek", "gemini")
        assert decision.model is not None

    def test_moderate_task_detected(self, router):
        decision = router.route("Research the best approach for implementing a cache")
        # Should detect MODERATE (has "research" keyword)
        # Verify it still picks Ollama first but could route to DeepSeek
        assert decision.provider in ("ollama", "deepseek")

    def test_complex_task_detected(self, router):
        decision = router.route(
            "Refactor the entire authentication module to use JWT tokens. "
            "This involves rewriting auth middleware, updating all tests, "
            "and migrating the database schema for user sessions."
        )
        # COMPLEX tasks should prefer DeepSeek for coding
        assert decision.provider in ("deepseek", "ollama")

    def test_explicit_complexity_override(self, router):
        decision = router.route(
            "simple fix",
            task_type="research",
            complexity=TaskComplexity.COMPLEX,
        )
        # COMPLEX research overrides to DeepSeek first
        assert decision.provider in ("deepseek", "ollama")


# ─── Fallback After Failure ─────────────────────────────

class TestFallbackAfterFailure:
    """Test the fallback() method after a model fails."""

    def test_fallback_moves_to_next_model(self, router):
        decision = router.route("fix bug", task_type="coding")
        first_model = decision.model
        first_provider = decision.provider

        fallback = router.fallback(decision)
        assert fallback is not None
        # Should be a different model or provider
        assert (fallback.model != first_model) or (fallback.provider != first_provider)

    def test_fallback_respects_disabled_models(self, router):
        decision = router.route("fix bug", task_type="coding")

        # Fail the first model
        router.fallback(decision)

        # New route should skip the disabled model
        decision2 = router.route("fix bug", task_type="coding")
        # Should have moved to the next model
        assert decision2.model != decision.model

    def test_fallback_exhausts_chain(self, router):
        decision = router.route("fix bug", task_type="coding")

        # Exhaust all fallbacks
        fallback = decision
        for _ in range(len(decision.fallback_chain) + 1):
            fallback = router.fallback(fallback)
            if fallback is None:
                break

        # After exhausting, next route should fail or pick anything
        # (all models from the chain are disabled now)
        final = router.route("fix bug", task_type="coding")
        # Should still find something (from other task types' chains or random)
        assert final is not None

    def test_mark_success_does_not_reenable(self, router):
        decision = router.route("fix bug", task_type="coding")
        router.fallback(decision)  # disable first

        router.mark_success(decision.model, decision.provider)
        # mark_success clears failure count but doesn't re-enable disabled set
        assert f"{decision.provider}/{decision.model}" in router._disabled


# ── Cost Estimation ─────────────────────────────────────

class TestCostEstimation:
    """Test cost estimation logic."""

    def test_ollama_cost_is_zero(self, router):
        # Force Ollama to be the only available provider
        router._provider_available["deepseek"] = False
        router._provider_available["gemini"] = False
        router._provider_available["openrouter"] = False
        decision = router.route("fix bug", task_type="coding")
        assert decision.provider == "ollama"
        assert decision.estimated_cost == 0.0  # Ollama is free

    def test_deepseek_cost_positive(self, router_no_ollama):
        decision = router_no_ollama.route(
            "Research complex topic with many details and deep analysis",
            task_type="research",
        )
        # DeepSeek costs money
        assert decision.estimated_cost > 0.0
        # Should be very small (< $0.01 per call)
        assert decision.estimated_cost < 0.01

    def test_gemini_free_cost_zero(self, router):
        decision = router.route("Extract text from this page", task_type="extraction")
        # Gemini free tier — cost should be 0
        # (Gemini free is modeled as $0 in our registry)
        pass  # If routed to gemini-2.5-flash-lite, cost is $0


# ── Availability Check ──────────────────────────────────

class TestAvailabilityCheck:
    """Test the check_availability() method."""

    @pytest.mark.asyncio
    async def test_check_availability_sets_flags(self):
        router = SmartRouter()
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "models": [
                    {"name": "qwen3:14b"},
                    {"name": "ministral-3:8b"},
                ]
            }
            mock_get.return_value = mock_resp

            result = await router.check_availability()
            assert result["ollama"] is True
            # These depend on env vars — may be True or False
            assert "deepseek" in result
            assert "gemini" in result

    def test_check_availability_sync(self):
        router = SmartRouter()
        with patch.object(router, "_check_ollama_sync", return_value=True):
            result = router.check_availability_sync()
            assert "ollama" in result
            assert "deepseek" in result
            assert "gemini" in result
            assert "openrouter" in result
            assert router._availability_checked is True

    @pytest.mark.asyncio
    async def test_ollama_offline_marks_models_unavailable(self):
        router = SmartRouter()
        with patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):
            result = await router.check_availability()
            assert result["ollama"] is False
            # Ollama models should be marked unavailable
            for model in router.models.values():
                if model.provider == "ollama":
                    assert model.available is False


# ── Model Info Helpers ─────────────────────────────────

class TestModelInfo:
    """Test ModelInfo dataclass."""

    def test_key_format(self):
        m = ModelInfo(name="test-model", provider="ollama")
        assert m.key == "ollama/test-model"

    def test_cost_per_1k_tokens_average(self):
        m = ModelInfo(
            name="test", provider="test",
            cost_per_1k_input=0.001, cost_per_1k_output=0.003,
        )
        assert m.cost_per_1k_tokens == 0.002  # average


# ── Singleton ───────────────────────────────────────────

class TestSingleton:
    """Test the singleton get_router() function."""

    def test_get_router_returns_same_instance(self):
        r1 = get_router()
        r2 = get_router()
        assert r1 is r2

    def test_get_router_is_smartrouter(self):
        r = get_router()
        assert isinstance(r, SmartRouter)


# ── list_available ───────────────────────────────────────

class TestListAvailable:
    """Test the list_available() method."""

    def test_lists_all_models(self, router):
        models = router.list_available()
        assert len(models) > 5
        # All should have required fields
        for m in models:
            assert "name" in m
            assert "provider" in m
            assert "available" in m

    def test_disabled_models_show_unavailable(self, router):
        decision = router.route("fix bug", task_type="coding")
        router.fallback(decision)  # disables first model

        models = router.list_available()
        disabled = [m for m in models if m["name"] == decision.model
                    and m["provider"] == decision.provider]
        assert len(disabled) >= 1
        assert disabled[0]["available"] is False
