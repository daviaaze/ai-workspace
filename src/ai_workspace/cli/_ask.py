"""CLI commands — `aiw ask`."""

from __future__ import annotations

import typer
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from ai_workspace.cli._app import app, console
from ai_workspace.providers import chat_sync
from ai_workspace.core.db import get_store
from ai_workspace.knowledge import KnowledgeStore

@app.command()
def ask(
    message: str = typer.Argument(..., help="Question or prompt"),
    provider: str = typer.Option("ollama", "--provider", "-p", help="LLM provider"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model name"),
    system: str | None = typer.Option(None, "--system", "-s", help="System prompt"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming output"),
):
    """Quick chat with any configured model."""
    from ai_workspace.providers import ProviderRegistry, chat_sync
    from ai_workspace.core.cost import CostService
    
    registry = ProviderRegistry()
    cost = CostService()
    cost.initialize()

    if model is None:
        model = registry.get_model(provider)

    console.print(f"[dim]Provider: {provider} | Model: {model}[/]")

    # Check semantic cache first
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": message})

    # Build cache key from the actual prompt
    cache_prompt = message
    if system:
        cache_prompt = f"[SYS]{system}[/SYS] {message}"

    cached = cost.cache.get(cache_prompt, "chat")
    if cached:
        console.print(f"[dim] Cache hit (similarity: {cached['similarity']:.0%})[/]")
        console.print()
        console.print(Panel(Markdown(cached["response_text"]), title=" Response (cached)"))
        cost.budget.record_success(
            provider=provider, model=model or "unknown",
            task_type="chat", cache_hit=True,
        )
        return

    # Budget check before calling LLM
    if provider in ("deepseek", "openrouter"):
        est_cost = 0.00014 * (len(message) // 4 + 500) / 1000  # ~0.0001 per short chat
        allowed, reason = cost.budget.can_call(est_cost, provider)
        if not allowed:
            console.print(f"[red] Budget blocked: {reason}[/]")
            console.print(f"[dim]Daily: ${cost.budget.today_spent():.4f}/${cost.budget.DAILY_BUDGET:.2f}[/]")
            raise typer.Exit(1)

    console.print()

    if no_stream or provider != "ollama":
        # Non-streaming path
        with console.status(f"[cyan]Thinking ({model})...", spinner="dots"):
            try:
                response = chat_sync(messages, provider=provider, model=model)
            except Exception as e:
                console.print(f"[red] Error: {e}[/]")
                cost.budget.record_failure(
                    provider=provider, model=model or "unknown",
                    task_type="chat", error=str(e)[:200],
                )
                raise typer.Exit(1)
        console.print(Panel(Markdown(response), title=" Response"))
        # Store in cache for future use
        cost.cache.set(cache_prompt, response, "chat", model or "unknown",
                       tokens_used=len(message)//4 + len(response)//4,
                       cost=0.0 if provider == "ollama" else 0.0001)
        # Log cost
        cost.budget.record_success(
            provider=provider, model=model or "unknown",
            task_type="chat",
            input_tokens=len(message)//4,
            output_tokens=len(response)//4,
            cost=0.0 if provider == "ollama" else 0.0001,
            cache_hit=False,
        )
    else:
        # Streaming path for Ollama (shows tokens as they arrive)
        token_buffer = []
        
        def print_token(token: str):
            token_buffer.append(token)
            # Print in real-time but try not to break mid-word
            console.print(token, end="")
        
        console.print("[bold cyan] Response[/]:")
        
        try:
            response = chat_sync(messages, provider=provider, model=model, stream=True, on_token=print_token)
        except Exception as e:
            console.print(f"\n[red] Error: {e}[/]")
            cost.budget.record_failure(
                provider=provider, model=model or "unknown",
                task_type="chat", error=str(e)[:200],
            )
            raise typer.Exit(1)
        
        console.print()  # Final newline after stream ends
        console.print(Panel("", title=" Response complete", border_style="dim"))
        # Store in cache
        cost.cache.set(cache_prompt, response, "chat", model or "unknown",
                       tokens_used=len(message)//4 + len(response)//4,
                       cost=0.0)  # Ollama = free
        # Log cost for streaming
        cost.budget.record_success(
            provider=provider, model=model or "unknown",
            task_type="chat",
            input_tokens=len(message)//4,
            output_tokens=len(response)//4,
            cost=0.0, cache_hit=False,
        )


# Models command



@app.command()
def chat(
    workspace: str = typer.Option("personal", "--workspace", "-w", help="Workspace context (personal, work, etc.)"),
    agent: str = typer.Option("default", "--persona", "-p", help="Persona: default, coder, researcher, planner"),
    provider: str = typer.Option("ollama", "--provider", help="LLM provider: ollama, deepseek, nvidia, openrouter"),
    model: str | None = typer.Option(None, "--model", "-m", help="Model name (uses provider default if not set)"),
    no_recall: bool = typer.Option(False, "--no-recall", help="Disable auto-recall of past context"),
):
    """Start an interactive chat session with persistent memory.

    The chat REPL maintains conversation history, auto-recalls relevant
    past context from the knowledge base, and stores key turns as agent
    memories for future recall.

    Slash commands available in the REPL:
        /workspace, /persona, /model, /provider, /recall, /clear,
        /save, /status, /help, /exit
    """
    from ai_workspace.chat import run_chat_repl

    run_chat_repl(
        workspace=workspace,
        agent=agent,
        provider=provider,
        model=model,
        no_recall=no_recall,
    )


# MCP commands (extracted to cli._mcp)