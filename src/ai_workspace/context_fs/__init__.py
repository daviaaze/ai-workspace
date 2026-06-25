"""
RAGFS — Context as Filesystem Experiment.

OpenViking-inspired virtual filesystem that exposes the AI Workspace's
knowledge base and memory as a browsable directory tree.

Usage::

    # Browse the context filesystem (no FUSE needed)
    ragfs = VirtualContextFS()
    ragfs.ls("/")           # List available contexts
    cat = ragfs.read("/kb/architecture/overview")
    ragfs.write("/memory/note.txt", "Remember this")

    # Mount as FUSE filesystem (requires fusepy)
    # aiw context-fs mount /mnt/context
"""

from __future__ import annotations

import io
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("aiw.ragfs")

# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

CONTEXT_ROOT = Path.home() / ".aiw" / "context"
MEMORY_ROOT = Path.home() / ".aiw" / "memory"


# ═══════════════════════════════════════════════════════════
# Virtual RAG Filesystem
# ═══════════════════════════════════════════════════════════


class VirtualContextFS:
    """Virtual filesystem over the AI Workspace's context & memory.

    Maps knowledge bases and memory stores into a browsable
    directory tree at ``~/.aiw/context/``.

    Directory layout::

        ~/.aiw/context/
        ├── kb/                    # Knowledge bases
        │   ├── <name>/            # Each KB = a directory
        │   │   ├── list           # List of documents
        │   │   └── <doc>.md       # Individual documents
        │   └── search/            # Search across all KBs
        │       └── <query>        # Read = retrieve (file name = query)
        ├── memory/                # Persistent memory
        │   ├── l1/                # Recent traces
        │   ├── l2/                # Facts/patterns
        │   └── l3/                # Summaries
        ├── trace/                 # Session traces
        │   └── <session_id>.json
        └── info                   # Overview of the FS (like a README)

    Files are virtual — they only exist as read/write operations.
    Listing is dynamic: entries reflect current system state.
    """

    def __init__(self, root: str | Path | None = None, knowledge_root: str | Path | None = None):
        self._root = Path(root) if root else CONTEXT_ROOT
        self._memory_root = MEMORY_ROOT
        self._knowledge_root = Path(knowledge_root) if knowledge_root else Path.home() / ".aiw" / "knowledge"

    @property
    def root(self) -> Path:
        return self._root

    # ── Filesystem Operations ──────────────────────────────────────

    def ls(self, path: str = "/") -> list[dict[str, Any]]:
        """List directory contents as a list of ``{name, type, size}``.

        Args:
            path: Virtual path within the context filesystem.

        Returns:
            List of entries with name, type (dir/file), and size.
        """
        clean = self._clean(path)
        parts = self._split(clean)

        if not parts:
            return self._ls_root()
        if parts[0] == "kb":
            return self._ls_kb(parts[1:])
        if parts[0] == "memory":
            return self._ls_memory(parts[1:])
        if parts[0] == "trace":
            return self._ls_trace(parts[1:])
        return []

    def read(self, path: str) -> str:
        """Read a virtual file. The path determines what is retrieved.

        Args:
            path: Virtual file path. Scheme:
                ``/kb/<name>/<doc>`` → read document from KB
                ``/kb/search/<query>`` → search KBs
                ``/memory/l1/`` → list recent traces
                ``/memory/l2/`` → list facts
                ``/memory/l3/`` → list summaries
                ``/trace/<id>`` → read trace
                ``/info`` → filesystem overview

        Returns:
            File content as string.

        Raises:
            FileNotFoundError: If the path doesn't exist.
        """
        clean = self._clean(path)
        parts = self._split(clean)

        if not parts:
            return self._render_info()

        if clean == "info":
            return self._render_info()

        if parts[0] == "kb":
            return self._read_kb(parts[1:])

        if parts[0] == "memory":
            return self._read_memory(parts[1:])

        if parts[0] == "trace":
            return self._read_trace(parts[1:])

        raise FileNotFoundError(path)

    def write(self, path: str, content: str) -> str:
        """Write content to a virtual file (stores to memory).

        ``/memory/l2/<name>`` → write an L2 fact
        ``/memory/l3/<name>`` → write an L3 summary
        Any other path → writes to ``~/.aiw/context/notes/``

        Returns:
            The path where content was stored.
        """
        clean = self._clean(path)
        parts = self._split(clean)

        if parts and parts[0] == "memory" and len(parts) >= 2:
            tier = parts[1].upper()
            name = "_".join(parts[2:]) if len(parts) > 2 else f"note_{int(datetime.now(timezone.utc).timestamp())}"
            return self._write_memory(tier, name, content)

        # Default: write to notes directory
        notes_dir = self._root / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        name = parts[-1] if parts else f"note_{int(datetime.now(timezone.utc).timestamp())}"
        filepath = notes_dir / name
        filepath.write_text(content, encoding="utf-8")
        return str(filepath)

    def exists(self, path: str) -> bool:
        """Check if a virtual path exists."""
        try:
            self.read(path)
            return True
        except FileNotFoundError:
            return False

    # ── Directory Listing Helpers ──────────────────────────────────

    def _ls_root(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = [
            {"name": "kb", "type": "dir", "size": 0},
            {"name": "memory", "type": "dir", "size": 0},
            {"name": "trace", "type": "dir", "size": 0},
        ]
        info_size = len(self._render_info())
        entries.insert(0, {"name": "info", "type": "file", "size": info_size})

        # Add notes if they exist
        notes_dir = self._root / "notes"
        if notes_dir.is_dir():
            for f in sorted(notes_dir.iterdir()):
                if f.is_file():
                    entries.append({
                        "name": f"notes/{f.name}",
                        "type": "file",
                        "size": f.stat().st_size,
                    })
        return entries

    def _ls_kb(self, parts: list[str]) -> list[dict[str, Any]]:
        if not parts:
            # List available KBs from ~/.aiw/knowledge/
            if not self._knowledge_root.is_dir():
                return [{"name": "search", "type": "dir", "size": 0}]
            entries: list[dict[str, Any]] = []
            for entry in sorted(self._knowledge_root.iterdir()):
                if entry.is_dir() and not entry.name.startswith("."):
                    doc_count = sum(1 for _ in entry.rglob("*") if _.is_file())
                    entries.append({
                        "name": entry.name,
                        "type": "dir",
                        "size": doc_count,
                    })
            # Add search dir
            entries.append({"name": "search", "type": "dir", "size": 0})
            return entries
        return []  # KB-specific listing — too dynamic

    def _ls_memory(self, parts: list[str]) -> list[dict[str, Any]]:
        tiers = {
            "l1": "Recent traces (L1)",
            "l2": "Extracted facts (L2)",
            "l3": "Synthesized summaries (L3)",
        }
        if not parts:
            return [
                {"name": t, "type": "dir", "size": 0, "desc": d}
                for t, d in tiers.items()
            ]

        # List files in a specific tier
        if parts[0].lower() in tiers:
            tier = parts[0].lower()
            tier_dir = self._memory_root / f"l3"  # L3 directory for summaries
            if tier_dir.is_dir():
                files = sorted(tier_dir.iterdir())
                return [
                    {"name": f.name, "type": "file", "size": f.stat().st_size}
                    for f in files if f.is_file()
                ]
        return []

    def _ls_trace(self, parts: list[str]) -> list[dict[str, Any]]:
        trace_dir = self._memory_root / "l1"
        if not trace_dir.is_dir():
            return []
        files = sorted(trace_dir.iterdir())
        return [
            {"name": f.name, "type": "file", "size": f.stat().st_size}
            for f in files if f.is_file()
        ][:20]  # Limit to 20 traces

    # ── Read Helpers ───────────────────────────────────────────────

    def _read_kb(self, parts: list[str]) -> str:
        if not parts:
            return self._list_kb_root()

        if parts[0] == "search":
            # /kb/search/<query> — search across KBs
            query = "/".join(parts[1:]) if len(parts) > 1 else ""
            if not query:
                return "Usage: cat /kb/search/<your query>\n"
            return self._search_kb(query)

        # /kb/<name>/<doc> — read specific document
        kb_name = parts[0]
        doc_path = "/".join(parts[1:]) if len(parts) > 1 else ""

        kb_dir = self._knowledge_root / kb_name
        if not kb_dir.is_dir():
            raise FileNotFoundError(f"Knowledge base '{kb_name}' not found")

        if not doc_path:
            # List documents in this KB
            files = sorted(kb_dir.rglob("*"))
            lines = [f"# KB: {kb_name}\n", f"Path: {kb_dir}\n", ""]
            for f in files:
                if f.is_file():
                    lines.append(f"  {f.relative_to(kb_dir)}  ({f.stat().st_size}b)")
            return "\n".join(lines)

        # Read specific document
        target = kb_dir / doc_path
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(f"/kb/{kb_name}/{doc_path}")

        return target.read_text(encoding="utf-8")

    def _read_memory(self, parts: list[str]) -> str:
        if not parts:
            return self._memory_overview()

        tier = parts[0].lower()
        if tier not in ("l1", "l2", "l3"):
            raise FileNotFoundError(f"/memory/{tier}")

        name = "/".join(parts[1:]) if len(parts) > 1 else ""
        if not name:
            return self._memory_tier_list(tier)

        return self._memory_tier_read(tier, name)

    def _read_trace(self, parts: list[str]) -> str:
        if not parts:
            raise FileNotFoundError("/trace/")
        name = parts[0]
        # Try to find trace file
        trace_dir = self._memory_root / "l1"
        target = trace_dir / name
        if not target.exists() and trace_dir.is_dir():
            # Try match by prefix
            for f in trace_dir.iterdir():
                if f.name.startswith(name):
                    target = f
                    break
        if target.is_file():
            return target.read_text(encoding="utf-8")
        raise FileNotFoundError(f"/trace/{name}")

    # ── Write Helpers ──────────────────────────────────────────────

    def _write_memory(self, tier: str, name: str, content: str) -> str:
        tier_dir = self._memory_root / tier.lower()
        tier_dir.mkdir(parents=True, exist_ok=True)
        filepath = tier_dir / f"{name}.md"
        filepath.write_text(content, encoding="utf-8")
        logger.info("RAGFS wrote %s fact: %s", tier, filepath)
        return str(filepath)

    # ── Search ─────────────────────────────────────────────────────

    def _list_kb_root(self) -> str:
        """List available knowledge bases."""
        if not self._knowledge_root.is_dir():
            return "No knowledge bases available.\n"

        lines = ["# Knowledge Bases\n"]
        for entry in sorted(self._knowledge_root.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                doc_count = sum(1 for _ in entry.rglob("*") if _.is_file())
                lines.append(f"  {entry.name}/  ({doc_count} documents)")

        if len(lines) == 1:
            lines.append("(empty)\n")

        lines.append("")
        lines.append("Use /kb/search/<query> to search across all KBs.")
        return "\n".join(lines)

    def _search_kb(self, query: str) -> str:
        """Simple keyword search across knowledge bases."""
        if not self._knowledge_root.is_dir():
            return "No knowledge bases found."

        query_lower = query.lower()
        results: list[tuple[str, str, str]] = []  # (kb, path, snippet)

        for kb_dir in sorted(self._knowledge_root.iterdir()):
            if not kb_dir.is_dir() or kb_dir.name.startswith("."):
                continue
            for f in kb_dir.rglob("*"):
                if not f.is_file():
                    continue
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if query_lower in text.lower():
                    snippet = text[:200].replace("\n", " ").strip()
                    rel = f.relative_to(kb_root)
                    results.append((kb_dir.name, str(rel), snippet))

        if not results:
            return f"No results for '{query}' in any knowledge base.\n"

        lines = [f"# Search: {query}", f"{len(results)} result(s)\n"]
        for kb, rel, snippet in results[:20]:
            lines.append(f"**{kb}/{rel}**")
            lines.append(f"  {snippet[:120]}...")
            lines.append("")
        return "\n".join(lines)

    # ── Render ─────────────────────────────────────────────────────

    def _render_info(self) -> str:
        """Overview of the RAGFS filesystem."""
        lines = [
            "# RAGFS — Context as Filesystem",
            "",
            "Virtual filesystem over the AI Workspace context store.",
            "",
            "## Directory Layout",
            "",
            "  kb/              Knowledge bases",
            "    <name>/        Individual KB",
            "    search/        Search across all KBs",
            "  memory/          Persistent memory",
            "    l1/            Recent traces (L1)",
            "    l2/            Extracted facts (L2)",
            "    l3/            Synthesized summaries (L3)",
            "  trace/           Session traces",
            "  info             This file",
            "",
            "## Usage",
            "",
            "  ls /kb/              List knowledge bases",
            "  cat /kb/<name>/      List documents in a KB",
            "  cat /kb/search/q     Search KBs for 'q'",
            "  cat /memory/l1/      List recent traces",
            "  echo 'fact' > /memory/l2/myfact   Write a fact",
            "",
            f"Context root: {self._root}",
            f"Memory root: {self._memory_root}",
        ]
        return "\n".join(lines)

    def _memory_overview(self) -> str:
        lines = ["# Memory", "", "Three-tier persistent memory hierarchy:"]
        for tier, desc in [("L1", "Recent traces"), ("L2", "Extracted facts"), ("L3", "Summaries")]:
            lines.append(f"\n  {tier}/   {desc}")
        return "\n".join(lines)

    def _memory_tier_list(self, tier: str) -> str:
        tier_dir = self._memory_root / tier.lower()
        if not tier_dir.is_dir():
            return f"No {tier.upper()} entries yet.\n"
        files = sorted(tier_dir.iterdir())
        if not files:
            return f"No {tier.upper()} entries yet.\n"
        lines = [f"# Memory {tier.upper()}\n"]
        for f in files[:30]:
            if f.is_file():
                size = f.stat().st_size
                modified = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
                lines.append(f"  {f.name:<40} {size:>6}b  {modified}")
        return "\n".join(lines)

    def _memory_tier_read(self, tier: str, name: str) -> str:
        # Strip .md extension if present
        base = name[:-3] if name.endswith(".md") else name
        tier_dir = self._memory_root / tier.lower()
        target = tier_dir / f"{base}.md"
        if not target.exists():
            # Try without extension
            target = tier_dir / base
        if not target.exists():
            raise FileNotFoundError(f"/memory/{tier}/{name}")
        return target.read_text(encoding="utf-8")

    # ── Path Helpers ───────────────────────────────────────────────

    @staticmethod
    def _clean(path: str) -> str:
        """Normalize a path: strip leading/trailing slashes."""
        return path.strip().strip("/")

    @staticmethod
    def _split(path: str) -> list[str]:
        """Split a cleaned path into parts."""
        return path.split("/") if path else []


# ═══════════════════════════════════════════════════════════
# FUSE Mount (optional — requires fusepy)
# ═══════════════════════════════════════════════════════════


def mount_fuse(mountpoint: str | Path) -> None:
    """Mount RAGFS as a FUSE filesystem.

    Requires ``fusepy`` to be installed. Raises ``ImportError`` if
    not available.

    Args:
        mountpoint: Directory where the filesystem will be mounted.

    Raises:
        ImportError: If ``fusepy`` is not installed.
        RuntimeError: If mount fails (permissions, already mounted).
    """
    try:
        import fuse
    except ImportError:
        raise ImportError(
            "FUSE support requires 'fusepy'. Install with: "
            "pip install fusepy"
        ) from None

    class RAGFUSE(fuse.Operations):
        """FUSE operations backed by VirtualContextFS."""

        def __init__(self) -> None:
            self._fs = VirtualContextFS()
            self._fd_counter = 0
            self._open_files: dict[int, str] = {}

        def readdir(self, path: str, fh: Any) -> list[dict[str, Any]]:
            entries = self._fs.ls(path)
            # Convert to (name, stat, 0) tuples for fuse
            dirs = [".", ".."]
            dirs.extend(e["name"] for e in entries)
            return dirs

        def getattr(self, path: str, fh: Any = None) -> dict[str, Any]:
            import stat as stat_mod

            clean = path.strip("/")
            if not clean or clean.startswith(".") and clean != "info":
                # Root or hidden — treat as directory
                return {
                    "st_mode": stat_mod.S_IFDIR | 0o755,
                    "st_nlink": 2,
                    "st_size": 4096,
                }

            # Check if it's a virtual directory
            is_dir = self._is_virtual_dir(clean)
            if is_dir:
                return {
                    "st_mode": stat_mod.S_IFDIR | 0o755,
                    "st_nlink": 2,
                    "st_size": 4096,
                }

            # Virtual file — get content size
            try:
                content = self._fs.read(path)
                return {
                    "st_mode": stat_mod.S_IFREG | 0o444,
                    "st_nlink": 1,
                    "st_size": len(content),
                }
            except FileNotFoundError:
                raise fuse.FuseOSError(2)  # ENOENT

        def open(self, path: str, flags: int) -> int:
            self._fd_counter += 1
            self._open_files[self._fd_counter] = path
            return self._fd_counter

        def read(self, path: str, size: int, offset: int, fh: int) -> bytes:
            try:
                content = self._fs.read(path)
                return content[offset:offset + size].encode("utf-8")
            except FileNotFoundError:
                return b""

        def release(self, path: str, fh: int) -> int:
            self._open_files.pop(fh, None)
            return 0

        def _is_virtual_dir(self, path: str) -> bool:
            parts = path.split("/")
            # Top-level dirs
            if len(parts) == 1:
                return parts[0] in ("kb", "memory", "trace", "notes")
            # Sub-dirs
            if parts[0] == "memory" and len(parts) == 2:
                return parts[1] in ("l1", "l2", "l3")
            if parts[0] == "kb" and len(parts) == 2:
                return not parts[1].startswith(".")  # KB names are dirs
            if parts[0] == "kb" and len(parts) >= 2 and parts[1] == "search":
                return True
            return False

    mountpoint = Path(mountpoint)
    mountpoint.mkdir(parents=True, exist_ok=True)

    logger.info("Mounting RAGFS at %s", mountpoint)
    fuse.FUSE(RAGFUSE(), str(mountpoint), foreground=True, nothreads=True)


# ═══════════════════════════════════════════════════════════
# Convenience
# ═══════════════════════════════════════════════════════════


def ensure_dirs() -> None:
    """Ensure all RAGFS directories exist."""
    CONTEXT_ROOT.mkdir(parents=True, exist_ok=True)
    MEMORY_ROOT.mkdir(parents=True, exist_ok=True)


__all__ = [
    "VirtualContextFS",
    "mount_fuse",
    "ensure_dirs",
    "CONTEXT_ROOT",
    "MEMORY_ROOT",
]
