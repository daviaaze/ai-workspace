"""
Persistent Memory — L1/L2/L3 Hierarchical Memory System.

Inspired by DeepTutor's 3-layer memory architecture. This is a *persistent*,
*cross-session* memory system (as opposed to the in-session ``MemoryTree``
in ``memory_tree.py``, which tracks execution state within a single session).

Each agent session writes an L1 trace → a summarizer extracts L2 facts →
periodic consolidation produces L3 synthesis. Every claim is traceable:
L3 ═══ cites ═══> L2 ═══ cites ═══> L1 (timestamped trace events).

Directory layout::

    ~/.aiw/memory/
    ├── l1/
    │   ├── 2026-06-24.jsonl          # One file per day
    │   └── 2026-06-25.jsonl
    ├── l2/
    │   ├── coding.md                  # Surface: coding patterns & fixes
    │   ├── research.md               # Surface: research findings
    │   ├── operations.md             # Surface: errors & workarounds
    │   └── decisions.md              # Surface: technical decisions
    └── l3/
        ├── profile.md                 # Who the user is, preferences
        ├── recent.md                  # What happened recently
        └── scope.md                   # Current context & active surfaces

Usage::

    # At end of session
    mem = PersistentMemory()
    mem.write_l1_trace(session_id, events)
    mem.consolidate_l2(surface="coding")
    mem.consolidate_l3()
    print(mem.summary())
"""

from __future__ import annotations

import json as _json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("aiw.memory")

# Default storage root
_DEFAULT_MEMORY_DIR = Path.home() / ".aiw" / "memory"


# ═══════════════════════════════════════════════════════════
# Data types
# ═══════════════════════════════════════════════════════════


@dataclass
class TraceEvent:
    """A single event recorded in an L1 trace."""

    timestamp: str  # ISO 8601
    session_id: str
    type: str  # "tool_call", "tool_result", "thinking", "error", "phase"
    content: str
    tool: str = ""
    tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class L1Trace:
    """A collection of events from one session (written to a daily .jsonl)."""

    session_id: str
    surface: str  # "coding", "research", "operations", "decisions"
    events: list[TraceEvent] = field(default_factory=list)
    started_at: str = ""
    ended_at: str = ""
    model: str = ""
    total_tokens: int = 0

    def add_event(self, event: TraceEvent) -> None:
        self.events.append(event)
        self.total_tokens += event.tokens


@dataclass
class L2Fact:
    """A single extracted fact for one surface."""

    surface: str
    title: str
    body: str
    source_session: str  # Session ID this fact was extracted from
    source_timestamp: str  # When the source event(s) occurred
    tags: list[str] = field(default_factory=list)


@dataclass
class MemoryStats:
    """Statistics about the persistent memory store."""

    l1_files: int = 0
    l1_events: int = 0
    l2_facts: int = 0
    l3_files: int = 0
    total_sessions: int = 0
    storage_bytes: int = 0
    memory_dir: str = ""


# ═══════════════════════════════════════════════════════════
# PersistentMemory
# ═══════════════════════════════════════════════════════════


