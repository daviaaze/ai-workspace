"""
Graph-Structured Execution — DAG-based Agent Orchestration.

Represents tasks as a Directed Acyclic Graph (DAG) instead of a flat
step list. Nodes without dependencies execute in parallel. When a node
fails, only the affected sub-tree is repaired (local repair, O(d^h)
instead of O(N)).

Inspired by:
- GraSP (arXiv 2604.17870) — graph-structured skill execution
- FlowBank (arXiv 2606.11290) — query-adaptive workflow matching

Refs:
- SPEC_DAG_EXECUTION.md
"""

from __future__ import annotations

import asyncio
import json as _json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger("aiw.dag_executor")


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


class NodeStatus(str, Enum):
    """Execution status of a DAG node."""
    PENDING = "pending"      # Not yet ready (dependencies incomplete)
    READY = "ready"          # All dependencies satisfied, can execute
    RUNNING = "running"      # Currently executing
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"        # Terminated with error
    SKIPPED = "skipped"      # Skipped because dependency failed


@dataclass
class DAGNode:
    """A single node in the execution DAG."""
    id: str
    description: str                           # What this node does
    dependencies: list[str] = field(default_factory=list)  # IDs of prerequisite nodes
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[str] = None               # Output when completed
    error: Optional[str] = None                # Error message if failed
    retries: int = 0
    max_retries: int = 2
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def reset(self) -> None:
        """Reset this node to PENDING for retry."""
        self.status = NodeStatus.PENDING
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None


@dataclass
class DAGPlan:
    """An execution plan represented as a DAG."""
    task: str
    nodes: dict[str, DAGNode] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)  # (from_id, to_id)
    compiled_at: float = field(default_factory=time.time)

    def add_node(self, node: DAGNode) -> None:
        """Add a node to the plan."""
        self.nodes[node.id] = node

    def add_edge(self, from_id: str, to_id: str) -> None:
        """Add a dependency edge: to_id depends on from_id."""
        self.edges.append((from_id, to_id))
        if to_id in self.nodes:
            if from_id not in self.nodes[to_id].dependencies:
                self.nodes[to_id].dependencies.append(from_id)

    def get_ready_nodes(self) -> list[DAGNode]:
        """Return nodes whose dependencies are all satisfied."""
        ready: list[DAGNode] = []
        for node in self.nodes.values():
            if node.status != NodeStatus.PENDING:
                continue
            if all(
                self.nodes[dep].status == NodeStatus.COMPLETED
                for dep in node.dependencies
            ):
                ready.append(node)
        return ready

    def get_affected_nodes(self, failed_node_id: str) -> list[str]:
        """Return all downstream nodes affected by a failure (for local repair).

        Uses BFS from the failed node to find all transitive dependents.
        """
        affected: set[str] = {failed_node_id}
        queue: list[str] = [failed_node_id]

        while queue:
            current = queue.pop(0)
            for nid, node in self.nodes.items():
                if current in node.dependencies and nid not in affected:
                    affected.add(nid)
                    queue.append(nid)

        return list(affected)

    def is_complete(self) -> bool:
        """Check if all nodes have been processed."""
        return all(
            n.status in (NodeStatus.COMPLETED, NodeStatus.FAILED, NodeStatus.SKIPPED)
            for n in self.nodes.values()
        )

    def is_successful(self) -> bool:
        """Check if all nodes completed successfully."""
        return all(n.status == NodeStatus.COMPLETED for n in self.nodes.values())

    def summary(self) -> dict[str, Any]:
        """Return a summary of the plan state."""
        return {
            "task": self.task,
            "total_nodes": len(self.nodes),
            "completed": sum(1 for n in self.nodes.values() if n.status == NodeStatus.COMPLETED),
            "failed": sum(1 for n in self.nodes.values() if n.status == NodeStatus.FAILED),
            "skipped": sum(1 for n in self.nodes.values() if n.status == NodeStatus.SKIPPED),
            "pending": sum(1 for n in self.nodes.values() if n.status == NodeStatus.PENDING),
            "running": sum(1 for n in self.nodes.values() if n.status == NodeStatus.RUNNING),
            "edges": len(self.edges),
        }


# ---------------------------------------------------------------------------
# DAG Executor
# ---------------------------------------------------------------------------


@dataclass
class DAGExecutorConfig:
    """Configuration for the DAG executor."""
    max_parallel: int = 4
    """Maximum nodes to execute in parallel."""

    local_repair: bool = True
    """Enable local repair: on failure, only reset affected sub-tree."""

    max_retries: int = 2
    """Default max retries per node."""

    timeout_per_node: float = 120.0
    """Timeout in seconds for each node execution."""


