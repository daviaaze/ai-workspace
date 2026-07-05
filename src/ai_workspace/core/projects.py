"""
Project & Repository Manager — Multi-agent coding with isolated git worktrees.

Projects group work. Repositories use git worktrees so multiple agents
can work in parallel without conflicts — each agent gets its own worktree.
"""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("aiw.projects")


@dataclass
class RepoConfig:
    """A git repository that agents can work on."""
    name: str
    path: str  # Absolute path to the main repo
    remote: str = ""  # e.g., "origin"


@dataclass
class WorktreeAgent:
    """An agent working in an isolated worktree."""
    name: str
    task: str
    worktree_path: str  # Absolute path to the worktree
    branch: str
    status: str = "active"  # active, completed, failed
    started_at: str = ""
    model: str = "qwen3:14b"


@dataclass
class Project:
    """A logical project that can span multiple repos and agents."""
    name: str
    description: str = ""
    repos: list[RepoConfig] = field(default_factory=list)
    agents: list[WorktreeAgent] = field(default_factory=list)
    created_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ProjectManager:
    """Manages projects, repositories, git worktrees, and coding agents."""

    WORKTREE_PREFIX = ".aiw/worktrees"

    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or os.getenv("AIW_DB_URL", "postgresql:///ai_workspace")
        self._conn = None

    @property
    def conn(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.db_url)
            self._conn.autocommit = True
        return self._conn

    #  DB initialization

    def initialize(self) -> None:
        """Create project tables."""
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                name            TEXT PRIMARY KEY,
                description     TEXT DEFAULT '',
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                metadata        JSONB DEFAULT '{}'
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS project_repos (
                project_name    TEXT REFERENCES projects(name) ON DELETE CASCADE,
                repo_name       TEXT NOT NULL,
                repo_path       TEXT NOT NULL,
                remote          TEXT DEFAULT '',
                PRIMARY KEY (project_name, repo_name)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS project_agents (
                id              SERIAL PRIMARY KEY,
                project_name    TEXT REFERENCES projects(name) ON DELETE CASCADE,
                agent_name      TEXT NOT NULL,
                repo_name       TEXT NOT NULL,
                task            TEXT NOT NULL,
                worktree_path   TEXT NOT NULL,
                branch          TEXT NOT NULL,
                model           TEXT DEFAULT 'qwen3:14b',
                status          TEXT DEFAULT 'active',
                started_at      TIMESTAMPTZ DEFAULT NOW(),
                completed_at    TIMESTAMPTZ,
                summary         TEXT DEFAULT ''
            )
        """)
        logger.info("Project tables initialized")

    #  Project CRUD

    def create_project(
        self,
        name: str,
        description: str = "",
        repos: list[dict[str, str]] | None = None,
    ) -> Project:
        """Create a new project with optional repositories."""
        c = self.conn.cursor()
        c.execute(
            "INSERT INTO projects (name, description) VALUES (%s, %s) "
            "ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description",
            (name, description),
        )

        repo_list = []
        for r in (repos or []):
            repo_path = os.path.abspath(r.get("path", "."))
            c.execute(
                "INSERT INTO project_repos (project_name, repo_name, repo_path, remote) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (project_name, repo_name) DO NOTHING",
                (name, r.get("name", "main"), repo_path, r.get("remote", "")),
            )
            repo_list.append(RepoConfig(
                name=r.get("name", "main"),
                path=repo_path,
                remote=r.get("remote", ""),
            ))

        return Project(name=name, description=description, repos=repo_list)

    def list_projects(self) -> list[Project]:
        """List all projects with their repos and active agents."""
        c = self.conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT * FROM projects ORDER BY created_at DESC")
        rows = c.fetchall()

        projects = []
        for row in rows:
            name = row["name"]
            # Get repos
            c.execute(
                "SELECT * FROM project_repos WHERE project_name = %s", (name,)
            )
            repos = [
                RepoConfig(name=r["repo_name"], path=r["repo_path"], remote=r["remote"])
                for r in c.fetchall()
            ]
            # Get agents
            c.execute(
                "SELECT * FROM project_agents WHERE project_name = %s AND status = 'active'",
                (name,),
            )
            agents = [
                WorktreeAgent(
                    name=a["agent_name"],
                    task=a["task"],
                    worktree_path=a["worktree_path"],
                    branch=a["branch"],
                    status=a["status"],
                    started_at=str(a["started_at"]),
                    model=a.get("model", "qwen3:14b"),
                )
                for a in c.fetchall()
            ]
            projects.append(Project(
                name=name,
                description=row["description"] or "",
                repos=repos,
                agents=agents,
                created_at=str(row["created_at"]),
                metadata=row["metadata"] or {},
            ))
        return projects

    #  Git worktree management

    def create_worktree(
        self,
        project_name: str,
        agent_name: str,
        repo_name: str,
        task: str,
        model: str = "qwen3:14b",
    ) -> WorktreeAgent:
        """Create an isolated git worktree for an agent.

        The worktree is created at: {repo_path}/.aiw/worktrees/{agent_name}/
        with its own branch: aiw/{agent_name}-{timestamp}
        """
        # Get repo config
        c = self.conn.cursor(cursor_factory=RealDictCursor)
        c.execute(
            "SELECT * FROM project_repos WHERE project_name = %s AND repo_name = %s",
            (project_name, repo_name),
        )
        repo_row = c.fetchone()
        if not repo_row:
            raise ValueError(f"Repo '{repo_name}' not found in project '{project_name}'")

        repo_path = repo_row["repo_path"]
        worktree_dir = os.path.join(repo_path, self.WORKTREE_PREFIX, agent_name)
        branch_name = f"aiw/{agent_name}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Create worktree
        os.makedirs(os.path.dirname(worktree_dir), exist_ok=True)

        # Check if worktree already exists and remove it
        if os.path.exists(worktree_dir):
            subprocess.run(
                ["git", "-C", repo_path, "worktree", "remove", "--force", worktree_dir],
                capture_output=True, timeout=30,
            )

        subprocess.run(
            ["git", "-C", repo_path, "worktree", "add", "-b", branch_name, worktree_dir],
            capture_output=True, text=True, timeout=30, check=True,
        )

        logger.info("Created worktree %s on branch %s for agent %s",
                     worktree_dir, branch_name, agent_name)

        # Record in DB
        c.execute(
            "INSERT INTO project_agents "
            "(project_name, agent_name, repo_name, task, worktree_path, branch, model, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')",
            (project_name, agent_name, repo_name, task, worktree_dir, branch_name, model),
        )

        return WorktreeAgent(
            name=agent_name,
            task=task,
            worktree_path=worktree_dir,
            branch=branch_name,
            model=model,
            started_at=datetime.now(UTC).isoformat(),
        )

    def cleanup_worktree(self, project_name: str, agent_name: str) -> None:
        """Remove a worktree when agent is done."""
        c = self.conn.cursor(cursor_factory=RealDictCursor)
        c.execute(
            "SELECT * FROM project_agents "
            "WHERE project_name = %s AND agent_name = %s AND status = 'active'",
            (project_name, agent_name),
        )
        row = c.fetchone()
        if not row:
            return

        worktree_dir = row["worktree_path"]
        repo_path = os.path.dirname(os.path.dirname(worktree_dir))  # Up from .aiw/worktrees/agent

        # Remove worktree
        subprocess.run(
            ["git", "-C", repo_path, "worktree", "remove", "--force", worktree_dir],
            capture_output=True, timeout=30,
        )
        # Prune the branch
        subprocess.run(
            ["git", "-C", repo_path, "branch", "-D", row["branch"]],
            capture_output=True, timeout=10,
        )

        # Mark as completed in DB
        c.execute(
            "UPDATE project_agents SET status = 'completed', completed_at = NOW() "
            "WHERE project_name = %s AND agent_name = %s",
            (project_name, agent_name),
        )

        logger.info("Cleaned up worktree %s for agent %s", worktree_dir, agent_name)

    def list_worktrees(self, repo_path: str) -> list[str]:
        """List active worktrees for a repository."""
        result = subprocess.run(
            ["git", "-C", repo_path, "worktree", "list", "--porcelain"],
            capture_output=True, text=True, timeout=10,
        )
        paths = []
        for line in result.stdout.split("\n"):
            if line.startswith("worktree "):
                paths.append(line.split(" ", 1)[1])
        return paths
