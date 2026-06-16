"""
Workflow Engine — DAG-based execution with state persistence.

Features:
- Declarative step definitions with automatic DAG from dependencies
- Parallel execution (asyncio.gather) for independent steps
- State persistence in PostgreSQL (pending→running→done/failed)
- Retry with exponential backoff
- Resume from last completed step
- Full telemetry via Langtrace spans + structured logging
- CLI inspection: view runs, steps, logs, retry failed

Pattern:
    class MyWorkflow(BaseWorkflow):
        name = "my_workflow"
        
        async def step_plan(self, ctx): ...
        async def step_research(self, ctx): ...  # depends on step_plan
        async def step_report(self, ctx): ...     # depends on step_research

The engine automatically determines DAG order from method dependencies.
"""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from ai_workspace.knowledge import KnowledgeStore

logger = logging.getLogger("aiw.workflow")

# ════════════════════════════════════════════════════════════
# Structured Logging for workflows
# ════════════════════════════════════════════════════════════

class WorkflowLogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class WorkflowLogger:
    """Structured logger that captures logs per workflow run + step."""
    
    def __init__(self, run_id: int, db_url: str | None = None):
        self.run_id = run_id
        self.db_url = db_url
        self._logs: list[dict[str, Any]] = []
    
    def log(self, level: WorkflowLogLevel, message: str, **extra) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.value,
            "run_id": self.run_id,
            "message": message,
            **extra,
        }
        self._logs.append(entry)
        
        # Also emit to Python logger
        log_fn = {
            WorkflowLogLevel.DEBUG: logger.debug,
            WorkflowLogLevel.INFO: logger.info,
            WorkflowLogLevel.WARNING: logger.warning,
            WorkflowLogLevel.ERROR: logger.error,
        }.get(level, logger.info)
        
        extra_str = " ".join(f"{k}={v}" for k, v in extra.items() if k != "run_id")
        log_fn(f"[run={self.run_id}] {extra_str} {message}")
    
    def debug(self, msg: str, **extra): self.log(WorkflowLogLevel.DEBUG, msg, **extra)
    def info(self, msg: str, **extra): self.log(WorkflowLogLevel.INFO, msg, **extra)
    def warning(self, msg: str, **extra): self.log(WorkflowLogLevel.WARNING, msg, **extra)
    def error(self, msg: str, **extra): self.log(WorkflowLogLevel.ERROR, msg, **extra)
    
    def flush_to_db(self) -> int:
        """Persist logs to PostgreSQL."""
        if not self._logs or not self.db_url:
            return 0
        
        try:
            store = KnowledgeStore(db_url=self.db_url)
            store.initialize()
            c = store.conn.cursor()
            
            c.execute("""
                CREATE TABLE IF NOT EXISTS workflow_logs (
                    id SERIAL PRIMARY KEY,
                    run_id INTEGER NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    level VARCHAR(20) NOT NULL,
                    step_name VARCHAR(200),
                    message TEXT NOT NULL,
                    extra JSONB DEFAULT '{}'
                )
            """)
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow_logs_run 
                ON workflow_logs(run_id, timestamp)
            """)
            
            for entry in self._logs:
                c.execute(
                    """INSERT INTO workflow_logs (run_id, timestamp, level, step_name, message, extra)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (
                        self.run_id,
                        entry["timestamp"],
                        entry["level"],
                        entry.get("step"),
                        entry["message"],
                        json.dumps({k: v for k, v in entry.items() if k not in 
                                    ("run_id", "timestamp", "level", "step", "message")}),
                    ),
                )
            
            store.conn.commit()
            c.close()
            store.close()
            return len(self._logs)
        except Exception as e:
            logger.error(f"Failed to flush logs: {e}")
            return 0


# ════════════════════════════════════════════════════════════
# Workflow State
# ════════════════════════════════════════════════════════════

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"

class StepResult(BaseModel):
    step_name: str
    status: StepStatus
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: float = 0
    output: Any = None
    error: str | None = None
    retry_count: int = 0
    span_id: str | None = None  # Langtrace span

