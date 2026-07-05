"""Tests for DAG Executor (SPEC_DAG_EXECUTION)."""

from __future__ import annotations

import asyncio
import time

import pytest

from ai_workspace.agents.dag_executor import (
    DAGExecutor,
    DAGExecutorConfig,
    DAGNode,
    DAGPlan,
    NodeStatus,
    WorkflowBank,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def executor() -> DAGExecutor:
    return DAGExecutor()


@pytest.fixture
def bank() -> WorkflowBank:
    return WorkflowBank()


# ---------------------------------------------------------------------------
# DAGNode tests
# ---------------------------------------------------------------------------


class TestDAGNode:
    def test_creation(self):
        node = DAGNode(id="A", description="Do something")
        assert node.id == "A"
        assert node.status == NodeStatus.PENDING
        assert node.dependencies == []

    def test_reset(self):
        node = DAGNode(id="A", description="Task", status=NodeStatus.FAILED, error="bad")
        node.reset()
        assert node.status == NodeStatus.PENDING
        assert node.error is None
        assert node.result is None

    def test_retries_count(self):
        node = DAGNode(id="A", description="Task", max_retries=3)
        assert node.max_retries == 3
        assert node.retries == 0


# ---------------------------------------------------------------------------
# DAGPlan tests
# ---------------------------------------------------------------------------


class TestDAGPlan:
    def test_empty_plan(self, executor):
        plan = DAGPlan(task="test")
        assert plan.get_ready_nodes() == []

    def test_single_node(self, executor):
        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="Task"))
        ready = plan.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == "A"

    def test_dependency_order(self, executor):
        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="First"))
        plan.add_node(DAGNode(id="B", description="Second", dependencies=["A"]))

        # Only A ready initially
        ready = plan.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == "A"

        # Complete A
        plan.nodes["A"].status = NodeStatus.COMPLETED
        ready = plan.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == "B"

    def test_parallel_nodes(self, executor):
        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="Task A"))
        plan.add_node(DAGNode(id="B", description="Task B"))
        plan.add_node(DAGNode(id="C", description="Task C", dependencies=["A", "B"]))

        # A and B ready (no deps)
        ready_ids = {n.id for n in plan.get_ready_nodes()}
        assert ready_ids == {"A", "B"}

        # Complete both
        plan.nodes["A"].status = NodeStatus.COMPLETED
        plan.nodes["B"].status = NodeStatus.COMPLETED

        # Now C is ready
        ready = plan.get_ready_nodes()
        assert len(ready) == 1
        assert ready[0].id == "C"

    def test_add_edge(self, executor):
        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="A"))
        plan.add_node(DAGNode(id="B", description="B"))
        plan.add_edge("A", "B")

        assert "A" in plan.nodes["B"].dependencies

    def test_is_complete(self, executor):
        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="A", status=NodeStatus.COMPLETED))
        plan.add_node(DAGNode(id="B", description="B", status=NodeStatus.COMPLETED))
        assert plan.is_complete()
        assert plan.is_successful()

    def test_not_complete(self, executor):
        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="A", status=NodeStatus.COMPLETED))
        plan.add_node(DAGNode(id="B", description="B", status=NodeStatus.PENDING))
        assert not plan.is_complete()

    def test_summary(self, executor):
        plan = DAGPlan(task="Complex task")
        plan.add_node(DAGNode(id="A", description="A", status=NodeStatus.COMPLETED))
        plan.add_node(DAGNode(id="B", description="B", status=NodeStatus.FAILED))
        plan.add_node(DAGNode(id="C", description="C", status=NodeStatus.PENDING))

        s = plan.summary()
        assert s["total_nodes"] == 3
        assert s["completed"] == 1
        assert s["failed"] == 1

    def test_affected_nodes_simple(self, executor):
        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="A"))
        plan.add_node(DAGNode(id="B", description="B", dependencies=["A"]))
        plan.add_node(DAGNode(id="C", description="C", dependencies=["B"]))
        plan.add_node(DAGNode(id="D", description="D"))  # Independent

        affected = plan.get_affected_nodes("A")
        assert set(affected) == {"A", "B", "C"}
        # D is NOT affected (independent)

    def test_affected_nodes_diamond(self, executor):
        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="A"))
        plan.add_node(DAGNode(id="B", description="B", dependencies=["A"]))
        plan.add_node(DAGNode(id="C", description="C", dependencies=["A"]))
        plan.add_node(DAGNode(id="D", description="D", dependencies=["B", "C"]))

        # If A fails, everything downstream is affected
        affected = plan.get_affected_nodes("A")
        assert set(affected) == {"A", "B", "C", "D"}

        # If B fails, only B and D are affected (C is independent from B)
        affected_b = plan.get_affected_nodes("B")
        assert set(affected_b) == {"B", "D"}


