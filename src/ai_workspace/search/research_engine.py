"""
Deep Research v2 — Graph-Based Multi-Agent Research Engine.

Replaces deep_search.py. No crewAI dependency.
Uses AgentLoop (Phase 1) + ToolExecution (Phase 3) for parallel research.

Architecture:
  1. Planner (LLM) -> Task Graph (DAG)
  2. Executor Swarm -> parallel sub-task execution
  3. Verifier -> source validation + claim extraction
  4. Reflector -> check sufficiency, re-plan if needed
  5. Synthesizer (LLM) -> final report with citations

Refs:
- SPEC_DEEP_RESEARCH_V2.md
- DuMate (Baidu), GPT Researcher, STORM (Stanford), Marco (Alibaba)
"""

from __future__ import annotations

import asyncio
import json as _json
import logging
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from ai_workspace.agents.loop import (
    agent_loop,
    LoopParams,
    LoopPattern,
    suggest_pattern,
)

logger = logging.getLogger("aiw.research")


# ═══════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════

class ResearchPhase(str, Enum):
    """Phases of the research pipeline, emitted as progress events."""
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REFLECTING = "reflecting"
    SYNTHESIZING = "synthesizing"


@dataclass
class ResearchTask:
    """A node in the research task graph (DAG).

    Attributes:
        id: Short identifier (e.g., "q1", "gap-2").
        question: The specific research question.
        dependencies: Task IDs that must complete before this one.
        agent_type: 'web_search', 'academic', 'technical', or 'citation'.
        status: 'pending', 'running', 'completed', 'failed'.
        findings: Collected results from tool calls.
        confidence: Estimated confidence (0.0 - 1.0).
        start_ms: Execution timing.
    """
    id: str
    question: str
    dependencies: list[str] = field(default_factory=list)
    agent_type: str = "web_search"
    status: str = "pending"
    findings: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    response_text: str = ""
    """Raw text response from the agent (stored for synthesis)."""
    start_ms: float = 0.0


@dataclass
class EvidenceClaim:
    """A claim extracted from a source with provenance tracking.

    Attributes:
        text: The claim text (truncated for storage).
        source_url: URL of the source.
        source_title: Title or description of the source.
        relevance_score: How relevant to the query (0.0 - 1.0).
        verification_status: 'unverified', 'verified', 'contradicted',
                              'insufficient_evidence'.
    """
    text: str
    source_url: str
    source_title: str = "Unknown"
    relevance_score: float = 0.5
    verification_status: str = "unverified"


@dataclass
class ResearchReport:
    """Complete research output with audit trail.

    Attributes:
        query: Original research question.
        summary: Executive summary (2-3 sentences).
        sections: Report sections with title and content.
        claims: Extracted claims with provenance.
        sources: All source URLs consulted.
        confidence: Overall confidence score (0.0 - 1.0).
        trace: Audit trail of phases executed.
        duration_ms: Total research time.
    """
    query: str
    summary: str = ""
    sections: list[dict[str, Any]] = field(default_factory=list)
    claims: list[EvidenceClaim] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    confidence: float = 0.0
    trace: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: float = 0.0


# ═══════════════════════════════════════════════════════════
# Tool loading (lazy, no crewAI)
# ═══════════════════════════════════════════════════════════

def _load_research_tools() -> list:
    """Load research-oriented tools lazily."""
    tools: list = []
    try:
        from ai_workspace.tools import Crawl4AITool
        tools.append(Crawl4AITool())
    except Exception as e:
        logger.debug("Crawl4AI not available: %s", e)

    try:
        from ai_workspace.tools import WebFetchTool
        tools.append(WebFetchTool())
    except Exception as e:
        logger.debug("WebFetchTool not available: %s", e)

    try:
        from ai_workspace.tools import HeadlessBrowserTool
        tools.append(HeadlessBrowserTool())
    except Exception as e:
        logger.debug("HeadlessBrowserTool not available: %s", e)

    try:
        from ai_workspace.tools import PaginatedScraperTool
        tools.append(PaginatedScraperTool())
    except Exception as e:
        logger.debug("PaginatedScraperTool not available: %s", e)

    try:
        from ai_workspace.tools import MercadoLivreSearchTool
        tools.append(MercadoLivreSearchTool())
    except Exception as e:
        logger.debug("MercadoLivreSearchTool not available: %s", e)

    try:
        from ai_workspace.tools import OLXSearchTool
        tools.append(OLXSearchTool())
    except Exception as e:
        logger.debug("OLXSearchTool not available: %s", e)

    return tools


