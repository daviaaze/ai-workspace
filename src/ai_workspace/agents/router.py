"""
SmartRouter — intelligent model selection with fallback.

Routes tasks to the optimal model based on:
- Task type (coding, research, quick chat)
- Model availability (Ollama local, DeepSeek API, Gemini free tier)
- Cost constraints (GPU local first, API only when needed)
- Automatic retry with fallback models on failure

Architecture:
  Task → SmartRouter.analyze() → select best model
    → attempt execution
    → on failure: SmartRouter.fallback() → try next model
    → on success: SmartRouter.learn() → update preferences
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

logger = logging.getLogger("aiw.router")


class TaskComplexity(Enum):
    SIMPLE = auto()      # Quick chat, small edits, single file
    MODERATE = auto()   # Multi-file changes, research
    COMPLEX = auto()    # Large refactors, deep research, multi-step


@dataclass
class ModelInfo:
    """Information about an available model."""
    name: str
    provider: str          # ollama, deepseek, gemini
    cost_per_1k_tokens: float = 0.0
    max_tokens: int = 8_192
    supports_tools: bool = True
    speed: str = "medium"  # fast, medium, slow
    priority: int = 50     # Higher = preferred
    available: bool = True


@dataclass
class RoutingDecision:
    """The result of SmartRouter's analysis."""
    model: str
    provider: str
    reason: str
    fallback_chain: list[ModelInfo] = field(default_factory=list)


