"""Tasks module - Huey-based scheduling, periodic tasks, telemetry."""

from ai_workspace.tasks.scheduler import (
    # Huey instance
    huey,

    # Task definitions
    deep_research_task,
    sync_obsidian_task,
    daily_briefing_task,
    continuous_learning_task,
    run_scheduled_db_task,
    run_workflow_task,
    update_source_reputation_task,
    cleanup_semantic_cache_task,

    # Periodic schedules
    periodic_morning_briefing,
    periodic_daily_research,
    periodic_continuous_learning,
    periodic_check_db_tasks,
    periodic_telemetry_report,
    periodic_source_reputation_update_mon,
    periodic_source_reputation_update_thu,
    periodic_cache_cleanup,

    # Telemetry
    init_telemetry,
    telemetry,
    TelemetrySpan,

    # Worker
    start_worker,
)

__all__ = [
    "huey",
    "deep_research_task",
    "sync_obsidian_task",
    "daily_briefing_task",
    "continuous_learning_task",
    "run_scheduled_db_task",
    "run_workflow_task",
    "update_source_reputation_task",
    "cleanup_semantic_cache_task",
    "periodic_morning_briefing",
    "periodic_daily_research",
    "periodic_continuous_learning",
    "periodic_check_db_tasks",
    "periodic_telemetry_report",
    "periodic_source_reputation_update_mon",
    "periodic_source_reputation_update_thu",
    "periodic_cache_cleanup",
    "init_telemetry",
    "telemetry",
    "TelemetrySpan",
    "start_worker",
]