_TOOL_DESCRIPTIONS = (
    "Available tools (try in order):\n"
    "- crawl4ai_scrape: PRIMARY scraper. Returns clean markdown from any URL.\n"
    "- web_fetch: reads static HTML pages and APIs (fallback)\n"
    "- headless_browser: renders JavaScript SPA pages\n"
    "- paginated_scraper: navigates multi-page tables\n"
    "- mercado_livre_search / olx_search: BR marketplace prices\n"
)


# ═══════════════════════════════════════════════════════════
# ResearchEngine
# ═══════════════════════════════════════════════════════════

class ResearchEngine:
    """Deep Research v2 — Graph-based multi-agent research engine.

    Attributes:
        model: LLM model name.
        provider: LLM provider ('ollama', 'deepseek', etc.).
        max_parallel: Maximum concurrent research tasks.
        max_depth: Maximum depth for recursive sub-questions.
        max_tasks: Maximum total sub-tasks.
        min_sources: Minimum unique sources before synthesis.
    """

    def __init__(
        self,
        model: str = "qwen3:14b",
        provider: str = "ollama",
        max_parallel: int = 5,
        max_depth: int = 3,
        max_tasks: int = 8,
        min_sources: int = 3,
    ):
        self.model = model
        self.provider = provider
        self.max_parallel = max_parallel
        self.max_depth = max_depth
        self.max_tasks = max_tasks
        self.min_sources = min_sources

        # Lazily-loaded tools
        self._tools: list | None = None

    # ── Public API ─────────────────────────────────────────

    async def research(
        self,
        query: str,
        *,
        progress: Callable[[str, str], None] | None = None,
    ) -> ResearchReport:
        """Execute deep research on a query.

        Args:
            query: The research question.
            progress: Optional callback(phase: str, detail: str) for
                      real-time streaming progress.

        Returns:
            ResearchReport with summary, sections, claims, sources,
            confidence, and full audit trail.
        """
        t0 = time.monotonic()
        trace: list[dict[str, Any]] = []

        # Ensure tools are loaded
        if self._tools is None:
            self._tools = _load_research_tools()

        # 1. Planning — build Task Graph
        self._notify(progress, ResearchPhase.PLANNING, "Building research plan...")
        tasks = await self._plan(query)
        trace.append({"phase": "planning", "task_count": len(tasks)})
        self._notify(progress, ResearchPhase.PLANNING,
                     f"Plan: {len(tasks)} sub-tasks to research")

        if not tasks:
            tasks = [ResearchTask(id="main", question=query)]

        # 2. Execution — agent swarm in parallel (respects DAG)
        self._notify(progress, ResearchPhase.EXECUTING, "Researching in parallel...")
        tasks = await self._execute_parallel(tasks, progress)
        trace.append({"phase": "executing", "completed": sum(
            1 for t in tasks if t.status == "completed")})

        # 3. Verification — validate sources, extract claims
        self._notify(progress, ResearchPhase.VERIFYING, "Verifying sources and extracting claims...")
        claims = await self._verify_and_extract(tasks)
        try:
            claims = await self._filter_by_reputation(claims)
        except Exception as e:
            logger.debug("Source reputation filter skipped: %s", e)
        trace.append({"phase": "verifying", "claim_count": len(claims)})

        # 4. Reflect — is evidence sufficient?
        self._notify(progress, ResearchPhase.REFLECTING, "Checking completeness...")
        if not await self._is_sufficient(claims, query):
            self._notify(progress, ResearchPhase.REFLECTING,
                         "Evidence insufficient. Searching for gaps...")
            gap_tasks = self._identify_gaps(claims, query)
            if gap_tasks:
                self._notify(progress, ResearchPhase.EXECUTING,
                             f"Researching {len(gap_tasks)} gap tasks...")
                gap_tasks = await self._execute_parallel(gap_tasks, progress)
                tasks.extend(gap_tasks)
                new_claims = await self._verify_and_extract(gap_tasks)
                claims.extend(new_claims)
                trace.append({"phase": "reflecting", "gap_tasks": len(gap_tasks),
                              "additional_claims": len(new_claims)})
        else:
            trace.append({"phase": "reflecting", "sufficient": True})

        # 5. Synthesis — aggregate into report
        self._notify(progress, ResearchPhase.SYNTHESIZING, "Writing final report...")
        report = await self._synthesize(query, tasks, claims)
        report.duration_ms = round((time.monotonic() - t0) * 1000)
        report.trace = trace
        self._notify(progress, ResearchPhase.SYNTHESIZING,
                     f"Report complete ({report.duration_ms}ms, "
                     f"{len(report.sources)} sources)")

        return report

    # ── Phase 1: Planner ───────────────────────────────────

    async def _plan(self, query: str) -> list[ResearchTask]:
        """Planner agent: decompose query into a Task Graph (DAG).

        Uses a direct AgentLoop call to get a JSON plan from the LLM.
        Falls back to a single main task if parsing fails.
        """
        prompt = f"""Break down this research query into {self.max_tasks} or fewer specific sub-questions.

For each sub-question, specify:
- id: short identifier (e.g., "q1", "q2")
- question: the specific question to investigate
- dependencies: list of task IDs that must complete first (empty list if independent)
- agent_type: "web_search" (general web), "academic" (papers/journals),
  "technical" (docs/specs/code), or "citation" (find original sources)

Guidelines:
- Prioritize independent tasks (empty dependencies) for parallelism.
- Maximum {self.max_parallel} tasks can run concurrently.
- Include diverse angles: technical, practical, comparative, historical.
- For price/availability research, include BR marketplace tasks.

Output ONLY a JSON array of objects. No markdown, no explanation.

Query: {query}"""

        params = LoopParams(
            task=prompt,
            pattern=LoopPattern.DIRECT,
            model=self.model,
            provider=self.provider,
            stream=True,
            max_turns=2,
        )

        result_text = ""
        async for event in agent_loop(params):
            if event.type == "token":
                result_text += event.data.get("text", "")

        tasks = self._parse_task_json(result_text)
        if not tasks:
            # Fallback: single task
            tasks = [ResearchTask(id="main", question=query)]
        return tasks[:self.max_tasks]

    def _parse_task_json(self, text: str) -> list[ResearchTask]:
        """Parse a JSON array of sub-questions from LLM output."""
        # Strip markdown code fences
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        # Try direct parse
        try:
            data = _json.loads(cleaned)
            if isinstance(data, list):
                return [
                    ResearchTask(
                        id=t.get("id", f"q{i}"),
                        question=t.get("question", ""),
                        dependencies=t.get("dependencies", []),
                        agent_type=t.get("agent_type", "web_search"),
                    )
                    for i, t in enumerate(data)
                    if t.get("question")
                ]
        except (_json.JSONDecodeError, ValueError):
            pass

        # Try regex extraction of JSON array
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                data = _json.loads(match.group())
                if isinstance(data, list):
                    return [
                        ResearchTask(
                            id=t.get("id", f"q{i}"),
                            question=t.get("question", ""),
                            dependencies=t.get("dependencies", []),
                            agent_type=t.get("agent_type", "web_search"),
                        )
                        for i, t in enumerate(data)
                        if t.get("question")
                    ]
            except (_json.JSONDecodeError, ValueError):
                pass

        return []

    # ── Phase 2: Executor Swarm ─────────────────────────────

    async def _execute_parallel(
        self,
        tasks: list[ResearchTask],
        progress: Callable | None = None,
    ) -> list[ResearchTask]:
        """Execute tasks in parallel respecting DAG dependencies.

        Uses topological execution: runs all tasks with no pending
        dependencies concurrently (up to max_parallel), then proceeds
        to the next wave once dependencies resolve.

        Each task runs its own AgentLoop in ReAct mode with tools.
        """
        # Ensure tools are loaded
        if self._tools is None:
            self._tools = _load_research_tools()

        # Map of id -> ResearchTask for dependency resolution
        task_map: dict[str, ResearchTask] = {t.id: t for t in tasks}
        completed: set[str] = set()
        failed: set[str] = set()

        # Build initial ready set
        def is_ready(task: ResearchTask) -> bool:
            return all(
                dep in completed and dep not in failed
                for dep in task.dependencies
            )

        sem = asyncio.Semaphore(self.max_parallel)

        while len(completed) + len(failed) < len(tasks):
            ready = [
                t for t in tasks
                if t.id not in completed and t.id not in failed and is_ready(t)
            ]

            if not ready:
                # Deadlock: remaining tasks have unresolvable deps -> run anything pending
                ready = [
                    t for t in tasks
                    if t.id not in completed and t.id not in failed
                ]
                if not ready:
                    break

            async def research_one(task: ResearchTask) -> ResearchTask:
                async with sem:
                    task.status = "running"
                    task.start_ms = time.monotonic()
                    self._notify(
                        progress, ResearchPhase.EXECUTING,
                        f"Researching: {task.question[:80]}...",
                    )

                    try:
                        prompt = self._build_research_prompt(task)
                        # REACT+tools work with any provider now.
                        # Tools are auto-normalized to provider format.
                        use_react = (
                            task.agent_type in ("web_search", "citation")
                            and bool(self._tools)
                        )

                        # Build tool handlers from BaseTool instances
                        tool_handlers: dict[str, Any] = {}
                        if use_react and self._tools:
                            for t in self._tools:
                                name = getattr(t, "name", None)
                                run_fn = getattr(t, "_run", None) or getattr(t, "run", None)
                                if name and run_fn:
                                    tool_handlers[name] = run_fn

                        params = LoopParams(
                            task=prompt,
                            pattern=LoopPattern.REACT if use_react else LoopPattern.DIRECT,
                            tools=self._tools if use_react else None,
                            tool_handlers=tool_handlers,
                            model=self.model,
                            provider=self.provider,
                            stream=True,
                            max_turns=5 if use_react else 2,
                            parallel_tools=True,
                        )

                        result_text = ""
                        async for event in agent_loop(params):
                            if event.type == "token":
                                result_text += event.data.get("text", "")
                            if event.type == "tool_result":
                                result_data = event.data
                                if isinstance(result_data, dict):
                                    task.findings.append(result_data)

                        task.status = "completed"
                        task.response_text = result_text
                        task.confidence = self._estimate_confidence(
                            task.findings, result_text
                        )
                        duration = round(
                            (time.monotonic() - task.start_ms) * 1000
                        )
                        self._notify(
                            progress, ResearchPhase.EXECUTING,
                            f"Done: {task.id} ({duration}ms, "
                            f"confidence: {task.confidence:.0%})",
                        )

                    except Exception as exc:
                        task.status = "failed"
                        logger.warning(
                            "Task %s failed: %s", task.id, exc,
                        )
                        self._notify(
                            progress, ResearchPhase.EXECUTING,
                            f"Failed: {task.id} — {exc}",
                        )

                    return task

            results = await asyncio.gather(
                *[research_one(t) for t in ready],
            )

            for r in results:
                if r.status == "completed":
                    completed.add(r.id)
                else:
                    failed.add(r.id)

            # Update task_map with results
            for r in results:
                task_map[r.id] = r

        return list(task_map.values())

    def _build_research_prompt(self, task: ResearchTask) -> str:
        """Build a research prompt for a single sub-task."""
        # For factual/definition tasks, use a concise direct prompt.
        # Only include tool instructions for tasks that need web research.
        needs_tools = task.agent_type in ("web_search", "citation")

        search_focus = {
            "web_search": (
                "Search the web broadly. Compare multiple sources. "
                "Prioritize recent information. Note any disagreements."
            ),
            "academic": (
                "Search for academic papers, peer-reviewed journals, "
                "and scholarly publications."
            ),
            "technical": (
                "Search technical documentation, API references, source code, "
                "and implementation guides."
            ),
            "citation": (
                "Find the original source for claims. Trace information back "
                "to primary documents."
            ),
        }.get(task.agent_type, "Search thoroughly and verify sources.")

        if needs_tools:
            return f"""Research this question thoroughly using the available web tools.

Question: {task.question}

Strategy: {search_focus}

{_TOOL_DESCRIPTIONS}

IMPORTANT:
- Use crawl4ai_scrape first for any URL.
- Always note the source URL for each piece of information.
- If tools fail, report honestly — do NOT fabricate data.

Provide a thorough answer with specific data points and source URLs."""
        else:
            return f"""Answer this question concisely but thoroughly.

Question: {task.question}

Provide a clear, factual answer. Include specific details and examples."""

    @staticmethod
    def _estimate_confidence(
        findings: list[dict[str, Any]],
        result_text: str,
    ) -> float:
        """Estimate confidence based on findings quantity and text quality."""
        if not findings and not result_text.strip():
            return 0.0
        # Heuristic: more sources = higher confidence
        source_count = len(findings)
        text_length = len(result_text)
        if source_count >= 5:
            return 0.9
        elif source_count >= 3:
            return 0.75
        elif source_count >= 1:
            return 0.6
        # No tool findings — base confidence on response quality
        elif text_length > 500:
            return 0.8
        elif text_length > 200:
            return 0.7
        elif text_length > 50:
            return 0.5
        return 0.3

    # ── Phase 3: Verification ───────────────────────────────

    async def _verify_and_extract(
        self,
        tasks: list[ResearchTask],
    ) -> list[EvidenceClaim]:
        """Extract claims with provenance from task findings.

        Each finding with a URL becomes an EvidenceClaim.
        Also extracts URLs from raw response text.
        """
        claims: list[EvidenceClaim] = []

        for task in tasks:
            if task.status != "completed":
                continue

            # Extract from structured findings
            for finding in task.findings:
                url = finding.get("url", finding.get("source_url", ""))
                if url:
                    claims.append(EvidenceClaim(
                        text=finding.get("content", finding.get("summary", ""))[:500],
                        source_url=url,
                        source_title=finding.get("title", "Unknown"),
                        relevance_score=0.7,
                    ))

            # Extract URLs from response text (LLM cites sources inline)
            if hasattr(task, 'response_text') and task.response_text:
                import re as _re
                urls = _re.findall(
                    r'https?://[^\s\)\]]+',
                    task.response_text,
                )
                for url in urls[:5]:  # max 5 urls per task
                    # Only add if not already present
                    if not any(c.source_url == url for c in claims):
                        claims.append(EvidenceClaim(
                            text=task.response_text[:200],
                            source_url=url,
                            source_title=url.split("/")[2] if "://" in url else url,
                            relevance_score=0.6,
                        ))

        return claims

    async def _filter_by_reputation(
        self,
        claims: list[EvidenceClaim],
    ) -> list[EvidenceClaim]:
        """Filter claims through source reputation service.

        Uses ai_workspace.sources.SourceReputationService if available.
        Falls back to returning all claims if service is unavailable.
        """
        try:
            from ai_workspace.sources import SourceReputationService

            svc = SourceReputationService()
            svc.initialize()

            urls = list(set(c.source_url for c in claims if c.source_url))
            if not urls:
                return claims

            trusted_list, ignored_list = svc.filter_sources(urls)
            ignored_urls = {i["url"] for i in ignored_list}
            trusted_urls = {t["url"] for t in trusted_list}

            # Mark verification status
            for claim in claims:
                if claim.source_url in ignored_urls:
                    claim.verification_status = "insufficient_evidence"
                    claim.relevance_score *= 0.5
                elif claim.source_url in trusted_urls:
                    claim.verification_status = "verified"

            # Log cross-reference if we have enough claims
            if trusted_list and len(trusted_list) >= 2:
                try:
                    claim_dicts = [
                        {
                            "claim": c.text[:200],
                            "sources_agreeing": [c.source_url],
                            "sources_disagreeing": [],
                        }
                        for c in claims
                        if c.verification_status == "verified"
                    ]
                    if claim_dicts:
                        svc.log_cross_reference(None, claim_dicts)
                except Exception as e:
                    logger.debug("Cross-reference logging skipped: %s", e)

            # Record source usage
            for url in urls:
                try:
                    svc.record_use(url)
                except Exception:
                    pass

            return claims
        except Exception as e:
            logger.debug("Source reputation filter unavailable: %s", e)
            return claims

    # ── Phase 4: Reflector ──────────────────────────────────

    async def _is_sufficient(
        self,
        claims: list[EvidenceClaim],
        query: str,
    ) -> bool:
        """Check if collected evidence is sufficient for synthesis.

        Criteria:
        - At least min_sources unique sources.
        - No detected contradictions that need resolution.
        """
        verified_claims = [
            c for c in claims
            if c.verification_status in ("verified", "unverified")
        ]
        unique_sources = len(set(
            c.source_url for c in verified_claims if c.source_url
        ))

        if unique_sources < self.min_sources:
            logger.debug(
                "Insufficient sources: %d < %d",
                unique_sources, self.min_sources,
            )
            return False

        # Check for contradictions (simplified)
        if self._detect_contradictions(claims):
            logger.debug("Contradictions detected — need more evidence")
            return False

        return True

    def _detect_contradictions(self, claims: list[EvidenceClaim]) -> bool:
        """Detect contradictions between claims (simplified heuristic).

        Production implementation would use LLM-as-judge to compare claims.
        """
        has_verified = any(
            c.verification_status == "verified" for c in claims
        )
        has_contradicted = any(
            c.verification_status == "contradicted" for c in claims
        )
        return has_verified and has_contradicted

    def _identify_gaps(
        self,
        claims: list[EvidenceClaim],
        query: str,
    ) -> list[ResearchTask]:
        """Identify research gaps and create gap-filling tasks.

        If evidence is insufficient, generates 2-3 additional tasks
        to fill the gaps.
        """
        # Simple gap detection: if we have fewer than min_sources,
        # create extra search tasks with different angles.
        verified_claims = [
            c for c in claims
            if c.verification_status in ("verified", "unverified")
        ]
        unique_sources = len(set(
            c.source_url for c in verified_claims if c.source_url
        ))

        if unique_sources >= self.min_sources:
            return []

        gap_tasks = []
        angles = [
            "from a practical, real-world perspective",
            "from a technical deep-dive angle",
            "from a comparative analysis angle",
            "with recent data and statistics from 2025-2026",
            "from an expert opinion and industry analysis perspective",
        ]

        for i, angle in enumerate(angles[:3]):
            gap_tasks.append(ResearchTask(
                id=f"gap-{i + 1}",
                question=f"{query} — {angle}",
                agent_type="web_search",  # use tools to find real sources
            ))

        return gap_tasks

    # ── Phase 5: Synthesizer ────────────────────────────────

    async def _synthesize(
        self,
        query: str,
        tasks: list[ResearchTask],
        claims: list[EvidenceClaim],
    ) -> ResearchReport:
        """Synthesize all findings into a final research report.

        Uses a direct AgentLoop call to generate a structured report.
        """
        # Build findings summary
        completed = [t for t in tasks if t.status == "completed"]
        findings_parts = []
        for t in completed:
            # Include the actual response text if available
            response = t.response_text.strip() if hasattr(t, 'response_text') else ""
            task_claims = [
                c for c in claims
                if c.source_url in [
                    f.get("url", f.get("source_url", ""))
                    for f in t.findings
                ]
            ]
            sources_str = "\n".join(
                f"  - [{c.source_title}]({c.source_url}): {c.text[:200]}"
                for c in task_claims[:5]
            ) if task_claims else "  (no explicit sources)"

            findings_parts.append(
                f"## Sub-question: {t.question}\n"
                f"Confidence: {t.confidence:.0%}\n"
                f"Answer: {response[:2000] if response else '(no response)'}\n"
                f"Sources:\n{sources_str}"
            )

        findings_text = "\n\n".join(findings_parts)

        prompt = f"""Synthesize these research findings into a comprehensive report.

Original research question: {query}

Research findings from {len(completed)} sub-questions:
{findings_text[:10000]}

Write a report with the following sections:

1. EXECUTIVE SUMMARY (2-3 sentences summarizing the conclusions)
2. KEY FINDINGS (5-10 bullet points, each citing specific sources with URLs)
3. DETAILED ANALYSIS (comprehensive discussion synthesizing all findings)
4. CONFIDENCE ASSESSMENT (how reliable is this report? note any gaps or limitations)
5. SOURCES (complete list of all sources consulted, as [title](url) format)

Important:
- Always cite sources inline using [Source: title](url) format.
- If data is uncertain or contradictory, note it explicitly.
- No fabricated data. If something is unknown, say so."""

        params = LoopParams(
            task=prompt,
            pattern=LoopPattern.DIRECT,
            model=self.model,
            provider=self.provider,
            stream=True,
            max_turns=2,
        )

        report_text = ""
        async for event in agent_loop(params):
            if event.type == "token":
                report_text += event.data.get("text", "")

        # Parse sections from the report text
        sections = self._parse_report_sections(report_text)

        # Extract all unique source URLs
        all_sources = list(set(
            c.source_url for c in claims if c.source_url
        ))

        # Compute overall confidence
        if completed:
            avg_confidence = sum(t.confidence for t in completed) / len(completed)
        else:
            avg_confidence = 0.3

        # Adjust by verification
        verified_count = sum(
            1 for c in claims if c.verification_status == "verified"
        )
        if verified_count > 0:
            avg_confidence = min(0.95, avg_confidence * 1.1)

        return ResearchReport(
            query=query,
            summary=self._extract_section(report_text, "EXECUTIVE SUMMARY", "")
                or report_text[:300],
            sections=sections,
            claims=claims,
            sources=all_sources,
            confidence=round(avg_confidence, 2),
        )

    @staticmethod
    def _parse_report_sections(text: str) -> list[dict[str, Any]]:
        """Extract sections from a markdown report."""
        sections = []
        current_title = "Report"
        current_content: list[str] = []

        for line in text.split("\n"):
            if line.startswith("## ") or line.startswith("# "):
                # Save previous section
                if current_content:
                    sections.append({
                        "title": current_title,
                        "content": "\n".join(current_content).strip(),
                    })
                current_title = line.lstrip("#").strip()
                current_content = []
            elif line.startswith("### "):
                if current_content:
                    sections.append({
                        "title": current_title,
                        "content": "\n".join(current_content).strip(),
                    })
                current_title = line.lstrip("#").strip()
                current_content = []
            else:
                current_content.append(line)

        # Last section
        if current_content:
            sections.append({
                "title": current_title,
                "content": "\n".join(current_content).strip(),
            })

        return sections

    @staticmethod
    def _extract_section(text: str, heading: str, default: str = "") -> str:
        """Extract the content of a markdown section by heading name."""
        pattern = rf"(?:^|\n)#{{1,3}}\s*{re.escape(heading)}\s*\n(.*?)(?=\n#{{1,3}}\s|\Z)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return default

    # ── Helpers ─────────────────────────────────────────────

    @staticmethod
    def _notify(
        progress: Callable | None,
        phase: ResearchPhase,
        detail: str,
    ) -> None:
        """Emit a progress event if the callback is set."""
        if progress:
            try:
                progress(phase.value, detail)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════
# Convenience function
# ═══════════════════════════════════════════════════════════

async def deep_research(
    query: str,
    *,
    model: str = "qwen3:14b",
    provider: str = "ollama",
    max_parallel: int = 5,
    max_depth: int = 3,
    max_tasks: int = 8,
    progress: Callable | None = None,
) -> ResearchReport:
    """Run a deep research query (convenience function).

    Args:
        query: Research question.
        model: LLM model name.
        provider: LLM provider.
        max_parallel: Max concurrent research tasks.
        max_depth: Max recursion depth.
        max_tasks: Max total sub-questions.
        progress: Optional callback(phase, detail).

    Returns:
        ResearchReport.
    """
    engine = ResearchEngine(
        model=model,
        provider=provider,
        max_parallel=max_parallel,
        max_depth=max_depth,
        max_tasks=max_tasks,
    )
    return await engine.research(query, progress=progress)