class SmartRouter:
    """Intelligent model router with fallback chains.
    
    Usage:
        router = SmartRouter()
        decision = router.route("Fix the auth middleware bug", task_type="coding")
        # → qwen3:14b via ollama (GPU local, fast, free)
        
        # On failure:
        fallback = router.fallback(decision)
        # → ministral-3:8b via ollama (smaller, faster)
    """
    
    # ─── Model Registry ────────────────────────────────
    
    DEFAULT_MODELS: list[ModelInfo] = [
        # Local GPU (Ollama) — primary, free
        ModelInfo(name="qwen3:14b", provider="ollama", cost_per_1k_tokens=0.0,
                  max_tokens=8_192, speed="medium", priority=90),
        ModelInfo(name="ministral-3:8b", provider="ollama", cost_per_1k_tokens=0.0,
                  max_tokens=8_192, speed="fast", priority=80),
        ModelInfo(name="qwen3.5:9b", provider="ollama", cost_per_1k_tokens=0.0,
                  max_tokens=8_192, speed="fast", priority=75),
        
        # DeepSeek API — paid, high quality
        ModelInfo(name="deepseek-chat", provider="deepseek", cost_per_1k_tokens=0.00014,
                  max_tokens=8_192, speed="medium", priority=70),
        
        # Gemini free tier — fallback
        ModelInfo(name="gemini-2.0-flash", provider="gemini", cost_per_1k_tokens=0.0,
                  max_tokens=8_192, speed="fast", priority=40,
                  supports_tools=False),
    ]
    
    # ─── Routing Rules ────────────────────────────────
    
    TASK_ROUTING: dict[str, list[str]] = {
        # Coding tasks: prefer local GPU models first
        "coding": ["qwen3:14b", "qwen3.5:9b", "ministral-3:8b", "deepseek-chat"],
        
        # Research: prefer larger models
        "research": ["qwen3:14b", "deepseek-chat", "qwen3.5:9b"],
        
        # Quick chat: fastest model
        "chat": ["ministral-3:8b", "qwen3.5:9b", "qwen3:14b"],
        
        # General: balanced
        "general": ["qwen3:14b", "ministral-3:8b", "deepseek-chat"],
    }
    
    # Complexity-based adjustments
    COMPLEXITY_PRIORITY: dict[TaskComplexity, list[str]] = {
        TaskComplexity.SIMPLE: ["ministral-3:8b", "qwen3.5:9b", "qwen3:14b"],
        TaskComplexity.MODERATE: ["qwen3:14b", "qwen3.5:9b", "deepseek-chat"],
        TaskComplexity.COMPLEX: ["qwen3:14b", "deepseek-chat"],
    }
    
    def __init__(self, custom_models: list[ModelInfo] | None = None):
        self.models: dict[str, ModelInfo] = {}
        for m in (custom_models or self.DEFAULT_MODELS):
            self.models[f"{m.provider}/{m.name}"] = m
        self._failure_counts: dict[str, int] = {}
        self._disabled: set[str] = set()
    
    # ─── Routing ──────────────────────────────────────
    
    def route(
        self,
        task: str,
        task_type: str = "general",
        complexity: TaskComplexity | None = None,
    ) -> RoutingDecision:
        """Select the best model for a task.
        
        Args:
            task: The task description.
            task_type: coding, research, chat, general.
            complexity: Optional override for complexity detection.
            
        Returns:
            RoutingDecision with model, provider, and fallback chain.
        """
        # Auto-detect complexity if not provided
        if complexity is None:
            complexity = self._detect_complexity(task)
        
        # Get routing order for this task type
        routing_order = self.TASK_ROUTING.get(task_type, self.TASK_ROUTING["general"])
        
        # Adjust by complexity
        complexity_order = self.COMPLEXITY_PRIORITY.get(complexity, [])
        # Merge: complexity models first, then remaining task-type models
        ordered = []
        seen = set()
        for name in complexity_order + routing_order:
            if name not in seen:
                ordered.append(name)
                seen.add(name)
        
        # Build fallback chain (available, not disabled)
        chain = []
        primary = None
        for name in ordered:
            model = self.models.get(f"ollama/{name}") or self.models.get(f"deepseek/{name}") or self.models.get(f"gemini/{name}")
            if not model:
                # Try matching just the name
                for key, m in self.models.items():
                    if m.name == name:
                        model = m
                        break
            if not model:
                continue
            
            if key_with_provider(model) in self._disabled:
                continue
            
            if primary is None and model.available:
                primary = model
            chain.append(model)
        
        if primary is None:
            # Fallback: first available model
            for m in self.models.values():
                if m.available and key_with_provider(m) not in self._disabled:
                    primary = m
                    chain = [m]
                    break
        
        if primary is None:
            raise RuntimeError("No models available")
        
        return RoutingDecision(
            model=primary.name,
            provider=primary.provider,
            reason=f"{task_type}/{complexity.name.lower()} → {primary.name} ({primary.speed})",
            fallback_chain=chain,
        )
    
    def fallback(self, decision: RoutingDecision) -> RoutingDecision | None:
        """Get the next fallback model after a failure.
        
        Returns None if no more fallbacks available.
        """
        # Disable the current model
        current_key = f"{decision.provider}/{decision.model}"
        self._disabled.add(current_key)
        self._failure_counts[current_key] = self._failure_counts.get(current_key, 0) + 1
        
        # Find next in chain
        for i, model in enumerate(decision.fallback_chain):
            key = key_with_provider(model)
            if key == current_key and i + 1 < len(decision.fallback_chain):
                next_model = decision.fallback_chain[i + 1]
                return RoutingDecision(
                    model=next_model.name,
                    provider=next_model.provider,
                    reason=f"Fallback from {decision.model} → {next_model.name}",
                    fallback_chain=decision.fallback_chain[i + 1:],
                )
        
        return None
    
    def mark_success(self, model: str, provider: str) -> None:
        """Mark a model as successfully used (reset failure count)."""
        key = f"{provider}/{model}"
        self._failure_counts.pop(key, None)
    
    def reset_failures(self) -> None:
        """Reset all failure counts (e.g., after network restore)."""
        self._failure_counts.clear()
        self._disabled.clear()
    
    # ─── Complexity Detection ─────────────────────────
    
    def _detect_complexity(self, task: str) -> TaskComplexity:
        """Auto-detect task complexity from the description."""
        task_lower = task.lower()
        length = len(task)
        
        # Complex indicators
        complex_keywords = [
            "refactor", "rewrite", "redesign", "architecture",
            "implement from scratch", "full stack", "entire module",
            "migrate", "restructure", "build a", "create a new",
        ]
        if any(kw in task_lower for kw in complex_keywords) or length > 500:
            return TaskComplexity.COMPLEX
        
        # Moderate indicators
        moderate_keywords = [
            "add feature", "implement", "fix multiple", "several files",
            "research", "analyze", "investigate", "debug",
            "add tests", "add documentation",
        ]
        if any(kw in task_lower for kw in moderate_keywords) or length > 200:
            return TaskComplexity.MODERATE
        
        # Simple (quick edits, single file, questions)
        return TaskComplexity.SIMPLE
    
    # ─── Info ──────────────────────────────────────────
    
    def list_available(self) -> list[dict[str, Any]]:
        """List available models with status."""
        result = []
        for key, model in self.models.items():
            disabled = key in self._disabled
            failures = self._failure_counts.get(key, 0)
            result.append({
                "name": model.name,
                "provider": model.provider,
                "speed": model.speed,
                "cost": model.cost_per_1k_tokens,
                "available": model.available and not disabled,
                "failures": failures,
            })
        return sorted(result, key=lambda m: -m["available"])
    
    def estimate_cost(self, task: str, decision: RoutingDecision) -> float:
        """Estimate cost for a task based on model and task length."""
        model = self.models.get(f"{decision.provider}/{decision.model}")
        if not model:
            return 0.0
        # Rough estimate: 1 token ≈ 4 chars
        estimated_tokens = max(50, len(task) // 4)
        return model.cost_per_1k_tokens * (estimated_tokens / 1000)


def key_with_provider(model: ModelInfo) -> str:
    return f"{model.provider}/{model.name}"


# ─── Singleton ────────────────────────────────────────

_router_instance: SmartRouter | None = None


def get_router() -> SmartRouter:
    """Get or create the global SmartRouter instance."""
    global _router_instance
    if _router_instance is None:
        _router_instance = SmartRouter()
    return _router_instance
