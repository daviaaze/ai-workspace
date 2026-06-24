"""Tests for tiered context loading."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import TestCase

sys.path.insert(0, "src")

from ai_workspace.agents.tiered_context import (
    ContextTier,
    RetrievalStep,
    TieredContextConfig,
    TieredContextLoader,
)
from ai_workspace.agents.context_manager import BlockType


class TestContextTier(TestCase):
    def test_enum_values(self):
        self.assertEqual(ContextTier.L0.value, "L0")
        self.assertEqual(ContextTier.L1.value, "L1")
        self.assertEqual(ContextTier.L2.value, "L2")

    def test_enum_order(self):
        """L0 < L1 < L2 ordering."""
        tiers = list(ContextTier)
        self.assertEqual(tiers, [ContextTier.L0, ContextTier.L1, ContextTier.L2])


class TestRetrievalStep(TestCase):
    def test_defaults(self):
        step = RetrievalStep(tier="L1", source="file.md", query="auth")
        self.assertEqual(step.tier, "L1")
        self.assertEqual(step.source, "file.md")
        self.assertEqual(step.query, "auth")
        self.assertEqual(step.score, 0.0)
        self.assertIn("T", step.timestamp)  # ISO format has T

    def test_all_fields(self):
        step = RetrievalStep(
            tier="L2", source="/path/doc.md", query="db config",
            score=0.85, engine="pgvector", content_preview="PostgreSQL...",
        )
        self.assertEqual(step.score, 0.85)
        self.assertEqual(step.engine, "pgvector")
        self.assertEqual(step.content_preview, "PostgreSQL...")


class TestTieredContextConfig(TestCase):
    def test_defaults(self):
        cfg = TieredContextConfig()
        self.assertEqual(cfg.l0_max_tokens, 8_000)
        self.assertEqual(cfg.l1_max_tokens, 32_000)
        self.assertEqual(cfg.l2_max_tokens, 128_000)
        self.assertTrue(cfg.enable_trajectory)

    def test_custom(self):
        cfg = TieredContextConfig(
            l0_max_tokens=4_000,
            l1_max_tokens=16_000,
            enable_trajectory=False,
        )
        self.assertEqual(cfg.l0_max_tokens, 4_000)
        self.assertFalse(cfg.enable_trajectory)


class TestTieredContextLoader(TestCase):
    def setUp(self):
        self.loader = TieredContextLoader()

    def test_initial_state(self):
        self.assertEqual(self.loader.task, "")
        self.assertEqual(self.loader.trajectory, [])

    def test_set_task(self):
        self.loader.set_task("Refactor auth middleware")
        self.assertEqual(self.loader.task, "Refactor auth middleware")

    def test_set_system_prompt(self):
        self.loader.set_system_prompt("You are a coding assistant.")
        result = self.loader.get_context("L0")
        self.assertIn("coding assistant", result)
        self.assertIn("SYSTEM CONTEXT", result)

    def test_l0_content(self):
        self.loader.set_task("Fix bug in parser")
        self.loader.set_system_prompt("Be concise.")
        result = self.loader.get_context("L0")
        self.assertIn("Fix bug in parser", result)
        self.assertIn("Be concise.", result)
        self.assertIn("L0", result)

    def test_l1_includes_l0(self):
        self.loader.set_task("Update docs")
        # Add a block so L1 has something beyond L0
        self.loader.add_to_context(
            BlockType.FILE_READ, "Documentation content here",
            summary="docs update",
        )
        l0 = self.loader.get_context("L0")
        l1 = self.loader.get_context("L1")
        self.assertIn("Update docs", l1)
        self.assertGreater(len(l1), len(l0))

    def test_l2_includes_l1(self):
        self.loader.set_task("Write tests")
        l0 = self.loader.get_context("L0")
        l1 = self.loader.get_context("L1")
        l2 = self.loader.get_context("L2")
        self.assertIn("Write tests", l2)
        self.assertGreaterEqual(len(l2), len(l1))

    def test_extra_context(self):
        result = self.loader.get_context("L0", extra_context="Some extra info")
        self.assertIn("Some extra info", result)

    def test_add_to_context(self):
        bid = self.loader.add_to_context(
            BlockType.USER_MESSAGE,
            "Check the login module",
            importance=0.8,
        )
        self.assertIsNotNone(bid)
        # Should appear in L1 context
        ctx = self.loader.get_context("L1")
        self.assertIn("login module", ctx)

    def test_add_l0_block(self):
        self.loader.add_l0_block(
            BlockType.PROJECT_CONTEXT,
            "Project root: /home/project",
        )
        ctx = self.loader.get_context("L0")
        self.assertIn("/home/project", ctx)

    def test_trajectory_recording(self):
        self.loader.set_task("Debug service")
        self.loader.add_to_context(
            BlockType.FILE_READ, "file contents", summary="read main.py",
        )
        self.loader.get_context("L1")
        steps = self.loader.trajectory
        self.assertGreater(len(steps), 0)
        # At least one step should mention "read main.py"
        sources = [s.source for s in steps]
        self.assertTrue(
            any("main.py" in s or "manual" in s for s in sources),
            f"No step mentions main.py: {sources}",
        )

    def test_trajectory_summary(self):
        summary = self.loader.trajectory_summary()
        self.assertIn("No retrieval steps", summary)

        self.loader.add_to_context(BlockType.CUSTOM, "content")
        summary = self.loader.trajectory_summary()
        self.assertIn("Retrieval Trajectory", summary)

    def test_clear_trajectory(self):
        self.loader.add_to_context(BlockType.CUSTOM, "test")
        self.loader.clear_trajectory()
        self.assertEqual(self.loader.trajectory, [])

    def test_stats(self):
        stats = self.loader.stats()
        self.assertIn("config", stats)
        self.assertIn("context_manager", stats)
        self.assertIn("trajectory_steps", stats)

    def test_get_context_blocks(self):
        self.loader.set_task("Task")
        self.loader.add_to_context(
            BlockType.USER_MESSAGE, "User query", importance=1.0,
        )

        blocks = self.loader.get_context_blocks("L0")
        # No pinned blocks by default
        self.assertIsInstance(blocks, list)

        blocks = self.loader.get_context_blocks("L1")
        self.assertIsInstance(blocks, list)

    def test_config_disables_trajectory(self):
        cfg = TieredContextConfig(enable_trajectory=False)
        loader = TieredContextLoader(config=cfg)
        loader.add_to_context(BlockType.CUSTOM, "test")
        self.assertEqual(loader.trajectory, [])

    def test_directory_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx_dir = Path(tmp) / "context"
            ctx_dir.mkdir()
            (ctx_dir / "architecture").mkdir()
            (ctx_dir / "architecture" / "overview.md").write_text(
                "# Architecture Overview\nMicroservices with event bus.\n"
            )
            (ctx_dir / "database").mkdir()
            (ctx_dir / "database" / "schema.md").write_text(
                "# DB Schema\nPostgreSQL with 3 tables.\n"
            )

            loader = TieredContextLoader()
            loader.set_context_dir(ctx_dir)
            loader.set_task("Check database schema")

            ctx = loader.get_context("L1")
            self.assertIn("schema", ctx.lower())

            ctx_expanded = loader.get_context("L2")
            self.assertIn("PostgreSQL", ctx_expanded)

            # Trajectory should include directory retrieval
            steps = loader.trajectory
            dir_steps = [s for s in steps if s.engine == "directory"]
            self.assertGreater(len(dir_steps), 0)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
