"""
Tests for connection pooling and dependency injection (core/db.py).

Covers:
- ConnectionPool creation and reuse
- get_store() singleton behavior
- reset_store() cleanup
- get_connection() / return_connection() lifecycle
- KnowledgeStore transparent pool usage
- KnowledgeStore fallback to direct connect
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import psycopg2
import pytest

from ai_workspace.core.db import (
    close_pool,
    get_connection,
    get_pool,
    get_store,
    reset_store,
    return_connection,
)

# ═══════════════════════════════════════════════════════
# Setup / teardown
# ═══════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _clean_pool():
    """Reset pool state before each test."""
    reset_store()
    yield
    reset_store()


# ═══════════════════════════════════════════════════════
# Pool creation
# ═══════════════════════════════════════════════════════


class TestPoolCreation:
    """get_pool() creates and reuses a ThreadedConnectionPool."""

    def test_get_pool_creates_pool(self):
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            p = get_pool("postgresql:///test_db")
            mock_pool.assert_called_once_with(
                minconn=1, maxconn=5, dsn="postgresql:///test_db"
            )
            assert p is mock_pool.return_value

    def test_get_pool_reuses_same_url(self):
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            p1 = get_pool("postgresql:///db_a")
            p2 = get_pool("postgresql:///db_a")
            assert p1 is p2
            mock_pool.assert_called_once()  # Only created once

    def test_get_pool_different_url_recreates(self):
        old = MagicMock()
        with patch("psycopg2.pool.ThreadedConnectionPool", return_value=old) as mock_pool:
            get_pool("postgresql:///db_a")
            get_pool("postgresql:///db_b")
            assert mock_pool.call_count == 2
            old.closeall.assert_called_once()  # Old pool closed

    def test_get_pool_custom_limits(self):
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            get_pool("postgresql:///test", min_connections=3, max_connections=10)
            mock_pool.assert_called_once_with(
                minconn=3, maxconn=10, dsn="postgresql:///test"
            )

    def test_get_pool_default_url_from_env(self, monkeypatch):
        monkeypatch.setenv("AIW_DB_URL", "postgresql://env_host/db")
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            get_pool()
            mock_pool.assert_called_once_with(
                minconn=1, maxconn=5, dsn="postgresql://env_host/db"
            )

    def test_get_pool_handles_closeall_error(self):
        """Old pool closeall failure should not prevent new pool creation."""
        old = MagicMock()
        old.closeall.side_effect = Exception("connection lost")
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            mock_pool.return_value = old
            get_pool("postgresql:///db_a")
            mock_pool.return_value = MagicMock()
            # Should not raise
            p = get_pool("postgresql:///db_b")
            assert p is not None


# ═══════════════════════════════════════════════════════
# get_connection / return_connection
# ═══════════════════════════════════════════════════════


class TestConnectionLifecycle:
    """get_connection() draws from pool, return_connection() puts back."""

    def test_get_connection_from_pool(self):
        mock_conn = MagicMock()
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            mock_pool.return_value.getconn.return_value = mock_conn
            conn = get_connection("postgresql:///test")
            assert conn is mock_conn
            assert conn.autocommit is True

    def test_return_connection_to_pool(self):
        mock_conn = MagicMock()
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            mock_pool.return_value.getconn.return_value = mock_conn
            conn = get_connection("postgresql:///test")
            return_connection(conn)
            mock_pool.return_value.putconn.assert_called_once_with(mock_conn)

    def test_return_connection_no_pool(self):
        """return_connection should not fail if pool doesn't exist."""
        reset_store()
        conn = MagicMock()
        return_connection(conn)  # Should not raise

    def test_return_connection_putconn_error(self):
        """If putconn fails, close the raw connection."""
        mock_conn = MagicMock()
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            mock_pool.return_value.getconn.return_value = mock_conn
            mock_pool.return_value.putconn.side_effect = Exception("pool full")
            conn = get_connection("postgresql:///test")
            return_connection(conn)
            mock_conn.close.assert_called_once()

    def test_close_pool(self):
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            get_pool("postgresql:///test")
            close_pool()
            mock_pool.return_value.closeall.assert_called_once()


# ═══════════════════════════════════════════════════════
# get_store() singleton
# ═══════════════════════════════════════════════════════


class TestStoreSingleton:
    """get_store() returns a singleton backed by the pool."""

    def test_get_store_returns_same_instance(self):
        with patch("psycopg2.pool.ThreadedConnectionPool"):
            s1 = get_store("postgresql:///test")
            s2 = get_store("postgresql:///test")
            assert s1 is s2

    def test_get_store_initializes(self):
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            # Mock cursor so initialize() doesn't fail
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_cursor.fetchall.return_value = []
            mock_conn.cursor.return_value = mock_cursor
            mock_pool.return_value.getconn.return_value = mock_conn

            store = get_store("postgresql:///test")
            assert store is not None
            # get_store calls initialize() which creates tables
            assert mock_cursor.execute.called

    def test_reset_store_clears_singleton(self):
        with patch("psycopg2.pool.ThreadedConnectionPool"):
            s1 = get_store("postgresql:///test")
            reset_store()
            s2 = get_store("postgresql:///test")
            assert s1 is not s2  # New instance after reset

    def test_reset_store_closes_pool(self):
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            get_store("postgresql:///test")
            reset_store()
            mock_pool.return_value.closeall.assert_called_once()


