"""
Partner System — Swarm Agents with Personality.

DeepTutor-inspired partners with SOUL.md identity, private workspace,
isolated memory, and consult-subagent pattern.

Architecture::

    ~/.aiw/partners/
    ├── <partner-name>/
    │   ├── config.yaml              # Name, description, tool policy
    │   ├── workspace/
    │   │   └── user/
    │   │       └── workspace/
    │   │           ├── SOUL.md      # Identity, rules, expertise
    │   │           ├── memory/      # Partner's private PersistentMemory
    │   │           └── knowledge/   # Partner's own knowledge files
    │   └── sessions/               # Conversation history

Usage::

    # Create a partner
    partner = Partner.create(
        name="critic",
        soul="You are a ruthless code reviewer..."
    )

    # List partners
    for p in Partner.list_all():
        print(p.name, p.soul_preview)

    # Consult a partner
    response = partner.consult("Review this code: ...")

    # CLI
    # aiw partners list
    # aiw partners create <name> --soul <text>
    # aiw partners chat <name> <message>
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("aiw.partner")

# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

_PARTNERS_DIR = Path.home() / ".aiw" / "partners"
_SOUL_FILENAME = "SOUL.md"
_CONFIG_FILENAME = "config.yaml"

_DEFAULT_SOUL = """# Soul

I am a helpful AI assistant. I communicate clearly,
adapt to the user's needs, and value accuracy over speed.
"""

_ID_SAFE_RE = re.compile(r"[^a-z0-9-]+")

# ═══════════════════════════════════════════════════════════
# Data Types
# ═══════════════════════════════════════════════════════════


def _now() -> str:
    return datetime.now(UTC).isoformat()


def slugify(name: str) -> str:
    """Create a filesystem-safe partner ID from a name."""
    slug = _ID_SAFE_RE.sub("-", name.strip().lower()).strip("-")
    return slug or "partner"


@dataclass
class ToolPolicy:
    """Allowed and denied tools for a partner.

    Tools checked at invocation time::

        if tool in denied:             → block
        if allowed is not None
            and tool not in allowed:   → block
        else:                          → allow

    ``allowed=None`` means all tools allowed (except denied).
    """

    allowed: list[str] | None = None  # None = allow all
    denied: list[str] = field(default_factory=list)

    def is_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed for this partner."""
        if tool_name in self.denied:
            return False
        if self.allowed is not None and tool_name not in self.allowed:
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.allowed is not None:
            out["allowed"] = self.allowed
        if self.denied:
            out["denied"] = self.denied
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> ToolPolicy:
        if not data:
            return cls()
        return cls(
            allowed=data.get("allowed"),
            denied=data.get("denied", []),
        )


