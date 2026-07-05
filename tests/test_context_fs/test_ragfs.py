"""Tests for RAGFS — context as filesystem."""

import sys; sys.path.insert(0, "src")
import tempfile
import unittest
from pathlib import Path
from unittest import TestCase

from ai_workspace.context_fs import (
    VirtualContextFS,
    mount_fuse,
)


class TestVirtualContextFS(TestCase):
    def setUp(self):
        # Use temp dirs for testing
        self._tmp = tempfile.TemporaryDirectory()
        self._tmp_root = Path(self._tmp.name) / "context"
        self._tmp_memory = Path(self._tmp.name) / "memory"
        self._tmp_root.mkdir(parents=True, exist_ok=True)
        self._tmp_memory.mkdir(parents=True, exist_ok=True)
        self._tmp_kb = Path(self._tmp.name) / "knowledge"
        self._tmp_kb.mkdir(parents=True, exist_ok=True)
        self.fs = VirtualContextFS(
            root=self._tmp_root,
            knowledge_root=self._tmp_kb,
        )
        # Monkey-patch memory root
        self.fs._memory_root = self._tmp_memory

    def tearDown(self):
        self._tmp.cleanup()

    # ── Root Listing ────────────────────────────────────────────────

    def test_ls_root(self):
        entries = self.fs.ls("/")
        names = [e["name"] for e in entries]
        self.assertIn("kb", names)
        self.assertIn("memory", names)
        self.assertIn("trace", names)
        self.assertIn("info", names)

    def test_ls_root_has_types(self):
        entries = self.fs.ls("/")
        for e in entries:
            self.assertIn(e["type"], ("dir", "file"))

    # ── Info ────────────────────────────────────────────────────────

    def test_read_info(self):
        info = self.fs.read("/info")
        self.assertIn("RAGFS", info)
        self.assertIn("kb/", info)
        self.assertIn("memory/", info)

    def test_info_exists(self):
        self.assertTrue(self.fs.exists("/info"))

    def test_info_size(self):
        info = self.fs.read("/info")
        self.assertGreater(len(info), 100)

    # ── KB ──────────────────────────────────────────────────────────

    def test_ls_kb_root(self):
        entries = self.fs.ls("/kb/")
        # At minimum should have 'search' dir
        names = [e["name"] for e in entries]
        self.assertIn("search", names)

    def test_read_kb_no_doc_raises(self):
        with self.assertRaises(FileNotFoundError):
            self.fs.read("/kb/nonexistent")

    def test_search_no_results(self):
        result = self.fs.read("/kb/search/zzzznonexistent")
        self.assertIn("No results", result)

    # ── Memory ──────────────────────────────────────────────────────

    def test_ls_memory_root(self):
        entries = self.fs.ls("/memory/")
        names = [e["name"] for e in entries]
        self.assertIn("l1", names)
        self.assertIn("l2", names)
        self.assertIn("l3", names)

    def test_read_memory_overview(self):
        content = self.fs.read("/memory/")
        self.assertIn("Three-tier", content)
        self.assertIn("L1", content)

    def test_read_memory_empty_tier(self):
        content = self.fs.read("/memory/l1")
        self.assertIn("L1", content)

    def test_read_memory_tier_not_found(self):
        with self.assertRaises(FileNotFoundError):
            self.fs.read("/memory/l4")

    # ── Trace ───────────────────────────────────────────────────────

    def test_ls_trace_empty(self):
        entries = self.fs.ls("/trace/")
        self.assertEqual(entries, [])

    def test_read_trace_missing(self):
        with self.assertRaises(FileNotFoundError):
            self.fs.read("/trace/nonexistent")

    # ── Write ───────────────────────────────────────────────────────

    def test_write_memory_l2(self):
        path = self.fs.write("/memory/l2/test_fact", "Test content")
        self.assertIn("l2", path)
        self.assertTrue(Path(path).exists())
        self.assertEqual(Path(path).read_text(), "Test content")

    def test_write_memory_l3(self):
        path = self.fs.write("/memory/l3/my_summary", "Summary text")
        self.assertIn("l3", path)
        self.assertTrue(Path(path).exists())

    def test_write_notes_default(self):
        path = self.fs.write("/notes/my_note.txt", "Note content")
        self.assertIn("notes", path)
        self.assertTrue(Path(path).exists())

    def test_write_then_read_memory(self):
        self.fs.write("/memory/l2/myfact", "Important fact")
        content = self.fs.read("/memory/l2/myfact")
        self.assertEqual(content, "Important fact")

    def test_write_then_read_memory_with_ext(self):
        self.fs.write("/memory/l2/myfact", "Important fact")
        content = self.fs.read("/memory/l2/myfact.md")
        self.assertEqual(content, "Important fact")

    # ── Exists ──────────────────────────────────────────────────────

    def test_exists_root(self):
        self.assertTrue(self.fs.exists("/"))

    def test_exists_info(self):
        self.assertTrue(self.fs.exists("/info"))

    def test_exists_kb(self):
        self.assertTrue(self.fs.exists("/kb/"))

    def test_exists_memory(self):
        self.assertTrue(self.fs.exists("/memory/"))

    def test_not_exists(self):
        self.assertFalse(self.fs.exists("/nonexistent/path"))

    # ── Path edge cases ─────────────────────────────────────────────

    def test_path_with_double_slashes(self):
        entries = self.fs.ls("//kb//")
        self.assertGreater(len(entries), 0)

    def test_path_trailing_slash(self):
        info = self.fs.read("/info/")
        self.assertIn("RAGFS", info)


class TestFuseMount(TestCase):
    def test_mount_raises_without_fusepy(self):
        with self.assertRaises(ImportError):
            mount_fuse("/tmp/fake_mount")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
