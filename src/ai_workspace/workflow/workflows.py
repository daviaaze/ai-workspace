"""Concrete workflow definitions: deep research, daily briefing, learning."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

from ai_workspace.workflow.engine import BaseWorkflow, Context, step, workflow


class _LazyChat:
    """Lazily initialises a simple chat function on first access.

    Replaces the previous ``_LazyLLMs`` (which created CrewAI LLM instances)
    with a lightweight wrapper around ``chat_sync``.  The ``os.path.expanduser``
    + sops-nix fallback pattern is preserved for backward compat.

    Usage in step methods::

        result = self._model.chat(
            system="You are a helpful assistant.",
            user="What is the capital of France?",
        )
    """

    def __init__(self):
        self._initialized = False
        self._provider: str = ""
        self._model: str = ""

    def _ensure(self) -> None:
        if self._initialized:
            return

        # Prefer DeepSeek if API key is available
        from ai_workspace.user_config import PROVIDER_DEFAULTS
        ds_entry = PROVIDER_DEFAULTS.get("deepseek", {})

        env_key = os.environ.get(ds_entry.get("env_var", ""), "")
        if not env_key:
            try:
                sops_path = os.path.expanduser(
                    f"~/.local/share/sops-nix/secrets/{ds_entry.get('sops_file', '')}"
                )
                if os.path.exists(sops_path):
                    with open(sops_path) as f:
                        env_key = f.read().strip()
            except Exception:
                pass

        if env_key:
            self._provider = "deepseek"
            self._model = ds_entry.get("default_model", "deepseek-chat")
        else:
            # Fallback: Ollama
            self._provider = "ollama"
            self._model = os.environ.get("AIW_DEFAULT_MODEL", "qwen3:14b")

        self._initialized = True

    def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.7,
    ) -> str:
        """Single-turn chat via ``chat_sync``.

        Automatically picks DeepSeek (when key available) or Ollama fallback.
        """
        self._ensure()

        from ai_workspace.providers import chat_sync

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return chat_sync(
            messages,
            provider=self._provider,
            model=self._model,
            temperature=temperature,
        )


class _LazyTools:
    """Lazily creates agent tools on first access (no crewAI needed)."""

    def __init__(self):
        self._tools: list | None = None

    def _ensure(self) -> list:
        if self._tools is not None:
            return self._tools

        from ai_workspace.tools.marketplace import MercadoLivreSearchTool, OLXSearchTool
        from ai_workspace.tools.web_fetch import WebFetchTool

        self._tools = [
            WebFetchTool(),
            MercadoLivreSearchTool(),
            OLXSearchTool(),
        ]
        return self._tools

    def get(self) -> list:
        return list(self._ensure())


# ═══════════════════════════════════════════════════════════
# Deep Research Workflow
# ═══════════════════════════════════════════════════════════


@workflow
class DeepResearchWorkflow(BaseWorkflow):
    """Multi-step deep research: plan → parallel research for multiple sub-questions → synthesise."""

    def __init__(self, db_url: str | None = None):
        super().__init__(db_url)
        self._model = _LazyChat()
        self._tools = _LazyTools()

    @step()
    async def step_plan(self, ctx: Context) -> list[str]:
        """Break the query into specific sub-questions."""
        query = ctx.inputs["query"]

        system_prompt = (
            "You are a Research Planner. Break down research questions "
            "into specific sub-questions. Return as a JSON list of strings."
        )

        user_prompt = (
            f"Research query: {query}\n\n"
            f"Generate 3-5 specific, actionable sub-questions. "
            f"Each sub-question must be specific and directly answerable "
            f"by fetching a URL or searching a marketplace. "
            f"Return as a JSON list of strings."
        )

        result = self._model.chat(system=system_prompt, user=user_prompt)

        try:
            questions = json.loads(str(result))
            if isinstance(questions, dict):
                questions = questions.get("questions", [])
        except (json.JSONDecodeError, TypeError):
            questions = [q.strip().lstrip("0123456789.- ") for q in str(result).split("\n") if q.strip()]

        # Filter to valid questions
        questions = [q for q in questions if isinstance(q, str) and len(q) > 10]
        if not questions:
            questions = [query]

        self.set_inputs(ctx, {"sub_questions": questions})
        return questions

    @step(depends_on=["step_plan"])
    async def step_research_q1(self, ctx: Context) -> dict:
        return await self._research_single_question(ctx, 0)

    @step(depends_on=["step_plan"])
    async def step_research_q2(self, ctx: Context) -> dict:
        return await self._research_single_question(ctx, 1)

    @step(depends_on=["step_plan"])
    async def step_research_q3(self, ctx: Context) -> dict:
        return await self._research_single_question(ctx, 2)

    @step(depends_on=["step_plan"])
    async def step_research_q4(self, ctx: Context) -> dict:
        return await self._research_single_question(ctx, 3)

    @step(depends_on=["step_plan"])
    async def step_research_q5(self, ctx: Context) -> dict:
        return await self._research_single_question(ctx, 4)

    async def _research_single_question(self, ctx: Context, idx: int) -> dict:
        """Perform a single sub-question research using tools."""
        questions: list[str] = ctx.inputs.get("sub_questions", [])
        if idx >= len(questions):
            return {}

        q = questions[idx]

        system_prompt = (
            "You are a thorough web researcher. Use the tools available to you "
            "(web_fetch, mercadolibre_search, olx_search) to gather real data. "
            "Return a JSON dict with keys: 'findings', 'sources', 'confidence'."
        )

        user_prompt = f"Research question: {q}"

        result = self._model.chat(system=system_prompt, user=user_prompt)

        try:
            data = json.loads(str(result))
        except (json.JSONDecodeError, TypeError):
            data = {"findings": str(result)[:500], "sources": [], "confidence": "low"}

        return data

    @step(depends_on=["step_research_q1", "step_research_q2", "step_research_q3"])
    async def step_synthesise(self, ctx: Context) -> str:
        """Combine all research findings into a single report."""
        results = {}
        for key in ["step_research_q1", "step_research_q2", "step_research_q3",
                     "step_research_q4", "step_research_q5"]:
            if key in ctx.inputs:
                results[key] = ctx.inputs[key]

        system_prompt = "You are a report writer. Synthesise research findings."
        user_prompt = (
            "Synthesise the following research results into a coherent report. "
            f"Results:\n{json.dumps(results, indent=2, ensure_ascii=False)}"
        )

        return self._model.chat(system=system_prompt, user=user_prompt)


# ═══════════════════════════════════════════════════════════
# Tutorial workflows (replaced Crew calls with chat_sync)
# ═══════════════════════════════════════════════════════════

# Each workflow below had its ``from crewai import Agent, Crew, Task`` +
# ``Crew(...).kickoff()`` replaced by ``self._model.chat()`` — same
# system/user message split, same LLM fallback logic, no crewAI dep.


@workflow
class DeepResearchPipeline(BaseWorkflow):
    """Original deep research with planning, execution, report writing.

    This is the canonical pipeline matching ``DeepSearchEngine``.
    """

    def __init__(self, db_url: str | None = None):
        super().__init__(db_url)
        self._model = _LazyChat()

    @step()
    async def step_plan(self, ctx: Context) -> list[str]:
        query = ctx.inputs["query"]

        system_prompt = (
            "You are a Research Planner. Break down research questions into "
            "sub-questions. Return as JSON list of strings."
        )
        user_prompt = (
            f"Research query: {query}\n\n"
            f"Generate 3-5 specific, actionable sub-questions. "
            f"Return as a JSON list of strings."
        )

        result = self._model.chat(system=system_prompt, user=user_prompt)

        try:
            questions = json.loads(str(result))
        except (json.JSONDecodeError, TypeError):
            questions = [q.strip() for q in str(result).split("\n") if q.strip()[:2].isdigit()]
        questions = [q for q in questions if isinstance(q, str) and len(q) > 10]
        if not questions:
            questions = [query]
        self.set_inputs(ctx, {"sub_questions": questions})
        return questions

    @step(depends_on=["step_plan"])
    async def step_research(self, ctx: Context) -> dict:
        """Researcher step — replaced Agent+Task with chat_sync."""
        questions: list[str] = ctx.inputs.get("sub_questions", [])
        query = ctx.inputs.get("query", "")
        if not query:
            return {}

        system_prompt = (
            "You are a thorough researcher. Search and gather real data. "
            "Return JSON with keys: 'findings', 'sources', 'confidence'."
        )
        user_prompt = (
            f"Query: {query}\n"
            f"Sub-questions: {json.dumps(questions, ensure_ascii=False)}\n"
            "Research each sub-question carefully."
        )

        result = self._model.chat(system=system_prompt, user=user_prompt)

        try:
            data = json.loads(str(result))
        except (json.JSONDecodeError, TypeError):
            data = {"findings": str(result)[:500], "sources": [], "confidence": "low"}
        return data

    @step(depends_on=["step_research"])
    async def step_synthesise(self, ctx: Context) -> str:
        results = ctx.inputs.get("step_research", {})

        system_prompt = "You are a report writer. Synthesise findings."
        user_prompt = (
            "Write a clear, structured report from these findings.\n"
            f"Findings:\n{json.dumps(results, indent=2, ensure_ascii=False)}"
        )

        return self._model.chat(system=system_prompt, user=user_prompt)


@workflow
class TutorialWorkflow(BaseWorkflow):
    """Tutorial workflow — replaced Crew calls with chat_sync."""

    def __init__(self, db_url: str | None = None):
        super().__init__(db_url)
        self._model = _LazyChat()

    @step()
    async def step_research(self, ctx: Context) -> dict:
        query = ctx.inputs.get("query", "")

        system_prompt = (
            "You are a technical researcher. Find relevant information. "
            "Return JSON with keys: 'findings', 'sources', 'confidence'."
        )
        user_prompt = f"Research query: {query}"

        result = self._model.chat(system=system_prompt, user=user_prompt)

        try:
            data = json.loads(str(result))
        except (json.JSONDecodeError, TypeError):
            data = {"findings": str(result)[:500], "sources": [], "confidence": "low"}
        return data

    @step(depends_on=["step_research"])
    async def step_write(self, ctx: Context) -> str:
        research = ctx.inputs.get("step_research", {})

        system_prompt = "You are a technical writer. Write clear tutorials."
        user_prompt = (
            f"Write a tutorial based on these findings.\n"
            f"Findings:\n{json.dumps(research, indent=2, ensure_ascii=False)}"
        )

        return self._model.chat(system=system_prompt, user=user_prompt)

    @step(depends_on=["step_write"])
    async def step_format(self, ctx: Context) -> str:
        tutorial = ctx.inputs.get("step_write", "")

        system_prompt = "You are a documentation specialist."
        user_prompt = (
            f"Format this tutorial with proper markdown structure.\n"
            f"Tutorial:\n{tutorial}"
        )

        return self._model.chat(system=system_prompt, user=user_prompt)


@workflow
class CodeReviewWorkflow(BaseWorkflow):
    """Code review workflow — replaced Crew calls with chat_sync."""

    def __init__(self, db_url: str | None = None):
        super().__init__(db_url)
        self._model = _LazyChat()

    @step()
    async def step_analyze(self, ctx: Context) -> dict:
        code = ctx.inputs.get("code", "")

        system_prompt = (
            "You are a senior code reviewer. Analyse code for bugs, "
            "security issues, and improvements. Return JSON with keys: "
            "'issues', 'suggestions', 'security_concerns'."
        )
        user_prompt = f"Review this code:\n\n```\n{code}\n```"

        result = self._model.chat(system=system_prompt, user=user_prompt)

        try:
            data = json.loads(str(result))
        except (json.JSONDecodeError, TypeError):
            data = {"issues": [], "suggestions": [], "security_concerns": []}
        return data

    @step(depends_on=["step_analyze"])
    async def step_report(self, ctx: Context) -> str:
        analysis = ctx.inputs.get("step_analyze", {})

        system_prompt = "You are a code review report writer."
        user_prompt = (
            f"Write a review report.\n"
            f"Analysis:\n{json.dumps(analysis, indent=2, ensure_ascii=False)}"
        )

        return self._model.chat(system=system_prompt, user=user_prompt)


@workflow
class DailyBriefingWorkflow(BaseWorkflow):
    """Daily briefing — replaced Crew calls with chat_sync."""

    def __init__(self, db_url: str | None = None):
        super().__init__(db_url)
        self._model = _LazyChat()

    @step()
    async def step_analyze(self, ctx: Context) -> dict:
        data = ctx.inputs.get("data", "No data available.")

        system_prompt = (
            "You are a data analyst. Analyse daily data and summarise. "
            "Return JSON with keys: 'key_points', 'insights', 'trends'."
        )
        user_prompt = f"Daily data to analyse:\n{str(data)[:5000]}"

        result = self._model.chat(system=system_prompt, user=user_prompt)

        try:
            parsed = json.loads(str(result))
        except (json.JSONDecodeError, TypeError):
            parsed = {"key_points": str(result)[:500], "insights": [], "trends": []}
        return parsed

    @step(depends_on=["step_analyze"])
    async def step_format(self, ctx: Context) -> str:
        analysis = ctx.inputs.get("step_analyze", {})

        system_prompt = "You are a briefing writer."
        user_prompt = (
            f"Write a structured daily briefing.\n"
            f"Analysis:\n{json.dumps(analysis, indent=2, ensure_ascii=False)}"
        )

        return self._model.chat(system=system_prompt, user=user_prompt)


@workflow
class ContinuousLearningWorkflow(BaseWorkflow):
    """Extract patterns and insights from historical research.

    Steps:
    1. step_extract    — Gather research history
    2. step_analyze    — Find patterns with agent
    3. step_remember   — Store as agent memory
    """

    name = "continuous_learning"

    def __init__(self, db_url: str | None = None):
        super().__init__(db_url)
        self._model = _LazyChat()

    @step()
    async def step_extract(self, ctx: Context) -> list[dict]:
        """Extract research history for analysis."""
        if not ctx.store:
            ctx.store.initialize()

        history = ctx.store.get_research_history(limit=50)

        data = [
            {"query": r["query"], "summary": r.get("summary", "")[:300]}
            for r in history
            if r.get("summary") and len(r.get("summary", "")) > 20
        ]

        ctx.log.info(f"Extracted {len(data)} research items for learning")
        return data

    @step(depends_on=["step_extract"])
    async def step_analyze(self, ctx: Context) -> str:
        """Analyze history for patterns."""
        history = ctx.get("step_extract", [])

        if not history:
            ctx.log.info("No research history to analyze")
            return "No research data available for analysis."

        summaries = "\n".join(
            f"- [{h['query']}] {h['summary']}"
            for h in history[:30]
        )

        system_prompt = (
            "You are a Pattern Analyst. Extract lasting insights and patterns "
            "from research history. Separate signal from noise. "
            "Return a numbered list of 5-10 key insights, one sentence each."
        )
        user_prompt = (
            f"Analyze this research history and extract lasting insights:\n\n"
            f"{summaries}\n\n"
            f"Return 5-10 key insights. Each should be one sentence and genuinely "
            f"useful for future reference. Focus on patterns, trends, and "
            f"actionable knowledge."
        )

        result = self._model.chat(system=system_prompt, user=user_prompt)
        ctx.log.info("Generated insights")
        return result

    @step(depends_on=["step_analyze"])
    async def step_remember(self, ctx: Context) -> dict[str, Any]:
        """Store insights as agent memory."""
        insights = ctx.get("step_analyze", "")
        history_len = len(ctx.get("step_extract", []))

        if not ctx.store or not insights:
            return {"remembered": False}

        ctx.store.initialize()

        ctx.store.remember(
            agent_name="continuous-learner",
            content=insights,
            memory_type="learning",
            importance=0.8,
            metadata={
                "source": "continuous_learning_workflow",
                "history_size": history_len,
                "generated_at": datetime.now(UTC).isoformat(),
            },
        )

        ctx.log.info("Stored insights as agent memory")
        return {"remembered": True, "insights_count": insights.count("\n") + 1}


@workflow
class LearnWorkflow(BaseWorkflow):
    """Classify an observation and persist it to memory.

    Mirrors the pi coding agent `/learn` skill:
    - Observations are classified into conventions, patterns, or learnings
      using keyword-based heuristics (no LLM overhead)
    - Written to markdown files in the workspace memory/ directory
    - Optionally stored in PostgreSQL knowledge base for semantic search

    Steps:
    1. step_classify        — Heuristic classification (always available)
    2. step_persist_markdown — Write to the appropriate markdown file
    3. step_store           — Store in PostgreSQL knowledge base (optional)
    """

    name = "learn"

    @step()
    async def step_classify(self, ctx: Context) -> dict[str, Any]:
        """Classify the observation using keyword heuristics."""
        observation = ctx.inputs.get("observation", "")
        if not observation:
            ctx.log.warning("No observation provided")
            return {"category": "learning", "title": "Untitled", "tags": []}

        lower = observation.lower()

        if any(kw in lower for kw in ["always", "never", "must", "rule", "standard", "convention"]):
            category = "convention"
        elif any(kw in lower for kw in ["workflow", "process", "when", "step", "pattern"]):
            category = "pattern"
        else:
            category = "learning"

        tags = []
        tag_map = {
            "git": ["git", "commit", "branch", "push", "merge", "pr"],
            "nix": ["nix", "nixos", "flake", "home-manager"],
            "python": ["python", "pip", "pyproject", "pytest", "ruff"],
            "debug": ["debug", "bug", "fix", "error", "crash", "failed"],
            "code-review": ["review", "code review", "refactor"],
            "testing": ["test", "testing", "ci", "assert"],
            "infra": ["infra", "deploy", "docker", "database", "postgres"],
            "learning": ["learned", "discovered", "found", "realized"],
        }
        for tag, keywords in tag_map.items():
            if any(kw in lower for kw in keywords):
                tags.append(tag)

        first_line = observation.split("\n")[0].strip().rstrip(".")
        title = first_line[:80] if len(first_line) > 80 else first_line

        ctx.log.info(f"Classified as {category}")
        return {"category": category, "title": title, "tags": tags}

    @step(depends_on=["step_classify"])
    async def step_persist_markdown(self, ctx: Context) -> dict[str, Any]:
        """Write the learning to the appropriate markdown memory file."""
        classification = ctx.get("step_classify", {"category": "learning"})
        observation = ctx.inputs.get("observation", "")
        category = classification.get("category", "learning")
        title = classification.get("title", "Untitled")
        tags = classification.get("tags", [])

        if not observation:
            return {"written": False, "reason": "empty observation"}

        store = ctx.store
        if store:
            store.initialize()

        filepath = None
        if store:
            filepath = store.append_memory_markdown(category, {
                "title": title,
                "content": observation,
                "tags": tags,
            })

        ctx.log.info(f"Persisted to markdown: {category}")
        return {
            "written": filepath is not None,
            "category": category,
            "title": title,
            "file": str(filepath) if filepath else None,
            "tags": tags,
        }

    @step(depends_on=["step_persist_markdown"])
    async def step_store(self, ctx: Context) -> dict[str, Any]:
        """Store in PostgreSQL knowledge base for semantic search."""
        observation = ctx.inputs.get("observation", "")
        classification = ctx.get("step_classify", {"category": "learning", "title": "Untitled"})
        if not observation:
            return {"stored": False}

        store = ctx.store
        if store:
            store.initialize()
            memory_id = store.remember(
                agent_name="learn-workflow",
                content=f"{classification.get('title', '')}: {observation}",
                memory_type="learning",
                tags=classification.get("tags", []),
                metadata={
                    "source": "learn_workflow",
                    "category": classification.get("category", "learning"),
                },
            )
            ctx.log.info(f"Stored in knowledge base: {memory_id}")
            return {"stored": True, "memory_id": memory_id}

        return {"stored": False, "reason": "no store available"}