class PersistentMemory:
    """Cross-session persistent memory with L1/L2/L3 layers.

    Thread-safe for concurrent sessions writing to the same daily file
    (each write is a single append, so OS file writes are atomic enough).

    Args:
        memory_dir: Root directory for memory storage.
            Defaults to ``~/.aiw/memory/``.
    """

    def __init__(self, memory_dir: str | Path | None = None) -> None:
        self._root = Path(memory_dir) if memory_dir else _DEFAULT_MEMORY_DIR
        self._l1_dir = self._root / "l1"
        self._l2_dir = self._root / "l2"
        self._l3_dir = self._root / "l3"

        for d in [self._l1_dir, self._l2_dir, self._l3_dir]:
            d.mkdir(parents=True, exist_ok=True)

        logger.debug("PersistentMemory root: %s", self._root)

    # ── L1: Event Traces ────────────────────────────────────────────────────

    def write_l1_trace(self, session_id: str, events: list[TraceEvent]) -> None:
        """Write an L1 trace to the daily JSONL file.

        Each event is one line. The daily file is append-only.

        Args:
            session_id: Unique session identifier.
            events: List of trace events from this session.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = self._l1_dir / f"{today}.jsonl"

        records: list[dict[str, Any]] = []
        for event in events:
            records.append({
                "timestamp": event.timestamp,
                "session_id": session_id or event.session_id,
                "type": event.type,
                "content": event.content[:2000],
                "tool": event.tool,
                "tokens": event.tokens,
                "metadata": event.metadata,
            })

        try:
            with open(path, "a") as f:
                for record in records:
                    f.write(_json.dumps(record, ensure_ascii=False) + "\n")
            logger.debug(
                "Wrote L1 trace: %d events → %s (session=%s)",
                len(events), path.name, session_id,
            )
        except OSError as exc:
            logger.error("Failed to write L1 trace to %s: %s", path, exc)

    def read_l1_events(
        self,
        session_id: str | None = None,
        surface: str | None = None,
        since: str | None = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        """Read L1 events with optional filters.

        Args:
            session_id: Filter by session ID.
            surface: Filter by surface tag.
            since: ISO date string (e.g. "2026-06-01").
            limit: Maximum events to return.

        Returns:
            List of event dicts, newest first.
        """
        events: list[dict[str, Any]] = []
        files = sorted(self._l1_dir.glob("*.jsonl"), reverse=True)

        for filepath in files:
            if since and filepath.stem < since:
                continue

            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = _json.loads(line)
                    except _json.JSONDecodeError:
                        continue

                    if session_id and event.get("session_id") != session_id:
                        continue
                    if surface and surface not in event.get("metadata", {}).get("surfaces", []):
                        continue

                    events.append(event)

                    if len(events) >= limit:
                        return events

        return events

    def get_l1_files(self) -> list[Path]:
        """Return sorted list of daily L1 trace files (newest first)."""
        return sorted(self._l1_dir.glob("*.jsonl"), reverse=True)

    # ── L2: Per-Surface Facts ───────────────────────────────────────────────

    def write_l2_facts(
        self,
        surface: str,
        facts: list[L2Fact],
        append: bool = True,
    ) -> None:
        """Write extracted facts to the L2 markdown file for a surface.

        Args:
            surface: Surface name (e.g. "coding", "research").
            facts: List of extracted facts.
            append: If True, append to existing file. Otherwise overwrite.
        """
        path = self._l2_dir / f"{surface}.md"
        mode = "a" if append else "w"

        lines: list[str] = []

        if not append:
            lines.append(f"# {surface.title()}\n")

        for fact in facts:
            lines.append(f"\n## {fact.title}\n")
            lines.append(f"{fact.body}\n")
            if fact.tags:
                lines.append(f"Tags: {', '.join(f'`{t}`' for t in fact.tags)}\n")
            lines.append(
                f"*Source: session `{fact.source_session}` "
                f"at {fact.source_timestamp}*\n"
            )

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, mode) as f:
                f.writelines(lines)
            logger.debug(
                "Wrote L2 facts: %d facts → %s/%s",
                len(facts), surface, path.name,
            )
        except OSError as exc:
            logger.error("Failed to write L2 facts to %s: %s", path, exc)

    def read_l2_facts(self, surface: str) -> list[dict[str, Any]]:
        """Read L2 facts for a given surface.

        Returns:
            List of fact dicts with keys: title, body, tags, source.
        """
        path = self._l2_dir / f"{surface}.md"
        if not path.exists():
            return []

        return self._parse_l2_markdown(path)

    def list_l2_surfaces(self) -> list[str]:
        """List all surfaces that have L2 fact files."""
        return sorted(
            path.stem for path in self._l2_dir.glob("*.md")
        )

    def get_l2_context(self, surfaces: list[str] | None = None) -> str:
        """Build a context string from L2 facts for given surfaces.

        Args:
            surfaces: List of surfaces to include. If None, includes all.

        Returns:
            Markdown-formatted context string.
        """
        if surfaces is None:
            surfaces = self.list_l2_surfaces()

        parts: list[str] = []
        for surface in surfaces:
            facts = self.read_l2_facts(surface)
            if not facts:
                continue

            parts.append(f"### {surface.title()}\n")
            for fact in facts[:5]:  # Top 5 per surface
                parts.append(f"- **{fact['title']}**: {fact['body'][:300]}")
            parts.append("")

        return "\n".join(parts)

    # ── L3: Cross-Surface Synthesis ─────────────────────────────────────────

    def write_l3_profile(self, content: str, append: bool = False) -> None:
        """Write or update the L3 profile synthesis.

        The profile captures:
        - Who the user is (role, expertise)
        - Preferences (model, tools, workflow)
        - Long-term patterns

        Args:
            content: Markdown content for the profile.
            append: If True, append. Otherwise overwrite.
        """
        self._write_l3("profile", content, append=append)

    def write_l3_recent(self, content: str, append: bool = False) -> None:
        """Write or update the L3 recent activity synthesis.

        The recent file captures what happened in the last few sessions.

        Args:
            content: Markdown content for recent activity.
            append: If True, append. Otherwise overwrite.
        """
        self._write_l3("recent", content, append=append)

    def write_l3_scope(self, content: str, append: bool = False) -> None:
        """Write or update the L3 scope synthesis.

        The scope file captures:
        - Current active projects/contexts
        - What the user is working on now
        - Open questions or blockers

        Args:
            content: Markdown content for scope.
            append: If True, append. Otherwise overwrite.
        """
        self._write_l3("scope", content, append=append)

    def read_l3(self, name: str) -> str:
        """Read an L3 synthesis file.

        Args:
            name: One of "profile", "recent", "scope".

        Returns:
            File content as string, or empty string if not found.
        """
        path = self._l3_dir / f"{name}.md"
        if path.exists():
            return path.read_text()
        return ""

    def list_l3_files(self) -> list[Path]:
        """List all L3 synthesis files."""
        return sorted(self._l3_dir.glob("*.md"))

    # ── Consolidation Helpers ───────────────────────────────────────────────

    def consolidate_l2(
        self,
        surface: str,
        session_id: str,
        events: list[TraceEvent],
        llm_summary: bool = False,
    ) -> list[L2Fact]:
        """Consolidate session events into L2 facts for a surface.

        This is the bridge from L1 → L2. It extracts structured facts
        from raw trace events using heuristic patterns.

        Args:
            surface: Surface name to consolidate into.
            session_id: Current session ID for source attribution.
            events: List of trace events from this session.
            llm_summary: If True, use LLM for extraction (expensive).
                If False, use heuristic pattern matching (fast).

        Returns:
            List of extracted L2Facts.
        """
        if llm_summary:
            return self._extract_facts_llm(surface, session_id, events)

        return self._extract_facts_heuristic(surface, session_id, events)

    def consolidate_l3(self, surfaces: list[str] | None = None) -> dict[str, str]:
        """Generate an L3 synthesis from current L2 facts.

        Reads all L2 surfaces, builds profile/recent/scope summaries,
        and writes them to L3.

        This is a heuristic consolidation. For LLM-powered consolidation,
        use ``consolidate_l3_with_llm()``.

        Args:
            surfaces: Subset of surfaces to consolidate. Defaults to all.

        Returns:
            Dict mapping L3 file name to content written.
        """
        if surfaces is None:
            surfaces = self.list_l2_surfaces()

        # Build recent activity from all surfaces
        recent_parts: list[str] = []
        for surface in surfaces:
            facts = self.read_l2_facts(surface)
            if facts:
                recent_parts.append(f"### {surface.title()}")
                for fact in facts[-3:]:  # Last 3 facts per surface
                    recent_parts.append(
                        f"- {fact['title']}: {fact['body'][:200]}"
                    )
                recent_parts.append("")

        recent_content = (
            f"# Recent Activity\n"
            f"*Generated: {datetime.now(timezone.utc).isoformat()}*\n\n"
            + "\n".join(recent_parts)
            if recent_parts
            else "# Recent Activity\n*No activity recorded yet.*\n"
        )

        # Build scope from surfaces
        scope_content = (
            f"# Current Scope\n"
            f"*Generated: {datetime.now(timezone.utc).isoformat()}*\n\n"
            f"Active surfaces: {', '.join(f'`{s}`' for s in surfaces)}\n\n"
            f"See individual surface files in L2 for details.\n"
        )

        self.write_l3_recent(recent_content)
        self.write_l3_scope(scope_content)

        return {"recent": recent_content, "scope": scope_content}

    async def consolidate_l3_with_llm(
        self,
        model: str = "qwen3:14b",
        provider: str = "ollama",
    ) -> dict[str, str]:
        """Generate L3 synthesis using an LLM for richer consolidation.

        This reads all L2 facts, sends them to an LLM, and writes
        the synthesized L3 files.

        Args:
            model: Model name for the LLM.
            provider: Provider name.

        Returns:
            Dict mapping L3 file name to content written.
        """
        from ai_workspace.providers import ProviderRegistry

        registry = ProviderRegistry()
        client = registry.get_client(provider)
        if not client:
            logger.warning("No provider '%s' available, using heuristic L3", provider)
            return self.consolidate_l3()

        surfaces = self.list_l2_surfaces()
        all_facts: list[str] = []

        for surface in surfaces:
            facts = self.read_l2_facts(surface)
            for fact in facts:
                all_facts.append(
                    f"[{surface}] {fact['title']}: {fact['body'][:500]}"
                )

        if not all_facts:
            return self.consolidate_l3()

        facts_text = "\n".join(all_facts)

        prompt = f"""You are the synthesis layer of a persistent memory system.
