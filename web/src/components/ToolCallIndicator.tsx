/**
 * Shows a running tool call with status.
 * Used in the agent view to display tool execution in real-time.
 */
export interface ToolCallInfo {
  id: string;
  tool: string;
  args: Record<string, unknown>;
  status: "running" | "done" | "error";
  result?: string;
  error?: string;
}

export function ToolCallIndicator({ call }: { call: ToolCallInfo }) {
  const argsStr = Object.entries(call.args)
    .slice(0, 2)
    .map(([k, v]) => `${k}=${String(v).slice(0, 40)}`)
    .join(", ");

  return (
    <div className="flex items-center gap-2 py-1.5 px-3 rounded-lg bg-white/5 mb-1 animate-fade-in">
      {/* Icon */}
      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
        call.status === "running" ? "bg-yellow-400 animate-pulse" :
        call.status === "done" ? "bg-green-400" :
        "bg-red-400"
      }`} />
      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-accent-400">{call.tool}</span>
          <span className="text-[11px] text-surface-400 truncate">{argsStr}</span>
        </div>
        {call.status === "error" && call.error && (
          <div className="text-[11px] text-red-400 mt-0.5">{call.error.slice(0, 100)}</div>
        )}
      </div>
      {/* Status badge */}
      <span className={`text-[10px] font-medium ${
        call.status === "running" ? "text-yellow-400" :
        call.status === "done" ? "text-green-400" :
        "text-red-400"
      }`}>
        {call.status === "running" ? "..." :
         call.status === "done" ? "OK" : "ERR"}
      </span>
    </div>
  );
}
