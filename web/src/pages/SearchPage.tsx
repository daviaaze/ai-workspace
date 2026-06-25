import { useState, useRef, useEffect } from "react";
import { searchStream } from "../lib/api";

interface SearchResult {
  summary: string;
  detailed_report: string;
  confidence: number;
  sources: string[];
  sub_questions: Array<{
    question: string;
    answer: string;
    confidence: number;
    sources: string[];
  }>;
  original_query: string;
}

interface ProgressEvent {
  phase?: string;
  detail?: string;
  status?: string;
  report?: {
    summary: string;
    confidence: number;
    sources: string[];
    preview: string;
  };
}

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [depth, setDepth] = useState(2);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState<ProgressEvent[]>([]);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const progressEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    progressEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [progress]);

  const handleSearch = async () => {
    const q = query.trim();
    if (!q || isRunning) return;

    setIsRunning(true);
    setResult(null);
    setError(null);
    setProgress([{ phase: "starting", detail: "Initializing research...", status: "running" }]);

    try {
      await searchStream(q, {
        onProgress: (p) => {
          setProgress((prev) => [
            ...prev,
            {
              phase: p.phase as string,
              detail: p.detail as string,
              status: p.status as string,
            },
          ]);
        },
        onResult: (r) => {
          setResult(r as unknown as SearchResult);
          setProgress((prev) => [
            ...prev,
            { phase: "complete", detail: "Research complete!", status: "done" },
          ]);
        },
        onError: (err) => {
          setError(err);
          setProgress((prev) => [
            ...prev,
            { phase: "error", detail: err, status: "error" },
          ]);
        },
        onDone: () => {
          setIsRunning(false);
        },
      }, depth);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
      setIsRunning(false);
    }
  };

  const confidenceColor =
    result && result.confidence >= 0.7
      ? "text-green-400"
      : result && result.confidence >= 0.4
        ? "text-yellow-400"
        : "text-red-400";

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/10">
        <h1 className="text-sm font-semibold">Deep Research</h1>
        <p className="text-[10px] text-surface-400">Recursive analysis with planning & critique</p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {/* Input area */}
        <div className="mb-4">
          <div className="flex items-end gap-2 bg-white/5 rounded-2xl px-3 py-2 mb-2 focus-within:ring-1 focus-within:ring-accent-500/50 transition-all">
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="What do you want to research deeply?"
              rows={2}
              disabled={isRunning}
              className="flex-1 bg-transparent text-[15px] text-white placeholder-surface-500 outline-none resize-none leading-relaxed disabled:opacity-50"
            />
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <label className="text-[11px] text-surface-400">Depth:</label>
              <div className="flex gap-1">
                {[1, 2, 3, 4].map((d) => (
                  <button
                    key={d}
                    onClick={() => setDepth(d)}
                    disabled={isRunning}
                    className={`px-2 py-0.5 text-[11px] rounded-md transition-colors ${
                      depth === d
                        ? "bg-accent-500 text-white"
                        : "bg-white/5 text-surface-300 hover:bg-white/10"
                    } disabled:opacity-50`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>
            <button
              onClick={handleSearch}
              disabled={!query.trim() || isRunning}
              className="px-4 py-1.5 bg-accent-500 disabled:bg-white/10 disabled:text-surface-500 text-white text-sm rounded-full transition-all active:scale-95"
            >
              {isRunning ? "Researching..." : "Research"}
            </button>
          </div>
        </div>

        {/* Progress log */}
        {progress.length > 1 && (
          <div className="mb-4 space-y-1">
            {progress.slice(1).map((p, i) => (
              <div
                key={i}
                className="flex items-center gap-2 py-1 animate-fade-in"
              >
                <span
                  className={`flex-shrink-0 text-[10px] ${
                    p.status === "done"
                      ? "text-green-400"
                      : p.status === "error" || p.status === "error"
                        ? "text-red-400"
                        : p.status === "awaiting_approval"
                          ? "text-yellow-400"
                          : "text-accent-400"
                  }`}
                >
                  {p.status === "done"
                    ? ""
                    : p.status === "error"
                      ? ""
                      : p.status === "awaiting_approval"
                        ? ""
                        : ""}
                </span>
                <span className="text-[12px] text-surface-300">
                  {p.phase && (
                    <span className="text-accent-400 font-medium">{p.phase}: </span>
                  )}
                  {p.detail}
                </span>
              </div>
            ))}
            {isRunning && (
              <div className="flex items-center gap-2 py-1">
                <div className="w-2 h-2 rounded-full bg-accent-400 animate-pulse" />
                <span className="text-[12px] text-accent-400">Processing...</span>
              </div>
            )}
            <div ref={progressEndRef} />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 mb-4">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-4 animate-fade-in">
            {/* Score */}
            <div className="flex items-center gap-2">
              <span className="text-[11px] text-surface-400">Confidence:</span>
              <span className={`text-sm font-semibold ${confidenceColor}`}>
                {(result.confidence * 100).toFixed(0)}%
              </span>
            </div>

            {/* Summary */}
            <div className="bg-white/5 rounded-xl px-4 py-3">
              <h2 className="text-xs font-semibold text-surface-300 mb-1">Summary</h2>
              <p className="text-[14px] leading-relaxed">{result.summary}</p>
            </div>

            {/* Sub-questions */}
            {result.sub_questions.length > 0 && (
              <div>
                <h2 className="text-xs font-semibold text-surface-300 mb-2">
                  Research Breakdown ({result.sub_questions.length} questions)
                </h2>
                <div className="space-y-2">
                  {result.sub_questions.map((sq, i) => (
                    <details key={i} className="bg-white/5 rounded-xl overflow-hidden">
                      <summary className="px-4 py-2.5 text-sm font-medium cursor-pointer hover:bg-white/[0.02] active:bg-white/[0.04]">
                        <span className="text-accent-400 mr-2">Q{i + 1}</span>
                        {sq.question}
                      </summary>
                      <div className="px-4 pb-3">
                        <p className="text-[13px] text-surface-300 leading-relaxed mb-2">
                          {sq.answer}
                        </p>
                        <div className="flex gap-2 text-[11px]">
                          <span className="text-surface-400">
                            Confidence: {(sq.confidence * 100).toFixed(0)}%
                          </span>
                          {sq.sources.length > 0 && (
                            <span className="text-surface-400">
                              · {sq.sources.length} source{sq.sources.length > 1 ? "s" : ""}
                            </span>
                          )}
                        </div>
                      </div>
                    </details>
                  ))}
                </div>
              </div>
            )}

            {/* Full report */}
            {result.detailed_report && (
              <div className="bg-white/5 rounded-xl px-4 py-3">
                <h2 className="text-xs font-semibold text-surface-300 mb-2">Full Report</h2>
                <div className="prose prose-invert text-[13px]">
                  {result.detailed_report.split("\n").map((line, i) => (
                    <p key={i} className="mb-1">
                      {line}
                    </p>
                  ))}
                </div>
              </div>
            )}

            {/* Sources */}
            {result.sources.length > 0 && (
              <div>
                <h2 className="text-xs font-semibold text-surface-300 mb-2">
                  Sources ({result.sources.length})
                </h2>
                <div className="space-y-1">
                  {result.sources.map((src, i) => (
                    <a
                      key={i}
                      href={src}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="block text-[12px] text-accent-400 truncate hover:underline px-3 py-1.5 rounded-lg bg-white/5"
                    >
                      {src}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {!result && progress.length <= 1 && !isRunning && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-16 h-16 rounded-2xl bg-accent-500/10 flex items-center justify-center mb-4">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-accent-400">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.3-4.3" />
                <path d="M11 7v8" />
                <path d="M7 11h8" />
              </svg>
            </div>
            <h3 className="text-sm font-medium text-surface-300 mb-1">Deep Research</h3>
            <p className="text-xs text-surface-500 max-w-[250px]">
              Ask a complex question and I'll recursively research it, breaking it into sub-questions, synthesizing findings, and critiquing the result.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