Given the following L2 facts from recent sessions, generate three L3 summaries:

1. **Profile**: Who the user appears to be based on patterns. Keep it concise.
2. **Recent**: A chronological narrative of the last few sessions. Group by surface.
3. **Scope**: What the user is currently working on, open questions, blockers.

L2 Facts:
{facts_text}

Respond with:

---profile
<profile content>

---recent
<recent content>

---scope
<scope content>"""

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                stream=False,
            )

            content = response.choices[0].message.content if response.choices else ""
            sections: dict[str, str] = {}

            current_section = ""
            current_body: list[str] = []

            for line in content.split("\n"):
                if line.startswith("---"):
                    if current_section and current_body:
                        sections[current_section] = "\n".join(current_body)
                    current_section = line.strip("- ").strip()
                    current_body = []
                else:
                    current_body.append(line)

            if current_section and current_body:
                sections[current_section] = "\n".join(current_body)

            if sections.get("profile"):
                self.write_l3_profile(sections["profile"])
            if sections.get("recent"):
                self.write_l3_recent(sections["recent"])
            if sections.get("scope"):
                self.write_l3_scope(sections["scope"])

            return sections

        except Exception as exc:
            logger.warning("LLM L3 consolidation failed: %s", exc)
            return self.consolidate_l3()

    # ── Summary & Stats ─────────────────────────────────────────────────────

    def summary(self) -> str:
        """Return a human-readable summary of memory contents."""
        stats = self.stats()

        lines = [
            "## Persistent Memory Summary",
            f"**Location:** {stats.memory_dir}",
            f"**L1 Traces:** {stats.l1_files} files, {stats.l1_events} events",
            f"**L2 Facts:** {stats.l2_facts} across {len(self.list_l2_surfaces())} surfaces",
            f"**L3 Files:** {stats.l3_files}",
            f"**Total Sessions Indexed:** {stats.total_sessions}",
            f"**Storage:** {self._format_bytes(stats.storage_bytes)}",
            "",
            "### L2 Surfaces",
        ]

        for surface in self.list_l2_surfaces():
            facts = self.read_l2_facts(surface)
            lines.append(f"  - `{surface}` — {len(facts)} facts")

        lines.append("")
        lines.append("### L3 Files")
        for path in self.list_l3_files():
            size = len(path.read_text()) if path.exists() else 0
            lines.append(f"  - `{path.name}` — {size} bytes")

        return "\n".join(lines)

    def stats(self) -> MemoryStats:
        """Get statistics about the memory store."""
        l1_files = list(self._l1_dir.glob("*.jsonl"))
        l2_files = list(self._l2_dir.glob("*.md"))
        l3_files = list(self._l3_dir.glob("*.md"))

        l1_events = 0
        session_ids: set[str] = set()

        for path in l1_files:
            try:
                with open(path) as f:
                    for line in f:
                        if line.strip():
                            l1_events += 1
                            try:
                                ev = _json.loads(line)
                                if "session_id" in ev:
                                    session_ids.add(ev["session_id"])
                            except _json.JSONDecodeError:
                                pass
            except OSError:
                pass

        l2_facts = 0
        for path in l2_files:
            try:
                l2_facts += len(self._parse_l2_markdown(path))
            except OSError:
                pass

        total_bytes = sum(
            f.stat().st_size
            for d in [self._l1_dir, self._l2_dir, self._l3_dir]
            for f in d.glob("*")
            if f.is_file()
        )

        return MemoryStats(
            l1_files=len(l1_files),
            l1_events=l1_events,
            l2_facts=l2_facts,
            l3_files=len(l3_files),
            total_sessions=len(session_ids),
            storage_bytes=total_bytes,
            memory_dir=str(self._root),
        )

    # ── Private helpers ─────────────────────────────────────────────────────

    def _write_l3(self, name: str, content: str, *, append: bool) -> None:
        """Private writer for L3 files."""
        path = self._l3_dir / f"{name}.md"
        mode = "a" if append else "w"

        if not append:
            content = (
                f"# {name.title()}\n"
                f"*Updated: {datetime.now(timezone.utc).isoformat()}*\n\n"
                + content
            )

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, mode) as f:
                f.write(content + "\n")
            logger.debug("Wrote L3 file: %s", path.name)
        except OSError as exc:
            logger.error("Failed to write L3 file %s: %s", path, exc)

    def _extract_facts_heuristic(
        self,
        surface: str,
        session_id: str,
        events: list[TraceEvent],
    ) -> list[L2Fact]:
        """Extract facts using heuristic pattern matching.

        Much faster than LLM extraction. Good enough for most cases.
        """
        facts: list[L2Fact] = []
        seen: set[str] = set()

        tool_patterns = {
            "error": re.compile(r"(error|failed|exception|traceback)", re.IGNORECASE),
            "fix": re.compile(r"(fixed|patched|resolved|workaround|solution)", re.IGNORECASE),
            "install": re.compile(r"(pip install|npm install|nix-env|apt )", re.IGNORECASE),
            "decision": re.compile(r"(decided|chose|prefer|switched to|migrated)", re.IGNORECASE),
            "pattern": re.compile(r"(pattern|convention|standard|anti-pattern)", re.IGNORECASE),
        }

        for event in events:
            if not event.content:
                continue

            # Skip thinking events — they're internal
            if event.type == "thinking":
                continue

            # Check for errors
            if event.type == "error" or event.type == "tool_result" and tool_patterns["error"].search(event.content):
                title = self._truncate(event.content[:80], 60)
                fact = L2Fact(
                    surface=surface,
                    title=f"Error: {title}",
                    body=event.content[:500],
                    source_session=session_id,
                    source_timestamp=event.timestamp,
                    tags=["error"],
                )
                dedup_key = fact.title[:40]
                if dedup_key not in seen:
                    facts.append(fact)
                    seen.add(dedup_key)
                continue

            # Check for fixes
            if tool_patterns["fix"].search(event.content):
                title = self._truncate(event.content[:80], 60)
                fact = L2Fact(
                    surface=surface,
                    title=f"Fix: {title}",
                    body=event.content[:500],
                    source_session=session_id,
                    source_timestamp=event.timestamp,
                    tags=["fix"],
                )
                dedup_key = fact.title[:40]
                if dedup_key not in seen:
                    facts.append(fact)
                    seen.add(dedup_key)
                continue

            # Check for decisions
            if tool_patterns["decision"].search(event.content):
                title = self._truncate(event.content[:80], 60)
                fact = L2Fact(
                    surface=surface,
                    title=f"Decision: {title}",
                    body=event.content[:500],
                    source_session=session_id,
                    source_timestamp=event.timestamp,
                    tags=["decision"],
                )
                dedup_key = fact.title[:40]
                if dedup_key not in seen:
                    facts.append(fact)
                    seen.add(dedup_key)
                continue

            # Check for conventions/patterns (shorter content matters)
            if tool_patterns["pattern"].search(event.content):
                title = self._truncate(event.content[:80], 60)
                fact = L2Fact(
                    surface=surface,
                    title=f"Pattern: {title}",
                    body=event.content[:500],
                    source_session=session_id,
                    source_timestamp=event.timestamp,
                    tags=["pattern"],
                )
                dedup_key = fact.title[:40]
                if dedup_key not in seen:
                    facts.append(fact)
                    seen.add(dedup_key)
                continue

            # Check for tool installs
            if tool_patterns["install"].search(event.content):
                title = self._truncate(event.content[:80], 60)
                fact = L2Fact(
                    surface=surface,
                    title=f"Install: {title}",
                    body=event.content[:500],
                    source_session=session_id,
                    source_timestamp=event.timestamp,
                    tags=["installation"],
                )
                dedup_key = fact.title[:40]
                if dedup_key not in seen:
                    facts.append(fact)
                    seen.add(dedup_key)
                continue

        return facts

    async def _extract_facts_llm(
        self,
        surface: str,
        session_id: str,
        events: list[TraceEvent],
    ) -> list[L2Fact]:
        """Extract facts using an LLM for richer extraction.

        More expensive but better at finding implicit patterns.
        """
        from ai_workspace.providers import ProviderRegistry

        events_text = "\n".join(
            f"[{e.type}] {e.content[:300]}"
            for e in events[-20:]  # Last 20 events max
        )

        prompt = f"""Extract key facts from these agent session events for surface '{surface}'.
