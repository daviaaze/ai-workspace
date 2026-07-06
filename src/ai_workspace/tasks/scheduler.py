"""
Task scheduling and queue — Huey (lightweight, SQLite-backed).

Huey provides:
- Task queue with retry, timeout, rate limiting
- Periodic tasks via crontab/intervals
- SQLite backend (zero infrastructure!)
- Task result storage
- Signal hooks for telemetry

Architecture:
  Huey consumer process (aiw worker)
   @huey.task()           → one-off async tasks
   @huey.periodic_task()  → recurring scheduled tasks
   @huey.on_startup()     → telemetry init
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from huey import SqliteHuey, crontab

logger = logging.getLogger(__name__)



# Huey instance

DATA_DIR = Path(os.getenv("AIW_DATA_DIR", Path.home() / ".ai-workspace"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

huey = SqliteHuey(
    name="ai-workspace",
    filename=str(DATA_DIR / "tasks.db"),
    results=True,          # Store task results
    store_none=True,       # Store None results too
    utc=True,
)

# Telemetry init (runs once when consumer starts)

def init_telemetry() -> None:
    """Initialize Langtrace for auto-instrumentation of crewAI + Ollama."""
    try:
        import langtrace_python_sdk as langtrace
        langtrace.init(
            api_key=os.getenv("LANGTRACE_API_KEY", ""),  # optional: cloud upload
            write_to_remote=False,  # local-first
            batch=True,
            write_spans_to_console=False,
            disable_logging=True,
        )
    except ImportError:
        pass  # Langtrace not installed
    except Exception as e:
        logger.warning("Langtrace init warning: %s", e)


# Telemetry decorator — manual spans for non-crewAI operations

class TelemetrySpan:
    """Simple manual span for tracking non-crewAI operations."""

    def __init__(self):
        self._spans: dict[str, dict[str, Any]] = {}

    def start(self, name: str, **attrs) -> str:
        import uuid
        span_id = str(uuid.uuid4())[:8]
        self._spans[span_id] = {
            "name": name,
            "attrs": attrs,
            "start": datetime.now(UTC),
            "end": None,
            "status": "running",
        }
        return span_id

    def end(self, span_id: str, output: Any = None, error: str | None = None) -> dict:
        span = self._spans.get(span_id, {})
        span["end"] = datetime.now(UTC)
        span["duration_ms"] = (
            (span["end"] - span["start"]).total_seconds() * 1000
            if span.get("start") and span.get("end")
            else 0
        )
        span["status"] = "error" if error else "ok"
        if error:
            span["error"] = error
        if output is not None:
            span["output"] = str(output)[:500]
        return span

telemetry = TelemetrySpan()


# Task definitions

# Workflow execution task (decoupled from terminal)

@huey.task(retries=2, retry_delay=30, priority=50)
def run_workflow_task(
    workflow_name: str,
    inputs: dict[str, Any],
    db_url: str | None = None,
) -> dict[str, Any]:
    if db_url is None:
        db_url = os.environ.get("AIW_DB_URL", "postgresql:///ai_workspace")
    """Run a DAG workflow via the Huey worker (background, crash-resistant).

    The workflow persists state per-step in PostgreSQL, so even if the
    worker process dies mid-execution, you can resume with:
        aiw wf retry <run_id>
    """
    span_id = telemetry.start("run_workflow", workflow=workflow_name, inputs=inputs)

    try:
        from ai_workspace.workflow import WorkflowRegistry

        wf_cls = WorkflowRegistry.get(workflow_name)
        if not wf_cls:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        wf = wf_cls(db_url=db_url)
        result = asyncio.run(wf.run(**inputs))

        telemetry.end(span_id, output={
            "run_id": result.run_id,
            "status": result.status.value,
            "steps": len(result.steps),
        })

        return {
            "run_id": result.run_id,
            "status": result.status.value,
            "error": result.error,
            "duration_ms": result.duration_ms,
            "steps": {
                name: {"status": step.status.value, "duration_ms": step.duration_ms}
                for name, step in result.steps.items()
            },
        }

    except Exception as e:
        telemetry.end(span_id, error=str(e))
        raise


def _detect_provider() -> str:
    """Detect available LLM provider: 'deepseek' (preferred) or 'ollama'."""
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not key:
        try:
            key = open(os.path.expanduser("~/.local/share/sops-nix/secrets/deepseek_api_key")).read().strip()
        except Exception:
            pass
    return "deepseek" if key else "ollama"


def _make_llm(model: str = "deepseek-chat") -> Any:
    """Create a CrewAI LLM instance for the configured provider."""
    from crewai import LLM as CrewLLM

    if _detect_provider() == "deepseek":
        key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not key:
            try:
                key = open(os.path.expanduser("~/.local/share/sops-nix/secrets/deepseek_api_key")).read().strip()
            except Exception:
                pass
        return CrewLLM(
            model=model,
            base_url="https://api.deepseek.com/v1",
            api_key=key,
        )

    # Ollama fallback
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    return CrewLLM(
        model=model,
        base_url=f"{host}/v1",
        api_key="ollama",
    )


@huey.task(retries=2, retry_delay=30, priority=50)
def deep_research_task(
    query: str,
    depth: int = 2,
    model: str | None = None,
    fast_model: str | None = None,
    db_url: str | None = None,
    save_to_db: bool = True,
) -> dict[str, Any]:
    """Run deep recursive research on a query (huey task, retryable)."""
    if db_url is None:
        db_url = os.environ.get("AIW_DB_URL", "postgresql:///ai_workspace")
    span_id = telemetry.start("deep_research", query=query, depth=depth)

    try:
        provider = _detect_provider()
        if provider == "deepseek":
            from ai_workspace.search import DeepSearchEngine
            engine = DeepSearchEngine(
                model="deepseek-chat",
                deep_model="deepseek-reasoner",
                max_depth=depth,
                provider="deepseek",
            )
        else:
            from ai_workspace.search import DeepSearchEngine
            engine = DeepSearchEngine(
                model=f"ollama/{fast_model or os.environ.get('AIW_DEFAULT_MODEL', 'qwen3:14b')}",
                deep_model=f"ollama/{model or os.environ.get('AIW_DEEP_MODEL', 'deepseek-r1:14b')}",
                max_depth=depth,
            )

        result = asyncio.run(engine.research(query))

        report = {
            "query": query,
            "summary": result.summary,
            "detailed_report": result.detailed_report[:5000],
            "sources": result.sources,
            "confidence": float(result.confidence) if isinstance(result.confidence, (int, float)) else 0.0,
            "sub_questions": [
                {
                    "question": sq.question,
                    "answer": sq.answer[:2000] if sq.answer else "",
                    "confidence": sq.confidence,
                }
                for sq in result.sub_questions
            ],
            "executed_at": datetime.now(UTC).isoformat(),
        }

        if save_to_db:
            try:
                from ai_workspace.knowledge import KnowledgeStore
                store = KnowledgeStore(db_url=db_url)
                store.initialize()
                store.save_research(query, report)
                store.close()
            except Exception as e:
                logger.error("Could not save research: %s", e)

        telemetry.end(span_id, output={"confidence": result.confidence, "sub_questions": len(result.sub_questions)})
        return report

    except Exception as e:
        telemetry.end(span_id, error=str(e))
        raise


@huey.task(retries=1, retry_delay=15)
def sync_obsidian_task(
    db_url: str | None = None,
    vault_path: str | None = None,
    direction: str = "both",
) -> dict[str, int]:
    """Sync knowledge between AI Workspace and Obsidian vault."""
    span_id = telemetry.start("obsidian_sync", direction=direction)

    try:
        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore(db_url=db_url, obsidian_vault=vault_path)
        store.initialize()

        imported = exported = 0
        if direction in ("import", "both"):
            imported = store.import_from_obsidian()
        if direction in ("export", "both"):
            exported = store.sync_to_obsidian()

        store.close()

        result = {"imported": imported, "exported": exported}
        telemetry.end(span_id, output=result)
        return result

    except Exception as e:
        telemetry.end(span_id, error=str(e))
        raise


@huey.task(retries=1)
def daily_briefing_task(
    db_url: str | None = None,
    topics: list[str] | None = None,
) -> dict[str, Any]:
    """Generate daily briefing from recent activity."""
    span_id = telemetry.start("daily_briefing")

    try:
        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore(db_url=db_url)
        store.initialize()

        recent = store.get_research_history(limit=10)
        pending = store.get_tasks(status="pending", limit=10)

        # Get recent agent learnings
        learnings = store.recall("continuous-learner", "%", memory_type="learning", limit=5)

        store.close()

        # Generate briefing
        from crewai import Agent, Crew, Task

        analyst = Agent(
            role="Daily Briefing Analyst",
            goal="Create concise, actionable daily briefing from knowledge base data",
            backstory=(
                "You analyze recent activity and produce clear, structured briefings. "
                "Focus on actionable insights and priorities."
            ),
            llm=_make_llm("deepseek-chat" if _detect_provider() == "deepseek" else "qwen3:14b"),
            verbose=False,
        )

        context_parts = []

        if recent:
            context_parts.append("## Recent Research\n" + "\n".join(
                f"- **{r.get('query', '?')}**: {r.get('summary', '?')[:200]}"
                for r in recent[:5]
            ))

        if pending:
            context_parts.append("## Pending Tasks\n" + "\n".join(
                f"- [{t.get('status', '?')}] {t.get('title', '?')}"
                for t in pending[:5]
            ))

        if learnings:
            context_parts.append("## Recent Learnings\n" + "\n".join(
                f"- {l.get('content', '')[:200]}"
                for l in learnings[:3]
            ))

        if topics:
            context_parts.append("## Focus Topics\n" + "\n".join(f"- {t}" for t in topics))

        context = "\n\n".join(context_parts) or "No activity today."

        briefing_task = Task(
            description=(
                f"Create a daily briefing from this data:\n\n{context}\n\n"
                "Structure the briefing as:\n"
                "###  Top Priorities Today\n"
                "###  Research Updates\n"
                "###  New Insights\n"
                "###  Scheduled Tasks\n"
                "###  Recommendations\n\n"
                "Be concise. Focus on what matters."
            ),
            expected_output="A markdown-formatted daily briefing.",
            agent=analyst,
        )

        crew = Crew(agents=[analyst], tasks=[briefing_task], verbose=False)
        result_text = crew.kickoff()

        briefing = {
            "date": datetime.now(UTC).isoformat(),
            "briefing": str(result_text),
            "research_count": len(recent),
            "pending_tasks": len(pending),
            "learnings_count": len(learnings),
        }

        telemetry.end(span_id, output={"research_count": len(recent), "tasks": len(pending)})
        return briefing

    except Exception as e:
        telemetry.end(span_id, error=str(e))
        raise


@huey.task(retries=1, retry_delay=30)
def continuous_learning_task(
    db_url: str | None = None,
) -> dict[str, Any]:
    """Extract patterns and insights from research history."""
    span_id = telemetry.start("continuous_learning")

    try:
        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore(db_url=db_url)
        store.initialize()

        history = store.get_research_history(limit=50)
        store.close()

        if not history:
            telemetry.end(span_id, output={"insights": 0})
            return {"insights": "No research history to analyze", "count": 0}

        # Use agent to extract patterns
        from crewai import Agent, Crew, Task

        analyst = Agent(
            role="Pattern & Insight Analyst",
            goal=(
                "Identify recurring themes, patterns, and lasting insights "
                "from historical research. Extract knowledge worth remembering."
            ),
            backstory=(
                "You find connections that others miss. From research history, "
                "you extract durable knowledge — facts, trends, and principles "
                "that remain valuable over time."
            ),
            llm=_make_llm("deepseek-chat" if _detect_provider() == "deepseek" else "qwen3:14b"),
            verbose=False,
        )

        summaries = "\n".join(
            f"- [{r.get('query', '?')}] {r.get('summary', '?')[:300]}"
            for r in history[:30]
            if r.get("summary")
        )

        extract_task = Task(
            description=(
                f"Analyze this research history and extract lasting insights:\n\n"
                f"{summaries}\n\n"
                f"Return 5-10 key insights, patterns, or learnings. "
                f"Each insight should be one sentence and genuinely useful "
                f"for future reference. Avoid generic statements."
            ),
            expected_output="Numbered list of insights, one per line.",
            agent=analyst,
        )

        crew = Crew(agents=[analyst], tasks=[extract_task], verbose=False)
        insights_text = str(crew.kickoff())

        # Save as agent memory
        store = KnowledgeStore(db_url=db_url)
        store.initialize()
        store.remember(
            agent_name="continuous-learner",
            content=insights_text,
            memory_type="learning",
            importance=0.8,
            metadata={
                "source": "continuous_learning",
                "history_size": len(history),
                "generated_at": datetime.now(UTC).isoformat(),
            },
        )
        store.close()

        result = {"insights": insights_text, "history_size": len(history)}
        telemetry.end(span_id, output={"insights_count": insights_text.count("\n")})
        return result

    except Exception as e:
        telemetry.end(span_id, error=str(e))
        raise


@huey.task(retries=2, retry_delay=60, priority=30)
def run_scheduled_db_task(
    task_id: int,
    db_url: str | None = None,
) -> dict[str, Any]:
    """Execute a task from the DB by ID (supports cron-scheduled DB tasks)."""
    span_id = telemetry.start("scheduled_db_task", task_id=task_id)

    try:
        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore(db_url=db_url)
        store.initialize()

        # Get task info
        tasks = store.get_tasks(limit=1000)
        task_info = next((t for t in tasks if t["id"] == task_id), None)

        if not task_info:
            telemetry.end(span_id, error=f"Task {task_id} not found")
            raise ValueError(f"Task {task_id} not found")

        # Mark as in progress
        store.update_task_status(task_id, "in_progress")

        # Run the appropriate handler based on task metadata
        metadata = task_info.get("metadata", {}) or {}
        task_type = metadata.get("type", "research")

        result = {}

        if task_type == "research":
            query = task_info["title"]
            depth = metadata.get("depth", 2)
            result = deep_research_task(query, depth=depth, db_url=db_url)

        elif task_type == "briefing":
            topics = metadata.get("topics", [])
            result = daily_briefing_task(db_url=db_url, topics=topics)

        elif task_type == "obsidian_sync":
            vault = metadata.get("vault_path")
            direction = metadata.get("direction", "both")
            result = sync_obsidian_task(db_url=db_url, vault_path=vault, direction=direction)

        elif task_type == "learning":
            result = continuous_learning_task(db_url=db_url)

        elif task_type == "leilao_pipeline":
            from ai_workspace.leilao_radar.tasks import leilao_pipeline_task
            result = leilao_pipeline_task(db_url=db_url)

        else:
            # Generic: just log execution
            result = {"status": "executed", "task_id": task_id, "title": task_info["title"]}

        # Mark as completed and update next_run
        store.update_task_status(task_id, "completed")

        # Calculate next_run from cron schedule
        schedule = task_info.get("schedule")
        if schedule:
            store.conn.cursor().execute(
                """UPDATE tasks
                   SET next_run = cron_next(%s, NOW()),
                       status = 'pending',
                       updated_at = NOW()
                   WHERE id = %s""",
                (schedule, task_id),
            )

        store.close()
        telemetry.end(span_id, output=result)
        return result

    except Exception as e:
        try:
            store = KnowledgeStore(db_url=db_url)
            store.initialize()
            store.update_task_status(task_id, "failed")
            store.close()
        except Exception:
            pass
        telemetry.end(span_id, error=str(e))
        raise


# Periodic Tasks (recurring schedules)

# These run automatically when `aiw worker` is running.
# Schedules are in BRT (America/Sao_Paulo). Huey uses UTC internally,
# so offset by -3. 7:00 BRT = 10:00 UTC, 8:00 BRT = 11:00 UTC, etc.

@huey.periodic_task(crontab(hour=10, minute=0))  # 7:00 BRT
def periodic_morning_briefing():
    """Daily morning briefing — sync + generate priorities (7:00 BRT)."""
    sync_obsidian_task(direction="import")
    return daily_briefing_task()


@huey.periodic_task(crontab(hour=11, minute=0))  # 8:00 BRT
def periodic_daily_research():
    """Daily automated research on configured topics (8:00 BRT)."""
    topics = [
        "Latest developments in AI and machine learning",
        "New open-source tools and libraries for developers",
        "NixOS and declarative system management innovations",
    ]
    results = []
    for topic in topics:
        result = deep_research_task(topic, depth=2)
        results.append(result)
    return {"researched": len(results), "topics": topics}


@huey.periodic_task(crontab(hour=5, minute=0))  # 2:00 BRT
def periodic_continuous_learning():
    """Extract patterns from research history (2:00 BRT)."""
    return continuous_learning_task()


@huey.periodic_task(crontab(minute=0))  # Every hour
def periodic_check_db_tasks():
    """Check and run any due tasks from the database."""
    try:
        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore()
        store.initialize()
        due = store.get_due_tasks()
        store.close()

        for task in due:
            run_scheduled_db_task(task["id"])

        return {"checked": len(due)}
    except Exception:
        return {"checked": 0, "error": True}


# Source Reputation tasks

@huey.task(retries=1, retry_delay=300)
def update_source_reputation_task():
    """Update CRED-1 dataset and recompute composite scores."""
    from pathlib import Path
    from urllib.request import urlretrieve

    from ai_workspace.sources import SourceReputationService

    svc = SourceReputationService()
    svc.initialize()

    # Download latest CRED-1
    cache_path = Path.home() / ".ai-workspace" / "cred1_current.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        urlretrieve(
            "https://raw.githubusercontent.com/aloth/cred-1/main/data/cred1_current.json",
            str(cache_path),
        )
        logger.info("Downloaded latest CRED-1 dataset")
    except Exception as e:
        logger.warning("CRED-1 download failed: %s (using cached)", e)
        if not cache_path.exists():
            return {"error": "No CRED-1 cache available", "detail": str(e)}

    # Seed/update
    cred1_count = svc.seed_cred1(str(cache_path))
    reliable_count = svc.seed_reliable()

    # Recompute composite scores for updated domains
    c = svc.conn.cursor()
    c.execute(
        "SELECT domain FROM domain_reputation WHERE cred1_last_updated > NOW() - INTERVAL '1 hour'"
    )
    recomputed = 0
    for (domain,) in c.fetchall():
        svc.recompute_composite(domain)
        recomputed += 1

    stats = svc.stats()
    logger.info(
        "Source reputation updated: %d CRED-1 + %d reliable = %d total. "
        "Recomputed %d composite scores. Coverage: %d/%d domains",
        cred1_count, reliable_count, stats["total_domains"],
        recomputed, stats["cred1_coverage"], stats["total_domains"],
    )

    return {
        "cred1_seeded": cred1_count,
        "reliable_seeded": reliable_count,
        "total_domains": stats["total_domains"],
        "cred1_coverage": stats["cred1_coverage"],
        "recomputed": recomputed,
    }


@huey.periodic_task(crontab(day_of_week=1, hour=9, minute=0))  # Monday 6:00 BRT
def periodic_source_reputation_update_mon():
    """Update source reputation dataset (Monday)."""
    return update_source_reputation_task()


@huey.periodic_task(crontab(day_of_week=4, hour=9, minute=0))  # Thursday 6:00 BRT
def periodic_source_reputation_update_thu():
    """Update source reputation dataset (Thursday)."""
    return update_source_reputation_task()


# Cache maintenance tasks

@huey.task(retries=1)
def cleanup_semantic_cache_task():
    """Remove expired cache entries (not hit in 30 days)."""
    from ai_workspace.core.cost import SemanticCache

    cache = SemanticCache()
    try:
        deleted = cache.cleanup_expired(max_age_days=30)
        logger.info("Cache cleanup: removed %d expired entries", deleted)
        return {"deleted": deleted}
    except Exception as e:
        logger.warning("Cache cleanup failed: %s", e)
        return {"deleted": 0, "error": str(e)}


@huey.periodic_task(crontab(day_of_week=0, hour=8, minute=0))  # Sunday 5:00 BRT
def periodic_cache_cleanup():
    """Weekly cache cleanup (Sunday)."""
    return cleanup_semantic_cache_task()


# Improvement cycle (HALO-inspired self-improvement)

def run_improvement_cycle():
    """Run the weekly self-improvement cycle.

    Collects traces from TraceStore, analyzes failure patterns,
    and writes recommendations to memory files.
    """
    from ai_workspace.agents.improvement import ImprovementCycle, print_report

    cycle = ImprovementCycle()
    report = cycle.run_sync()
    if report:
        print_report(report)
        return {"patterns": len(report.patterns), "recommendations": len(report.recommendations)}
    return {"patterns": 0, "recommendations": 0, "status": "no traces"}


@huey.periodic_task(crontab(day_of_week=0, hour=10, minute=0))  # Sunday 7:00 BRT
def periodic_improvement_cycle():
    """Weekly self-improvement cycle (Sunday)."""
    return run_improvement_cycle()


# Telemetry tasks (self-monitoring)

@huey.periodic_task(crontab(hour=12, minute=0))  # 9:00 BRT — daily
def periodic_telemetry_report():
    """Generate and store a daily telemetry snapshot."""
    span_id = telemetry.start("telemetry_report")

    try:
        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore()
        store.initialize()

        # Count recent activity
        c = store.conn.cursor()

        c.execute("SELECT COUNT(*) FROM research_entries WHERE created_at > NOW() - INTERVAL '24 hours'")
        research_24h = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM tasks WHERE updated_at > NOW() - INTERVAL '24 hours'")
        tasks_24h = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM agent_memory WHERE created_at > NOW() - INTERVAL '24 hours'")
        memories_24h = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM knowledge_entries WHERE created_at > NOW() - INTERVAL '24 hours'")
        knowledge_24h = c.fetchone()[0]

        c.close()
        store.close()

        report = {
            "date": datetime.now(UTC).isoformat(),
            "metrics": {
                "research_last_24h": research_24h,
                "tasks_updated_24h": tasks_24h,
                "memories_stored_24h": memories_24h,
                "knowledge_added_24h": knowledge_24h,
            },
        }

        telemetry.end(span_id, output=report)
        return report

    except Exception as e:
        telemetry.end(span_id, error=str(e))
        raise


# Signal handlers (graceful shutdown)

def register_signal_handlers():
    """Register graceful shutdown handlers."""
    def shutdown(signum, frame):
        logger.info("Received signal %s, shutting down...", signum)
        # Huey handles graceful shutdown internally
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)


# Consumer entry point

def start_worker():
    """Start the Huey consumer to process tasks and periodic schedules."""
    init_telemetry()
    register_signal_handlers()

    print("[worker] AI Workspace task consumer starting...")
    print(f"[worker] Data directory: {DATA_DIR}")
    print(f"[worker] Task DB: {DATA_DIR / 'tasks.db'}")
    print("[worker] Periodic tasks:")
    print("  - Morning briefing:       7:00 BRT (daily)")
    print("  - Daily research:         8:00 BRT (daily)")
    print("  - Continuous learning:     2:00 BRT (daily)")
    print("  - Source reputation:       Mon/Thu 6:00 BRT")
    print("  - Cache cleanup:           Sun 5:00 BRT")
    print("  - Improvement cycle:       Sun 7:00 BRT")
    print("  - DB task checker:         every hour")
    print("  - Telemetry report:        9:00 BRT (daily)")
    print()

    consumer = huey.create_consumer()
    consumer.run()
