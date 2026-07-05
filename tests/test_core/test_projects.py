"""Tests for projects.py — ProjectManager with mocked psycopg2."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_workspace.core.projects import (
    Project,
    ProjectManager,
    RepoConfig,
    WorktreeAgent,
)


class TestDataclasses:
    def test_repo_config_defaults(self):
        r = RepoConfig(name="main", path="/tmp/repo")
        assert r.name == "main"
        assert r.path == "/tmp/repo"
        assert r.remote == ""

    def test_worktree_agent_defaults(self):
        a = WorktreeAgent(
            name="agent-1", task="fix bug",
            worktree_path="/tmp/worktree", branch="fix/1",
        )
        assert a.status == "active"
        assert a.model == "qwen3:14b"
        assert a.started_at == ""

    def test_project_defaults(self):
        p = Project(name="my-project")
        assert p.description == ""
        assert p.repos == []
        assert p.agents == []
        assert p.created_at == ""


class TestProjectManagerInit:
    def test_default_db_url(self):
        pm = ProjectManager()
        assert pm._conn is None

    def test_custom_db_url(self):
        pm = ProjectManager(db_url="postgresql://user@host/db")
        assert pm.db_url == "postgresql://user@host/db"
        assert pm._conn is None


class TestProjectManagerDB:
    """Tests that mock the psycopg2 connection."""

    @pytest.fixture
    def mock_conn(self):
        with patch("ai_workspace.core.projects.psycopg2.connect") as mock_connect:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_connect.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            mock_conn.closed = False
            yield mock_cursor, mock_conn, mock_connect

    def test_initialize(self, mock_conn):
        mock_cursor, _, _ = mock_conn
        pm = ProjectManager(db_url="postgresql:///test")
        pm.initialize()
        assert mock_cursor.execute.called
        # Should have created tables
        calls = [c[0][0][:50] for c in mock_cursor.execute.call_args_list]
        table_calls = [c for c in calls if "CREATE TABLE" in c]
        assert len(table_calls) == 3  # projects, project_repos, project_agents

    def test_create_project(self, mock_conn):
        mock_cursor, mock_conn, _ = mock_conn
        pm = ProjectManager(db_url="postgresql:///test")
        project = pm.create_project(name="test-proj", description="Test project")
        assert isinstance(project, Project)
        assert project.name == "test-proj"
        assert project.description == "Test project"

    def test_create_project_with_repos(self, mock_conn):
        mock_cursor, mock_conn, _ = mock_conn
        pm = ProjectManager(db_url="postgresql:///test")
        repos = [{"name": "main", "path": "/tmp/repo", "remote": "origin"}]
        project = pm.create_project(name="test-proj", repos=repos)
        assert len(project.repos) == 1
        assert project.repos[0].name == "main"

    def test_list_projects(self, mock_conn):
        mock_cursor, _, _ = mock_conn
        pm = ProjectManager(db_url="postgresql:///test")
        # Mock fetchall to return some rows
        mock_cursor.fetchall.side_effect = [
            [{"name": "proj1", "description": "desc1",
              "created_at": None, "metadata": {}}],
            [],  # repos for proj1
            [],  # agents for proj1
            [{"name": "proj2", "description": "desc2",
              "created_at": None, "metadata": {}}],
            [],  # repos for proj2
            [],  # agents for proj2
        ]
        projects = pm.list_projects()
        assert len(projects) == 1  # only one row before fetchall returns empty
        assert projects[0].name == "proj1"

    def test_conn_property_connects_once(self, mock_conn):
        mock_cursor, mock_conn, mock_connect = mock_conn
        pm = ProjectManager(db_url="postgresql:///test")
        # Access conn twice
        c1 = pm.conn
        c2 = pm.conn
        assert c1 == c2
        mock_connect.assert_called_once()

    def test_conn_reconnects_when_closed(self, mock_conn):
        mock_cursor, mock_conn, mock_connect = mock_conn
        pm = ProjectManager(db_url="postgresql:///test")
        c1 = pm.conn
        # Simulate closed connection
        mock_conn.closed = True
        c2 = pm.conn
        assert mock_connect.call_count == 2
