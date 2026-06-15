"""
Concrete workflow definitions for AI Workspace.

Workflows:
- DeepResearchWorkflow:     plan → parallel research → synthesize → store
- DailyBriefingWorkflow:   sync obsidian → compile briefing → store
- ContinuousLearningWorkflow: extract → analyze → remember
- LearnWorkflow:           classify → persist_markdown → store

All agents use Ollama (local) or DeepSeek API — never default to GPT-4.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from ai_workspace.workflow.engine import BaseWorkflow, Context, workflow


# ════════════════════════════════════════════════════════════
# Lazy LLM factory — crewai imports numpy which needs libstdc++ on NixOS.
# We defer creation until a step method actually runs (in the worker process
# which has LD_LIBRARY_PATH set) to avoid crashes in the CLI process.
# ════════════════════════════════════════════════════════════

class _LazyLLMs:
    """Lazily creates CrewAI LLM instances on first access.
    
    This avoids importing crewai (→ numpy → libstdc++.so.6) until
    a step method actually runs, which happens inside the worker
    daemon where LD_LIBRARY_PATH is properly configured.
    """

    def __init__(self):
        self._llms: dict[str, Any] | None = None

    def _ensure(self) -> dict[str, Any]:
        if self._llms is not None:
            return self._llms

        # This is where crewai gets imported — only when steps actually execute
        from crewai import LLM

        # Prefer DeepSeek if API key is available
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not deepseek_key:
            try:
                deepseek_key = open(os.path.expanduser("~/.local/share/sops-nix/secrets/deepseek_api_key")).read().strip()
            except Exception:
                pass

        if deepseek_key:
            self._llms = {
                "fast": LLM(
                    model="deepseek-chat",
                    base_url="https://api.deepseek.com/v1",
                    api_key=deepseek_key,
                ),
                "deep": LLM(
                    model="deepseek-reasoner",
                    base_url="https://api.deepseek.com/v1",
                    api_key=deepseek_key,
                ),
                "name": "deepseek",
            }
            return self._llms

        # Fallback: Ollama
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        fast_model = os.environ.get("AIW_DEFAULT_MODEL", "qwen3:14b")
        deep_model = os.environ.get("AIW_DEEP_MODEL", "deepseek-r1:14b")
        self._llms = {
            "fast": LLM(model=fast_model, base_url=f"{host}/v1", api_key="ollama"),
            "deep": LLM(model=deep_model, base_url=f"{host}/v1", api_key="ollama"),
            "name": "ollama",
        }
        return self._llms

    def __getitem__(self, key: str) -> Any:
        return self._ensure()[key]

    def __contains__(self, key: str) -> bool:
        return key in self._ensure()


class _LazyTools:
    """Lazily creates web search/scraping tools for research agents.

    Same lazy pattern as _LazyLLMs — avoids importing crewai.tools
    (→ numpy → libstdc++.so.6) until a step actually executes.
    """

    def __init__(self):
        self._tools: list[Any] | None = None

    def _ensure(self) -> list[Any]:
        if self._tools is not None:
            return self._tools

        from ai_workspace.tools import WebFetchTool, MercadoLivreSearchTool, OLXSearchTool, HeadlessBrowserTool, PaginatedScraperTool

        self._tools = [
            WebFetchTool(),
            HeadlessBrowserTool(),
            PaginatedScraperTool(),
            MercadoLivreSearchTool(),
            OLXSearchTool(),
        ]
        return self._tools

    def get(self) -> list[Any]:
        return self._ensure()


# ════════════════════════════════════════════════════════════
# Deep Research Workflow
# ════════════════════════════════════════════════════════════

@workflow
class DeepResearchWorkflow(BaseWorkflow):
    """Deep recursive research with parallel sub-question answering.
    
    Steps:
    1. step_plan            — Break query into sub-questions
    2. step_research_q1..N  — Answer each in parallel (auto-parallel)
    3. step_synthesize      — Combine into report
    4. step_store           — Persist to knowledge base
    """
    
    name = "deep_research"
    
    def __init__(self, db_url: str | None = None):
        super().__init__(db_url)
        self._llms = _LazyLLMs()
        self._tools = _LazyTools()
    
    async def step_plan(self, ctx: Context) -> list[str]:
        """Break the query into specific sub-questions."""
        query = ctx.inputs["query"]
        depth = ctx.inputs.get("depth", 2)
        
        from crewai import Agent, Crew, Task
    
        planner = Agent(
            role="Research Planner",
            goal="Break down research questions into specific sub-questions",
            backstory="Expert at decomposing complex queries into answerable parts.",
            llm=self._llms["fast"],
            verbose=False,
        )
        
        task = Task(
            description=(
                f"Research query: {query}\n\n"
                f"Generate 3-5 specific, actionable sub-questions. "
                f"The researcher has tools to fetch web pages (web_fetch) "
                f"and search Mercado Livre (mercado_livre_search) "
                f"and OLX (olx_search) for prices.\n\n"
                f"Each sub-question must be specific and directly answerable "
                f"by fetching a URL or searching a marketplace. "
                f"For example: 'Search Mercado Livre for the price of item X' "
                f"or 'Fetch the page at URL Y and list the items found'.\n\n"
                f"DO NOT generate meta questions about methodology. "
                f"Generate questions that USE the tools to get real data.\n\n"
                f"Return as a JSON list of strings."
            ),
            expected_output='["question 1", "question 2", ...]',
            agent=planner,
        )
        
        crew = Crew(agents=[planner], tasks=[task], verbose=False)
        result = crew.kickoff()
        
        try:
            questions = json.loads(str(result))
            if isinstance(questions, dict):
                questions = questions.get("questions", [])
        except (json.JSONDecodeError, TypeError):
            questions = [q.strip().lstrip("0123456789.- ") for q in str(result).split("\n") if q.strip()]
        
        ctx.log.info(f"Generated {len(questions)} sub-questions", questions=questions)
        return questions
    
    async def step_research_q1(self, ctx: Context) -> dict:
        """Answer sub-question 1."""
        return await self._research_answer(ctx, 0)
    
    async def step_research_q2(self, ctx: Context) -> dict:
        """Answer sub-question 2."""
        return await self._research_answer(ctx, 1)
    
    async def step_research_q3(self, ctx: Context) -> dict:
        """Answer sub-question 3."""
        return await self._research_answer(ctx, 2)
    
    async def step_research_q4(self, ctx: Context) -> dict:
        """Answer sub-question 4."""
        return await self._research_answer(ctx, 3)
    
    async def step_research_q5(self, ctx: Context) -> dict:
        """Answer sub-question 5."""
        return await self._research_answer(ctx, 4)
    
    async def _research_answer(self, ctx: Context, idx: int) -> dict:
        """Answer a specific sub-question."""
        questions = ctx.get("step_plan", [])
        
        if idx >= len(questions):
            return {"question": "", "answer": "N/A", "skipped": True}
        
        question = questions[idx]
        
        from crewai import Agent, Crew, Task
        
        researcher = Agent(
            role="Research Analyst",
            goal="Provide thorough, accurate answers. Use web_fetch for static pages, headless_browser for SPA/JavaScript sites (Receita Federal, gov.br), and mercado_livre_search/olx_search for prices.",
            backstory=(
                "Diligent analyst. CRITICAL RULE: Never invent data. "
                "If a tool returns an error, empty result, or SPA shell HTML, "
                "report the failure honestly. NEVER make up prices, items, "
                "or API URLs. If you cannot get real data, say so explicitly.\n"
                "IMPORTANT: if web_fetch returns 'SPA PAGE' or 'Carregando', "
                "use headless_browser which runs a real Chromium browser."
            ),
            llm=self._llms["deep"],
            tools=self._tools.get(),
            verbose=False,
        )
        
        task = Task(
            description=(
                f"Question: {question}\n\n"
                f"Context: {ctx.inputs.get('query', '')}\n\n"
                f"Tools available:\n"
                f"- web_fetch: reads static pages and APIs\n"
                f"- headless_browser: opens SPA/JavaScript pages in a real Chromium browser\n"
                f"  (use this for Receita Federal, gov.br, or any 'Carregando...' page)\n"
                f"- paginated_scraper: scrapes multi-page tables by clicking 'next page'\n"
                f"  (use this for lists spanning multiple pages, like editais with 259 lots)\n"
                f"- mercado_livre_search: searches Mercado Livre prices\n"
                f"- olx_search: searches OLX prices\n\n"
                f"CRITICAL RULES:\n"
                f"1. ALWAYS use the tools — never answer from training data\n"
                f"2. If web_fetch fails on a SPA, use headless_browser\n"
                f"3. For multi-page lists, use paginated_scraper with max_pages\n"
                f"4. If a tool returns an error or empty result, "
                f"   report EXACTLY what happened. DO NOT invent data.\n"
                f"5. Never fabricate prices, item names, or API URLs.\n"
                f"6. If you cannot get real data, your answer must say so clearly.\n\n"
                f"Provide a comprehensive answer. Format as JSON:\n"
                f'{{"question": "{question}", "answer": "...", "confidence": 0.8, "sources": ["..."]}}'
            ),
            expected_output="JSON object with question, answer, confidence, sources",
            agent=researcher,
        )
        
        crew = Crew(agents=[researcher], tasks=[task], verbose=False)
        result = crew.kickoff()
        
        try:
            answer = json.loads(str(result))
        except (json.JSONDecodeError, TypeError):
            answer = {"question": question, "answer": str(result), "confidence": 0.5}
        
        ctx.log.info(f"Answered question {idx+1}", confidence=answer.get("confidence", 0))
        return answer
    
    async def step_synthesize(self, ctx: Context) -> dict[str, Any]:
        """Combine all research answers into a final report."""
        query = ctx.inputs["query"]
        
        # Collect all research answers
        answers = []
        for step_name in ["step_research_q1", "step_research_q2", "step_research_q3", "step_research_q4", "step_research_q5"]:
            ans = ctx.get(step_name)
            if ans and not ans.get("skipped"):
                answers.append(ans)
        
        if not answers:
            ctx.log.warning("No research answers to synthesize")
            return {"summary": "No research results", "report": ""}
        
        from crewai import Agent, Crew, Task
        
        writer = Agent(
            role="Research Synthesizer",
            goal="Create comprehensive, well-structured research reports",
            backstory="Skilled writer who weaves findings into clear narratives.",
            llm=self._llms["fast"],
            verbose=False,
        )
        
        findings = "\n\n".join(
            f"Q: {a.get('question', '')}\nA: {a.get('answer', '')[:500]}\nConfidence: {a.get('confidence', 0)}"
            for a in answers
        )
        
        task = Task(
            description=(
                f"Research question: {query}\n\n"
                f"Findings:\n{findings}\n\n"
                f"Synthesize into a report with:\n"
                f"1. Executive summary (2-3 sentences)\n"
                f"2. Key findings (bullet points)\n"
                f"3. Detailed analysis\n"
                f"4. Confidence assessment\n\n"
                f"Return as JSON: {{summary, key_findings, detailed_analysis, confidence, sources}}"
            ),
            expected_output="JSON report object",
            agent=writer,
        )
        
        crew = Crew(agents=[writer], tasks=[task], verbose=False)
        result = crew.kickoff()
        
        try:
            report = json.loads(str(result))
        except (json.JSONDecodeError, TypeError):
            report = {"summary": str(result)[:500], "report": str(result)}
        
        ctx.log.info(f"Report synthesized", confidence=report.get("confidence", 0))
        return report
    
    async def step_store(self, ctx: Context) -> dict[str, Any]:
        """Persist results to knowledge base."""
        query = ctx.inputs["query"]
        report = ctx.get("step_synthesize", {})
        plan = ctx.get("step_plan", [])
        
        if not ctx.store:
            ctx.log.warning("No store available, skipping persistence")
            return {"stored": False}
        
        ctx.store.initialize()
        
        # Save research
        ctx.store.save_research(query, {
            "summary": report.get("summary", ""),
            "detailed_report": report.get("detailed_analysis", json.dumps(report)),
            "sources": report.get("sources", []),
            "confidence": report.get("confidence", 0),
            "sub_questions": plan,
        })
        
        # Also add as knowledge entry
        ctx.store.add_knowledge(
            content=json.dumps(report, indent=2),
            content_type="research",
            title=f"Research: {query[:100]}",
            tags=["research", "auto-generated"],
        )
        
        ctx.log.info(f"Stored research results")
        return {"stored": True, "query": query}


# ════════════════════════════════════════════════════════════
# Daily Briefing Workflow
# ════════════════════════════════════════════════════════════

@workflow
class DailyBriefingWorkflow(BaseWorkflow):
    """Generate a daily briefing from recent activity.
    
    Steps:
    1. step_collect   — Gather data from all sources
    2. step_generate  — Generate briefing with agent
    3. step_store     — Persist briefing
    """
    
    name = "daily_briefing"
    
    def __init__(self, db_url: str | None = None):
        super().__init__(db_url)
        self._llms = _LazyLLMs()
    
    async def step_collect(self, ctx: Context) -> dict[str, Any]:
        """Collect recent activity from knowledge base."""
        if not ctx.store:
            ctx.store.initialize()
        
        # Recent research
        research = ctx.store.get_research_history(limit=10)
        
        # Pending tasks
        tasks = ctx.store.get_tasks(status="pending", limit=15)
        
        # Recent memories
        memories = ctx.store.recall("continuous-learner", "%", memory_type="learning", limit=5)
        
        # Knowledge entries (last 24h)
        c = ctx.store.conn.cursor()
        c.execute(
            "SELECT COUNT(*) FROM knowledge_entries WHERE created_at > NOW() - INTERVAL '24 hours'"
        )
        kb_24h = c.fetchone()[0]
        c.close()
        
        data = {
            "research_count": len(research),
            "recent_research": [
                {"query": r.get("query", "?"), "summary": r.get("summary", "")[:200]}
                for r in research[:5] if r.get("summary")
            ],
            "pending_tasks": len(tasks),
            "urgent_tasks": [
                t.get("title", "?") for t in tasks if t.get("priority", 0) >= 7
            ],
            "memories_count": len(memories),
            "knowledge_added_24h": kb_24h,
        }
        
        ctx.log.info(f"Collected activity data", data=data)
        return data
    
    async def step_generate(self, ctx: Context) -> str:
        """Generate the briefing using collected data."""
        data = ctx.get("step_collect", {})
        
        from crewai import Agent, Crew, Task
        
        analyst = Agent(
            role="Daily Briefing Analyst",
            goal="Create concise, actionable daily briefings",
            backstory="Expert at synthesizing activity into clear priorities.",
            llm=self._llms["fast"],
            verbose=False,
        )
        
        research_text = "\n".join(
            f"- {r.get('query', '?')}: {r.get('summary', '')[:100]}"
            for r in data.get("recent_research", [])
        )
        
        urgent_text = "\n".join(f"- {t}" for t in data.get("urgent_tasks", []))
        
        task = Task(
            description=(
                f"Create a daily briefing from:\n\n"
                f"## Activity\n"
                f"- Research: {data.get('research_count', 0)} items\n"
                f"- Pending tasks: {data.get('pending_tasks', 0)}\n"
                f"- Knowledge added (24h): {data.get('knowledge_added_24h', 0)}\n"
                f"- Agent memories: {data.get('memories_count', 0)}\n\n"
                f"## Recent Research\n{research_text}\n\n"
                f"## Urgent Tasks\n{urgent_text}\n\n"
                f"Structure:\n"
                f"### 📋 Top Priorities Today\n"
                f"### 🔍 Research Updates\n"
                f"### 💡 Insights\n"
                f"### ⏰ Schedule\n"
                f"### 🎯 Recommendations"
            ),
            expected_output="Markdown daily briefing",
            agent=analyst,
        )
        
        crew = Crew(agents=[analyst], tasks=[task], verbose=False)
        result = crew.kickoff()
        
        briefing = str(result)
        ctx.log.info(f"Briefing generated ({len(briefing)} chars)")
        return briefing
    
    async def step_store(self, ctx: Context) -> dict[str, Any]:
        """Save the briefing to knowledge base."""
        briefing = ctx.get("step_generate", "")
        data = ctx.get("step_collect", {})
        
        if not ctx.store or not briefing:
            return {"stored": False}
        
        ctx.store.initialize()
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ctx.store.add_knowledge(
            content=briefing,
            content_type="briefing",
            title=f"Daily Briefing — {today}",
            tags=["daily", "briefing", "auto-generated"],
            metadata={"date": today, "stats": data},
        )
        
        ctx.log.info("Briefing saved to knowledge base")
        return {"stored": True, "date": today}


# ════════════════════════════════════════════════════════════
# Continuous Learning Workflow
# ════════════════════════════════════════════════════════════

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
        self._llms = _LazyLLMs()
    
    async def step_extract(self, ctx: Context) -> list[dict]:
        """Extract research history for analysis."""
        if not ctx.store:
            ctx.store.initialize()
        
        history = ctx.store.get_research_history(limit=50)
        
        # Filter to those with meaningful summaries
        data = [
            {"query": r["query"], "summary": r.get("summary", "")[:300]}
            for r in history
            if r.get("summary") and len(r.get("summary", "")) > 20
        ]
        
        ctx.log.info(f"Extracted {len(data)} research items for learning")
        return data
    
    async def step_analyze(self, ctx: Context) -> str:
        """Analyze history for patterns."""
        history = ctx.get("step_extract", [])
        
        if not history:
            ctx.log.info("No research history to analyze")
            return "No research data available for analysis."
        
        from crewai import Agent, Crew, Task
        
        analyst = Agent(
            role="Pattern Analyst",
            goal="Extract lasting insights and patterns from research history",
            backstory=(
                "You find recurring themes, trends, and durable knowledge "
                "that remains valuable over time. You separate signal from noise."
            ),
            llm=self._llms["fast"],
            verbose=False,
        )
        
        summaries = "\n".join(
            f"- [{h['query']}] {h['summary']}"
            for h in history[:30]
        )
        
        task = Task(
            description=(
                f"Analyze this research history and extract lasting insights:\n\n"
                f"{summaries}\n\n"
                f"Return 5-10 key insights. Each should be one sentence and genuinely "
                f"useful for future reference. Focus on patterns, trends, and "
                f"actionable knowledge. Avoid generic statements."
            ),
            expected_output="Numbered list of insights",
            agent=analyst,
        )
        
        crew = Crew(agents=[analyst], tasks=[task], verbose=False)
        result = crew.kickoff()
        
        insights = str(result)
        ctx.log.info(f"Generated {insights.count(chr(10)) + 1} insights")
        return insights
    
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
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        
        ctx.log.info(f"Stored {insights.count(chr(10)) + 1} insights as agent memory")
        return {"remembered": True, "insights_count": insights.count("\n") + 1}


# ════════════════════════════════════════════════════════════
# Learn Workflow — persist knowledge from observations
# ════════════════════════════════════════════════════════════

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

    async def step_classify(self, ctx: Context) -> dict[str, Any]:
        """Classify the observation using keyword heuristics."""
        observation = ctx.inputs.get("observation", "")
        if not observation:
            ctx.log.warning("No observation provided")
            return {"category": "learning", "title": "Untitled", "tags": []}

        lower = observation.lower()

        # Classification heuristics (no LLM needed)
        if any(kw in lower for kw in ["always", "never", "must", "rule", "standard", "convention"]):
            category = "convention"
        elif any(kw in lower for kw in ["workflow", "process", "when", "step", "pattern"]):
            category = "pattern"
        else:
            category = "learning"

        # Auto-detect tags
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

        # Title from first line
        first_line = observation.split("\n")[0].strip().rstrip(".")
        title = first_line[:80] if len(first_line) > 80 else first_line

        ctx.log.info(f"Classified as {category}", title=title, tags=tags)
        return {"category": category, "title": title, "tags": tags}

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

        ctx.log.info(
            f"Persisted to markdown: {category}",
            file=str(filepath) if filepath else "store not available",
        )

        return {
            "written": filepath is not None,
            "category": category,
            "title": title,
            "file": str(filepath) if filepath else None,
            "tags": tags,
        }

    async def step_store(self, ctx: Context) -> dict[str, Any]:
        """Store in PostgreSQL knowledge base for semantic search."""
        observation = ctx.inputs.get("observation", "")
        classification = ctx.get("step_classify", {"category": "learning", "title": "Untitled"})
        persist = ctx.get("step_persist_markdown", {})

        if not observation:
            return {"stored": False}

        store = ctx.store
        if store:
            store.initialize()

            memory_id = store.remember(
                agent_name="learn-workflow",
                content=f"{classification.get('title', '')}: {observation}",
                memory_type="learning",
                importance=0.7 if classification.get("category") == "convention" else 0.5,
                metadata={
                    "source": "learn_workflow",
                    "category": classification.get("category"),
                    "tags": classification.get("tags", []),
                    "file": persist.get("file"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            store.add_knowledge(
                content=observation,
                content_type=f"memory/{classification.get('category', 'learning')}",
                title=classification.get("title", "Untitled"),
                tags=classification.get("tags", []),
            )

            ctx.log.info(f"Stored in DB: memory#{memory_id}")
            return {"stored": True, "memory_id": memory_id}

        return {"stored": False}
