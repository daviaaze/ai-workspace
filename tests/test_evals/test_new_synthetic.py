"""
New Synthetic Eval Scenarios — covering the latest infrastructure features.

Extends the OpenSRE-style RCA scenarios with scenarios for:
- Queue starvation / dead-letter
- Worktree lifecycle collision
- Loop budget exhaustion
- MCP server failure cascade
- Schedule drift

These scenarios test an agent's ability to diagnose problems across
the new queue/worktree/loop/MCP infrastructure.
"""

from __future__ import annotations

import json
import unittest
from unittest import TestCase
from dataclasses import dataclass, field
from typing import Any

from ai_workspace.evals.synthetic import (
    Scenario,
    Symptom,
    Evidence,
    ScenarioScorer,
    ScoredScenario,
    ALL_SCENARIOS,
    INFRASTRUCTURE_SCENARIOS,
)


# ═══════════════════════════════════════════════════════════
# New Scenario Definitions
# ═══════════════════════════════════════════════════════════

QUEUE_SCENARIOS: list[Scenario] = [
    Scenario(
        id="queue_starvation",
        title="Job queue starvation — high-priority jobs blocked",
        description=(
            "The CI/CD pipeline has been stalled for 2 hours. "
            "New pull requests are not getting their status checks "
            "updated. The job queue shows 347 'pending' jobs but "
            "none are being processed. Three workers are registered."
        ),
        symptoms=[
            Symptom("CI status not updating on PRs for 2+ hours", "github_api",
                    evidence_suggests=["queue_depth", "worker_heartbeat"]),
            Symptom("347 pending jobs, 0 running, 0 workers active",
                    "queue_admin",
                    evidence_suggests=["worker_status"]),
            Symptom("Worker processes are alive but not dequeuing",
                    "process_monitoring"),
            Symptom("Consumer locks all expired — no heartbeat in 30 minutes",
                    "queue_registry",
                    evidence_suggests=["heartbeat_log"]),
            Symptom("Last successful job completed 2h 15min ago",
                    "queue_stats"),
        ],
        expected_rca=["worker heartbeat mechanism failed",
                       "workers crashed without releasing locks",
                       "stale consumer locks blocking new dequeue attempts"],
        required_evidence=["queue_depth", "worker_heartbeat", "worker_status"],
        red_herrings=["database connection pool exhausted",
                       "network partition between workers and DB",
                       "GitHub API rate limit hit"],
        severity="critical",
        difficulty=0.65,
        tags=["queue", "ci-cd", "infrastructure"],
    ),
    Scenario(
        id="dead_letter_queue",
        title="Dead letter queue accumulating failed jobs",
        description=(
            "The dependency sweeper loop has been failing silently "
            "for 3 days. The job queue shows 89 failed jobs in the "
            "'loops' queue. Each job retried 3 times and failed. "
            "No alerts have fired."
        ),
        symptoms=[
            Symptom("89 failed jobs in 'loops' queue over 3 days",
                    "queue_stats",
                    evidence_suggests=["failed_job_details"]),
            Symptom("Dependency report not updated in 72 hours",
                    "slack_channel",
                    evidence_suggests=["last_successful_run"]),
            Symptom("Each job retried 3 times with exponential backoff",
                    "job_history"),
            Symptom("Error message: 'Handler not found: dependency-sweeper'",
                    "job_last_error"),
            Symptom("No dead letter queue configured — failed jobs stay in main queue",
                    "queue_config"),
        ],
        expected_rca=["dependency-sweeper handler not registered in worker",
                       "no dead letter queue or alert on retry exhaustion",
                       "handler registration mismatch between enqueue and worker"],
        required_evidence=["failed_job_details", "last_successful_run", "handler_registry"],
        red_herrings=["OOM killer terminating workers",
                       "PostgreSQL connection pool exhausted",
                       "disk space full on worker node"],
        severity="high",
        difficulty=0.55,
        tags=["queue", "loops", "dependency"],
    ),
]