Focus on: errors, fixes, decisions, patterns, and important findings.

Return each fact as a separate line in format:
TITLE: <short title>
BODY: <1-2 sentence description>
TAGS: <comma-separated tags>

Events:
{events_text}"""

        try:
            registry = ProviderRegistry()
            client = registry.get_client("ollama") or registry.get_client(
                list(registry.providers)[0]
            )

            response = await client.chat.completions.create(
                model="qwen3:14b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                stream=False,
            )

            content = response.choices[0].message.content if response.choices else ""
            facts: list[L2Fact] = []
            current_title = ""
            current_body = ""
            current_tags: list[str] = []
            timestamp = datetime.now(timezone.utc).isoformat()

            for line in content.split("\n"):
                line = line.strip()
                if line.upper().startswith("TITLE:"):
                    if current_title and current_body:
                        facts.append(L2Fact(
                            surface=surface,
                            title=current_title,
                            body=current_body,
                            source_session=session_id,
                            source_timestamp=timestamp,
                            tags=current_tags,
                        ))
                    current_title = line[6:].strip()
                    current_body = ""
                    current_tags = []
                elif line.upper().startswith("BODY:"):
                    current_body = line[5:].strip()
                elif line.upper().startswith("TAGS:"):
                    current_tags = [
                        t.strip() for t in line[5:].split(",")
                        if t.strip()
                    ]

            if current_title and current_body:
                facts.append(L2Fact(
                    surface=surface,
                    title=current_title,
                    body=current_body,
                    source_session=session_id,
                    source_timestamp=timestamp,
                    tags=current_tags,
                ))

            return facts

        except Exception as exc:
            logger.warning("LLM fact extraction failed, falling back to heuristic: %s", exc)
            return self._extract_facts_heuristic(surface, session_id, events)

    @staticmethod
    def _parse_l2_markdown(path: Path) -> list[dict[str, Any]]:
        """Parse an L2 markdown file into structured facts."""
        facts: list[dict[str, Any]] = []
        current: dict[str, Any] = {}

        with open(path) as f:
            for line in f:
                line = line.rstrip()
                if line.startswith("## "):
                    if current:
                        facts.append(current)
                    current = {"title": line[3:].strip(), "body": "", "tags": [], "source": ""}
                elif current:
                    if line.startswith("Tags:"):
                        current["tags"] = [
                            t.strip().strip("`") for t in line[5:].split(",")
                            if t.strip()
                        ]
                    elif line.startswith("*Source:"):
                        current["source"] = line
                    elif line.strip():
                        current["body"] += line + "\n"

        if current:
            facts.append(current)

        return facts

    @staticmethod
    def _truncate(text: str, max_len: int) -> str:
        """Truncate text to max_len, adding ellipsis if needed."""
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."

    @staticmethod
    def _format_bytes(n: int) -> str:
        """Format byte count as human-readable string."""
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024:
                return f"{n:.1f}{unit}"
            n /= 1024
        return f"{n:.1f}TB"
