"""Tasks module - Huey-based scheduling, periodic tasks, telemetry."""

from ai_workspace.tasks.scheduler import (
    TelemetrySpan,
    cleanup_semantic_cache_task,
    continuous_learning_task,
    daily_briefing_task,
    # Task definitions
    deep_research_task,
    # Huey instance
    huey,
    # Telemetry
    init_telemetry,
    periodic_cache_cleanup,
    periodic_check_db_tasks,
    periodic_continuous_learning,
    periodic_daily_research,
    periodic_improvement_cycle,
    # Periodic schedules
    periodic_morning_briefing,
    periodic_source_reputation_update_mon,
    periodic_source_reputation_update_thu,
    periodic_telemetry_report,
    run_improvement_cycle,
    run_scheduled_db_task,
    run_workflow_task,
    # Worker
    start_worker,
    sync_obsidian_task,
    telemetry,
    update_source_reputation_task,
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
    "run_improvement_cycle",
    "periodic_improvement_cycle",
    "init_telemetry",
    "telemetry",
    "TelemetrySpan",
    "start_worker",
]
