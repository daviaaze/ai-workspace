"""
`aiw chat` — Conversational CLI with persistent memory.

This is the v2 "daily driver" entry point. A chat session:
- Maintains a rolling conversation history
- Auto-recalls relevant past context from the knowledge base + agent memory
- Auto-summarizes each turn into long-term memory
- Tracks workspace (personal/work) context
- Supports tools (filesystem, git, shell, web)

Run as:
    aiw chat                                  # interactive REPL
    aiw chat --workspace work                 # scoped to work context
    aiw chat --provider openrouter --model gpt-4o
    aiw chat --agent coder                    # persona/coder
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from ai_workspace.providers import ProviderRegistry, chat_sync

console = Console()




@dataclass
class ChatSession:
    """One running chat session.

    Stores:
    - messages: full conversation history
    - workspace: personal/work context
    - agent: persona name (used for memory namespace)
    - provider/model: which LLM
    - recalled_context: vector-search hits the session is currently using
    """

    messages: list[dict[str, str]] = field(default_factory=list)
    workspace: str = "personal"
    agent: str = "default"
    provider: str = "ollama"
    model: str | None = None
    system_prompt: str | None = None
    recalled_context: list[dict[str, Any]] = field(default_factory=list)
    session_id: str | None = None
    turn_count: int = 0
    max_history: int = 20  # rolling window of in-context messages

    def add_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})
        self.turn_count += 1
        self._trim_history()

    def add_assistant(self, content: str) -> None:
        self.messages.append({"role": "assistant", "content": content})

    def add_system(self, content: str) -> None:
        # Keep the system prompt at the front
        if self.messages and self.messages[0]["role"] == "system":
            self.messages[0] = {"role": "system", "content": content}
        else:
            self.messages.insert(0, {"role": "system", "content": content})

    def _trim_history(self) -> None:
        """Keep the most recent N messages, but always keep the system prompt."""
        if len(self.messages) <= self.max_history:
            return
        system = self.messages[0] if self.messages[0]["role"] == "system" else None
        recent = self.messages[-(self.max_history - 1):] if system else self.messages[-self.max_history:]
        self.messages = ([system] if system else []) + recent

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "workspace": self.workspace,
            "agent": self.agent,
            "provider": self.provider,
            "model": self.model,
            "turn_count": self.turn_count,
            "messages": self.messages,
        }




SYSTEM_PROMPTS = {
    "default": (
        "You are AI Workspace, a personal AI assistant with access to a persistent knowledge base, "
        "task manager, and a rich set of tools. Be concise, helpful, and proactive about saving "
        "important context. When the user shares something worth remembering, suggest storing it."
    ),
    "coder": (
        "You are a senior software engineer working inside AI Workspace. "
        "You have filesystem, git, and shell tools available — use them to actually edit code, "
        "run tests, and open PRs rather than just suggesting changes. "
        "Always run tests after making changes. Prefer targeted edits over rewrites. "
        "Follow existing code conventions in the repo."
    ),
    "researcher": (
        "You are a deep research analyst working inside AI Workspace. "
        "Use the available web search and knowledge tools to gather comprehensive evidence. "
        "Cross-reference sources, identify gaps, and synthesize findings into clear reports. "
        "Cite URLs and prefer primary sources. Save key findings to the knowledge base."
    ),
    "planner": (
        "You are a strategic planner working inside AI Workspace. "
        "Break complex goals into ordered, executable steps. "
        "Use the task manager to track work, and the knowledge base to recall past context. "
        "When delegating, be specific about what the next step requires."
    ),
}




def recall_context(query: str, agent: str, workspace: str, limit: int = 3) -> list[dict[str, Any]]:
    """Recall relevant context from the knowledge base + agent memory.

    Best-effort: if the DB is unavailable, returns an empty list.
    """
    results: list[dict[str, Any]] = []
    try:
        from ai_workspace.knowledge import KnowledgeStore

        store = KnowledgeStore()
        store.initialize()

        # Knowledge base hits
        try:
            kb = store.search_knowledge(query, limit=limit)
            for k in kb:
                k["source"] = "knowledge_base"
                results.append(k)
        except Exception:
            pass

        # Agent memory hits
        try:
            mem = store.recall(agent, query, limit=limit)
            for m in mem:
                m["source"] = "agent_memory"
                results.append(m)
        except Exception:
            pass

        store.close()
    except Exception:
        pass
    return results


def store_turn_memory(session: ChatSession, user_msg: str, assistant_msg: str) -> None:
    """Store a compressed memory of the latest turn.

    Heuristic: if the turn is long or contains certain keywords, save it.
    """
    importance = 0.3
    text = f"{user_msg}\n→\n{assistant_msg}"
    if len(assistant_msg) > 500:
        importance += 0.2
    if any(kw in user_msg.lower() for kw in ["remember", "important", "always", "never", "rule", "preference"]):
        importance += 0.4
    importance = min(1.0, importance)

    try:
        from ai_workspace.knowledge import KnowledgeStore

        store = KnowledgeStore()
        store.initialize()
        store.remember(session.agent, text[:2000], "fact", importance)
        store.close()
    except Exception:
        pass




def _print_banner(session: ChatSession) -> None:
    console.print(Panel(
        f"[bold cyan]AI Workspace Chat[/]\n"
        f"Workspace: [yellow]{session.workspace}[/] | "
        f"Persona: [yellow]{session.agent}[/] | "
        f"Model: [yellow]{session.provider}/{session.model or 'default'}[/]\n\n"
        f"[dim]Commands: /exit, /workspace, /persona, /model, /recall, /clear, /help[/]",
        border_style="cyan",
    ))


def _format_recall(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    lines = ["Relevant context I found:"]
    for it in items[:5]:
        src = it.get("source", "?")
        title = it.get("title") or it.get("content", "")[:80]
        body = (it.get("content") or it.get("answer") or "")[:200]
        lines.append(f"  • [{src}] {title}: {body}")
    return "\n".join(lines)


def _handle_slash_command(cmd: str, session: ChatSession) -> bool:
    """Handle slash commands. Returns True if the REPL should continue."""
    parts = cmd.strip().split(maxsplit=1)
    name = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if name in ("/exit", "/quit", "/q"):
        console.print("[dim]Goodbye.[/]")
        return False

    if name == "/help":
        console.print(Panel(
            "[cyan]/workspace <name>[/]  — switch to personal/work/etc.\n"
            "[cyan]/persona <name>[/]   — switch to default/coder/researcher/planner\n"
            "[cyan]/model <id>[/]      — change model for current provider\n"
            "[cyan]/provider <id>[/]   — switch provider (ollama/deepseek/nvidia/openrouter)\n"
            "[cyan]/recall <query>[/]  — manually search knowledge base\n"
            "[cyan]/clear[/]           — clear conversation history\n"
            "[cyan]/save[/]            — save current session as a knowledge entry\n"
            "[cyan]/status[/]          — show current session state\n"
            "[cyan]/exit[/]            — quit",
            title="Commands",
            border_style="dim",
        ))
        return True

    if name == "/workspace":
        if arg:
            session.workspace = arg
            console.print(f"[green] Workspace → {arg}[/]")
        else:
            console.print(f"[dim]Current workspace: {session.workspace}[/]")
        return True

    if name == "/persona":
        if arg and arg in SYSTEM_PROMPTS:
            session.agent = arg
            session.system_prompt = SYSTEM_PROMPTS[arg]
            session.add_system(session.system_prompt)
            console.print(f"[green] Persona → {arg}[/]")
        else:
            valid = ", ".join(SYSTEM_PROMPTS.keys())
            console.print(f"[red]Unknown persona. Available: {valid}[/]")
        return True

    if name == "/model":
        if arg:
            session.model = arg
            console.print(f"[green] Model → {arg}[/]")
        else:
            console.print(f"[dim]Current model: {session.model}[/]")
        return True

    if name == "/provider":
        if arg:
            session.provider = arg
            session.model = None  # reset to provider default
            console.print(f"[green] Provider → {arg} (model reset)[/]")
        else:
            console.print(f"[dim]Current provider: {session.provider}[/]")
        return True

    if name == "/recall":
        if arg:
            hits = recall_context(arg, session.agent, session.workspace)
            session.recalled_context = hits
            if hits:
                console.print(Panel(_format_recall(hits), title=" Recalled", border_style="blue"))
            else:
                console.print(f"[dim]No results for '{arg}'[/]")
        else:
            console.print("[dim]Usage: /recall <query>[/]")
        return True

    if name == "/clear":
        session.messages = []
        if session.system_prompt:
            session.add_system(session.system_prompt)
        console.print("[green] Conversation cleared[/]")
        return True

    if name == "/save":
        try:
            from ai_workspace.knowledge import KnowledgeStore

            store = KnowledgeStore()
            store.initialize()
            transcript = json.dumps(
                [{"role": m["role"], "content": m["content"]} for m in session.messages],
                indent=2,
                ensure_ascii=False,
            )
            kid = store.add_knowledge(
                transcript,
                content_type="chat",
                title=f"Chat session {session.session_id or 'adhoc'} ({session.turn_count} turns)",
                tags=[session.workspace, session.agent, "chat-transcript"],
            )
            store.close()
            console.print(f"[green] Saved as knowledge #{kid}[/]")
        except Exception as e:
            console.print(f"[red] Save failed: {e}[/]")
        return True

    if name == "/status":
        console.print(Panel(
            f"Session: [cyan]{session.session_id or 'adhoc'}[/]\n"
            f"Workspace: [yellow]{session.workspace}[/]\n"
            f"Persona: [yellow]{session.agent}[/]\n"
            f"Provider/Model: [yellow]{session.provider}/{session.model or 'default'}[/]\n"
            f"Turns: [yellow]{session.turn_count}[/]\n"
            f"Messages in context: [yellow]{len(session.messages)}[/]",
            title="Status",
        ))
        return True

    console.print(f"[red]Unknown command: {cmd}[/] (try /help)")
    return True


def run_chat_repl(
    workspace: str = "personal",
    agent: str = "default",
    provider: str = "ollama",
    model: str | None = None,
    no_recall: bool = False,
) -> None:
    """Run the interactive chat REPL."""
    registry = ProviderRegistry()
    if model is None:
        try:
            model = registry.get_model(provider)
        except Exception:
            model = None

    session = ChatSession(
        workspace=workspace,
        agent=agent,
        provider=provider,
        model=model,
        system_prompt=SYSTEM_PROMPTS.get(agent, SYSTEM_PROMPTS["default"]),
    )
    session.add_system(session.system_prompt)

    _print_banner(session)

    while True:
        try:
            user_input = Prompt.ask("[bold green]you[/]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye.[/]")
            return
        if not user_input.strip():
            continue

        if user_input.startswith("/"):
            if not _handle_slash_command(user_input, session):
                return
            continue

        # Auto-recall relevant past context (unless disabled)
        recall_block = ""
        if not no_recall:
            hits = recall_context(user_input, session.agent, session.workspace, limit=3)
            if hits:
                recall_block = "[System: the following prior context is relevant]\n" + _format_recall(hits) + "\n[End context]\n\n"
                session.recalled_context = hits

        full_user_msg = recall_block + user_input
        session.add_user(full_user_msg)

        # Stream response
        token_buffer: list[str] = []

        def on_token(t: str) -> None:
            token_buffer.append(t)
            console.print(t, end="")

        try:
            console.print("[bold cyan]aiw[/]: ", end="")
            response = chat_sync(
                session.messages,
                provider=session.provider,
                model=session.model,
                stream=(session.provider == "ollama"),
                on_token=on_token,
            )
            console.print()  # newline
        except Exception as e:
            console.print(f"\n[red] Error: {e}[/]")
            # Roll back the failed user message
            if session.messages and session.messages[-1]["role"] == "user":
                session.messages.pop()
            continue

        session.add_assistant(response)

        # Auto-store turn memory (async would be better; for now sync)
        store_turn_memory(session, user_input, response)


__all__ = [
    "ChatSession",
    "SYSTEM_PROMPTS",
    "recall_context",
    "store_turn_memory",
    "run_chat_repl",
]
