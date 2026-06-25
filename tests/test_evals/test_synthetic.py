"""Tests for synthetic evaluation scenarios."""

import sys; sys.path.insert(0, "src")
import unittest
from unittest import TestCase
from ai_workspace.evals.synthetic import (
    Scenario,
    Symptom,
    Evidence,
    ScenarioScorer,
    ScoredScenario,
    INFRASTRUCTURE_SCENARIOS,
    ALL_SCENARIOS,
)


class TestSymptom(TestCase):
    def test_minimal(self):
        s = Symptom(text="Server 500 errors", source="monitoring")
        self.assertEqual(s.text, "Server 500 errors")
        self.assertEqual(s.source, "monitoring")

    def test_with_evidence_link(self):
        s = Symptom(text="High CPU", source="grafana", evidence_suggests=["cpu_bound"])
        self.assertIn("cpu_bound", s.evidence_suggests)


class TestEvidence(TestCase):
    def test_minimal(self):
        e = Evidence(id="log_error_rate", label="Error rate is 35%")
        self.assertEqual(e.id, "log_error_rate")

    def test_with_criticality(self):
        e = Evidence(id="db_conn", label="DB connections at max", critical=True)
        self.assertTrue(e.critical)


class TestScenario(TestCase):
    def test_minimal(self):
        s = Scenario(
            id="service_down",
            title="Service is down",
            symptoms=[Symptom(text="500 errors", source="logs")],
            expected_rca=["database connection failure"],
        )
        self.assertEqual(s.id, "service_down")
        self.assertEqual(len(s.symptoms), 1)
        self.assertEqual(len(s.expected_rca), 1)

    def test_full(self):
        s = Scenario(
            id="db_slow",
            title="Database slow queries",
            description="Users report slow page loads",
            symptoms=[
                Symptom(text="Slow queries", source="pg_stat_activity"),
                Symptom(text="High CPU", source="top"),
            ],
            expected_rca=["missing index on orders table"],
            required_evidence=["slow_query_log", "table_schema"],
            red_herrings=["network latency", "disk failure"],
            severity="medium",
        )
        self.assertEqual(s.severity, "medium")
        self.assertEqual(len(s.red_herrings), 2)

    def test_severity_default(self):
        s = Scenario(id="test", title="Test", symptoms=[], expected_rca=["x"])
        self.assertEqual(s.severity, "high")

    def test_difficulty_default(self):
        s = Scenario(id="test", title="Test", symptoms=[], expected_rca=["x"])
        self.assertEqual(s.difficulty, 0.5)

    def test_tags(self):
        s = Scenario(
            id="test", title="Test",
            symptoms=[], expected_rca=["x"],
            tags=["database", "performance"],
        )
        self.assertIn("database", s.tags)