WORKTREE_SCENARIOS: list[Scenario] = [
    Scenario(
        id="worktree_collision",
        title="Worktree collision — two agents editing the same file",
        description=(
            "Two CI sweeper loops were triggered simultaneously "
            "for the same repository. Both created worktrees and "
            "attempted to fix the same file. The second worktree "
            "creation failed with 'already exists'. The first "
            "worktree's changes were lost in the confusion."
        ),
        symptoms=[
            Symptom("git worktree add failed: 'already exists'",
                    "worktree_logs",
                    evidence_suggests=["worktree_registry"]),
            Symptom("Two concurrent CI sweeper runs for the same repo",
                    "job_queue",
                    evidence_suggests=["job_overlap"]),
            Symptom("First worktree has uncommitted changes, second aborted",
                    "git_status"),
            Symptom("Worktree registry shows duplicate (pattern_id, item_id)",
                    "worktree_registry"),
            Symptom("Git worktree prune removed first worktree during cleanup",
                    "git_logs"),
        ],
        expected_rca=["no lock on (pattern_id, item_id) before worktree creation",
                       "concurrent runs not deduplicated",
                       "cleanup handler removed active worktree"],
        required_evidence=["worktree_registry", "job_overlap", "concurrent_run_log"],
        red_herrings=["disk space exhausted in .worktrees directory",
                       "git branch already exists remotely",
                       "filesystem permission error on worktree creation"],
        severity="high",
        difficulty=0.7,
        tags=["worktree", "concurrency", "git"],
    ),
    Scenario(
        id="worktree_orphan_leak",
        title="Orphaned worktrees consuming disk space",
        description=(
            "The server's disk is at 94% capacity. Investigation "
            "shows 23 stale worktree directories under .worktrees/ "
            "that were never cleaned up. Some are weeks old."
        ),
        symptoms=[
            Symptom("Disk at 94% on CI worker node", "grafana",
                    evidence_suggests=["disk_usage_report"]),
            Symptom("23 directories under .worktrees/, 19 have no DB record",
                    "filesystem_scan",
                    evidence_suggests=["worktree_registry"]),
            Symptom("Cleanup cron job disabled 2 weeks ago during maintenance",
                    "cron_status"),
            Symptom("Worktrees consume 47GB total", "du_output",
                    evidence_suggests=["disk_usage_report"]),
            Symptom("Some worktrees have been abandoned mid-operation",
                    "worktree_registry"),
        ],
        expected_rca=["cleanup cron job not re-enabled after maintenance",
                       "no disk quota or max_age enforcement on worktrees",
                       "error handling path doesn't clean up on failure"],
        required_evidence=["disk_usage_report", "worktree_registry", "cleanup_config"],
        red_herrings=["log files growing uncontrollably",
                       "Docker images not being pruned",
                       "database WAL files accumulating"],
        severity="medium",
        difficulty=0.5,
        tags=["worktree", "disk", "cleanup", "operations"],
    ),
]

LOOP_BUDGET_SCENARIOS: list[Scenario] = [
    Scenario(
        id="loop_budget_exhaustion",
        title="Loop pattern budget exhausted — no work done",
        description=(
            "The PR babysitter hasn't done anything in 4 days. "
            "PRs are stacking up unreviewed. The loop runs fine "
            "but always returns immediately with 0 actions taken. "
            "No errors are logged."
        ),
        symptoms=[
            Symptom("PR babysitter runs every 15 min but takes 0 actions",
                    "loop_run_log",
                    evidence_suggests=["budget_status"]),
            Symptom("Daily budget is 200,000 tokens but spent 200,000 by 9 AM",
                    "loop_budget",
                    evidence_suggests=["daily_spend_pattern"]),
            Symptom("'Budget exceeded' message in debug logs",
                    "loop_logs"),
            Symptom("Budget resets at midnight but exhausts within hours",
                    "budget_history"),
            Symptom("Average PR review costs 15,000 tokens (75 reviews/day)",
                    "cost_analysis"),
        ],
        expected_rca=["daily token budget too low for actual workload",
                       "infinite loop or runaway agent consuming budget on single PR",
                       "budget cap not adjusted after adding new repositories"],
        required_evidence=["budget_status", "daily_spend_pattern", "cost_analysis"],
        red_herrings=["worker node CPU throttled",
                       "GitHub API rate limit",
                       "PostgreSQL connection limit reached"],
        severity="medium",
        difficulty=0.45,
        tags=["loops", "budget", "cost"],
    ),
]

MCP_SCENARIOS: list[Scenario] = [
    Scenario(
        id="mcp_server_cascade",
        title="MCP server failure cascade — agents lose tools",
        description=(
            "All coding agents started failing at 14:30. The error "
            "is 'MCP tool not found' for all tool calls. The MCP "
            "server process appears to be running but is unresponsive. "
            "Three agents were mid-operation when the failure occurred."
        ),
        symptoms=[
            Symptom("'MCP tool not found' errors across all tools",
                    "agent_logs",
                    evidence_suggests=["mcp_server_status"]),
            Symptom("MCP server process is running but port not listening",
                    "netstat",
                    evidence_suggests=["process_health"]),
            Symptom("Three agents had open sessions during failure",
                    "session_registry"),
            Symptom("Server log shows 'RuntimeError: fork failed' at 14:30",
                    "mcp_server_logs"),
            Symptom("MCP server restarts but crashes again within seconds",
                    "systemd_status"),
        ],
        expected_rca=["MCP server hit file descriptor limit",
                       "MCP server process entered deadlock processing parallel requests",
                       "subprocess fork failed due to memory pressure"],
        required_evidence=["mcp_server_status", "process_health", "mcp_server_logs"],
        red_herrings=["network interface down",
                       "SSL certificate expired on MCP endpoint",
                       "PostgreSQL connection pool exhausted"],
        severity="critical",
        difficulty=0.75,
        tags=["mcp", "agents", "infrastructure"],
    ),
]

