import { useState, useRef, useEffect } from "react";
import { ToolCallIndicator, type ToolCallInfo } from "../components/ToolCallIndicator";
import { agentStream } from "../lib/api";

interface AgentLog {
  id: string;
  type: "thinking" | "tool_call" | "tool_result" | "status" | "output" | "error";
  content: string;
  timestamp: number;
}

type AgentMode = "auto" | "research" | "code" | "browse";

export function AgentPage() {
  const [task, setTask] = useState("");
  const [mode, setMode] = useState<AgentMode>("auto");
  const [isRunning, setIsRunning] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [toolCalls, setToolCalls] = useState<ToolCallInfo[]>([]);
  const [finalOutput, setFinalOutput] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, toolCalls]);

  const handleRun = async () => {
    const t = task.trim();
    if (!t || isRunning) return;

    setIsRunning(true);
    setLogs([]);
    setToolCalls([]);
    setFinalOutput(null);
    setError(null);

    try {
      await agentStream(t, {
        onThinking: (thought) => {
          setLogs((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              type: "thinking",
              content: thought,
              timestamp: Date.now(),
            },
          ]);
        },
        onToolCall: (tool, args) => {
          const call: ToolCallInfo = {
            id: crypto.randomUUID(),
            tool,
            args,
            status: "running",
          };
          setToolCalls((prev) => [...prev, call]);
          setLogs((prev) => [
            ...prev,
            {
              id: call.id,
              type: "tool_call",
              content: `${tool}(${JSON.stringify(args).slice(0, 100)})`,
              timestamp: Date.now(),
            },
          ]);
        },
        onToolResult: (tool, result) => {
          setToolCalls((prev) =>
            prev.map((c) =>
              c.tool === tool && c.status === "running"
                ? { ...c, status: "done", result: result.slice(0, 500) }
                : c
            )
          );
          setLogs((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              type: "tool_result",
              content: `${tool} → ${result.slice(0, 200)}`,
              timestamp: Date.now(),
            },
          ]);
        },
        onStatus: (status, metadata) => {
          setLogs((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              type: "status",
              content: status + (metadata ? ` ${JSON.stringify(metadata)}` : ""),
              timestamp: Date.now(),
            },
          ]);
        },
        onToken: (token) => {
          // Accumulate tokens into final output
          setFinalOutput((prev) => (prev || "") + token);
        },
        onDone: () => {
          setIsRunning(false);
          setLogs((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              type: "status",
              content: "Agent complete",
              timestamp: Date.now(),
            },
          ]);
        },
        onError: (err) => {
          setError(err);
          setIsRunning(false);
          setLogs((prev) => [
            ...prev,
            {
              id: crypto.randomUUID(),
              type: "error",
              content: err,
              timestamp: Date.now(),
            },
          ]);
        },
      }, mode, sessionId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Agent run failed");
      setIsRunning(false);
    }
  };

  const modes: { value: AgentMode; label: string; desc: string }[] = [
    { value: "auto", label: "Auto", desc: "Auto-detect task type" },
    { value: "research", label: "Research", desc: "Web research & analysis" },
    { value: "code", label: "Code", desc: "Write, test, debug code" },
    { value: "browse", label: "Browse", desc: "Browser automation" },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10">
        <h1 className="text-sm font-semibold">Agent Sandbox</h1>
        <p className="text-[10px] text-surface-400">Autonomous agent with sandboxed tools</p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {/* Input */}
        <div className="mb-3">
          <div className="flex items-end gap-2 bg-white/5 rounded-2xl px-3 py-2 mb-2 focus-within:ring-1 focus-within:ring-accent-500/50 transition-all">
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="What should the agent do?"
              rows={2}
              disabled={isRunning}
              className="flex-1 bg-transparent text-[15px] text-white placeholder-surface-500 outline-none resize-none leading-relaxed disabled:opacity-50"
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="flex gap-1 flex-wrap">
              {modes.map((m) => (
                <button
                  key={m.value}
                  onClick={() => setMode(m.value)}
                  disabled={isRunning}
                  className={`px-2.5 py-1 text-[10px] rounded-full transition-colors ${
                    mode === m.value
                      ? "bg-accent-500 text-white"
                      : "bg-white/5 text-surface-300 hover:bg-white/10"
                  } disabled:opacity-50`}
                  title={m.desc}
                >
                  {m.label}
                </button>
              ))}
            </div>
            <button
              onClick={handleRun}
              disabled={!task.trim() || isRunning}
              className="px-4 py-1.5 bg-accent-500 disabled:bg-white/10 disabled:text-surface-500 text-white text-sm rounded-full transition-all active:scale-95"
            >
              {isRunning ? "Running..." : "Run Agent"}
            </button>
          </div>
        </div>

        {/* Running tool calls */}
        {toolCalls.length > 0 && (
          <div className="mb-3">
            <h2 className="text-[10px] font-semibold text-surface-400 mb-1 uppercase tracking-wider">
              Tool Execution
            </h2>
            {toolCalls.map((call) => (
              <ToolCallIndicator key={call.id} call={call} />
            ))}
          </div>
        )}

        {/* Logs */}
        {logs.length > 0 && (
          <div className="mb-3 space-y-0.5">
            <h2 className="text-[10px] font-semibold text-surface-400 mb-1 uppercase tracking-wider">
              Agent Log
            </h2>
            {logs.map((log) => (
              <div key={log.id} className="flex items-start gap-2 py-1 animate-fade-in">
                <span className="flex-shrink-0 mt-0.5">
                  {log.type === "thinking" && (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-yellow-400">
                      <circle cx="12" cy="12" r="10" />
                      <path d="M12 16v-4M12 8h.01" />
                    </svg>
                  )}
                  {log.type === "tool_call" && (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-accent-400">
                      <polyline points="16 3 21 3 21 8" />
                      <line x1="4" y1="20" x2="21" y2="3" />
                      <polyline points="21 16 21 21 16 21" />
                      <line x1="15" y1="15" x2="21" y2="21" />
                      <line x1="4" y1="4" x2="9" y2="9" />
                    </svg>
                  )}
                  {log.type === "tool_result" && (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-green-400">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  )}
                  {log.type === "error" && (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-red-400">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="15" y1="9" x2="9" y2="15" />
                      <line x1="9" y1="9" x2="15" y2="15" />
                    </svg>
                  )}
                  {log.type === "status" && (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-surface-400">
                      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                    </svg>
                  )}
                </span>
                <span className="text-[12px] text-surface-300 leading-relaxed">
                  {log.content}
                </span>
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        )}

        {/* Running indicator */}
        {isRunning && logs.length === 0 && (
          <div className="flex items-center gap-2 py-4">
            <div className="w-2 h-2 rounded-full bg-accent-400 animate-pulse" />
            <span className="text-sm text-accent-400">Initializing agent...</span>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 mb-4">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* Final output */}
        {finalOutput && (
          <div className="bg-white/5 rounded-xl px-4 py-3 mb-4 animate-fade-in">
            <h2 className="text-xs font-semibold text-surface-300 mb-2">Final Output</h2>
            <pre className="text-[13px] text-surface-200 whitespace-pre-wrap font-mono leading-relaxed">
              {finalOutput}
            </pre>
          </div>
        )}

        {/* Tools info */}
        {!isRunning && logs.length === 0 && !finalOutput && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-16 h-16 rounded-2xl bg-accent-500/10 flex items-center justify-center mb-4">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent-400">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                <line x1="8" y1="21" x2="16" y2="21" />
                <line x1="12" y1="17" x2="12" y2="21" />
              </svg>
            </div>
            <h3 className="text-sm font-medium text-surface-300 mb-1">Available Tools</h3>
            <div className="flex flex-wrap gap-1.5 justify-center max-w-[280px] mb-3">
              {["Shell (sandboxed)", "Git", "Filesystem", "Web Fetch", "Browser Agent", "Code Tools", "Web Search", "Mercado Livre", "OLX"].map(
                (tool) => (
                  <span
                    key={tool}
                    className="px-2 py-0.5 bg-white/5 rounded-full text-[10px] text-surface-400"
                  >
                    {tool}
                  </span>
                )
              )}
            </div>
            <p className="text-xs text-surface-500 max-w-[280px]">
              The agent operates in a sandbox with allowlisted commands. Dangerous operations require permission.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
