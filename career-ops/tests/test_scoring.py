from __future__ import annotations

import unittest

from career_ops.scoring import score_vaga


class ScoreVagaTests(unittest.TestCase):
    def test_missing_php_in_title_blocks_planiteasy_shape(self) -> None:
        result = score_vaga(
            "PlanitEasy",
            "Senior Backend Engineer — PHP + Sabre/GDS",
            "Remote travel role with Node.js, AWS and booking systems.",
        )

        self.assertEqual("descartar", result["decisao"])
        self.assertLessEqual(result["score"], 4)
        self.assertIn("ausente: PHP", result["hard_gaps"])

    def test_required_pending_skill_requires_human_review(self) -> None:
        result = score_vaga(
            "DirectCo",
            "Senior Backend Engineer",
            "Remote B2B role. NestJS is mandatory. Node.js and TypeScript on AWS.",
        )

        self.assertEqual("avaliar", result["decisao"])
        self.assertLessEqual(result["score"], 6)
        self.assertIn("pendente: NestJS", result["hard_gaps"])

    def test_skill_under_required_heading_triggers_gate(self) -> None:
        result = score_vaga(
            "DirectCo",
            "Senior Backend Engineer",
            "Requirements:\\n- PHP\\n- Node.js\\nNice to have:\\n- GraphQL",
        )

        self.assertEqual("descartar", result["decisao"])
        self.assertIn("ausente: PHP", result["hard_gaps"])

    def test_optional_php_does_not_trigger_hard_gate(self) -> None:
        result = score_vaga(
            "DirectCo",
            "Senior Node.js Engineer",
            "Remote Node.js and TypeScript role. PHP is nice to have, not required.",
        )

        self.assertNotEqual("descartar", result["decisao"])
        self.assertNotIn("ausente: PHP", result["hard_gaps"])

    def test_deep_sabre_requirement_is_classified_as_partial(self) -> None:
        result = score_vaga(
            "DirectTravel",
            "Senior Backend Engineer",
            "Remote B2B Node.js TypeScript role requiring deep Sabre expertise.",
        )

        self.assertEqual("avaliar", result["decisao"])
        self.assertIn("parcial: Sabre além de ticketing/pós-booking", result["hard_gaps"])

    def test_aligned_direct_role_can_reach_apply(self) -> None:
        result = score_vaga(
            "DirectTravel",
            "Senior Node.js TypeScript Backend Engineer",
            "Remote B2B contractor building AWS travel booking integrations.",
        )

        self.assertEqual("aplicar", result["decisao"])
        self.assertEqual([], result["hard_gaps"])

    def test_intermediary_is_discarded_before_scoring(self) -> None:
        result = score_vaga(
            "Combine",
            "Senior Node.js TypeScript Engineer",
            "Remote AWS travel role.",
        )

        self.assertEqual("descartar", result["decisao"])
        self.assertEqual(0, result["score"])


if __name__ == "__main__":
    unittest.main()
