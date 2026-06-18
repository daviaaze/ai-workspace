"""
Observability layer — Laminar tracing + structlog + cost metrics.

Fase 4: Know exactly where every cent and millisecond goes.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Any


try:
    import structlog

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    get_logger = structlog.get_logger
    HAS_STRUCTLOG = True
except ImportError:
    structlog = None  # type: ignore
    get_logger = logging.getLogger
    HAS_STRUCTLOG = False



try:
    import lmnr

    HAS_LAMINAR = True
except ImportError:
    lmnr = None  # type: ignore
    HAS_LAMINAR = False


class Observability:
    """Unified tracing + logging + metrics layer.

    Usage:
        obs = Observability()
        obs.init()

        with obs.trace("research_pipeline", query=query):
            result = await engine.research(query)
            obs.log("research_complete", confidence=result.confidence)
    """

    def __init__(self, project_name: str = "aiw"):
        self.project_name = project_name
        self._initialized = False
        self._logger = get_logger(__name__)

    def init(self) -> None:
        """Initialize tracing and logging."""
        if self._initialized:
            return

        if HAS_LAMINAR:
            try:
                lmnr.Laminar.initialize(
                    project_api_key=os.getenv("LAMINAR_API_KEY", ""),
                )
                self._logger.info("laminar_initialized", project=self.project_name)
            except Exception as e:
                self._logger.warning("laminar_init_failed", error=str(e))

        self._initialized = True

    @contextmanager
    def trace(self, name: str, **metadata: Any):
        """Context manager for tracing a block of code.

        With Laminar: creates a span with automatic timing.
        Without Laminar: just logs start/end with timing.
        """
        start = time.monotonic()
        self._logger.debug("trace_start", name=name, **metadata)

        try:
            if HAS_LAMINAR and lmnr:
                with lmnr.observe(name=name):
                    yield
            else:
                yield
        except Exception as e:
            elapsed = time.monotonic() - start
            self._logger.error(
                "trace_error", name=name, elapsed_ms=int(elapsed * 1000),
                error=str(e),
            )
            raise
        else:
            elapsed = time.monotonic() - start
            self._logger.info(
                "trace_complete", name=name, elapsed_ms=int(elapsed * 1000),
            )

    def log_llm_call(
        self,
        provider: str,
        model: str,
        task_type: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        cache_hit: bool = False,
        duration_ms: int = 0,
        success: bool = True,
    ) -> None:
        """Record a structured LLM call event."""
        self._logger.info(
            "llm_call",
            provider=provider,
            model=model,
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=round(cost, 6),
            cache_hit=cache_hit,
            duration_ms=duration_ms,
            success=success,
        )

    def log(self, event: str, level: str = "info", **data: Any) -> None:
        """Log a structured event."""
        log_fn = getattr(self._logger, level, self._logger.info)
        log_fn(event, **data)



_obs: Observability | None = None


def get_obs() -> Observability:
    """Get or create the global Observability instance."""
    global _obs
    if _obs is None:
        _obs = Observability()
        _obs.init()
    return _obs
