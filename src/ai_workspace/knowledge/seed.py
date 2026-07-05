"""
Knowledge seeding — index the aiw codebase so agents understand it.

Run: python -m ai_workspace.knowledge.seed
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Files to index (relative to workspace root)
SEED_FILES = [
    # Architecture & design
    ("docs/aiw-spec-v2.md", "doc", ["architecture", "design", "spec"]),
    ("README.md", "doc", ["readme", "overview"]),

    # Core source
    ("src/ai_workspace/cli.py", "code", ["cli", "typer", "entrypoint"]),
    ("src/ai_workspace/tui/app.py", "code", ["tui", "textual", "dashboard"]),
    ("src/ai_workspace/tui/widgets.py", "code", ["tui", "widgets", "ui"]),
    ("src/ai_workspace/mcp_server/server.py", "code", ["mcp", "server", "agent"]),

    # Knowledge & search
    ("src/ai_workspace/knowledge/store.py", "code", ["knowledge", "postgresql", "pgvector"]),
    ("src/ai_workspace/search/deep_search.py", "code", ["search", "research", "llm"]),

    # Agents & workflow
    ("src/ai_workspace/agents/swarm.py", "code", ["agents", "swarm", "orchestration"]),
    ("src/ai_workspace/workflow/engine.py", "code", ["workflow", "dag", "execution"]),
    ("src/ai_workspace/tasks/scheduler.py", "code", ["tasks", "scheduler", "cron"]),

    # Tools
    ("src/ai_workspace/tools/browser_agent.py", "code", ["tools", "browser", "playwright"]),
    ("src/ai_workspace/tools/headless_browser.py", "code", ["tools", "browser", "scraping"]),
    ("src/ai_workspace/tools/web_fetch.py", "code", ["tools", "web", "fetch"]),
    ("src/ai_workspace/tools/shell.py", "code", ["tools", "shell", "command"]),

    # Config
    ("pyproject.toml", "config", ["dependencies", "python", "project"]),
    ("Makefile", "config", ["make", "build", "commands"]),
    ("flake.nix", "config", ["nix", "environment"]),
]


def seed(store=None, verbose: bool = True):
    """Index all seed files into the knowledge store."""
    if store is None:
        from ai_workspace.knowledge import KnowledgeStore
        store = KnowledgeStore()
        store.initialize()
        own_store = True
    else:
        own_store = False

    try:
        indexed = 0
        skipped = 0

        for rel_path, content_type, tags in SEED_FILES:
            filepath = WORKSPACE_ROOT / rel_path
            if not filepath.exists():
                if verbose:
                    logger.info("Skipping (not found): %s", rel_path)
                skipped += 1
                continue

            content = filepath.read_text()
            title = rel_path

            # Extract first heading as title for markdown files
            if rel_path.endswith(".md"):
                for line in content.split("\n"):
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break

            try:
                store.add_knowledge(
                    content=content,
                    content_type=content_type,
                    title=title,
                    tags=tags,
                )
                indexed += 1
                if verbose:
                    logger.info("Indexed %s (%s bytes, type=%s)", rel_path, len(content), content_type)
            except Exception as e:
                if verbose:
                    logger.error("Failed to index %s: %s", rel_path, e)
                skipped += 1

        if verbose:
            logger.info("Indexed: %d | Skipped: %d", indexed, skipped)

        return indexed, skipped
    finally:
        if own_store:
            store.close()


def main():
    """Entry point: python -m ai_workspace.knowledge.seed"""
    logger.info("Seeding aiw knowledge graph...")
    seed()
    logger.info("Done. Agents can now search the codebase via search_knowledge().")


if __name__ == "__main__":
    main()