# ═══════════════════════════════════════════════════════
# KnowledgeStore with pool (transparent)
# ═══════════════════════════════════════════════════════


class TestKnowledgeStoreWithPool:
    """KnowledgeStore transparently uses the pool when available."""

    def test_knowledge_store_uses_pool_when_available(self):
        from ai_workspace.knowledge import KnowledgeStore

        mock_conn = MagicMock()
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            mock_pool.return_value.getconn.return_value = mock_conn
            get_pool("postgresql:///test_pool")

            store = KnowledgeStore(db_url="postgresql:///test_pool")
            conn = store.conn
            assert conn is mock_conn  # Came from pool
            assert conn.autocommit is True

    def test_knowledge_store_falls_back_without_pool(self):
        from ai_workspace.core import db as db_module
        from ai_workspace.knowledge import KnowledgeStore

        reset_store()
        mock_direct_conn = MagicMock()
        # Force get_connection to raise so we fall back to direct connect
        with patch.object(db_module, 'get_connection', side_effect=RuntimeError("no pool")), \
             patch("psycopg2.connect", return_value=mock_direct_conn):
            store = KnowledgeStore(db_url="postgresql:///no_pool")
            conn = store.conn
            assert conn is mock_direct_conn
            psycopg2.connect.assert_called_once_with("postgresql:///no_pool")

    def test_knowledge_store_close_returns_to_pool(self):
        from ai_workspace.knowledge import KnowledgeStore

        mock_conn = MagicMock()
        mock_conn.closed = False
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            mock_pool.return_value.getconn.return_value = mock_conn
            # Create pool FIRST, then store draws from it
            get_pool("postgresql:///test_close")
            store = KnowledgeStore(db_url="postgresql:///test_close")
            _ = store.conn
            store.close()
            mock_pool.return_value.putconn.assert_called_once_with(mock_conn)
            mock_conn.close.assert_not_called()

    def test_knowledge_store_close_direct_connection(self):
        from ai_workspace.core import db as db_module
        from ai_workspace.knowledge import KnowledgeStore

        reset_store()
        mock_direct_conn = MagicMock()
        mock_direct_conn.closed = False
        with patch.object(db_module, 'get_connection', side_effect=RuntimeError("no pool")), \
             patch("psycopg2.connect", return_value=mock_direct_conn):
            store = KnowledgeStore(db_url="postgresql:///direct")
            _ = store.conn
            store.close()
            mock_direct_conn.close.assert_called_once()

    def test_knowledge_store_multiple_share_pool(self):
        """Multiple store instances share the same pool."""
        from ai_workspace.knowledge import KnowledgeStore

        mock_conn_a = MagicMock()
        mock_conn_b = MagicMock()
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            mock_pool.return_value.getconn.side_effect = [mock_conn_a, mock_conn_b]
            get_pool("postgresql:///shared")

            store_a = KnowledgeStore(db_url="postgresql:///shared")
            store_b = KnowledgeStore(db_url="postgresql:///shared")

            assert store_a.conn is mock_conn_a
            assert store_b.conn is mock_conn_b  # Different connection from same pool
            assert mock_pool.return_value.getconn.call_count == 2


# ═══════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════


class TestEdgeCases:
    """Edge cases for pool and store."""

    def test_get_store_before_pool(self):
        """get_store() creates pool automatically if needed."""
        with patch("psycopg2.pool.ThreadedConnectionPool") as mock_pool:
            get_store("postgresql:///auto")
            mock_pool.assert_called_once()

    def test_conn_lazy_connection(self):
        """Connection is not created until conn is accessed."""
        from ai_workspace.knowledge import KnowledgeStore

        reset_store()
        with patch("psycopg2.connect") as mock_connect:
            store = KnowledgeStore(db_url="postgresql:///lazy")
            mock_connect.assert_not_called()  # Not yet
            _ = store.conn
            mock_connect.assert_called_once()  # Now it is

    def test_conn_reconnect_on_closed(self):
        """If connection is closed, create a new one."""
        from ai_workspace.knowledge import KnowledgeStore

        reset_store()
        mock_conn1 = MagicMock()
        mock_conn2 = MagicMock()
        with patch("psycopg2.connect", side_effect=[mock_conn1, mock_conn2]):
            store = KnowledgeStore(db_url="postgresql:///reconnect")
            c1 = store.conn
            mock_conn1.closed = True  # Simulate disconnection
            c2 = store.conn
            assert c1 is not c2
            assert c2 is mock_conn2

    def test_pool_handles_missing_psycopg2_pool_module(self):
        """If ThreadedConnectionPool is not available, fall back gracefully."""
        # Actually, psycopg2.pool is always available with psycopg2.
        # This tests the general try/except pattern.
        from ai_workspace.knowledge import KnowledgeStore

        reset_store()
        mock_conn = MagicMock()
        with patch("psycopg2.connect", return_value=mock_conn):
            # No pool initialized — falls back to direct connect
            store = KnowledgeStore(db_url="postgresql:///fallback")
            conn = store.conn
            assert conn is mock_conn
