"""Tests for Partner system."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from ai_workspace.agents.loop import LoopEvent

sys.path.insert(0, "src")

# Patch PARTNERS_DIR to temp dir before importing
import ai_workspace.agents.partner as pm
from ai_workspace.agents.partner import (
    Partner,
    ToolPolicy,
    slugify,
)


class TestSlugify(TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Code Critic"), "code-critic")

    def test_special_chars(self):
        self.assertEqual(slugify("Hello! World?"), "hello-world")

    def test_already_slug(self):
        self.assertEqual(slugify("my-partner"), "my-partner")

    def test_empty(self):
        self.assertEqual(slugify(""), "partner")


class TestToolPolicy(TestCase):
    def test_allow_all_by_default(self):
        policy = ToolPolicy()
        self.assertTrue(policy.is_allowed("any_tool"))

    def test_deny_specific(self):
        policy = ToolPolicy(denied=["rm", "write"])
        self.assertFalse(policy.is_allowed("rm"))
        self.assertFalse(policy.is_allowed("write"))
        self.assertTrue(policy.is_allowed("read"))

    def test_whitelist(self):
        policy = ToolPolicy(allowed=["read", "search"])
        self.assertTrue(policy.is_allowed("read"))
        self.assertFalse(policy.is_allowed("write"))

    def test_deny_overrides_allow(self):
        policy = ToolPolicy(allowed=["read", "search"], denied=["read"])
        self.assertFalse(policy.is_allowed("read"))
        self.assertTrue(policy.is_allowed("search"))

    def test_to_dict_empty(self):
        policy = ToolPolicy()
        self.assertEqual(policy.to_dict(), {})

    def test_to_dict_allowed(self):
        policy = ToolPolicy(allowed=["read"])
        self.assertEqual(policy.to_dict(), {"allowed": ["read"]})

    def test_to_dict_denied(self):
        policy = ToolPolicy(denied=["rm"])
        self.assertEqual(policy.to_dict(), {"denied": ["rm"]})

    def test_from_dict_none(self):
        policy = ToolPolicy.from_dict(None)
        self.assertIsNone(policy.allowed)

    def test_from_dict_full(self):
        policy = ToolPolicy.from_dict({"allowed": ["read"], "denied": ["write"]})
        self.assertEqual(policy.allowed, ["read"])
        self.assertEqual(policy.denied, ["write"])


class TestPartnerCreate(TestCase):
    def setUp(self):
        # Use a temp directory as partners dir
        self._tmp = tempfile.TemporaryDirectory()
        self._partners_dir = Path(self._tmp.name)
        # Monkey-patch the module constant
        self._orig_dir = pm._PARTNERS_DIR
        pm._PARTNERS_DIR = self._partners_dir

    def tearDown(self):
        pm._PARTNERS_DIR = self._orig_dir
        self._tmp.cleanup()

    def test_create_basic(self):
        p = Partner.create(name="Code Critic")
        self.assertEqual(p.name, "Code Critic")
        self.assertEqual(p.partner_id, "code-critic")
        self.assertTrue(p.soul)
        self.assertTrue(p.base_dir.exists())
        self.assertTrue(p.workspace_dir.exists())
        self.assertTrue(p.memory_dir.exists())
        self.assertTrue(p.knowledge_dir.exists())
        self.assertTrue(p.sessions_dir.exists())
        self.assertTrue(p.soul_file.exists())

    def test_create_with_custom_soul(self):
        soul = "# Soul\nI am a ruthless code reviewer."
        p = Partner.create(name="Critic", soul=soul)
        self.assertEqual(p.soul, soul)
        self.assertIn("ruthless", p.soul_preview)

    def test_create_with_description(self):
        p = Partner.create(name="Helper", description="Friendly assistant")
        self.assertEqual(p.description, "Friendly assistant")

    def test_create_with_tool_policy(self):
        policy = ToolPolicy(allowed=["read", "search"], denied=["write"])
        p = Partner.create(name="Limited", tool_policy=policy)
        self.assertFalse(p.tool_policy.is_allowed("write"))
        self.assertTrue(p.tool_policy.is_allowed("read"))

    def test_create_with_emoji_color(self):
        p = Partner.create(name="Star", emoji="⭐", color="#FFD700")
        self.assertEqual(p.emoji, "⭐")
        self.assertEqual(p.color, "#FFD700")

    def test_create_duplicate_raises(self):
        Partner.create(name="Unique")
        with self.assertRaises(FileExistsError):
            Partner.create(name="Unique")

    def test_create_overwrite(self):
        Partner.create(name="ReplaceMe", soul="old soul")
        p2 = Partner.create(name="ReplaceMe", soul="new soul", overwrite=True)
        self.assertEqual(p2.soul, "new soul")

    def test_slugify_special_chars(self):
        p = Partner.create(name="Hello! World?")
        self.assertEqual(p.partner_id, "hello-world")

class TestPartnerLoad(TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._partners_dir = Path(self._tmp.name)
        self._orig_dir = pm._PARTNERS_DIR
        pm._PARTNERS_DIR = self._partners_dir

    def tearDown(self):
        pm._PARTNERS_DIR = self._orig_dir
        self._tmp.cleanup()

    def test_load_created_partner(self):
        Partner.create(name="Test Partner", description="desc", emoji="📝")
        loaded = Partner.load("test-partner")
        self.assertEqual(loaded.name, "Test Partner")
        self.assertEqual(loaded.description, "desc")
        self.assertEqual(loaded.emoji, "📝")
        self.assertTrue(loaded.soul)

    def test_load_missing_raises(self):
        with self.assertRaises(FileNotFoundError):
            Partner.load("nonexistent")

    def test_list_all(self):
        self.assertEqual(Partner.list_all(), [])
        Partner.create(name="Alpha")
        Partner.create(name="Beta")
        partners = Partner.list_all()
        self.assertEqual(len(partners), 2)
        names = {p.name for p in partners}
        self.assertEqual(names, {"Alpha", "Beta"})

    def test_get_by_id(self):
        Partner.create(name="Target")
        p = Partner.get("target")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "Target")

    def test_get_by_slug(self):
        Partner.create(name="My Partner")
        p = Partner.get("my-partner")
        self.assertIsNotNone(p)

    def test_get_by_name_case_insensitive(self):
        Partner.create(name="CodeReviewer")
        p = Partner.get("codereviewer")
        self.assertIsNotNone(p)
        self.assertEqual(p.name, "CodeReviewer")

    def test_get_missing(self):
        self.assertIsNone(Partner.get("nobody"))


class TestPartnerSaveDelete(TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._partners_dir = Path(self._tmp.name)
        self._orig_dir = pm._PARTNERS_DIR
        pm._PARTNERS_DIR = self._partners_dir

    def tearDown(self):
        pm._PARTNERS_DIR = self._orig_dir
        self._tmp.cleanup()

    def test_save_updates_timestamp(self):
        p = Partner.create(name="Saver")
        old = p.updated_at
        p.save()
        self.assertNotEqual(p.updated_at, old)

    def test_delete_removes_directory(self):
        p = Partner.create(name="Goner")
        self.assertTrue(p.base_dir.exists())
        p.delete()
        self.assertFalse(p.base_dir.exists())

    def test_to_dict(self):
        p = Partner.create(name="DictTest", description="testing")
        d = p.to_dict()
        self.assertEqual(d["name"], "DictTest")
        self.assertEqual(d["description"], "testing")
        self.assertIn("soul_preview", d)
        self.assertIn("soul_length", d)


class TestPartnerConsult(TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._partners_dir = Path(self._tmp.name)
        self._orig_dir = pm._PARTNERS_DIR
        pm._PARTNERS_DIR = self._partners_dir

    def tearDown(self):
        pm._PARTNERS_DIR = self._orig_dir
        self._tmp.cleanup()

    @patch("ai_workspace.agents.loop.agent_loop")
    def test_consult_returns_string(self, mock_loop):
        """consult() returns response containing partner name and query."""
        async def fake_loop(params):
            yield LoopEvent(type="token", data={"text": "[Consultant] "})
            yield LoopEvent(type="token", data={"text": f"Regarding '{params.task}': "})
            yield LoopEvent(type="token", data={"text": "here is my perspective."})
            yield LoopEvent(type="done", data={"reason": "completed"})
        mock_loop.return_value = fake_loop(None)

        p = Partner.create(name="Consultant")
        response = p.consult("What is the meaning of life?")
        self.assertIn("Consultant", response)
        self.assertIn("meaning of life", response)

    @patch("ai_workspace.agents.loop.agent_loop")
    def test_consult_with_memory(self, mock_loop):
        """consult() includes memory_context in the system prompt."""
        async def fake_loop(params):
            # Verify memory_context was included in system_prompt
            assert "User likes Python" in params.system_prompt
            yield LoopEvent(type="token", data={"text": "[MemoryAware] Hello!"})
            yield LoopEvent(type="done", data={"reason": "completed"})
        mock_loop.return_value = fake_loop(None)

        p = Partner.create(name="MemoryAware")
        response = p.consult("Hello", memory_context="User likes Python")
        self.assertIn("Hello", response)


class TestEnsurePartnersDir(TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig_dir = pm._PARTNERS_DIR
        pm._PARTNERS_DIR = Path(self._tmp.name)

    def tearDown(self):
        pm._PARTNERS_DIR = self._orig_dir
        self._tmp.cleanup()

    def test_creates_dir(self):
        pm._PARTNERS_DIR = Path(self._tmp.name) / "new_partners"
        self.assertFalse(pm._PARTNERS_DIR.exists())
        result = pm.ensure_partners_dir()
        self.assertTrue(result.exists())


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