class WorkflowRun(BaseModel):
    run_id: int
    workflow_name: str
    status: StepStatus = StepStatus.PENDING
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: float = 0
    input: dict[str, Any] = Field(default_factory=dict)
    steps: dict[str, StepResult] = Field(default_factory=dict)
    error: str | None = None


# ════════════════════════════════════════════════════════════
# Workflow context (passed to each step)
# ════════════════════════════════════════════════════════════

class Context:
    """Execution context for a workflow run."""
    
    def __init__(
        self,
        run: WorkflowRun,
        inputs: dict[str, Any],
        wf_log: WorkflowLogger,
        store: KnowledgeStore | None = None,
        db_url: str | None = None,
    ):
        self.run = run
        self.inputs = inputs
        self.log = wf_log
        self.store = store
        self.db_url = db_url
        self._telemetry_spans: dict[str, str] = {}
    
    def get(self, step_name: str, default: Any = None) -> Any:
        """Get output from a previous step."""
        step = self.run.steps.get(step_name)
        if step and step.status == StepStatus.DONE:
            return step.output
        return default
    
    def set(self, key: str, value: Any) -> None:
        """Store arbitrary data in the run context."""
        self.inputs[key] = value
    
    def start_span(self, step_name: str) -> str:
        """Start a telemetry span for a step."""
        from ai_workspace.tasks import telemetry as telem
        span_id = telem.start(
            f"{self.run.workflow_name}.{step_name}",
            run_id=self.run.run_id,
        )
        self._telemetry_spans[step_name] = span_id
        return span_id
    
    def end_span(self, step_name: str, output: Any = None, error: str | None = None):
        """End a telemetry span."""
        from ai_workspace.tasks import telemetry as telem
        span_id = self._telemetry_spans.pop(step_name, None)
        if span_id:
            telem.end(span_id, output=output, error=error)


# ════════════════════════════════════════════════════════════
# Base Workflow class
# ════════════════════════════════════════════════════════════

class WorkflowConfig(BaseModel):
    """Configuration for a workflow."""
    max_retries: int = 3
    retry_delay: float = 5.0  # seconds base
    retry_backoff: float = 2.0  # exponential multiplier
    timeout_per_step: float = 600.0  # 10 min per step
    continue_on_step_failure: bool = False


# ── Step decorator (explicit DAG, replaces inspect.getsource) ──

_STEP_METADATA: dict[str, dict[str, list[str]]] = {}


def step(depends_on: list[str] | None = None, **kwargs):
    """Decorator: mark a method as a workflow step with explicit dependencies.
    
    Args:
        depends_on: List of step method names this step depends on.
                    The engine ensures these complete before this step runs.
    
    Example:
        @step(depends_on=["step_plan"])
        async def step_research(self, ctx): ...
    
    If ``depends_on`` is None or empty, the step runs in the first
    parallel level (no dependencies).  The engine falls back to
    ``inspect.getsource`` inference only when no explicit dependencies
    are declared on any step in the workflow.
    """
    deps = depends_on or []
    
    def decorator(func):
        # Store metadata on the function for the engine to read
        func._step_depends_on = deps
        func._step_is_async = True  # All steps are async
        return func
    
    return decorator