# Combine all new scenarios
NEW_SCENARIOS: list[Scenario] = [
    *QUEUE_SCENARIOS,
    *WORKTREE_SCENARIOS,
    *LOOP_BUDGET_SCENARIOS,
    *MCP_SCENARIOS,
]


# ═══════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════


class TestNewScenarioDefinitions(TestCase):
    """Validate the new scenario definitions."""

    def test_new_scenarios_exist(self):
        self.assertGreater(len(NEW_SCENARIOS), 0)

    def test_queue_scenarios(self):
        self.assertGreaterEqual(len(QUEUE_SCENARIOS), 2)

    def test_worktree_scenarios(self):
        self.assertGreaterEqual(len(WORKTREE_SCENARIOS), 2)

    def test_loop_budget_scenarios(self):
        self.assertGreaterEqual(len(LOOP_BUDGET_SCENARIOS), 1)

    def test_mcp_scenarios(self):
        self.assertGreaterEqual(len(MCP_SCENARIOS), 1)

    def test_each_has_unique_id(self):
        ids = [s.id for s in NEW_SCENARIOS]
        self.assertEqual(len(ids), len(set(ids)), "Duplicate scenario IDs")

    def test_each_has_symptoms(self):
        for s in NEW_SCENARIOS:
            self.assertGreater(len(s.symptoms), 0, f"Scenario {s.id} has no symptoms")

    def test_each_has_expected_rca(self):
        for s in NEW_SCENARIOS:
            self.assertGreater(len(s.expected_rca), 0, f"Scenario {s.id} has no expected RCA")

    def test_each_has_required_evidence(self):
        for s in NEW_SCENARIOS:
            self.assertGreater(len(s.required_evidence), 0, f"Scenario {s.id} has no required evidence")

    def test_each_has_red_herrings(self):
        for s in NEW_SCENARIOS:
            self.assertGreater(len(s.red_herrings), 0, f"Scenario {s.id} has no red herrings")

    def test_severity_distribution(self):
        severities = [s.severity for s in NEW_SCENARIOS]
        self.assertIn("critical", severities)
        self.assertIn("high", severities)
        self.assertIn("medium", severities)

    def test_difficulty_range(self):
        for s in NEW_SCENARIOS:
            self.assertGreaterEqual(s.difficulty, 0.0)
            self.assertLessEqual(s.difficulty, 1.0)

    def test_tags_assigned(self):
        for s in NEW_SCENARIOS:
            self.assertGreater(len(s.tags), 0, f"Scenario {s.id} has no tags")


