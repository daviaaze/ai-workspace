"""
Agent Metrics Panel — live metrics for the focused agent.

Opened with Ctrl+M. Shows a panel with real-time agent statistics:
- Model info (name, provider, session ID)
- Status and runtime
- Iteration count and accumulated context
- Pending messages in the loop queue
- Token budget from ContextManager
- Cost tracking from CostService
- Cache hit stats

Layout:
 Agent Metrics 
                                                                           
   coding-agent                                                         
                              
  Model:      qwen3:14b (ollama)                                          
  Status:      ongoing    Progress: 45%                                   
  Session:    abc123def456                                                 
  CWD:        ~/Projects/ai-workspace                                     
  Runtime:    3:42                                                         
  Iterations: 4                                                            
  Context:    12,340 chars accumulated                                     
  Queue:      2 messages pending                                           
                                                                            
   Cost                                                                  
                              
  Today:      $0.0042                                                      
  This month: $0.0891                                                      
  Cache hits: 3 (saved ~1,200 tokens)                                      
                                                                            
   Token Budget                                                          
                              
  Used:       12,340 / 128,000 (9.6%)                                      
  Blocks:     23 active                                                    
  Pinned:     5                                                            
  Excluded:   2                                                            
                                                                            
  [^M/Esc] close                                                           

"""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Label, Static

from ai_workspace.tui.worker import AgentWorker


class AgentMetrics(Static):
    """Overlay panel showing live metrics for a focused agent.

    Tracks worker state, context budget, and cost in real-time
    while the agent is running. Auto-refreshes every second.
    Dismiss with Escape.
    """

    can_focus = True

    DEFAULT_CSS = """
    AgentMetrics {
        display: none;
        layer: overlay;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
        width: 55;
        height: auto;
        max-height: 80%;
        dock: right;
        offset-x: 2;
        offset-y: 3;
        overflow-y: auto;
    }
    AgentMetrics.visible {
        display: block;
    }
    """

    class Closed(Message):
        """Posted when the metrics panel is dismissed."""

    worker: AgentWorker | None = None
    context_manager = None  # ContextManager
    agent_name: reactive[str] = reactive("")
    agent_model: reactive[str] = reactive("")
    session_id: reactive[str] = reactive("")
    cwd: reactive[str] = reactive(".")
    agent_type: reactive[str] = reactive("general")

    def __init__(
        self,
        worker: AgentWorker | None = None,
        context_manager=None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.worker = worker
        self.context_manager = context_manager
        self._refresh_timer = None

    def show(
        self,
        worker: AgentWorker | None = None,
        agent_name: str = "",
        agent_model: str = "",
        session_id: str = "",
        cwd: str = ".",
        agent_type: str = "general",
        context_manager=None,
    ) -> None:
        """Open the metrics panel with fresh data."""
        self.worker = worker
        self.agent_name = agent_name
        self.agent_model = agent_model
        self.session_id = session_id
        self.cwd = cwd
        self.agent_type = agent_type
        self.context_manager = context_manager

        self.set_class(True, "visible")
        self.refresh()

        # Start auto-refresh
        if self._refresh_timer is None:
            self._refresh_timer = self.set_interval(1.0, self._auto_refresh)

    def hide(self) -> None:
        """Close the metrics panel."""
        self.set_class(False, "visible")
        if self._refresh_timer:
            self._refresh_timer.stop()
            self._refresh_timer = None
        self.post_message(self.Closed())

    def _auto_refresh(self) -> None:
        """Refresh the panel every second while visible."""
        if self.has_class("visible"):
            self.refresh()

    def render(self) -> str:
        """Render the metrics panel content."""
        lines: list[str] = []

        # Header
        lines.append(f"[bold] {self.agent_name}[/]")
        lines.append("" * 45)

        # Worker info
        if self.worker:
            config = self.worker.config
            status = self.worker.status.name
            status_icon = {
                "RUNNING": "[green][/]",
                "PAUSED": "[yellow][/]",
                "IDLE": "[cyan][/]",
                "COMPLETED": "[green][/]",
                "ERROR": "[red][/]",
                "KILLED": "[red][/]",
            }.get(status, "")

            lines.append(f"Model:      [cyan]{config.model}[/] ([dim]{config.provider}[/])")
            lines.append(f"Status:     {status_icon} {status.lower()}")
            lines.append(f"Session:    [dim]{self.session_id[:16] if self.session_id else '—'}[/]")
            lines.append(f"CWD:        [dim]{self._shorten_path(self.cwd)}[/]")
            lines.append(f"Loop mode:  {'[green][/]' if config.loop_mode else '[dim] one-shot[/]'}")
            lines.append(f"Iterations: {getattr(self.worker, '_iteration_count', 0)}")
            ctx_chars = len(getattr(self.worker, '_accumulated_context', ''))
            lines.append(f"Context:    {ctx_chars:,} chars accumulated")
            pending = getattr(self.worker, 'pending_message_count', 0)
            lines.append(f"Queue:      {pending} messages pending")
        else:
            lines.append("[dim]No active worker[/]")
            lines.append(f"Session:    [dim]{self.session_id[:16] if self.session_id else '—'}[/]")
            lines.append(f"CWD:        [dim]{self._shorten_path(self.cwd)}[/]")

        lines.append("")

        # Cost section
        lines.append("[bold] Cost[/]")
        lines.append("" * 45)
        try:
            from ai_workspace.core.cost import CostService
            cost = CostService()
            cache_stats = cost.cache.stats()
            today = cost.logger.today_cost()
            month = cost.logger.month_cost()
            lines.append(f"Today:      [yellow]${today:.4f}[/]")
            lines.append(f"This month: [yellow]${month:.4f}[/]")
            lines.append(f"Cache hits: {cache_stats['total_hits']} "
                         f"(saved ~{cache_stats['tokens_saved']:,} tokens)")
        except Exception:
            lines.append("[dim]Cost service unavailable[/]")

        lines.append("")

        # Token budget section
        lines.append("[bold] Token Budget[/]")
        lines.append("" * 45)
        if self.context_manager:
            cm = self.context_manager
            pct = cm.budget_used_pct
            total = cm.total_tokens
            max_t = cm.context_window_tokens

            # Mini bar
            width = 20
            filled = int((min(pct, 100) / 100) * width)
            bar = "" * filled + "" * (width - filled)
            color = "green" if pct < 40 else ("yellow" if pct < 70 else "red")
            lines.append(f"Used:       [{color}]{bar}[/] {total:,}/{max_t:,} ({pct:.1f}%)")

            blocks = cm.get_active_blocks()
            pinned = sum(1 for b in blocks if b.pinned)
            excluded = sum(1 for b in blocks if b.excluded)
            lines.append(f"Blocks:     {len(blocks)} active, {pinned} pinned, {excluded} excluded")
        else:
            lines.append("[dim]Context manager not available[/]")

        lines.append("")
        lines.append("[dim][^M/Esc] close[/]")

        return "\n".join(lines)

    def _shorten_path(self, path: str, max_len: int = 35) -> str:
        """Shorten a path for display."""
        from pathlib import Path
        p = Path(path).expanduser()
        home = str(Path.home())
        result = str(p)
        if result.startswith(home):
            result = "~" + result[len(home):]
        if len(result) > max_len:
            result = "…" + result[-(max_len - 1):]
        return result


    def key_escape(self) -> None:
        self.hide()