# ---------------------------------------------------------------------------
# DAGExecutor — Execution tests
# ---------------------------------------------------------------------------


class TestDAGExecutorExecute:
    @pytest.mark.asyncio
    async def test_single_node_execution(self, executor):
        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="Simple task"))

        async def handler(node: DAGNode) -> str:
            return f"done {node.id}"

        results = await executor.execute(plan, handler)
        assert results["A"] == "done A"
        assert plan.nodes["A"].status == NodeStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_sequential_execution(self, executor):
        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="First"))
        plan.add_node(DAGNode(id="B", description="Second", dependencies=["A"]))

        order: list[str] = []

        async def handler(node: DAGNode) -> str:
            order.append(node.id)
            return node.id

        await executor.execute(plan, handler)
        assert order == ["A", "B"]  # A before B
        assert plan.is_successful()

    @pytest.mark.asyncio
    async def test_parallel_execution(self, executor):
        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="Task A"))
        plan.add_node(DAGNode(id="B", description="Task B"))

        start_times: dict[str, float] = {}
        completion_order: list[str] = []

        async def handler(node: DAGNode) -> str:
            start_times[node.id] = time.time()
            if node.id == "A":
                await asyncio.sleep(0.05)  # A takes longer
            completion_order.append(node.id)
            return node.id

        await executor.execute(plan, handler)
        # Both started at roughly the same time
        assert abs(start_times.get("A", 0) - start_times.get("B", 0)) < 0.02
        # B finishes before A (B is faster)
        assert completion_order == ["B", "A"]
        assert plan.is_successful()

    @pytest.mark.asyncio
    async def test_node_failure_with_retry(self, executor):
        config = DAGExecutorConfig(local_repair=True, max_retries=2)
        executor = DAGExecutor(config)

        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="Flaky task", max_retries=3))
        plan.add_node(DAGNode(id="B", description="Dependent", dependencies=["A"]))

        call_count = {"A": 0}

        async def handler(node: DAGNode) -> str:
            if node.id == "A":
                call_count["A"] += 1
                if call_count["A"] < 3:
                    raise RuntimeError(f"Attempt {call_count['A']} failed")
                return "success on attempt 3"
            return f"done {node.id}"

        results = await executor.execute(plan, handler)
        assert call_count["A"] == 3  # Tried 3 times
        assert results["A"] == "success on attempt 3"
        assert "B" in results  # B should run after A succeeds
        assert plan.is_successful()

    @pytest.mark.asyncio
    async def test_node_failure_skips_dependents(self, executor):
        config = DAGExecutorConfig(local_repair=True, max_retries=0)  # No retries
        executor = DAGExecutor(config)

        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="Will fail", max_retries=0))
        plan.add_node(DAGNode(id="B", description="Depends on A", dependencies=["A"]))
        plan.add_node(DAGNode(id="C", description="Independent"))

        async def handler(node: DAGNode) -> str:
            if node.id == "A":
                raise RuntimeError("Node A failed")
            return f"done {node.id}"

        results = await executor.execute(plan, handler)
        assert "A" not in results
        assert "B" not in results  # Skipped
        assert "C" in results  # Independent, should succeed
        assert plan.nodes["A"].status == NodeStatus.FAILED
        assert plan.nodes["B"].status == NodeStatus.SKIPPED
        assert plan.nodes["C"].status == NodeStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_timeout(self, executor):
        config = DAGExecutorConfig(timeout_per_node=0.05)
        executor = DAGExecutor(config)

        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="Slow task"))

        async def handler(node: DAGNode) -> str:
            await asyncio.sleep(0.2)  # Way longer than timeout
            return "done"

        results = await executor.execute(plan, handler)
        assert "A" not in results  # Timed out
        assert plan.nodes["A"].status == NodeStatus.FAILED

    @pytest.mark.asyncio
    async def test_semaphore_limits_parallelism(self, executor):
        config = DAGExecutorConfig(max_parallel=2)
        executor = DAGExecutor(config)

        plan = DAGPlan(task="test")
        for i in range(5):
            plan.add_node(DAGNode(id=str(i), description=f"Task {i}"))

        max_concurrent = 0
        current = 0

        async def handler(node: DAGNode) -> str:
            nonlocal current, max_concurrent
            current += 1
            max_concurrent = max(max_concurrent, current)
            await asyncio.sleep(0.01)
            current -= 1
            return node.id

        await executor.execute(plan, handler)
        assert max_concurrent <= 2

    @pytest.mark.asyncio
    async def test_sync_handler(self, executor):
        plan = DAGPlan(task="test")
        plan.add_node(DAGNode(id="A", description="Sync task"))

        def handler(node: DAGNode) -> str:
            return f"sync {node.id}"

        results = await executor.execute(plan, handler)
        assert results["A"] == "sync A"


