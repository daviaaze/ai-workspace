"""
Synthetic Evaluation Scenarios — OpenSRE-style Root Cause Analysis.

Agent investigation scenarios inspired by OpenSRE's synthetic RCA suites.
Each ``Scenario`` defines an infrastructure failure with symptoms, expected
root cause, and required evidence. The ``ScenarioScorer`` grades agent
responses against the ground truth.

Usage::

    from ai_workspace.evals.synthetic import (
        Scenario, ScenarioScorer, get_scenario
    )

    scenario = get_scenario("db_slow_queries")
    scorer = ScenarioScorer()

    # Agent reads symptoms and investigates
    context = scorer.build_context(scenario)
    agent_response = "..."  # Agent's investigation result

    # Score the response
    result = scorer.score(
        scenario=scenario,
        rca_output=["missing index on orders table"],
        evidence_found=["slow_query_log", "table_schema"],
    )
    print(f"Score: {result.overall_score:.2f}")
    print(f"RCA: {result.rca_score:.0%}")
    print(f"Evidence: {result.evidence_score:.0%}")
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


# ═══════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════


@dataclass
class Symptom:
    """A symptom observed in the system.

    Attributes:
        text: Description of the symptom.
        source: Where the symptom was observed (e.g., monitoring, logs).
        evidence_suggests: List of evidence IDs this symptom points to.
    """

    text: str
    source: str
    evidence_suggests: list[str] = field(default_factory=list)


@dataclass
class Evidence:
    """A piece of evidence the agent should discover.

    Attributes:
        id: Unique evidence identifier (used in ``required_evidence``).
        label: Human-readable description of the evidence.
        critical: If True, finding this evidence is mandatory.
    """

    id: str
    label: str
    critical: bool = False


@dataclass
class Scenario:
    """An infrastructure failure scenario for agent investigation.

    The agent is presented with ``symptoms`` and must investigate
    to determine the root cause (``expected_rca``), collecting
    ``required_evidence`` along the way while avoiding ``red_herrings``.

    Attributes:
        id: Unique scenario identifier.
        title: Short headline for the scenario.
        description: Longer scenario description / context.
        symptoms: Symptoms the agent observes.
        expected_rca: List of expected root cause statements.
            The agent's answer is scored against these.
        required_evidence: Evidence IDs the agent must find.
        red_herrings: Plausible-but-wrong root causes to distract.
        severity: Failure severity (low / medium / high / critical).
        difficulty: 0.0 (trivial) to 1.0 (expert).
        tags: Categorisation tags (e.g., database, network, config).
    """

    id: str
    title: str
    symptoms: list[Symptom]
    expected_rca: list[str]
    description: str = ""
    required_evidence: list[str] = field(default_factory=list)
    red_herrings: list[str] = field(default_factory=list)
    severity: str = "high"
    difficulty: float = 0.5
    tags: list[str] = field(default_factory=list)


@dataclass
class ScoredScenario:
    """Result of scoring an agent's response to a scenario.

    Attributes:
        scenario_id: The scenario that was scored.
        rca_score: Fraction of expected RCAs found in agent output.
        evidence_score: Fraction of required evidence found.
        red_herring_penalty: Fraction of output that matches red herrings.
        overall_score: Weighted combination of rca and evidence minus penalty.
        details: Per-component breakdown.
    """

    scenario_id: str
    rca_score: float
    evidence_score: float
    red_herring_penalty: float
    overall_score: float
    details: dict[str, Any] = field(default_factory=dict)

    def passed(self, threshold: float = 0.6) -> bool:
        """Whether the scenario was passed at a given threshold."""
        return self.overall_score >= threshold


# ═══════════════════════════════════════════════════════════
# Scorer
# ═══════════════════════════════════════════════════════════


class ScenarioScorer:
    """Scores agent responses against scenario expectations.

    Uses text-based matching (substring / keyword) to compare the
    agent's output against expected RCAs and required evidence.

    Args:
        rca_weight: Weight for RCA score in overall (default 0.5).
        evidence_weight: Weight for evidence score (default 0.5).
        case_sensitive: Whether matching is case-sensitive (default False).
    """

    def __init__(
        self,
        rca_weight: float = 0.5,
        evidence_weight: float = 0.5,
        case_sensitive: bool = False,
    ):
        self.rca_weight = rca_weight
        self.evidence_weight = evidence_weight
        self.case_sensitive = case_sensitive

    def score(
        self,
        scenario: Scenario,
        rca_output: list[str],
        evidence_found: list[str],
    ) -> ScoredScenario:
        """Score an agent's investigation output.

        Args:
            scenario: The scenario definition.
            rca_output: Root cause statements from the agent.
            evidence_found: Evidence items the agent identified.

        Returns:
            Detailed scoring result.
        """
        # ── RCA Score ─────────────────────────────────────────────────
        rca_matched = self._count_matches(scenario.expected_rca, rca_output)
        rca_total = len(scenario.expected_rca)
        rca_score = rca_matched / rca_total if rca_total > 0 else 0.0

        # ── Evidence Score ────────────────────────────────────────────
        ev_matched = self._count_matches(scenario.required_evidence, evidence_found)
        ev_total = len(scenario.required_evidence)
        evidence_score = ev_matched / ev_total if ev_total > 0 else 1.0  # no ev requirement = 1.0

        # ── Red Herring Penalty ───────────────────────────────────────
        if scenario.red_herrings:
            herring_hits = self._count_matches_in_output(
                scenario.red_herrings, rca_output,
            )
            herring_total = len(scenario.red_herrings)
            red_herring_penalty = herring_hits / herring_total if herring_total > 0 else 0.0

        else:
            red_herring_penalty = 0.0

        # ── Overall ───────────────────────────────────────────────────
        base_score = (
            self.rca_weight * rca_score
            + self.evidence_weight * evidence_score
        )
        overall_score = base_score * (1.0 - red_herring_penalty)

        return ScoredScenario(
            scenario_id=scenario.id,
            rca_score=rca_score,
            evidence_score=evidence_score,
            red_herring_penalty=red_herring_penalty,
            overall_score=overall_score,
            details={
                "rca": {
                    "expected": scenario.expected_rca,
                    "matched_count": rca_matched,
                    "total": rca_total,
                },
                "evidence": {
                    "required": scenario.required_evidence,
                    "found_count": ev_matched,
                    "total": ev_total,
                },
                "red_herrings": {
                    "present": scenario.red_herrings,
                    "penalty": round(red_herring_penalty, 3),
                },
                "weights": {
                    "rca_weight": self.rca_weight,
                    "evidence_weight": self.evidence_weight,
                },
            },
        )

    def build_context(self, scenario: Scenario) -> str:
        """Build a context string for the agent from a scenario.

        The context includes the title, description, and symptoms
        but deliberately *excludes* the expected RCA and red herrings.
        This is what you'd give the agent before asking it to investigate.
        """
        lines = [
            f"# Scenario: {scenario.title}",
            f"Severity: {scenario.severity}",
            "",
        ]
        if scenario.description:
            lines.append(scenario.description)
            lines.append("")

        lines.append("## Observed Symptoms")
        for symptom in scenario.symptoms:
            lines.append(f"- [{symptom.source}] {symptom.text}")
            if symptom.evidence_suggests:
                hints = ", ".join(symptom.evidence_suggests)
                lines.append(f"  → suggests checking: {hints}")

        return "\n".join(lines)

    # ── Matching ──────────────────────────────────────────────────────

    def _count_matches(self, expected: list[str], actual: list[str]) -> int:
        """Count how many expected items appear in the actual list.

        Uses substring matching on each actual item against each expected.
        """
        if not expected:
            return 0
        if not actual:
            return 0

        actual_normalised = [
            a.lower() if not self.case_sensitive else a
            for a in actual
        ]

        matches = 0
        for exp in expected:
            exp_norm = exp.lower() if not self.case_sensitive else exp
            for act in actual_normalised:
                if exp_norm in act or act in exp_norm:
                    matches += 1
                    break
        return matches

    def _count_matches_in_output(self, expected: list[str], output: list[str]) -> int:
        """Count how many expected items appear in the agent's output."""
        return self._count_matches(expected, output)