@dataclass
class Partner:
    """A persistent agent with its own identity, workspace, and memory.

    Attributes:
        name: Human-readable partner name.
        partner_id: Filesystem-safe ID (auto-derived from name).
        description: One-line description of expertise.
        soul_path: Path to the SOUL.md file.
        workspace_dir: Partner's private workspace root.
        config_path: Path to config.yaml.
        tool_policy: Allowed/denied tool configuration.
        created_at: ISO timestamp of creation.
        updated_at: ISO timestamp of last update.
        emoji: Optional emoji avatar.
        color: Optional hex color for UI display.
    """

    name: str
    partner_id: str = ""
    description: str = ""
    soul: str = ""
    tool_policy: ToolPolicy = field(default_factory=ToolPolicy)
    created_at: str = ""
    updated_at: str = ""
    emoji: str = ""
    color: str = ""

    # Derived paths (set after creation)
    _base_dir: str = ""
    _config_path: str = ""
    _soul_path: str = ""

    def __post_init__(self) -> None:
        if not self.partner_id:
            self.partner_id = slugify(self.name)
        if not self.created_at:
            self.created_at = _now()
        if not self.updated_at:
            self.updated_at = self.created_at

    # ── Property Adapters ─────────────────────────────────────────────

    @property
    def base_dir(self) -> Path:
        return Path(self._base_dir) if self._base_dir else _PARTNERS_DIR / self.partner_id

    @property
    def workspace_dir(self) -> Path:
        return self.base_dir / "workspace" / "user" / "workspace"

    @property
    def memory_dir(self) -> Path:
        return self.workspace_dir / "memory"

    @property
    def knowledge_dir(self) -> Path:
        return self.workspace_dir / "knowledge"

    @property
    def sessions_dir(self) -> Path:
        return self.base_dir / "sessions"

    @property
    def config_path(self) -> Path:
        return Path(self._config_path) if self._config_path else self.base_dir / _CONFIG_FILENAME

    @property
    def soul_file(self) -> Path:
        return Path(self._soul_path) if self._soul_path else self.workspace_dir / _SOUL_FILENAME

    @property
    def soul_preview(self) -> str:
        """First line of the SOUL.md after the title."""
        lines = self.soul.strip().split("\n")
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return stripped[:80]
        return "(empty)"

    # ── CRUD ──────────────────────────────────────────────────────────

    @classmethod
    def create(
        cls,
        name: str,
        soul: str = "",
        description: str = "",
        tool_policy: ToolPolicy | None = None,
        emoji: str = "",
        color: str = "",
        overwrite: bool = False,
    ) -> Partner:
        """Create a new partner with filesystem workspace.

        Args:
            name: Human-readable name.
            soul: SOUL.md content (identity, rules, expertise).
            description: One-line description.
            tool_policy: Tool access policy (default: all allowed).
            emoji: Optional emoji avatar.
            color: Optional hex color.
            overwrite: Overwrite existing partner if True.

        Returns:
            The created Partner instance.

        Raises:
            FileExistsError: If partner already exists and overwrite=False.
        """
        partner_id = slugify(name)
        base_dir = _PARTNERS_DIR / partner_id

        if base_dir.exists() and not overwrite:
            raise FileExistsError(
                f"Partner '{name}' already exists at {base_dir}. "
                "Use overwrite=True to replace."
            )

        now = _now()

        partner = cls(
            name=name,
            partner_id=partner_id,
            description=description,
            soul=soul or _DEFAULT_SOUL,
            tool_policy=tool_policy or ToolPolicy(),
            created_at=now,
            updated_at=now,
            emoji=emoji,
            color=color,
        )

        # Create filesystem structure
        partner.workspace_dir.mkdir(parents=True, exist_ok=True)
        partner.memory_dir.mkdir(parents=True, exist_ok=True)
        partner.knowledge_dir.mkdir(parents=True, exist_ok=True)
        partner.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Write SOUL.md
        partner.soul_file.write_text(partner.soul, encoding="utf-8")

        # Write config
        partner._write_config()

        logger.info("Created partner '%s' (%s)", name, partner_id)
        return partner

    def save(self) -> None:
        """Save current state to filesystem."""
        self.updated_at = _now()
        self._write_config()
        if self.soul:
            self.soul_file.parent.mkdir(parents=True, exist_ok=True)
            self.soul_file.write_text(self.soul, encoding="utf-8")
        logger.debug("Saved partner '%s'", self.name)

    def delete(self) -> None:
        """Delete this partner and its entire workspace."""
        import shutil

        if self.base_dir.exists():
            shutil.rmtree(self.base_dir)
            logger.info("Deleted partner '%s' (%s)", self.name, self.partner_id)

    # ── Partner Directory ─────────────────────────────────────────────

    @classmethod
    def list_all(cls) -> list[Partner]:
        """List all registered partners."""
        if not _PARTNERS_DIR.is_dir():
            return []
        partners: list[Partner] = []
        for entry in sorted(_PARTNERS_DIR.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                try:
                    partner = cls.load(entry.name)
                    partners.append(partner)
                except Exception as exc:
                    logger.warning("Failed to load partner '%s': %s", entry.name, exc)
        return partners

    @classmethod
    def load(cls, partner_id: str) -> Partner:
        """Load a partner from its directory by partner_id.

        Args:
            partner_id: Filesystem-safe partner ID.

        Returns:
            Partner instance.

        Raises:
            FileNotFoundError: If the partner directory doesn't exist.
        """
        base_dir = _PARTNERS_DIR / partner_id
        if not base_dir.is_dir():
            raise FileNotFoundError(f"Partner not found: '{partner_id}'")

        config_path = base_dir / _CONFIG_FILENAME
        soul_path = base_dir / "workspace" / "user" / "workspace" / _SOUL_FILENAME

        config: dict[str, Any] = {}
        if config_path.exists():
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

        soul = ""
        if soul_path.exists():
            soul = soul_path.read_text(encoding="utf-8")

        partner = cls(
            name=config.get("name", partner_id),
            partner_id=partner_id,
            description=config.get("description", ""),
            soul=soul,
            tool_policy=ToolPolicy.from_dict(config.get("tool_policy")),
            created_at=config.get("created_at", ""),
            updated_at=config.get("updated_at", ""),
            emoji=config.get("emoji", ""),
            color=config.get("color", ""),
        )
        partner._base_dir = str(base_dir)
        partner._config_path = str(config_path)
        partner._soul_path = str(soul_path)
        return partner

    @classmethod
    def get(cls, name_or_id: str) -> Partner | None:
        """Find a partner by name (fuzzy) or partner_id.

        Tries exact partner_id first, then slugified name, then
        case-insensitive name match.
        """
        # Exact match first
        if (_PARTNERS_DIR / name_or_id).is_dir():
            return cls.load(name_or_id)

        slug = slugify(name_or_id)
        if slug != name_or_id and (_PARTNERS_DIR / slug).is_dir():
            return cls.load(slug)

        # Case-insensitive name match
        for p in cls.list_all():
            if p.name.lower() == name_or_id.lower():
                return p

        return None

    # ── Represent ─────────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "partner_id": self.partner_id,
            "description": self.description,
            "tool_policy": self.tool_policy.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "emoji": self.emoji,
            "color": self.color,
            "soul_preview": self.soul_preview,
            "soul_length": len(self.soul),
        }

    def __repr__(self) -> str:
        return f"Partner(name='{self.name}', id='{self.partner_id}')"

    # ── Consultation ──────────────────────────────────────────────────

    def consult(self, message: str, memory_context: str = "") -> str:
        """Consult the partner with a message.

        Routes through the agent loop with the partner's SOUL.md
        persona and private knowledge injected into context.
        Falls back to a simulated response if the loop is unavailable.

        Args:
            message: The message/query to send to the partner.
            memory_context: Optional context from the caller's memory.

        Returns:
            Partner's response text.
        """
        try:
            import asyncio

            from ai_workspace.agents.loop import (
                LoopParams,
                LoopPattern,
                agent_loop,
            )

            # Build system prompt from SOUL.md + private context
            soul = self.soul_preview
            l2_ctx = ""
            if self.memory_dir.exists():
                l2_files = list(self.memory_dir.glob("*.md"))[:3]
                for f in l2_files:
                    l2_ctx += f"\n\n--- {f.stem} ---\n{f.read_text(encoding='utf-8')[:2000]}"

            system = (
                f"You are {self.name}, a partner with the following persona:\n\n"
                f"{soul}\n\n"
                f"Respond in character. Be concise and helpful."
            )
            if l2_ctx:
                system += f"\n\n[PRIVATE KNOWLEDGE]\n{l2_ctx}"
            if memory_context:
                system += f"\n\n[CALLER CONTEXT]\n{memory_context}"

            params = LoopParams(
                task=message,
                pattern=LoopPattern.DIRECT,
                system_prompt=system,
                max_turns=5,
            )

            async def _run():
                result = ""
                async for event in agent_loop(params):
                    if event.type == "token":
                        result += event.data.get("text", "")
                return result

            # Run in existing event loop or create one
            try:
                asyncio.get_running_loop()
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(asyncio.run, _run())
                    result = future.result(timeout=60)
            except RuntimeError:
                result = asyncio.run(_run())
            except Exception:
                result = ""

            # Fallback to simulated response if LLM result is empty
            if not result:
                raise RuntimeError("Empty LLM response")
            return result

        except Exception:
            # Fallback: simulated response using persona
            soul = self.soul_preview
            persona_hint = soul[:100] if soul else self.name
            return (
                f"[{self.name} ({persona_hint}...) "
                f"consulting on: {message[:80]}...]"
            )

    # ── Internal ──────────────────────────────────────────────────────

    def _write_config(self) -> None:
        """Write config.yaml to the partner's base directory."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "name": self.name,
            "partner_id": self.partner_id,
            "description": self.description,
            "tool_policy": self.tool_policy.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "emoji": self.emoji,
            "color": self.color,
        }
        self.config_path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True),
            encoding="utf-8",
        )


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════


def ensure_partners_dir() -> Path:
    """Ensure the global partners directory exists."""
    _PARTNERS_DIR.mkdir(parents=True, exist_ok=True)
    return _PARTNERS_DIR


__all__ = [
    "Partner",
    "ToolPolicy",
    "slugify",
    "ensure_partners_dir",
    "_DEFAULT_SOUL",
]