# ---------------------------------------------------------------------------
# WorkflowBank tests
# ---------------------------------------------------------------------------


class TestWorkflowBank:
    def test_store_and_match(self, bank):
        plan = DAGPlan(task="Add authentication to API")
        bank.store("auth", plan)

        matched = bank.match("Add authentication to the API")
        assert matched is not None
        assert matched.task == "Add authentication to API"

    def test_match_no_match(self, bank):
        matched = bank.match("completely unrelated task")
        assert matched is None

    def test_learn_improves_match(self, bank):
        plan = DAGPlan(task="Setup database")
        bank.learn(plan, success=True, duration_ms=500)
        bank.learn(plan, success=True, duration_ms=450)

        # learn uses _make_workflow_id, not the store key
        from ai_workspace.agents.dag_executor import _make_workflow_id
        wf_id = _make_workflow_id("Setup database")
        assert bank.workflows[wf_id].success_count == 2
        assert bank.workflows[wf_id].avg_duration_ms == 475.0

    def test_stats(self, bank):
        plan = DAGPlan(task="Test task")
        bank.learn(plan, success=True, duration_ms=100)
        bank.learn(plan, success=False, duration_ms=200)

        stats = bank.stats()
        assert stats["total_workflows"] == 1
        assert stats["total_attempts"] == 2


# ---------------------------------------------------------------------------
# Complex DAG scenarios
# ---------------------------------------------------------------------------


class TestComplexDAG:
    @pytest.mark.asyncio
    async def test_diamond_pattern(self, executor):
        """A → B, A → C, B → D, C → D"""
        plan = DAGPlan(task="Diamond pattern")
        plan.add_node(DAGNode(id="A", description="Root"))
        plan.add_node(DAGNode(id="B", description="Left", dependencies=["A"]))
        plan.add_node(DAGNode(id="C", description="Right", dependencies=["A"]))
        plan.add_node(DAGNode(id="D", description="Merge", dependencies=["B", "C"]))

        execution_order: list[str] = []

        async def handler(node: DAGNode) -> str:
            execution_order.append(node.id)
            if node.id == "B":
                await asyncio.sleep(0.02)
            return node.id

        await executor.execute(plan, handler)
        assert execution_order[0] == "A"  # Root first
        assert "D" == execution_order[-1]  # Merge last
        assert "B" in execution_order[1:3]  # B and C in parallel (order within parallel is non-deterministic)
        assert "C" in execution_order[1:3]
        assert plan.is_successful()

    @pytest.mark.asyncio
    async def test_local_repair_isolates_failure(self, executor):
        config = DAGExecutorConfig(local_repair=True, max_retries=2)
        executor = DAGExecutor(config)

        plan = DAGPlan(task="Isolated failure")
        plan.add_node(DAGNode(id="A", description="Root", max_retries=3))
        plan.add_node(DAGNode(id="B", description="Left branch", dependencies=["A"]))
        plan.add_node(DAGNode(id="C", description="Right branch", dependencies=["A"]))
        plan.add_node(DAGNode(id="D", description="Dependent on B", dependencies=["B"]))

        call_count = {"A": 0}

        async def handler(node: DAGNode) -> str:
            if node.id == "A":
                call_count["A"] += 1
                if call_count["A"] < 2:
                    raise RuntimeError("A failed initially")
            return node.id

        results = await executor.execute(plan, handler)
        assert "A" in results  # Retried successfully
        assert "B" in results
        assert "C" in results
        assert "D" in results  # B succeeded, so D runs
        assert call_count["A"] == 2
        assert plan.is_successful()
