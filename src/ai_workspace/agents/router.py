"""
SmartRouter — intelligent model selection with cross-provider fallback.

Routes tasks to the optimal model based on:
- Task type (coding, research, quick chat, planning, extraction, classification)
- Provider availability (Ollama local, DeepSeek API, Gemini free tier, OpenRouter)
- Cost constraints (free Ollama first, cheap DeepSeek next, Gemini free for simple)
- Automatic retry with fallback models on failure

Fallback strategy (per task type):
  Ollama (local, $0) → DeepSeek ($0.14/M) → Gemini free ($0, 60/min) → OpenRouter

Architecture:
  Task → SmartRouter.route() → select best model
    → attempt execution
    → on failure: SmartRouter.fallback() → try next model
    → on success: SmartRouter.mark_success() → update preferences
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

logger = logging.getLogger("aiw.router")


class TaskComplexity(Enum):
    SIMPLE = auto()      # Quick chat, small edits, single file
    MODERATE = auto()    # Multi-file changes, research
    COMPLEX = auto()     # Large refactors, deep research, multi-step


class TaskType(str, Enum):
    """Well-known task types for routing decisions."""
    CODING = "coding"
    RESEARCH = "research"
    CHAT = "chat"
    PLANNING = "planning"
    SYNTHESIS = "synthesis"
    EXTRACTION = "extraction"
    CLASSIFICATION = "classification"
    GENERAL = "general"


@dataclass
class ModelInfo:
    """Information about an available model."""
    name: str
    provider: str          # ollama, deepseek, gemini, openrouter
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    max_tokens: int = 8_192
    supports_tools: bool = True
    speed: str = "medium"  # fast, medium, slow
    priority: int = 50     # Higher = preferred
    available: bool = True  # Set by availability check

    @property
    def cost_per_1k_tokens(self) -> float:
        """Average cost for estimation purposes."""
        return (self.cost_per_1k_input + self.cost_per_1k_output) / 2

    @property
    def key(self) -> str:
        return f"{self.provider}/{self.name}"


@dataclass
class RoutingDecision:
    """The result of SmartRouter's analysis."""
    model: str
    provider: str
    reason: str
    fallback_chain: list[ModelInfo] = field(default_factory=list)
    estimated_cost: float = 0.0


# ── Cost constants (per 1M tokens) ──────────────────────

COST_DEEPSEEK_CHAT_INPUT = 0.14    # $0.14 / 1M input
COST_DEEPSEEK_CHAT_OUTPUT = 0.28   # $0.28 / 1M output
COST_DEEPSEEK_REASONER_INPUT = 0.55
COST_DEEPSEEK_REASONER_OUTPUT = 2.19
COST_GEMINI_FLASH_INPUT = 0.10     # $0.10 / 1M (or free tier)
COST_GEMINI_FLASH_OUTPUT = 0.40


