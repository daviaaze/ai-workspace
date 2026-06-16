"""
Database connection pool and dependency injection for KnowledgeStore.

Provides:
- ConnectionPool: psycopg2 ThreadedConnectionPool wrapper
- get_store(): singleton KnowledgeStore backed by the pool
- reset_store(): clear singleton (for tests and reconfiguration)
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import psycopg2
from psycopg2 import pool

logger = logging.getLogger(__name__)

# Module-level state
_pool: Optional[pool.ThreadedConnectionPool] = None
_pool_db_url: Optional[str] = None
_store_singleton: Optional["KnowledgeStore"] = None  # noqa: F821


def _get_default_db_url() -> str:
    """Resolve the default database URL from environment."""
    return os.environ.get(
        "AIW_DB_URL",
        "postgresql:///ai_workspace",
    )


def get_pool(
    db_url: str | None = None,
    min_connections: int = 1,
    max_connections: int = 5,
) -> pool.ThreadedConnectionPool:
    """Get or create a thread-safe connection pool for the given database URL.

    Args:
        db_url: PostgreSQL connection string. Defaults to AIW_DB_URL env var.
        min_connections: Minimum idle connections to keep.
        max_connections: Maximum connections in the pool.

    Returns:
        A psycopg2 ThreadedConnectionPool instance.
    """
    global _pool, _pool_db_url

    resolved_url = db_url or _get_default_db_url()

    if _pool is not None and _pool_db_url == resolved_url:
        return _pool

    # Close old pool if URL changed
    if _pool is not None:
        try:
            _pool.closeall()
        except Exception:
            pass

    logger.info(
        "Creating connection pool for %s (min=%d, max=%d)",
        resolved_url.split("@")[-1] if "@" in resolved_url else resolved_url,
        min_connections,
        max_connections,
    )

    _pool = pool.ThreadedConnectionPool(
        minconn=min_connections,
        maxconn=max_connections,
        dsn=resolved_url,
    )
    _pool_db_url = resolved_url
    return _pool


def get_store(db_url: str | None = None) -> "KnowledgeStore":  # noqa: F821
    """Get or create a singleton KnowledgeStore backed by the connection pool.

    All callers share the same pool — no more scattered connections.
    Use this instead of ``KnowledgeStore()`` in application code.

    Args:
        db_url: PostgreSQL connection string. Defaults to AIW_DB_URL env var.

    Returns:
        A KnowledgeStore instance that draws connections from the pool.
    """
    global _store_singleton
    from ai_workspace.knowledge import KnowledgeStore

    resolved_url = db_url or _get_default_db_url()

    if _store_singleton is not None:
        return _store_singleton

    # Create pool and store
    get_pool(resolved_url)
    _store_singleton = KnowledgeStore(db_url=resolved_url)
    _store_singleton.initialize()
    return _store_singleton


def reset_store() -> None:
    """Reset the singleton and close the pool. Use in tests or on shutdown."""
    global _store_singleton, _pool, _pool_db_url
    _store_singleton = None
    if _pool is not None:
        try:
            _pool.closeall()
        except Exception:
            pass
    _pool = None
    _pool_db_url = None


def get_connection(db_url: str | None = None) -> psycopg2.extensions.connection:
    """Get a single connection from the pool.

    Prefer ``get_store()`` for application code. Use this only when you
    need a raw connection (e.g., migrations, direct SQL).

    Args:
        db_url: PostgreSQL connection string.

    Returns:
        A psycopg2 connection from the pool.
    """
    p = get_pool(db_url)
    conn = p.getconn()
    conn.autocommit = True
    return conn


def return_connection(conn: psycopg2.extensions.connection) -> None:
    """Return a connection to the pool, or close it if pool unavailable.

    Args:
        conn: A connection previously obtained via get_connection().
    """
    if _pool is not None:
        try:
            _pool.putconn(conn)
            return
        except Exception:
            pass
    # No pool or putconn failed — close directly
    try:
        conn.close()
    except Exception:
        pass


def close_pool() -> None:
    """Close all pool connections. Call on application shutdown."""
    global _pool, _pool_db_url
    if _pool is not None:
        _pool.closeall()
    _pool = None
    _pool_db_url = None