class TestScenarioScorer(TestCase):
    def setUp(self):
        self.scorer = ScenarioScorer()

    def test_perfect_match(self):
        scenario = Scenario(
            id="test", title="Test",
            symptoms=[Symptom("Error", "logs")],
            expected_rca=["database connection lost"],
            required_evidence=["error_log_entry"],
        )
        result = self.scorer.score(
            scenario=scenario,
            rca_output=["database connection lost"],
            evidence_found=["error_log_entry"],
        )
        self.assertEqual(result.rca_score, 1.0)
        self.assertEqual(result.evidence_score, 1.0)
        self.assertEqual(result.red_herring_penalty, 0.0)
        self.assertEqual(result.overall_score, 1.0)

    def test_partial_rca(self):
        scenario = Scenario(
            id="test", title="Test",
            symptoms=[Symptom("Error", "logs")],
            expected_rca=["database connection lost", "connection pool exhausted"],
            required_evidence=["error_log"],
        )
        result = self.scorer.score(
            scenario=scenario,
            rca_output=["database connection lost"],
            evidence_found=["error_log"],
        )
        self.assertAlmostEqual(result.rca_score, 0.5)
        self.assertAlmostEqual(result.overall_score, 0.75)

    def test_missing_evidence(self):
        scenario = Scenario(
            id="test", title="Test",
            symptoms=[Symptom("Error", "logs")],
            expected_rca=["database down"],
            required_evidence=["error_log", "db_status", "cpu_metric"],
        )
        result = self.scorer.score(
            scenario=scenario,
            rca_output=["database down"],
            evidence_found=["error_log"],
        )
        self.assertEqual(result.rca_score, 1.0)
        self.assertAlmostEqual(result.evidence_score, 1/3)
        self.assertAlmostEqual(result.overall_score, (1.0 + 1/3) / 2)

    def test_red_herring_penalty(self):
        scenario = Scenario(
            id="test", title="Test",
            symptoms=[Symptom("Error", "logs")],
            expected_rca=["database down"],
            required_evidence=["evidence_1"],
            red_herrings=["network issue", "disk full"],
        )
        result = self.scorer.score(
            scenario=scenario,
            rca_output=["database down", "network issue"],
            evidence_found=[],
        )
        # rca=1.0, evidence=0.0, base=(0.5*1.0+0.5*0.0)=0.5
        # red herrings: 1/2 hit = 0.5 penalty
        # overall = 0.5 * (1 - 0.5) = 0.25
        self.assertAlmostEqual(result.red_herring_penalty, 0.5)
        self.assertAlmostEqual(result.overall_score, 0.25)

    def test_empty_rca_and_evidence(self):
        scenario = Scenario(
            id="test", title="Test",
            symptoms=[Symptom("Error", "logs")],
            expected_rca=["database down"],
            required_evidence=["error_log"],
        )
        result = self.scorer.score(
            scenario=scenario,
            rca_output=[],
            evidence_found=[],
        )
        self.assertEqual(result.rca_score, 0.0)
        self.assertEqual(result.evidence_score, 0.0)

    def test_weighted_scoring(self):
        scenario = Scenario(
            id="test", title="Test",
            symptoms=[Symptom("Error", "logs")],
            expected_rca=["database down"],
            required_evidence=["error_log"],
        )
        scorer = ScenarioScorer(rca_weight=0.7, evidence_weight=0.3)
        result = scorer.score(scenario=scenario, rca_output=["database down"], evidence_found=["error_log"])
        self.assertEqual(result.overall_score, 1.0)

        result2 = scorer.score(scenario=scenario, rca_output=["database down"], evidence_found=[])
        # overall = 0.7 * 1.0 + 0.3 * 0.0 = 0.7
        self.assertAlmostEqual(result2.overall_score, 0.7)

    def test_scenario_includes_symptoms_in_context(self):
        scenario = Scenario(
            id="web_degraded",
            title="Web server degraded",
            description="Pages load 5x slower than normal",
            symptoms=[
                Symptom(text="latency > 5s", source="user_reports"),
                Symptom(text="CPU at 95%", source="top"),
            ],
            expected_rca=["memory leak in worker process"],
        )
        context = self.scorer.build_context(scenario)
        self.assertIn("latency", context)
        self.assertIn("CPU at 95%", context)
        self.assertIn("Web server degraded", context)
        # expected_rca NOT included in context (that's what agent must find)


class TestScenarioDefinitions(TestCase):
    def test_scenarios_exist(self):
        self.assertGreater(len(ALL_SCENARIOS), 0)

    def test_infrastructure_scenarios(self):
        self.assertGreaterEqual(len(INFRASTRUCTURE_SCENARIOS), 5)

    def test_each_scenario_has_id(self):
        for s in ALL_SCENARIOS:
            self.assertTrue(s.id, f"Scenario missing id: {s.title}")

    def test_each_scenario_has_symptoms(self):
        for s in ALL_SCENARIOS:
            self.assertGreater(
                len(s.symptoms), 0,
                f"Scenario {s.id} has no symptoms",
            )

    def test_each_scenario_has_expected_rca(self):
        for s in ALL_SCENARIOS:
            self.assertGreater(
                len(s.expected_rca), 0,
                f"Scenario {s.id} has no expected RCA",
            )

    def test_get_by_id(self):
        from ai_workspace.evals.synthetic import get_scenario
        s = get_scenario("db_slow_queries")
        self.assertIsNotNone(s)
        self.assertEqual(s.id, "db_slow_queries")

    def test_get_by_id_missing(self):
        from ai_workspace.evals.synthetic import get_scenario
        s = get_scenario("nonexistent")
        self.assertIsNone(s)

    def test_summary(self):
        from ai_workspace.evals.synthetic import scenario_summary
        summary = scenario_summary()
        self.assertIn("scenarios", summary)
        self.assertGreater(summary["scenarios"], 0)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