class SmartRouter:
    """Intelligent model router with cross-provider fallback chains.

    Usage:
        router = SmartRouter()
        await router.check_availability()  # optional: probe providers
        
        decision = router.route("research topic", task_type="research")
        # → qwen3:14b via ollama (local, free)
        #   fallback: deepseek-chat → gemini-2.5-flash
        
        # On failure:
        fallback = router.fallback(decision)
        # → deepseek-chat via deepseek
    """

    # ─── Model Registry ────────────────────────────────

    DEFAULT_MODELS: list[ModelInfo] = [
        # ── Ollama (local, free) ──
        ModelInfo(name="qwen3:14b", provider="ollama",
                  max_tokens=8_192, speed="medium", priority=90),
        ModelInfo(name="qwen3.5:9b", provider="ollama",
                  max_tokens=8_192, speed="fast", priority=85),
        ModelInfo(name="ministral-3:8b", provider="ollama",
                  max_tokens=8_192, speed="fast", priority=80),
        ModelInfo(name="codellama:13b", provider="ollama",
                  max_tokens=8_192, speed="medium", priority=75,
                  supports_tools=False),

        # ── DeepSeek API (paid, cheap) ──
        ModelInfo(name="deepseek-chat", provider="deepseek",
                  cost_per_1k_input=COST_DEEPSEEK_CHAT_INPUT / 1000,
                  cost_per_1k_output=COST_DEEPSEEK_CHAT_OUTPUT / 1000,
                  max_tokens=8_192, speed="medium", priority=70),
        ModelInfo(name="deepseek-reasoner", provider="deepseek",
                  cost_per_1k_input=COST_DEEPSEEK_REASONER_INPUT / 1000,
                  cost_per_1k_output=COST_DEEPSEEK_REASONER_OUTPUT / 1000,
                  max_tokens=8_192, speed="slow", priority=65,
                  supports_tools=False),

        # ── Gemini free tier (free, rate-limited) ──
        ModelInfo(name="gemini-2.5-flash", provider="gemini",
                  max_tokens=8_192, speed="fast", priority=50,
                  supports_tools=False),
        ModelInfo(name="gemini-2.5-flash-lite", provider="gemini",
                  max_tokens=8_192, speed="fast", priority=45,
                  supports_tools=False),

        # ── OpenRouter (paid, global fallback) ──
        ModelInfo(name="anthropic/claude-3.7-sonnet", provider="openrouter",
                  cost_per_1k_input=0.003, cost_per_1k_output=0.015,
                  max_tokens=200_000, speed="slow", priority=30),
    ]

    # ─── Routing Rules ──────────────────────────────────

    # For each task type: ordered list of models to try.
    # The router will check availability and use the first available.
    TASK_ROUTING: dict[str, list[tuple[str, str]]] = {
        # Coding: Ollama first (qwen3 is great at code), DeepSeek fallback
        TaskType.CODING: [
            ("ollama", "qwen3:14b"),
            ("ollama", "qwen3.5:9b"),
            ("ollama", "codellama:13b"),
            ("deepseek", "deepseek-chat"),
            ("openrouter", "anthropic/claude-3.7-sonnet"),
        ],

        # Research: Ollama first, DeepSeek for deep reasoning
        TaskType.RESEARCH: [
            ("ollama", "qwen3:14b"),
            ("deepseek", "deepseek-chat"),
            ("ollama", "qwen3.5:9b"),
            ("gemini", "gemini-2.5-flash"),
            ("openrouter", "anthropic/claude-3.7-sonnet"),
        ],

        # Planning (sub-questions, task decomposition): cheap models
        TaskType.PLANNING: [
            ("ollama", "ministral-3:8b"),
            ("ollama", "qwen3:14b"),
            ("gemini", "gemini-2.5-flash"),
            ("deepseek", "deepseek-chat"),
        ],

        # Synthesis (report writing): medium models
        TaskType.SYNTHESIS: [
            ("ollama", "qwen3:14b"),
            ("deepseek", "deepseek-chat"),
            ("gemini", "gemini-2.5-flash"),
            ("ollama", "qwen3.5:9b"),
        ],

        # Extraction (from scraped content): cheapest possible
        TaskType.EXTRACTION: [
            ("gemini", "gemini-2.5-flash-lite"),
            ("gemini", "gemini-2.5-flash"),
            ("ollama", "ministral-3:8b"),
            ("ollama", "qwen3.5:9b"),
            ("deepseek", "deepseek-chat"),
        ],

        # Classification (binary/simple): cheapest
        TaskType.CLASSIFICATION: [
            ("gemini", "gemini-2.5-flash-lite"),
            ("ollama", "ministral-3:8b"),
            ("gemini", "gemini-2.5-flash"),
        ],

        # Quick chat: fastest model
        TaskType.CHAT: [
            ("ollama", "ministral-3:8b"),
            ("ollama", "qwen3.5:9b"),
            ("ollama", "qwen3:14b"),
            ("gemini", "gemini-2.5-flash"),
            ("deepseek", "deepseek-chat"),
        ],

        # General: balanced
        TaskType.GENERAL: [
            ("ollama", "qwen3:14b"),
            ("ollama", "ministral-3:8b"),
            ("deepseek", "deepseek-chat"),
            ("gemini", "gemini-2.5-flash"),
        ],
    }

    # Complexity overrides: for COMPLEX tasks, prefer larger reasoning models
    COMPLEXITY_OVERRIDE: dict[str, list[tuple[str, str]]] = {
        TaskType.CODING: [
            ("deepseek", "deepseek-chat"),
            ("ollama", "qwen3:14b"),
            ("openrouter", "anthropic/claude-3.7-sonnet"),
            ("ollama", "qwen3.5:9b"),
        ],
        TaskType.RESEARCH: [
            ("deepseek", "deepseek-chat"),
            ("deepseek", "deepseek-reasoner"),
            ("ollama", "qwen3:14b"),
            ("openrouter", "anthropic/claude-3.7-sonnet"),
        ],
    }

    def __init__(self, custom_models: list[ModelInfo] | None = None):
        self.models: dict[str, ModelInfo] = {}
        for m in (custom_models or self.DEFAULT_MODELS):
            self.models[m.key] = m
        self._failure_counts: dict[str, int] = {}
        self._disabled: set[str] = set()
        self._availability_checked = False
        self._provider_available: dict[str, bool] = {}

    # ─── Availability Check ─────────────────────────────

    async def check_availability(self) -> dict[str, bool]:
        """Probe all providers and update availability status.

        Returns:
            Dict of provider → available (True/False).
        """
        results = {}

        # ── Ollama: check if local server is running ──
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{ollama_host}/api/tags", timeout=5.0
                )
                if resp.status_code == 200:
                    # Also check which models are actually pulled
                    data = resp.json()
                    available_models = {
                        m["name"] for m in data.get("models", [])
                    }
                    results["ollama"] = True
                    # Mark individual Ollama models as available/unavailable
                    for key, model in self.models.items():
                        if model.provider == "ollama":
                            model.available = model.name in available_models
                            if not model.available:
                                logger.info(
                                    "Ollama model %s not pulled (available: %s)",
                                    model.name,
                                    sorted(available_models),
                                )
                else:
                    results["ollama"] = False
        except Exception as e:
            logger.warning("Ollama not available: %s", e)
            results["ollama"] = False
            for key, model in self.models.items():
                if model.provider == "ollama":
                    model.available = False

        # ── DeepSeek: check if API key is configured ──
        deepseek_key = (
            os.getenv("DEEPSEEK_API_KEY")
            or _read_sops_secret("deepseek_api_key")
        )
        results["deepseek"] = bool(deepseek_key)

        # ── Gemini: check if API key is configured ──
        gemini_key = (
            os.getenv("GEMINI_API_KEY")
            or _read_sops_secret("gemini_api_key")
        )
        results["gemini"] = bool(gemini_key)

        # ── OpenRouter: check if API key is configured ──
        or_key = (
            os.getenv("OPENROUTER_API_KEY")
            or _read_sops_secret("openrouter_api_key")
        )
        results["openrouter"] = bool(or_key)

        self._provider_available = results
        self._availability_checked = True

        logger.info(
            "Provider availability: %s",
            {k: v for k, v in results.items()},
        )
        return results

    def check_availability_sync(self) -> dict[str, bool]:
        """Synchronous wrapper for check_availability()."""
        try:
            return asyncio.run(self.check_availability())
        except RuntimeError:
            # Already in an event loop
            import concurrent.futures
            import threading
            
            # Non-blocking fallback: just check env vars
            results = {}
            results["ollama"] = self._check_ollama_sync()
            results["deepseek"] = bool(
                os.getenv("DEEPSEEK_API_KEY")
                or _read_sops_secret("deepseek_api_key")
            )
            results["gemini"] = bool(
                os.getenv("GEMINI_API_KEY")
                or _read_sops_secret("gemini_api_key")
            )
            results["openrouter"] = bool(
                os.getenv("OPENROUTER_API_KEY")
                or _read_sops_secret("openrouter_api_key")
            )
            self._provider_available = results
            self._availability_checked = True
            return results

    def _check_ollama_sync(self) -> bool:
        """Quick synchronous Ollama check."""
        try:
            import httpx
            resp = httpx.get(
                f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/tags",
                timeout=3.0,
            )
            return resp.status_code == 200
        except Exception:
            return False

    # ─── Routing ────────────────────────────────────────

    def route(
        self,
        task: str,
        task_type: str = "general",
        complexity: TaskComplexity | None = None,
    ) -> RoutingDecision:
        """Select the best model for a task.

        Strategy:
        1. Auto-detect complexity from task description
        2. Look up routing rules for this task_type
        3. Apply complexity overrides if COMPLEX
        4. Walk the chain, pick the first available model
        5. Return RoutingDecision with full fallback chain

        Args:
            task: The task description.
            task_type: coding, research, chat, planning, synthesis,
                       extraction, classification, general.
            complexity: Optional override for complexity detection.

        Returns:
            RoutingDecision with model, provider, and fallback chain.
        """
        # Auto-detect complexity
        if complexity is None:
            complexity = self._detect_complexity(task)

        # Get routing order
        if (
            complexity == TaskComplexity.COMPLEX
            and task_type in self.COMPLEXITY_OVERRIDE
        ):
            routing_order = self.COMPLEXITY_OVERRIDE[task_type]
        else:
            routing_order = self.TASK_ROUTING.get(
                task_type, self.TASK_ROUTING[TaskType.GENERAL]
            )

        # Walk the chain: build fallback chain, pick first available
        chain = []
        primary = None

        for provider, model_name in routing_order:
            model = self._find_model(provider, model_name)
            if model is None:
                continue

            # Skip disabled models
            if model.key in self._disabled:
                continue

            # Check provider availability (if checked)
            if self._availability_checked:
                if not self._provider_available.get(provider, False):
                    model.available = False
                    continue
                # For Ollama, also check individual model availability
                if provider == "ollama" and not model.available:
                    if model.key not in self._disabled:
                        logger.debug(
                            "Skipping unavailable Ollama model: %s", model.name
                        )
                    continue

            chain.append(model)
            if primary is None:
                primary = model

        # If nothing found in the chain, try any available model
        if primary is None:
            for model in self.models.values():
                if model.key in self._disabled:
                    continue
                provider_ok = True
                if self._availability_checked:
                    provider_ok = self._provider_available.get(
                        model.provider, True
                    )
                if provider_ok and model.available:
                    primary = model
                    chain = [model]
                    break

        if primary is None:
            raise RuntimeError(
                "No models available. Check provider configuration "
                "(Ollama running? DeepSeek/Gemini API keys set?)"
            )

        # Estimate cost
        est_cost = self._estimate_cost(task, primary)

        reason = (
            f"{task_type}/{complexity.name.lower()} → "
            f"{primary.provider}/{primary.name} ({primary.speed}"
        )
        if est_cost > 0:
            reason += f", ~${est_cost:.4f}"
        reason += ")"

        return RoutingDecision(
            model=primary.name,
            provider=primary.provider,
            reason=reason,
            fallback_chain=chain,
            estimated_cost=est_cost,
        )

    def fallback(self, decision: RoutingDecision) -> RoutingDecision | None:
        """Get the next fallback model after a failure.

        Returns None if no more fallbacks available.
        """
        # Disable the failed model
        current_key = f"{decision.provider}/{decision.model}"
        self._disabled.add(current_key)
        self._failure_counts[current_key] = (
            self._failure_counts.get(current_key, 0) + 1
        )

        logger.info(
            "Model %s disabled (failure #%d), trying fallback",
            current_key,
            self._failure_counts[current_key],
        )

        # Find next in chain (skip disabled)
        for i, model in enumerate(decision.fallback_chain):
            if model.key == current_key and i + 1 < len(decision.fallback_chain):
                # Find next available model
                for j in range(i + 1, len(decision.fallback_chain)):
                    next_model = decision.fallback_chain[j]
                    if next_model.key not in self._disabled:
                        return RoutingDecision(
                            model=next_model.name,
                            provider=next_model.provider,
                            reason=(
                                f"Fallback from {decision.model} "
                                f"→ {next_model.provider}/{next_model.name}"
                            ),
                            fallback_chain=decision.fallback_chain[j:],
                        )
                break

        return None

    def mark_success(self, model: str, provider: str) -> None:
        """Mark a model as successfully used (reset failure count)."""
        key = f"{provider}/{model}"
        if key in self._failure_counts:
            logger.info("Model %s recovered (was %d failures)", key, self._failure_counts[key])
        self._failure_counts.pop(key, None)
        # Don't re-enable here — failures accumulate across calls

    def reset_failures(self) -> None:
        """Reset all failure counts (e.g., after network restore)."""
        logger.info("Resetting all failure counts and disabled models")
        self._failure_counts.clear()
        self._disabled.clear()

    # ─── Helpers ────────────────────────────────────────

    def _find_model(self, provider: str, name: str) -> ModelInfo | None:
        """Find a model by provider + name."""
        key = f"{provider}/{name}"
        if key in self.models:
            return self.models[key]
        # Try matching just by name
        for model in self.models.values():
            if model.name == name and model.provider == provider:
                return model
        return None

    def _estimate_cost(self, task: str, model: ModelInfo) -> float:
        """Estimate cost for a task."""
        if model.cost_per_1k_input == 0:
            return 0.0
        # Rough: 1 token ≈ 4 chars
        estimated_input = max(100, len(task) // 4)
        estimated_output = estimated_input // 2  # output usually smaller
        cost = (
            model.cost_per_1k_input * (estimated_input / 1000)
            + model.cost_per_1k_output * (estimated_output / 1000)
        )
        return round(cost, 6)

    def _detect_complexity(self, task: str) -> TaskComplexity:
        """Auto-detect task complexity from the description."""
        task_lower = task.lower()
        length = len(task)

        complex_kw = [
            "refactor", "rewrite", "redesign", "architecture",
            "implement from scratch", "full stack", "entire module",
            "migrate", "restructure", "build a", "create a new",
        ]
        if any(kw in task_lower for kw in complex_kw) or length > 500:
            return TaskComplexity.COMPLEX

        moderate_kw = [
            "add feature", "implement", "fix multiple", "several files",
            "research", "analyze", "investigate", "debug",
            "add tests", "add documentation",
        ]
        if any(kw in task_lower for kw in moderate_kw) or length > 200:
            return TaskComplexity.MODERATE

        return TaskComplexity.SIMPLE

    # ─── Info ───────────────────────────────────────────

    def list_available(self) -> list[dict[str, Any]]:
        """List available models with status."""
        result = []
        for key, model in self.models.items():
            disabled = key in self._disabled
            failures = self._failure_counts.get(key, 0)
            provider_avail = self._provider_available.get(model.provider, True)
            result.append({
                "name": model.name,
                "provider": model.provider,
                "speed": model.speed,
                "cost_per_1k": round(
                    model.cost_per_1k_input + model.cost_per_1k_output, 6
                ),
                "available": (
                    model.available
                    and not disabled
                    and provider_avail
                ),
                "failures": failures,
            })
        return sorted(result, key=lambda m: (-m["available"], m["cost_per_1k"]))


# ─── Helpers ────────────────────────────────────────────

def _read_sops_secret(name: str) -> str:
    """Read a sops-nix secret file."""
    try:
        path = os.path.expanduser(f"~/.local/share/sops-nix/secrets/{name}")
        if os.path.exists(path):
            return open(path).read().strip()
    except Exception:
        pass
    return ""


# ─── Singleton ──────────────────────────────────────────

_router_instance: SmartRouter | None = None


def get_router() -> SmartRouter:
    """Get or create the global SmartRouter instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = SmartRouter()
    return _router_instance