# ═══════════════════════════════════════════════════════════
# Scenario Definitions
# ═══════════════════════════════════════════════════════════

INFRASTRUCTURE_SCENARIOS: list[Scenario] = [
    Scenario(
        id="service_crash_loop",
        title="Web service crash-looping",
        description=(
            "Users on the customer-facing web app are seeing "
            "\"502 Bad Gateway\" errors. The backend service restarts "
            "every few minutes but does not stay up."
        ),
        symptoms=[
            Symptom("502 Bad Gateway errors in load balancer logs", "haproxy"),
            Symptom("Container exits with code 137 (OOM)", "k8s_events"),
            Symptom("Memory usage spikes to 95% before restart", "grafana"),
            Symptom("OutOfMemoryError in Java heap", "app_logs",
                    evidence_suggests=["heap_dump", "jvm_flags"]),
        ],
        expected_rca=["Java heap too small", "memory leak in request handler",
                       "OOM killer terminates process"],
        required_evidence=["heap_dump", "jvm_flags", "memory_profile"],
        red_herrings=["network misconfiguration", "DNS resolution failure",
                       "SSL certificate expired"],
        severity="critical",
        difficulty=0.6,
        tags=["web", "java", "memory", "k8s"],
    ),
    Scenario(
        id="db_slow_queries",
        title="Database query performance degradation",
        description=(
            "The product catalogue page takes 8-10 seconds to load "
            "(normally <200ms). CPU on the database server is at 98% "
            "and there are hundreds of active connections."
        ),
        symptoms=[
            Symptom("Page load time increased 40x", "user_reports",
                    evidence_suggests=["slow_query_log"]),
            Symptom("CPU at 98% on DB server", "grafana",
                    evidence_suggests=["top_processes"]),
            Symptom("Hundreds of active connections in pg_stat_activity",
                    "pg_monitoring"),
            Symptom("Queries spending 95% of time on sequential scans",
                    "pg_stat_statements"),
        ],
        expected_rca=["missing index on orders table",
                       "full table scan on large table"],
        required_evidence=["slow_query_log", "table_schema", "query_plan"],
        red_herrings=["application server too slow", "network latency",
                       "disk I/O bottleneck"],
        severity="high",
        difficulty=0.5,
        tags=["database", "performance", "postgresql"],
    ),
    Scenario(
        id="config_drift",
        title="Configuration drift after deployment",
        description=(
            "After a rolling update last night, the API gateway "
            "is returning 403 for valid requests. Only traffic "
            "on the new instances is affected."
        ),
        symptoms=[
            Symptom("403 Forbidden for authenticated requests", "api_gateway_logs"),
            Symptom("Only new pods affected; old pods work fine", "k8s_events",
                    evidence_suggests=["deployment_diff"]),
            Symptom("Auth service sees no errors on its side", "auth_service_logs"),
            Symptom("Rate limiting config changed in last deploy", "git_log"),
        ],
        expected_rca=["rate limit configuration too restrictive in new release",
                       "default rate limit changed from 1000/s to 10/s"],
        required_evidence=["deployment_diff", "rate_limit_config", "changelog"],
        red_herrings=["authentication token expired", "firewall rule changed",
                       "load balancer misconfiguration"],
        severity="high",
        difficulty=0.4,
        tags=["config", "deployment", "api"],
    ),
    Scenario(
        id="disk_full",
        title="Disk space exhaustion on log server",
        description=(
            "The centralised logging system stopped accepting new logs "
            "around 3 AM. Incident response team reports that the "
            "log aggregation server has 0 bytes free."
        ),
        symptoms=[
            Symptom("Log shipping failing with 'disk quota exceeded'", "fluentd_logs"),
            Symptom("Root partition at 100% on log-server-01", "grafana",
                    evidence_suggests=["disk_usage_report"]),
            Symptom("Weekly log rotation did not run", "cron_logs"),
            Symptom("Debug logging was enabled on all services 2 weeks ago",
                    "config_change_log"),
        ],
        expected_rca=["debug logging enabled across all services",
                       "log rotation cron job skipped / failed"],
        required_evidence=["disk_usage_report", "cron_status", "log_retention_policy"],
        red_herrings=["DDoS attack causing log flood", "hardware disk failure"],
        severity="medium",
        difficulty=0.3,
        tags=["logging", "disk", "operations"],
    ),
    Scenario(
        id="network_partition",
        title="Microservice partition — order service unreachable",
        description=(
            "The checkout flow fails at \"place order\" step. "
            "Frontend gets a timeout calling the order service. "
            "Other services are reachable from the frontend."
        ),
        symptoms=[
            Symptom("Checkout timeouts on order placement", "frontend_logs"),
            Symptom("Order service health check failing on port 8080",
                    "consul",
                    evidence_suggests=["service_discovery_status"]),
            Symptom("Other services (catalogue, auth) are healthy",
                    "health_checks"),
            Symptom("Order service pod is Running but not accepting traffic",
                    "k8s_events"),
        ],
        expected_rca=["service mesh sidecar proxy crashed",
                       "istio/envoy proxy unable to route to order service"],
        required_evidence=["service_discovery_status", "sidecar_logs", "network_policies"],
        red_herrings=["database migration in progress", "order service code bug",
                       "TLS certificate mismatch"],
        severity="critical",
        difficulty=0.7,
        tags=["network", "microservices", "service-mesh"],
    ),
    Scenario(
        id="ssl_cert_expired",
        title="SSL certificate expiration in staging",
        description=(
            "QA reports that the staging environment returns "
            "\"ERR_CERT_DATE_INVALID\" when accessed via HTTPS. "
            "The staging certificate was issued 90 days ago."
        ),
        symptoms=[
            Symptom("ERR_CERT_DATE_INVALID in browser", "qa_report",
                    evidence_suggests=["certificate_details"]),
            Symptom("Staging certificate expires in 2 days", "cert_manager",
                    evidence_suggests=["certificate_details"]),
            Symptom("No alert fired for certificate expiry", "alertmanager"),
            Symptom("Auto-renewal cron job is disabled", "cron_status"),
        ],
        expected_rca=["certificate auto-renewal not configured for staging",
                       "Let's Encrypt renewal cron job disabled"],
        required_evidence=["certificate_details", "renewal_config", "alert_rules"],
        red_herrings=["browser cache issue", "DNS resolution problem",
                       "CDN caching old certificate"],
        severity="medium",
        difficulty=0.3,
        tags=["security", "certificates", "staging"],
    ),
    Scenario(
        id="api_rate_limited",
        title="External API rate limiting",
        description=(
            "The payment processing pipeline is falling behind. "
            "Thousands of orders are stuck in \"processing\" state. "
            "The external payment gateway is returning HTTP 429."
        ),
        symptoms=[
            Symptom("Payment gateway returns HTTP 429 Too Many Requests",
                    "payment_service_logs"),
            Symptom("Order queue backlog growing", "rabbitmq"),
            Symptom("Rate limit was 100 req/s, now seeing 500 req/s",
                    "api_metrics",
                    evidence_suggests=["api_usage_report"]),
            Symptom("No rate limiter on payment service client",
                    "code_review"),
        ],
        expected_rca=["payment service sending requests without rate limiting",
                       "burst of traffic exceeding API quota"],
        required_evidence=["api_usage_report", "rate_limiter_config", "circuit_breaker_status"],
        red_herrings=["payment gateway outage", "network packet loss",
                       "incorrect API credentials"],
        severity="high",
        difficulty=0.5,
        tags=["api", "integration", "payments"],
    ),
    Scenario(
        id="dns_misconfig",
        title="DNS misconfiguration after infrastructure migration",
        description=(
            "After migrating DNS providers last week, the staging "
            "subdomain intermittently resolves to the old IP address. "
            "Some users see the old site, some see the new one."
        ),
        symptoms=[
            Symptom("Staging resolves to two different IPs", "dig",
                    evidence_suggests=["dns_records"]),
            Symptom("Old DNS records still have higher TTL (86400s)",
                    "dns_provider"),
            Symptom("New DNS provider only added 3 days ago",
                    "change_ticket"),
            Symptom("TTL was not lowered before migration",
                    "migration_plan"),
        ],
        expected_rca=["TTL not reduced before DNS migration",
                       "old DNS records not removed after cutover"],
        required_evidence=["dns_records", "migration_ticket", "ttl_config"],
        red_herrings=["CDN propagation delay", "browser cache",
                       "BGP routing issue"],
        severity="medium",
        difficulty=0.4,
        tags=["dns", "infrastructure", "migration"],
    ),
    Scenario(
        id="memory_leak",
        title="Memory leak in batch processor",
        description=(
            "The nightly batch job has been crashing for three nights "
            "in a row. It processes ~2M records but crashes around "
            "1.5M. Memory increases linearly during execution."
        ),
        symptoms=[
            Symptom("Batch job crashes at ~1.5M records", "batch_logs"),
            Symptom("Heap grows linearly from 256MB to 2GB",
                    "jvm_monitoring",
                    evidence_suggests=["heap_analysis"]),
            Symptom("No object deallocation visible in GC logs",
                    "gc_logs"),
            Symptom("List grows unbounded in DataProcessor.process()",
                    "code_review"),
        ],
        expected_rca=["unbounded list accumulation in DataProcessor",
                       "objects not released after each batch iteration"],
        required_evidence=["heap_analysis", "gc_logs", "code_diff"],
        red_herrings=["database connection leak", "too much input data",
                       "JVM version incompatible"],
        severity="high",
        difficulty=0.6,
        tags=["batch", "memory", "java"],
    ),
    Scenario(
        id="cache_stampede",
        title="Cache stampede taking down database",
        description=(
            "Every hour at :00, the database CPU spikes to 100% and "
            "queries queue up. The spike lasts 2-3 minutes then "
            "subsides. Cache hit rate drops to near 0 during the spike."
        ),
        symptoms=[
            Symptom("Hourly DB CPU spike to 100%", "grafana",
                    evidence_suggests=["cache_hit_rate"]),
            Symptom("Cache hit rate drops from 95% to 5% at :00",
                    "redis_metrics"),
            Symptom("Thousands of identical queries hit DB simultaneously",
                    "pg_stat_statements"),
            Symptom("Cache TTL is exactly 3600s for popular keys",
                    "cache_config"),
        ],
        expected_rca=["all cache entries expire at the same time",
                       "no jitter/stagger on cache TTL"],
        required_evidence=["cache_hit_rate", "cache_ttl_config", "db_query_pattern"],
        red_herrings=["DDoS attack", "scheduled database maintenance",
                       "network congestion"],
        severity="high",
        difficulty=0.5,
        tags=["caching", "database", "performance"],
    ),
]