class DAGExecutor:
    """Executes a DAGPlan with parallelism and local repair.

    Usage::

        plan = DAGPlan(task="Add auth to API")
        plan.add_node(DAGNode(id="A", description="Create middleware"))
        plan.add_node(DAGNode(id="B", description="Add JWT validation"))
        plan.add_node(DAGNode(id="C", description="Update routes", dependencies=["A", "B"]))

        executor = DAGExecutor()
        results = await executor.execute(plan, node_handler=my_handler)
    """

    def __init__(self, config: DAGExecutorConfig | None = None) -> None:
        self.config = config or DAGExecutorConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_parallel)

    async def execute(
        self,
        plan: DAGPlan,
        node_handler: Callable[[DAGNode], Any],
    ) -> dict[str, Any]:
        """Execute a DAG plan.

        Parameters
        ----------
        plan:
            The DAG plan to execute.
        node_handler:
            Async or sync callable that executes a single node.
            Receives the DAGNode and returns the result.

        Returns
        -------
        Dict mapping node_id -> result.
        """
        results: dict[str, Any] = {}
        iteration = 0

        while not plan.is_complete():
            iteration += 1
            ready = plan.get_ready_nodes()

            if not ready:
                # Check for dead nodes (dependencies failed)
                dead = [
                    n for n in plan.nodes.values()
                    if n.status == NodeStatus.PENDING
                    and any(
                        plan.nodes[dep].status == NodeStatus.FAILED
                        for dep in n.dependencies
                    )
                ]
                for node in dead:
                    node.status = NodeStatus.SKIPPED
                    logger.debug("Skipped %s (dependency failed)", node.id)

                if not plan.is_complete():
                    # Still not done — some nodes are running, wait
                    await asyncio.sleep(0.1)
                    continue
                break

            # Mark ready nodes as running
            for node in ready:
                node.status = NodeStatus.RUNNING
                node.started_at = time.time()

            # Execute ready nodes in parallel (up to semaphore limit)
            tasks = []
            for node in ready:
                task = self._execute_node(node, node_handler)
                tasks.append(task)

            node_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for node, result in zip(ready, node_results):
                if isinstance(result, Exception):
                    node.status = NodeStatus.FAILED
                    node.error = str(result)
                    logger.warning("Node %s failed: %s", node.id, result)

                    if self.config.local_repair and node.retries < node.max_retries:
                        node.retries += 1
                        # Reset only the affected sub-tree
                        affected = plan.get_affected_nodes(node.id)
                        repaired = 0
                        for nid in affected:
                            if nid != node.id:
                                plan.nodes[nid].reset()
                                repaired += 1
                        node.reset()  # Reset the failed node itself
                        logger.info(
                            "Local repair: reset %s + %d downstream nodes (retry %d/%d)",
                            node.id, repaired, node.retries, node.max_retries,
                        )
                else:
                    node.status = NodeStatus.COMPLETED
                    node.result = str(result) if result is not None else ""
                    node.completed_at = time.time()
                    results[node.id] = result
                    logger.debug("Node %s completed", node.id)

        return results

    async def _execute_node(
        self,
        node: DAGNode,
        handler: Callable[[DAGNode], Any],
    ) -> Any:
        """Execute a single node with semaphore and timeout."""
        async with self._semaphore:
            try:
                result = await asyncio.wait_for(
                    asyncio.ensure_future(self._call_handler(handler, node)),
                    timeout=self.config.timeout_per_node,
                )
                return result
            except asyncio.TimeoutError:
                raise TimeoutError(f"Node {node.id} timed out after {self.config.timeout_per_node}s")

    @staticmethod
    async def _call_handler(
        handler: Callable[[DAGNode], Any],
        node: DAGNode,
    ) -> Any:
        """Call the node handler, supporting both sync and async."""
        result = handler(node)
        if asyncio.iscoroutine(result):
            return await result
        return result


# ---------------------------------------------------------------------------
# DAG Compiler — LLM-based plan generation
# ---------------------------------------------------------------------------