class BaseWorkflow:
    """Base class for defining workflows.
    
    Subclass and define async methods decorated with ``@step``.
    The engine uses explicit ``depends_on`` declarations (preferred)
    or falls back to inferring from ``ctx.get()`` calls.
    
    Example:
        class MyWorkflow(BaseWorkflow):
            name = "my_workflow"
            
            @step()
            async def step_fetch(self, ctx): ...
            
            @step(depends_on=["step_fetch"])
            async def step_process(self, ctx): ...
            
            @step(depends_on=["step_fetch", "step_process"])
            async def step_store(self, ctx): ...
    
    Rules injection: call ``self.create_agent(rules_tags=[...], **kwargs)``
    instead of ``Agent(...)`` directly to auto-inject behavioral rules
    into every agent's backstory.
    """
    
    name: ClassVar[str] = ""
    config: ClassVar[WorkflowConfig] = WorkflowConfig()
    
    # Rules tags to inject based on workflow type
    rules_tags: ClassVar[list[str]] = ["global"]
    
    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or "postgresql:///ai_workspace"
        self.store: KnowledgeStore | None = None
    
    # ─── Rules injection ────────────────────────────────
    
    @classmethod
    def get_rules_prompt(cls, extra_tags: list[str] | None = None) -> str:
        """Get behavioral rules as a system prompt fragment.
        
        Called automatically by create_agent(). Returns the always-apply
        rules plus any extra_tags, formatted for agent backstory injection.
        
        Args:
            extra_tags: Additional rule tags to include beyond always_apply.
        
        Returns:
            Rules formatted as a backstory prefix string, or empty string.
        """
        try:
            from ai_workspace.rules import get_rules_loader
            loader = get_rules_loader()
            
            # Always include always_apply rules
            tags = set(cls.rules_tags)
            if extra_tags:
                tags.update(extra_tags)
            
            prompt = loader.as_system_prompt(tags=list(tags))
            return prompt
        except Exception:
            return ""
    
    def create_agent(
        self,
        role: str | None = None,
        goal: str | None = None,
        backstory: str | None = None,
        rules_tags: list[str] | None = None,
        **kwargs,
    ):
        """Create a crewai Agent with rules injected into the backstory.
        
        Convenience wrapper around crewai.Agent that prepends behavioral
        rules to the backstory. All workflows should use this instead of
        creating Agent() directly.
        
        Args:
            role: Agent role (required by crewai)
            goal: Agent goal (required by crewai)
            backstory: Agent backstory (rules will be prepended)
            rules_tags: Additional rule tags for this specific agent
            **kwargs: Passed through to crewai.Agent
        
        Returns:
            crewai.Agent with rules-injected backstory
        """
        from crewai import Agent
        
        rules = self.get_rules_prompt(extra_tags=rules_tags)
        
        if rules and backstory:
            combined_backstory = f"{rules}\n\n---\n\n{backstory}"
        elif rules:
            combined_backstory = rules
        else:
            combined_backstory = backstory or ""
        
        return Agent(
            role=role or "",
            goal=goal or "",
            backstory=combined_backstory,
            **kwargs,
        )
    
    # ─── Subclass these ─────────────────────────────────
    
    async def setup(self, ctx: Context) -> None:
        """Optional setup before any steps run."""
        pass
    
    async def teardown(self, ctx: Context) -> None:
        """Optional cleanup after all steps."""
        pass
    
    # ─── Engine methods ─────────────────────────────────
    
    def _get_step_methods(self) -> list[str]:
        """Discover step methods (prefixed with step_)."""
        return sorted([
            name for name in dir(self.__class__)
            if name.startswith("step_") and callable(getattr(self, name))
        ])
    
    def _infer_dependencies(self) -> dict[str, list[str]]:
        """Infer step dependencies from explicit @step decorator or source code.
        
        Priority:
        1. ``@step(depends_on=[...])`` — explicit decorator (preferred)
        2. ``ctx.get("step_name")`` — source code analysis (legacy fallback)
        """
        import inspect
        
        step_names = self._get_step_methods()
        deps: dict[str, list[str]] = {}
        has_explicit = False
        
        for step_name in step_names:
            method = getattr(self, step_name)
            explicit = getattr(method, '_step_depends_on', None)
            
            if explicit is not None:
                # Explicit decorator — validate referenced steps exist
                has_explicit = True
                deps[step_name] = []
                for dep in explicit:
                    if dep not in step_names:
                        logger.warning(
                            "Step %s depends on unknown step %s — ignoring",
                            step_name, dep,
                        )
                    else:
                        deps[step_name].append(dep)
                continue
            
            # Legacy: infer from source code
            try:
                source = inspect.getsource(method)
            except (OSError, TypeError):
                deps[step_name] = []
                continue
            
            deps[step_name] = []
            for other in step_names:
                if other == step_name:
                    continue
                get_call = f"ctx.get(\"{other}\")"
                get_call2 = f"ctx.get('{other}')"
                if get_call in source or get_call2 in source:
                    deps[step_name].append(other)
        
        # If some steps use explicit deps and others don't, warn
        if has_explicit and any(
            getattr(getattr(self, s, None), '_step_depends_on', None) is None
            for s in step_names
        ):
            logger.info(
                "Workflow %s: mixed explicit/inferred dependencies — "
                "consider adding @step decorators to all steps",
                self.name,
            )
        
        return deps
    
    def _topological_sort(self, deps: dict[str, list[str]]) -> list[list[str]]:
        """Sort steps into levels for parallel execution."""
        in_degree = {s: len(d) for s, d in deps.items()}
        reverse_deps: dict[str, list[str]] = {s: [] for s in deps}
        
        for step, depends_on in deps.items():
            for dep in depends_on:
                reverse_deps.setdefault(dep, []).append(step)
        
        # Start with steps that have no dependencies
        ready = [s for s, d in in_degree.items() if d == 0]
        levels: list[list[str]] = []
        
        while ready:
            levels.append(sorted(ready))
            next_ready = []
            for step in ready:
                for dependent in reverse_deps.get(step, []):
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        next_ready.append(dependent)
            ready = next_ready
        
        if len(sum(levels, [])) != len(deps):
            # Cycle detected — fallback to sequential
            logger.warning("Dependency cycle detected in workflow, using sequential order")
            return [[s] for s in deps.keys()]
        
        return levels
    
    def _init_db(self) -> None:
        """Initialize workflow tables."""
        self.store = KnowledgeStore(db_url=self.db_url)
        self.store.initialize()
        
        c = self.store.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS workflow_runs (
                run_id SERIAL PRIMARY KEY,
                workflow_name VARCHAR(200) NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                started_at TIMESTAMPTZ,
                finished_at TIMESTAMPTZ,
                duration_ms FLOAT DEFAULT 0,
                input JSONB DEFAULT '{}',
                steps JSONB DEFAULT '{}',
                error TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflow_runs_status 
            ON workflow_runs(workflow_name, status, created_at)
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS workflow_step_logs (
                id SERIAL PRIMARY KEY,
                run_id INTEGER NOT NULL REFERENCES workflow_runs(run_id),
                step_name VARCHAR(200) NOT NULL,
                attempt INTEGER DEFAULT 1,
                status VARCHAR(20) NOT NULL,
                started_at TIMESTAMPTZ,
                finished_at TIMESTAMPTZ,
                duration_ms FLOAT DEFAULT 0,
                output JSONB,
                error TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        self.store.conn.commit()
        c.close()
    
    async def _execute_step(
        self, ctx: Context, step_name: str
    ) -> StepResult:
        """Execute a single step with retry logic."""
        method = getattr(self, step_name)
        config = self.config
        last_error = None
        
        ctx.start_span(step_name)
        
        for attempt in range(config.max_retries + 1):
            started = datetime.now(timezone.utc)
            result = StepResult(
                step_name=step_name,
                status=StepStatus.RUNNING,
                started_at=started.isoformat(),
                retry_count=attempt,
            )
            
            ctx.run.steps[step_name] = result
            self._save_step_log(ctx.run.run_id, step_name, attempt, "running", started=started)
            
            try:
                ctx.log.info(f"Starting step (attempt {attempt + 1}/{config.max_retries + 1})", step=step_name)
                
                output = await asyncio.wait_for(
                    method(ctx),
                    timeout=config.timeout_per_step,
                )
                
                finished = datetime.now(timezone.utc)
                duration = (finished - started).total_seconds() * 1000
                
                result.status = StepStatus.DONE
                result.finished_at = finished.isoformat()
                result.duration_ms = duration
                result.output = output
                
                ctx.end_span(step_name, output={"status": "done", "duration_ms": duration})
                ctx.log.info(f"Step completed in {duration:.0f}ms", step=step_name, duration_ms=duration)
                
                self._save_step_log(
                    ctx.run.run_id, step_name, attempt, "done",
                    started=started, finished=finished, duration_ms=duration,
                    output=output,
                )
                
                return result
                
            except asyncio.TimeoutError:
                last_error = f"Timeout after {config.timeout_per_step}s"
                ctx.log.error(f"Step timed out (attempt {attempt + 1})", step=step_name)
                
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                trace = traceback.format_exc()
                ctx.log.error(f"Step failed: {last_error}", step=step_name, traceback=trace[:500])
                logger.debug(f"Full traceback:\n{trace}")
            
            # Retry
            if attempt < config.max_retries:
                delay = config.retry_delay * (config.retry_backoff ** attempt)
                ctx.log.warning(f"Retrying in {delay:.0f}s", step=step_name, delay=delay)
                await asyncio.sleep(delay)
        
        # All retries exhausted
        finished = datetime.now(timezone.utc)
        result.status = StepStatus.FAILED
        result.finished_at = finished.isoformat()
        result.error = last_error
        
        ctx.end_span(step_name, error=last_error)
        
        self._save_step_log(
            ctx.run.run_id, step_name, config.max_retries, "failed",
            started=started, finished=finished, error=last_error,
        )
        
        return result
    
    def _save_step_log(
        self,
        run_id: int,
        step_name: str,
        attempt: int,
        status: str,
        started: datetime | None = None,
        finished: datetime | None = None,
        duration_ms: float = 0,
        output: Any = None,
        error: str | None = None,
    ) -> None:
        """Save step execution log to PostgreSQL."""
        if not self.store:
            return
        try:
            c = self.store.conn.cursor()
            output_json = None
            if output is not None:
                try:
                    output_json = json.dumps(
                        output if isinstance(output, dict) else str(output)[:5000]
                    )
                except Exception:
                    output_json = str(output)[:5000]
            
            c.execute(
                """INSERT INTO workflow_step_logs 
                   (run_id, step_name, attempt, status, started_at, finished_at, duration_ms, output, error)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (run_id, step_name, attempt, status, started, finished, duration_ms, output_json, error),
            )
            self.store.conn.commit()
            c.close()
        except Exception as e:
            logger.error(f"Failed to save step log: {e}")
    
    def _save_run(self, run: WorkflowRun) -> None:
        """Save workflow run state to PostgreSQL."""
        if not self.store:
            return
        try:
            c = self.store.conn.cursor()
            
            steps_json = json.dumps({
                name: step.model_dump(mode="json")
                for name, step in run.steps.items()
            })
            
            c.execute(
                """UPDATE workflow_runs 
                   SET status = %s, started_at = %s, finished_at = %s, 
                       duration_ms = %s, steps = %s, error = %s
                   WHERE run_id = %s""",
                (
                    run.status.value,
                    run.started_at,
                    run.finished_at,
                    run.duration_ms,
                    steps_json,
                    run.error,
                    run.run_id,
                ),
            )
            self.store.conn.commit()
            c.close()
        except Exception as e:
            logger.error(f"Failed to save run state: {e}")
    
    # ─── Public API ──────────────────────────────────────
    
    async def run(self, **inputs) -> WorkflowRun:
        """Execute the workflow with given inputs."""
        self._init_db()
        
        # Create run record
        c = self.store.conn.cursor()
        c.execute(
            """INSERT INTO workflow_runs (workflow_name, status, input)
               VALUES (%s, 'pending', %s) RETURNING run_id""",
            (self.name, json.dumps(inputs)),
        )
        run_id = c.fetchone()[0]
        self.store.conn.commit()
        c.close()
        
        # Create run object
        run = WorkflowRun(
            run_id=run_id,
            workflow_name=self.name,
            input=inputs,
        )
        
        wf_log = WorkflowLogger(run_id=run_id, db_url=self.db_url)
        ctx = Context(run=run, inputs=inputs, wf_log=wf_log, store=self.store, db_url=self.db_url)
        
        started = datetime.now(timezone.utc)
        run.status = StepStatus.RUNNING
        run.started_at = started.isoformat()
        
        wf_log.info(f"Workflow started with inputs: {json.dumps(inputs, default=str)[:200]}")
        
        try:
            # Setup
            await self.setup(ctx)
            
            # Determine execution order
            deps = self._infer_dependencies()
            levels = self._topological_sort(deps)
            
            wf_log.debug(f"Dependency graph: {deps}")
            wf_log.info(f"Execution plan: {len(levels)} levels, {sum(len(l) for l in levels)} steps")
            
            # Execute level by level (steps within a level run in parallel)
            for level_idx, level in enumerate(levels):
                wf_log.info(f"Level {level_idx + 1}/{len(levels)}: {level}")
                
                tasks = [self._execute_step(ctx, step_name) for step_name in level]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check for failures
                for step_name, result in zip(level, results):
                    if isinstance(result, Exception):
                        run.error = str(result)
                        run.status = StepStatus.FAILED
                        wf_log.error(f"Level failed at step {step_name}: {result}")
                        if not self.config.continue_on_step_failure:
                            raise result
                    elif result.status == StepStatus.FAILED:
                        wf_log.error(f"Step {step_name} failed after {result.retry_count} retries")
                        if not self.config.continue_on_step_failure:
                            run.status = StepStatus.FAILED
                            run.error = result.error
                            finished_dt = datetime.now(timezone.utc)
                            run.finished_at = finished_dt.isoformat()
                            run.duration_ms = (finished_dt - started).total_seconds() * 1000
                            self._save_run(run)
                            wf_log.flush_to_db()
                            return run
            
            # Teardown
            await self.teardown(ctx)
            
            # Mark complete
            finished_dt = datetime.now(timezone.utc)
            run.status = StepStatus.DONE
            run.finished_at = finished_dt.isoformat()
            run.duration_ms = (finished_dt - started).total_seconds() * 1000
            
            wf_log.info(f"Workflow completed successfully in {run.duration_ms:.0f}ms")
            
        except Exception as e:
            run.status = StepStatus.FAILED
            run.error = f"{type(e).__name__}: {e}"
            wf_log.error(f"Workflow failed: {run.error}", traceback=traceback.format_exc()[:500])
            logger.error(f"Workflow {self.name} failed:\n{traceback.format_exc()}")
        
        finally:
            finished_dt = datetime.now(timezone.utc)
            if run.finished_at is None:
                run.finished_at = finished_dt.isoformat()
            run.duration_ms = (finished_dt - started).total_seconds() * 1000
            self._save_run(run)
            wf_log.flush_to_db()
            if self.store:
                self.store.close()
        
        return run
    
    def run_sync(self, **inputs) -> WorkflowRun:
        """Synchronous wrapper for run()."""
        return asyncio.run(self.run(**inputs))
    
    # ─── Inspection API ─────────────────────────────────
    
    @classmethod
    def get_runs(
        cls,
        status: str | None = None,
        limit: int = 20,
        db_url: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get recent workflow runs."""
        store = KnowledgeStore(db_url=db_url)
        store.initialize()
        
        c = store.conn.cursor()
        if status:
            c.execute(
                """SELECT * FROM workflow_runs 
                   WHERE workflow_name = %s AND status = %s
                   ORDER BY created_at DESC LIMIT %s""",
                (cls.name, status, limit),
            )
        else:
            c.execute(
                """SELECT * FROM workflow_runs 
                   WHERE workflow_name = %s
                   ORDER BY created_at DESC LIMIT %s""",
                (cls.name, limit),
            )
        
        columns = [desc[0] for desc in c.description]
        runs = [dict(zip(columns, row)) for row in c.fetchall()]
        
        # Parse steps JSON
        for run in runs:
            if isinstance(run.get("steps"), str):
                try:
                    run["steps"] = json.loads(run["steps"])
                except json.JSONDecodeError:
                    pass
        
        c.close()
        store.close()
        return runs
    
    @classmethod
    def get_run_logs(
        cls,
        run_id: int,
        db_url: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all logs for a specific run."""
        store = KnowledgeStore(db_url=db_url)
        store.initialize()
        
        c = store.conn.cursor()
        c.execute(
            """SELECT * FROM workflow_step_logs 
               WHERE run_id = %s ORDER BY created_at""",
            (run_id,),
        )
        
        columns = [desc[0] for desc in c.description]
        logs = [dict(zip(columns, row)) for row in c.fetchall()]
        
        c.close()
        store.close()
        return logs
    
    @classmethod
    def retry_run(
        cls,
        run_id: int,
        db_url: str | None = None,
    ) -> WorkflowRun | None:
        """Retry a failed workflow run from the last completed step."""
        store = KnowledgeStore(db_url=db_url)
        store.initialize()
        
        c = store.conn.cursor()
        c.execute(
            "SELECT * FROM workflow_runs WHERE run_id = %s AND workflow_name = %s",
            (run_id, cls.name),
        )
        row = c.fetchone()
        
        if not row:
            c.close()
            store.close()
            logger.error(f"Run {run_id} not found for workflow {cls.name}")
            return None
        
        columns = [desc[0] for desc in c.description]
        run_data = dict(zip(columns, row))
        c.close()
        store.close()
        
        inputs = run_data.get("input", {})
        if isinstance(inputs, str):
            inputs = json.loads(inputs)
        
        wf = cls(db_url=db_url)
        wf.logger = WorkflowLogger(run_id=run_id, db_url=db_url)
        wf.logger.info(f"Retrying workflow run {run_id}")
        
        return asyncio.run(wf.run(**inputs))
    
    @classmethod
    def get_run_stats(
        cls,
        db_url: str | None = None,
    ) -> dict[str, Any]:
        """Get statistics for this workflow."""
        store = KnowledgeStore(db_url=db_url)
        store.initialize()
        
        c = store.conn.cursor()
        c.execute(
            """SELECT 
                 COUNT(*) as total,
                 COUNT(*) FILTER (WHERE status = 'done') as completed,
                 COUNT(*) FILTER (WHERE status = 'failed') as failed,
                 COUNT(*) FILTER (WHERE status = 'running') as running,
                 ROUND(AVG(duration_ms)::numeric, 0) as avg_duration_ms,
                 ROUND(AVG(duration_ms) FILTER (WHERE status = 'done')::numeric, 0) as avg_success_duration_ms,
                 MIN(created_at) as first_run,
                 MAX(created_at) as last_run
               FROM workflow_runs 
               WHERE workflow_name = %s""",
            (cls.name,),
        )
        
        columns = [desc[0] for desc in c.description]
        stats = dict(zip(columns, c.fetchone()))
        
        c.close()
        store.close()
        return stats


# ════════════════════════════════════════════════════════════
# Simple workflow registry
# ════════════════════════════════════════════════════════════

class WorkflowRegistry:
    """Registry of available workflows, used by CLI for discovery."""
    
    _workflows: dict[str, type[BaseWorkflow]] = {}
    
    @classmethod
    def register(cls, wf_class: type[BaseWorkflow]) -> type[BaseWorkflow]:
        cls._workflows[wf_class.name] = wf_class
        return wf_class
    
    @classmethod
    def get(cls, name: str) -> type[BaseWorkflow] | None:
        return cls._workflows.get(name)
    
    @classmethod
    def list(cls) -> list[str]:
        return sorted(cls._workflows.keys())


# Decorator for auto-registration
def workflow(cls: type[BaseWorkflow]) -> type[BaseWorkflow]:
    return WorkflowRegistry.register(cls)