# Additional scenario categories for future expansion
NETWORK_SCENARIOS: list[Scenario] = []
SECURITY_SCENARIOS: list[Scenario] = []

# All scenarios combined
ALL_SCENARIOS: list[Scenario] = [
    *INFRASTRUCTURE_SCENARIOS,
    *NETWORK_SCENARIOS,
    *SECURITY_SCENARIOS,
]

# Index by ID for quick lookup
_SCENARIO_INDEX: dict[str, Scenario] = {
    s.id: s for s in ALL_SCENARIOS
}


# ═══════════════════════════════════════════════════════════
# Convenience Functions
# ═══════════════════════════════════════════════════════════


def get_scenario(scenario_id: str) -> Scenario | None:
    """Get a scenario by ID."""
    return _SCENARIO_INDEX.get(scenario_id)


def scenario_summary() -> dict[str, Any]:
    """Get a summary of all available scenarios."""
    tags: dict[str, int] = {}
    severities: dict[str, int] = {}
    for s in ALL_SCENARIOS:
        for tag in s.tags:
            tags[tag] = tags.get(tag, 0) + 1
        severities[s.severity] = severities.get(s.severity, 0) + 1

    return {
        "scenarios": len(ALL_SCENARIOS),
        "tags": dict(sorted(tags.items(), key=lambda x: x[1], reverse=True)),
        "severities": severities,
        "avg_difficulty": round(
            sum(s.difficulty for s in ALL_SCENARIOS) / len(ALL_SCENARIOS),
            2,
        ) if ALL_SCENARIOS else 0.0,
        "ids": [s.id for s in ALL_SCENARIOS],
    }


def random_scenario(tags: list[str] | None = None) -> Scenario:
    """Pick a random scenario, optionally filtered by tags."""
    pool = ALL_SCENARIOS
    if tags:
        pool = [s for s in pool if any(t in s.tags for t in tags)]
    return random.choice(pool)


__all__ = [
    "Scenario",
    "Symptom",
    "Evidence",
    "ScenarioScorer",
    "ScoredScenario",
    "INFRASTRUCTURE_SCENARIOS",
    "ALL_SCENARIOS",
    "get_scenario",
    "scenario_summary",
    "random_scenario",
]