async def compile_dag_plan(
    task: str,
    stream_chat: Callable[..., Any],
    available_tools: list[str] | None = None,
    model: str = "qwen3:14b",
) -> DAGPlan:
    """Use an LLM to compile a natural language task into a DAG plan.

    Parameters
    ----------
    task:
        Natural language description of the task.
    stream_chat:
        Async callable for streaming LLM chat (matches agent_loop's pattern).
    available_tools:
        Names of available tools the agent can use.
    model:
        Model name to use for compilation.

    Returns
    -------
    A DAGPlan with nodes and edges.
    """
    tools_str = ", ".join(available_tools) if available_tools else "general reasoning"
    prompt = f"""Break down this task into a DAG (Directed Acyclic Graph) of subtasks.

For each subtask, specify:
- id: a short unique identifier (e.g., "A", "B", "C")
- description: what the subtask does (one sentence)
- dependencies: list of subtask IDs that must COMPLETE BEFORE this one (empty if none)

Rules:
- Break the task into 3-5 subtasks
- Identify which subtasks can run in PARALLEL (no dependencies between them)
- Identify which subtasks depend on others

Task: {task}
Available tools: {tools_str}

Output ONLY valid JSON:
{{
  "nodes": [
    {{"id": "A", "description": "Create auth middleware", "dependencies": []}},
    {{"id": "B", "description": "Add JWT validation", "dependencies": ["A"]}}
  ]
}}"""

    try:
        # Call LLM for plan generation
        text_parts: list[str] = []
        async for chunk in stream_chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            temperature=0.3,
        ):
            if isinstance(chunk, dict):
                text = chunk.get("text", "") or chunk.get("content", "")
                if text:
                    text_parts.append(text)

        full_text = "".join(text_parts)

        # Extract JSON from response (may have markdown fences)
        json_text = _extract_json(full_text)
        data = _json.loads(json_text)

        plan = DAGPlan(task=task)
        for node_data in data.get("nodes", []):
            node = DAGNode(
                id=node_data["id"],
                description=node_data["description"],
                dependencies=node_data.get("dependencies", []),
            )
            plan.add_node(node)
            for dep in node.dependencies:
                plan.add_edge(dep, node.id)

        logger.info("Compiled DAG plan: %d nodes, %d edges", len(plan.nodes), len(plan.edges))
        return plan

    except Exception as exc:
        logger.warning("DAG compilation failed, creating fallback linear plan: %s", exc)
        # Fallback: create a linear plan (each node depends on previous)
        return _fallback_linear_plan(task)


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response (may include markdown fences)."""
    # Try to find JSON between markdown fences
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    elif "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    # Try to find first { and last }
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start >= 0 and brace_end > brace_start:
        return text[brace_start:brace_end + 1]
    return text.strip()


def _fallback_linear_plan(task: str) -> DAGPlan:
    """Create a simple linear plan when LLM compilation fails."""
    plan = DAGPlan(task=task)
    steps = ["Analyze task", "Plan approach", "Execute", "Validate"]
    prev_id: Optional[str] = None
    for i, step in enumerate(steps):
        node_id = f"L{i}"
        deps = [prev_id] if prev_id else []
        plan.add_node(DAGNode(id=node_id, description=step, dependencies=deps))
        prev_id = node_id
    return plan


# ---------------------------------------------------------------------------
# Workflow Bank — FlowBank-inspired workflow matching
# ---------------------------------------------------------------------------


@dataclass
class WorkflowRecord:
    """A stored workflow with performance history."""
    plan: DAGPlan
    success_count: int = 0
    total_attempts: int = 0
    avg_duration_ms: float = 0.0
    last_used: float = field(default_factory=time.time)


class WorkflowBank:
    """Portfolio of optimized workflows with query matching (FlowBank-inspired).

    Learns which workflows work best for which types of tasks and reuses
    them to avoid re-planning from scratch.
    """

    def __init__(self) -> None:
        self.workflows: dict[str, WorkflowRecord] = {}
        """Workflow records keyed by workflow_id."""

    def store(self, workflow_id: str, plan: DAGPlan) -> None:
        """Store a new workflow or update existing."""
        if workflow_id in self.workflows:
            self.workflows[workflow_id].plan = plan
        else:
            self.workflows[workflow_id] = WorkflowRecord(plan=plan)

    def match(self, task: str) -> Optional[DAGPlan]:
        """Find the best matching workflow for a task.

        Currently uses keyword matching. In production, would use
        semantic similarity (embeddings) + success history scoring.
        """
        keywords = set(task.lower().split())

        best: Optional[WorkflowRecord] = None
        best_score = 0.0

        for wf_id, record in self.workflows.items():
            wf_keywords = set(record.plan.task.lower().split())
            overlap = len(keywords & wf_keywords)
            total = len(keywords | wf_keywords) or 1
            similarity = overlap / total

            # Boost score with success rate
            success_rate = record.success_count / max(1, record.total_attempts)
            score = similarity * 0.6 + success_rate * 0.4

            if score > best_score:
                best_score = score
                best = record

        if best and best_score > 0.3:
            logger.info("Matched workflow %s (score=%.2f)", best.plan.task[:50], best_score)
            return best.plan

        return None

    def learn(self, plan: DAGPlan, success: bool, duration_ms: float) -> None:
        """Learn from execution result to improve future matching."""
        wf_id = _make_workflow_id(plan.task)
        if wf_id not in self.workflows:
            self.workflows[wf_id] = WorkflowRecord(plan=plan)

        record = self.workflows[wf_id]
        record.total_attempts += 1
        if success:
            record.success_count += 1
        record.avg_duration_ms = (
            (record.avg_duration_ms * (record.total_attempts - 1) + duration_ms)
            / record.total_attempts
        )
        record.last_used = time.time()

    def stats(self) -> dict[str, Any]:
        """Return statistics about the workflow bank."""
        return {
            "total_workflows": len(self.workflows),
            "total_attempts": sum(r.total_attempts for r in self.workflows.values()),
            "avg_success_rate": (
                sum(r.success_count / max(1, r.total_attempts) for r in self.workflows.values())
                / max(1, len(self.workflows))
            ),
            "most_used": max(
                self.workflows.items(),
                key=lambda x: x[1].total_attempts,
                default=(None, None),
            )[0],
        }


def _make_workflow_id(task: str) -> str:
    """Generate a stable workflow ID from a task description."""
    # Simple hash-based ID
    import hashlib
    words = " ".join(sorted(task.lower().split())[:10])
    return hashlib.md5(words.encode()).hexdigest()[:12]