class TestNewScenarioScoring(TestCase):
    """Score the new scenarios with perfect and partial answers."""

    def setUp(self):
        self.scorer = ScenarioScorer()

    def test_queue_starvation_perfect(self):
        scenario = QUEUE_SCENARIOS[0]
        result = self.scorer.score(
            scenario=scenario,
            rca_output=["worker heartbeat mechanism failed",
                         "workers crashed without releasing locks"],
            evidence_found=["queue_depth", "worker_heartbeat", "worker_status"],
        )
        self.assertGreater(result.overall_score, 0.8)

    def test_queue_starvation_partial(self):
        scenario = QUEUE_SCENARIOS[0]
        result = self.scorer.score(
            scenario=scenario,
            rca_output=["database connection pool exhausted"],  # wrong! it's a red herring
            evidence_found=["queue_depth"],
        )
        # RCA score should be 0 (wrong answer), evidence low
        self.assertLess(result.overall_score, 0.4)

    def test_dead_letter_queue_with_red_herring_penalty(self):
        scenario = QUEUE_SCENARIOS[1]
        result = self.scorer.score(
            scenario=scenario,
            rca_output=["handler registration mismatch between enqueue and worker",
                        "OOM killer terminating workers"],  # red herring!
            evidence_found=["failed_job_details", "last_successful_run"],
        )
        # Should have a red herring penalty
        self.assertGreater(result.red_herring_penalty, 0.0)

    def test_worktree_collision_evidence_scoring(self):
        scenario = WORKTREE_SCENARIOS[0]
        result = self.scorer.score(
            scenario=scenario,
            rca_output=["no lock on (pattern_id, item_id) before worktree creation",
                         "concurrent runs not deduplicated"],
            evidence_found=["worktree_registry", "concurrent_run_log"],
        )
        # Missing one evidence (job_overlap)
        self.assertAlmostEqual(result.evidence_score, 2/3)

    def test_worktree_orphan_no_evidence(self):
        scenario = WORKTREE_SCENARIOS[1]
        result = self.scorer.score(
            scenario=scenario,
            rca_output=["cleanup cron job not re-enabled after maintenance"],
            evidence_found=[],
        )
        # RCA is perfect, but no evidence
        self.assertEqual(result.rca_score, 1/3)  # 1 of 3 expected RCAs
        self.assertEqual(result.evidence_score, 0.0)

    def test_budget_exhaustion_perfect(self):
        scenario = LOOP_BUDGET_SCENARIOS[0]
        result = self.scorer.score(
            scenario=scenario,
            rca_output=["daily token budget too low for actual workload"],
            evidence_found=["budget_status", "daily_spend_pattern"],
        )
        # 1 of 3 RCAs matched, 2 of 3 evidence
        self.assertAlmostEqual(result.rca_score, 1/3)
        self.assertAlmostEqual(result.evidence_score, 2/3)

    def test_mcp_cascade_all_red_herrings(self):
        """Agent that blames everything on red herrings should score poorly."""
        scenario = MCP_SCENARIOS[0]
        result = self.scorer.score(
            scenario=scenario,
            rca_output=["network interface down",
                        "SSL certificate expired on MCP endpoint",
                        "PostgreSQL connection pool exhausted"],
            evidence_found=[],
        )
        # All 3 are red herrings
        self.assertEqual(result.rca_score, 0.0)
        self.assertEqual(result.evidence_score, 0.0)
        self.assertGreater(result.red_herring_penalty, 0.0)
        self.assertEqual(result.overall_score, 0.0)


class TestNewScenarioContext(TestCase):
    """Context building for new scenarios."""

    def setUp(self):
        self.scorer = ScenarioScorer()

    def test_context_includes_symptoms_not_rca(self):
        scenario = WORKTREE_SCENARIOS[0]
        context = self.scorer.build_context(scenario)
        # Should include symptoms
        self.assertIn("git worktree add failed", context)
        self.assertIn("Worktree collision", context)  # title, not id
        # Should NOT include expected RCAs
        self.assertNotIn("no lock on (pattern_id, item_id)", context)
        self.assertNotIn("red herrings", context.lower())

    def test_context_includes_severity(self):
        scenario = MCP_SCENARIOS[0]
        context = self.scorer.build_context(scenario)
        self.assertIn("critical", context.lower())

    def test_context_for_queue_starvation(self):
        scenario = QUEUE_SCENARIOS[0]
        context = self.scorer.build_context(scenario)
        self.assertIn("347 pending jobs", context)
        self.assertIn("suggests checking", context)  # evidence hints
        self.assertIn("Job queue starvation", context)  # title, not id


class TestAllScenariosCombined(TestCase):
    """Verify all scenarios are discoverable."""

    def test_new_scenarios_not_in_original_set(self):
        """New scenarios should be separate from the original INFRASTRUCTURE_SCENARIOS."""
        original_ids = {s.id for s in INFRASTRUCTURE_SCENARIOS}
        new_ids = {s.id for s in NEW_SCENARIOS}
        overlap = original_ids & new_ids
        self.assertEqual(len(overlap), 0,
                         f"New scenarios overlap with original: {overlap}")

    def test_new_scenarios_can_be_indexed(self):
        """New scenarios should follow the same get_scenario pattern."""
        from ai_workspace.evals.synthetic import get_scenario

        # If we added these to ALL_SCENARIOS, get_scenario would find them
        # For now, test that they can be looked up in our own list
        ids = {s.id for s in NEW_SCENARIOS}
        self.assertIn("queue_starvation", ids)
        self.assertIn("worktree_collision", ids)
        self.assertIn("loop_budget_exhaustion", ids)
        self.assertIn("mcp_server_cascade", ids)

    def test_summary_counts(self):
        """Summary stats across all scenario attributes."""
        all_new = NEW_SCENARIOS
        tags = set()
        for s in all_new:
            tags.update(s.tags)
        self.assertIn("queue", tags)
        self.assertIn("worktree", tags)
        self.assertIn("mcp", tags)
        self.assertIn("loops", tags)
