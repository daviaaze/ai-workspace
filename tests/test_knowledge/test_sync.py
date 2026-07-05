"""Tests for sync.py — SyncManager with mocked IO."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_workspace.knowledge.sync import SyncManager


class TestSyncManagerInit:
    def test_default_urls_from_env(self):
        with patch.dict("os.environ", {
            "AIW_PRIMARY_DB_URL": "postgresql://user@primary/db",
            "AIW_LOCAL_DB_URL": "postgresql:///local",
        }, clear=False):
            mgr = SyncManager()
            assert "primary" in mgr.primary_db_url
            assert "local" in mgr.local_db_url

    def test_custom_urls(self):
        mgr = SyncManager(
            primary_db_url="postgresql://custom-primary/db",
            local_db_url="postgresql://custom-local/db",
        )
        assert "custom-primary" in mgr.primary_db_url
        assert "custom-local" in mgr.local_db_url

    def test_empty_queue_on_init(self):
        mgr = SyncManager()
        assert mgr._offline_queue == []


class TestOfflineQueue:
    def test_enqueue_adds_entry(self, tmp_path: Path):
        with patch.object(Path, "home", return_value=tmp_path):
            mgr = SyncManager()
            mgr.enqueue_offline("add_knowledge", content="test", title="test")
            assert len(mgr._offline_queue) == 1
            assert mgr._offline_queue[0]["op"] == "add_knowledge"
            assert mgr._offline_queue[0]["args"]["content"] == "test"

    def test_enqueue_with_timestamp(self, tmp_path: Path):
        with patch.object(Path, "home", return_value=tmp_path):
            mgr = SyncManager()
            mgr.enqueue_offline("remember", agent_name="alice", content="hello")
            entry = mgr._offline_queue[0]
            assert "timestamp" in entry
            assert entry["op"] == "remember"

    def test_save_and_load_persists_queue(self, tmp_path: Path):
        with patch.object(Path, "home", return_value=tmp_path):
            mgr = SyncManager()
            mgr.enqueue_offline("add_knowledge", content="test")
            mgr.enqueue_offline("save_research", query="test")

            # Create a new manager to test load
            mgr2 = SyncManager()
            mgr2._load_queue()
            assert len(mgr2._offline_queue) == 2
            assert mgr2._offline_queue[0]["op"] == "add_knowledge"
            assert mgr2._offline_queue[1]["op"] == "save_research"

    def test_enqueue_multiple_ops(self, tmp_path: Path):
        with patch.object(Path, "home", return_value=tmp_path):
            mgr = SyncManager()
            for i in range(5):
                mgr.enqueue_offline("add_knowledge", content=f"test{i}")
            assert len(mgr._offline_queue) == 5


class TestIsPrimaryAvailable:
    def test_returns_false_on_socket_error(self):
        with patch("socket.socket") as mock_socket:
            mock_instance = MagicMock()
            mock_socket.return_value = mock_instance
            mock_instance.connect_ex.return_value = 1  # Connection failed

            mgr = SyncManager(primary_db_url="postgresql://u@host:5432/db")
            assert mgr.is_primary_available() is False

    def test_returns_true_on_socket_success(self):
        with patch("socket.socket") as mock_socket:
            mock_instance = MagicMock()
            mock_socket.return_value = mock_instance
            mock_instance.connect_ex.return_value = 0  # Success

            mgr = SyncManager(primary_db_url="postgresql://u@host:5432/db")
            assert mgr.is_primary_available() is True

    def test_handles_exception_gracefully(self):
        with patch("socket.socket", side_effect=OSError("no net")):
            mgr = SyncManager(primary_db_url="postgresql://u@host:5432/db")
            assert mgr.is_primary_available() is False

    def test_no_at_sign_in_url(self):
        """When URL has no @, the default branch handles it."""
        mgr = SyncManager(primary_db_url="postgresql:///local")
        # Should not crash
        result = mgr.is_primary_available()
        assert isinstance(result, bool)


class TestGetStore:
    def test_returns_primary_when_available(self):
        with patch.object(SyncManager, "is_primary_available", return_value=True):
            with patch("ai_workspace.knowledge.sync.KnowledgeStore") as mock_store:
                mgr = SyncManager(primary_db_url="pg://primary/db")
                store = mgr.get_store()
                mock_store.assert_called_once_with(db_url="pg://primary/db")

    def test_returns_local_when_unavailable(self):
        with patch.object(SyncManager, "is_primary_available", return_value=False):
            with patch("ai_workspace.knowledge.sync.KnowledgeStore") as mock_store:
                mgr = SyncManager(local_db_url="pg://local/db")
                store = mgr.get_store()
                mock_store.assert_called_once_with(db_url="pg://local/db")


class TestSyncVault:
    def test_vault_does_not_exist_tries_clone(self, tmp_path: Path):
        vault = tmp_path / "nonexistent-vault"
        mgr = SyncManager(vault_path=str(vault))
        with patch("subprocess.run") as mock_run:
            result = asyncio.run(mgr.sync_vault())
            assert result.get("cloned") is True
            mock_run.assert_called_once()

    def test_vault_exists_runs_git_commands(self, tmp_path: Path):
        vault = tmp_path / "test-vault"
        vault.mkdir()
        mgr = SyncManager(vault_path=str(vault))
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = asyncio.run(mgr.sync_vault())
            assert "committed" in result
            assert "pulled" in result
            assert "pushed" in result

    def test_vault_error_handling(self, tmp_path: Path):
        vault = tmp_path / "test-vault"
        vault.mkdir()
        mgr = SyncManager(vault_path=str(vault))
        with patch("subprocess.run", side_effect=OSError("git failed")):
            result = asyncio.run(mgr.sync_vault())
            assert "error" in result
            assert "git failed" in result["error"]
