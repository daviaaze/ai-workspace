"""
Tests for Workflow Engine — DAG execution, retry, state persistence.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from ai_workspace.workflow.engine import (
    BaseWorkflow,
    Context,
    StepResult,
    StepStatus,
    WorkflowLogger,
    WorkflowRegistry,
    WorkflowRun,
    workflow,
)

# ─── WorkflowLogger ───────────────────────────────────


def test_workflow_logger_records_logs():
    """WorkflowLogger should accumulate log entries."""
    log = WorkflowLogger(run_id=1)
    log.info("test message", step="step_a")
    log.debug("debug msg")
    log.warning("warning!", code="W001")
    log.error("error!", trace="...")

    assert len(log._logs) == 4
    assert log._logs[0]["level"] == "info"
    assert log._logs[0]["step"] == "step_a"
    assert log._logs[3]["level"] == "error"


def test_workflow_logger_flush_empty():
    """flush_to_db should return 0 when no logs."""
    log = WorkflowLogger(run_id=1)
    assert log.flush_to_db() == 0


def test_workflow_logger_flush_with_db(mock_psycopg2_conn):
    """flush_to_db should persist logs to PostgreSQL."""
    log = WorkflowLogger(run_id=42, db_url="postgresql:///mock_db")
    log.info("Test message")

    with patch("ai_workspace.workflow.engine.KnowledgeStore") as MockStore:
        MockStore.return_value.conn = mock_psycopg2_conn
        count = log.flush_to_db()
        assert count == 1  # One log entry was written


# ─── Context ──────────────────────────────────────────


def test_context_get_previous_step():
    """ctx.get() should retrieve completed step output."""
    run = WorkflowRun(run_id=1, workflow_name="test", input={})
    run.steps["step_plan"] = StepResult(
        step_name="step_plan",
        status=StepStatus.DONE,
        output=["q1", "q2", "q3"],
    )
    log = WorkflowLogger(run_id=1)
    ctx = Context(run=run, inputs={}, wf_log=log)

    assert ctx.get("step_plan") == ["q1", "q2", "q3"]


def test_context_get_pending_step():
    """ctx.get() should return None for not-yet-completed steps."""
    run = WorkflowRun(run_id=1, workflow_name="test", input={})
    run.steps["step_plan"] = StepResult(
        step_name="step_plan",
        status=StepStatus.PENDING,
    )
    log = WorkflowLogger(run_id=1)
    ctx = Context(run=run, inputs={}, wf_log=log)

    assert ctx.get("step_plan") is None


# ─── Workflow discovery ───────────────────────────────


def test_get_step_methods():
    """_get_step_methods should find all step_* methods."""
    class TestWF(BaseWorkflow):
        name = "test"

        async def step_a(self, ctx): pass
        async def step_b(self, ctx): pass
        async def not_a_step(self): pass

    wf = TestWF()
    steps = wf._get_step_methods()
    assert "step_a" in steps
    assert "step_b" in steps
    assert "not_a_step" not in steps


def test_infer_dependencies():
    """_infer_dependencies should find ctx.get() references in step source."""
    class TestWF(BaseWorkflow):
        name = "test"

        async def step_plan(self, ctx): pass

        async def step_research(self, ctx):
            ctx.get("step_plan")

        async def step_report(self, ctx):
            ctx.get("step_research")
            ctx.get("step_plan")

    wf = TestWF()
    deps = wf._infer_dependencies()

    # step_plan has no deps (doesn't call ctx.get)
    assert deps["step_plan"] == []

    # step_research depends on step_plan
    assert "step_plan" in deps["step_research"]

    # step_report depends on both
    assert "step_plan" in deps["step_report"]
    assert "step_research" in deps["step_report"]


def test_topological_sort_linear():
    """_topological_sort should produce correct levels for linear deps."""
    class WF(BaseWorkflow):
        name = "test"

    wf = WF()
    deps = {
        "step_a": [],
        "step_b": ["step_a"],
        "step_c": ["step_b"],
    }
    levels = wf._topological_sort(deps)

    assert len(levels) == 3
    assert levels[0] == ["step_a"]
    assert levels[1] == ["step_b"]
    assert levels[2] == ["step_c"]


def test_topological_sort_parallel():
    """_topological_sort should put independent steps in the same level."""
    class WF(BaseWorkflow):
        name = "test"

    wf = WF()
    deps = {
        "step_plan": [],
        "step_research_q1": ["step_plan"],
        "step_research_q2": ["step_plan"],
        "step_research_q3": ["step_plan"],
        "step_report": ["step_research_q1", "step_research_q2", "step_research_q3"],
    }
    levels = wf._topological_sort(deps)

    assert len(levels) == 3
    assert levels[0] == ["step_plan"]
    # All research steps in level 1 (parallel)
    assert "step_research_q1" in levels[1]
    assert "step_research_q2" in levels[1]
    assert "step_research_q3" in levels[1]
    assert levels[2] == ["step_report"]


def test_topological_sort_cycle_detection():
    """_topological_sort should fall back to sequential on cycles."""
    class WF(BaseWorkflow):
        name = "test"

    wf = WF()
    deps = {
        "step_a": ["step_b"],
        "step_b": ["step_a"],
    }
    levels = wf._topological_sort(deps)
    # Should be two sequential levels
    assert len(levels) >= 2


# ─── Registry ──────────────────────────────────────────


def test_workflow_registry_register():
    """@workflow decorator should register the workflow."""
    # Clear
    WorkflowRegistry._workflows = {}

    @workflow
    class MyWF(BaseWorkflow):
        name = "my_test_wf"

    assert "my_test_wf" in WorkflowRegistry.list()
    assert WorkflowRegistry.get("my_test_wf") is MyWF

    # Cleanup
    WorkflowRegistry._workflows = {}


def test_workflow_registry_get_nonexistent():
    """WorkflowRegistry.get should return None for unknown workflows."""
    assert WorkflowRegistry.get("this_does_not_exist_xyz") is None


# ─── Step execution with retry ────────────────────────


@pytest.mark.asyncio
async def test_execute_step_success(mock_psycopg2_conn):
    """_execute_step should return DONE on successful execution."""
    class TestWF(BaseWorkflow):
        name = "test"

        async def step_hello(self, ctx):
            return {"message": "hello"}

    wf = TestWF(db_url="postgresql:///mock_db")
    wf.store = MagicMock()
    wf.store.conn = mock_psycopg2_conn
    wf.store.initialize = MagicMock()

    run = WorkflowRun(run_id=1, workflow_name="test", input={})
    log = WorkflowLogger(run_id=1)
    ctx = Context(run=run, inputs={}, wf_log=log, store=wf.store)

    result = await wf._execute_step(ctx, "step_hello")

    assert result.status == StepStatus.DONE
    assert result.output == {"message": "hello"}
    assert result.duration_ms > 0


@pytest.mark.asyncio
async def test_execute_step_failure_with_retry(mock_psycopg2_conn):
    """_execute_step should retry on failure and eventually fail."""
    call_count = [0]

    class TestWF(BaseWorkflow):
        name = "test"
        config = __import__("ai_workspace.workflow.engine", fromlist=["WorkflowConfig"]).WorkflowConfig(
            max_retries=2,
            retry_delay=0.01,
        )

        async def step_flaky(self, ctx):
            call_count[0] += 1
            raise ValueError("Boom!")

    wf = TestWF(db_url="postgresql:///mock_db")
    wf.store = MagicMock()
    wf.store.conn = mock_psycopg2_conn
    wf.store.initialize = MagicMock()

    run = WorkflowRun(run_id=1, workflow_name="test", input={})
    log = WorkflowLogger(run_id=1)
    ctx = Context(run=run, inputs={}, wf_log=log, store=wf.store)

    result = await wf._execute_step(ctx, "step_flaky")

    assert result.status == StepStatus.FAILED
    assert result.retry_count >= 1
    assert call_count[0] == 3  # 1 initial + 2 retries


# ─── Learn workflow heuristics ────────────────────────


def test_learn_classify_convention():
    """Observations with 'always', 'never', 'must' should be classified as convention."""
    from ai_workspace.workflow.workflows import LearnWorkflow

    wf = LearnWorkflow()

    async def run_classify(text):
        run = WorkflowRun(run_id=1, workflow_name="learn", input={"observation": text})
        log = WorkflowLogger(run_id=1)
        ctx = Context(run=run, inputs={"observation": text}, wf_log=log)
        return await wf.step_classify(ctx)

    result = asyncio.run(run_classify("Always use asyncpg for database connections"))
    assert result["category"] == "convention"


def test_learn_classify_pattern():
    """Observations with 'workflow', 'process', 'when', 'step' should be classified as pattern."""
    from ai_workspace.workflow.workflows import LearnWorkflow

    wf = LearnWorkflow()

    async def run_classify(text):
        run = WorkflowRun(run_id=1, workflow_name="learn", input={"observation": text})
        log = WorkflowLogger(run_id=1)
        ctx = Context(run=run, inputs={"observation": text}, wf_log=log)
        return await wf.step_classify(ctx)

    result = asyncio.run(run_classify("When deploying to NixOS, the workflow should include a nix flake check step"))
    assert result["category"] == "pattern"


def test_learn_classify_learning():
    """General observations should default to 'learning'."""
    from ai_workspace.workflow.workflows import LearnWorkflow

    wf = LearnWorkflow()

    async def run_classify(text):
        run = WorkflowRun(run_id=1, workflow_name="learn", input={"observation": text})
        log = WorkflowLogger(run_id=1)
        ctx = Context(run=run, inputs={"observation": text}, wf_log=log)
        return await wf.step_classify(ctx)

    result = asyncio.run(run_classify("CrewAI 1.14.7 has native MCP DSL"))
    assert result["category"] == "learning"


# ═══════════════════════════════════════════════════════════════
# @step decorator — explicit DAG (replaces inspect.getsource)
# ═══════════════════════════════════════════════════════════════


class TestStepDecorator:
    """@step decorator records explicit dependencies."""

    def test_step_decorator_no_deps(self):
        from ai_workspace.workflow.engine import step

        @step()
        async def my_step(self, ctx):
            pass

        assert my_step._step_depends_on == []
        assert my_step._step_is_async is True

    def test_step_decorator_with_deps(self):
        from ai_workspace.workflow.engine import step

        @step(depends_on=["step_a", "step_b"])
        async def my_step(self, ctx):
            pass

        assert my_step._step_depends_on == ["step_a", "step_b"]

    def test_step_decorator_keeps_function_identity(self):
        from ai_workspace.workflow.engine import step

        @step(depends_on=["step_plan"])
        async def step_process(self, ctx):
            return 42

        assert step_process.__name__ == "step_process"
        assert hasattr(step_process, '_step_depends_on')

    def test_explicit_deps_override_source_inference(self):
        """When @step has depends_on, source code is not scanned."""
        from ai_workspace.workflow.engine import BaseWorkflow, step

        class ExplicitWF(BaseWorkflow):
            name = "explicit_test"

            @step()
            async def step_first(self, ctx):
                return {"data": 1}

            @step(depends_on=["step_first"])
            async def step_second(self, ctx):
                # Even though this calls ctx.get("step_first"),
                # the explicit depends_on is what matters
                _ = ctx.get("step_first")
                return {"data": 2}

        wf = ExplicitWF()
        deps = wf._infer_dependencies()
        assert deps["step_first"] == []
        assert deps["step_second"] == ["step_first"]

    def test_unknown_dependency_is_filtered(self):
        """Dependency on non-existent step is logged and ignored."""
        from ai_workspace.workflow.engine import BaseWorkflow, step

        class BadDepWF(BaseWorkflow):
            name = "bad_dep_test"

            @step(depends_on=["step_nonexistent"])
            async def step_real(self, ctx):
                return {"data": 1}

        wf = BadDepWF()
        deps = wf._infer_dependencies()
        assert deps["step_real"] == []

    def test_mixed_explicit_and_inferred(self):
        """Workflows with mixed decorator usage still work."""
        from ai_workspace.workflow.engine import BaseWorkflow, step

        class MixedWF(BaseWorkflow):
            name = "mixed_test"

            @step()
            async def step_a(self, ctx):
                return {"x": 1}

            # No @step decorator — inference from source
            async def step_b(self, ctx):
                _ = ctx.get("step_a")
                return {"y": 2}

        wf = MixedWF()
        deps = wf._infer_dependencies()
        assert deps["step_a"] == []
        assert deps["step_b"] == ["step_a"]

    def test_all_four_workflows_have_step_decorators(self):
        """Verify all concrete workflows use @step decorators."""
        from ai_workspace.workflow.workflows import (
            ContinuousLearningWorkflow,
            DailyBriefingWorkflow,
            DeepResearchWorkflow,
            LearnWorkflow,
        )
        for wf_cls in [DeepResearchWorkflow, DailyBriefingWorkflow, ContinuousLearningWorkflow, LearnWorkflow]:
            wf = wf_cls()
            step_methods = wf._get_step_methods()
            assert len(step_methods) > 0, f"{wf_cls.__name__} has no steps"
            for name in step_methods:
                method = getattr(wf, name)
                assert hasattr(method, '_step_depends_on'), (
                    f"{wf_cls.__name__}.{name} missing @step decorator"
                )


def test_learn_classify_empty():
    """Empty observation should return default classification."""
    from ai_workspace.workflow.workflows import LearnWorkflow

    wf = LearnWorkflow()

    async def run_classify(text):
        run = WorkflowRun(run_id=1, workflow_name="learn", input={"observation": text})
        log = WorkflowLogger(run_id=1)
        ctx = Context(run=run, inputs={"observation": text}, wf_log=log)
        return await wf.step_classify(ctx)

    result = asyncio.run(run_classify(""))
    assert result["category"] == "learning"
    assert result["title"] == "Untitled"
