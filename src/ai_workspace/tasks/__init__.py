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
    
    # Periodic schedules
    periodic_morning_briefing,
    periodic_daily_research,
    periodic_continuous_learning,
    periodic_check_db_tasks,
    periodic_telemetry_report,
    
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
    "periodic_morning_briefing",
    "periodic_daily_research",
    "periodic_continuous_learning",
    "periodic_check_db_tasks",
    "periodic_telemetry_report",
    "init_telemetry",
    "telemetry",
    "TelemetrySpan",
    "start_worker",
]
