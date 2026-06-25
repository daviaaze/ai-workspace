/**
 * API client for the AI Workspace backend.
 * Handles SSE streaming, WebSocket connections, and REST calls.
 */

const API_BASE = "/api";
const WS_BASE = `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;

export interface SSECallbacks {
  onToken?: (token: string) => void;
  onThinking?: (thought: string) => void;
  onToolCall?: (tool: string, args: Record<string, unknown>) => void;
  onToolResult?: (tool: string, result: string) => void;
  onStatus?: (status: string, metadata?: Record<string, unknown>) => void;
  onProgress?: (progress: Record<string, unknown>) => void;
  onResult?: (result: Record<string, unknown>) => void;
  onDone?: (metadata?: Record<string, unknown>) => void;
  onError?: (error: string) => void;
}

/**
 * Read an SSE stream from a fetch Response, dispatching events to callbacks.
 */
async function readSSEStream(
  response: Response,
  callbacks: SSECallbacks
): Promise<void> {
  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";
  let currentEvent = "";
  let currentData = "";

  const flush = () => {
    if (!currentData) return;
    try {
      const payload = JSON.parse(currentData);
      switch (currentEvent) {
        case "token":
          callbacks.onToken?.(payload.token);
          break;
        case "thinking":
          callbacks.onThinking?.(payload.thought);
          break;
        case "tool_call":
          callbacks.onToolCall?.(payload.tool, payload.args);
          break;
        case "tool_result":
          callbacks.onToolResult?.(payload.tool, payload.result);
          break;
        case "status":
          callbacks.onStatus?.(payload.status, payload.metadata);
          break;
        case "progress":
          callbacks.onProgress?.(payload);
          break;
        case "result":
          callbacks.onResult?.(payload);
          break;
        case "done":
          callbacks.onDone?.(payload);
          break;
        case "error":
          callbacks.onError?.(payload.error);
          break;
      }
    } catch (e) {
      console.error("SSE parse error:", e, currentData);
    }
    currentEvent = "";
    currentData = "";
  };

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          flush();
          currentEvent = line.slice(7).trim();
        } else if (line.startsWith("data: ")) {
          currentData = line.slice(6).trim();
        } else if (line === "") {
          flush();
        }
      }
    }
    // Flush remaining
    flush();
  } finally {
    reader.releaseLock();
  }
}

/** Chat with streaming response */
export function chatStream(
  message: string,
  callbacks: SSECallbacks,
  sessionId?: string,
  provider?: string,
  model?: string
): Promise<void> {
  return fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, session_id: sessionId, provider, model }),
  }).then((res) => readSSEStream(res, callbacks));
}

/** Deep research with streaming progress */
export function searchStream(
  query: string,
  callbacks: SSECallbacks,
  depth = 2,
  maxSubQuestions = 5
): Promise<void> {
  return fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, depth, max_sub_questions: maxSubQuestions }),
  }).then((res) => readSSEStream(res, callbacks));
}

/** Run agent task with streaming */
export function agentStream(
  task: string,
  callbacks: SSECallbacks,
  mode = "auto",
  sessionId?: string
): Promise<void> {
  return fetch(`${API_BASE}/agent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task, mode, session_id: sessionId }),
  }).then((res) => readSSEStream(res, callbacks));
}

/** Health check */
export async function healthCheck(): Promise<{
  status: string;
  version: string;
  providers: Record<string, boolean>;
}> {
  const res = await fetch("/health");
  return res.json();
}

/** Connect to permission WebSocket */
export function connectPermissionSocket(
  onRequest: (req: {
    requestId: string;
    agentName: string;
    toolName: string;
    description: string;
    preview: string;
  }) => void
): {
  send: (data: Record<string, unknown>) => void;
  close: () => void;
} {
  const ws = new WebSocket(`${WS_BASE}/ws/permissions`);

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.type === "permission_request") {
        onRequest(data);
      }
    } catch (e) {
      console.error("WS parse error:", e);
    }
  };

  ws.onerror = () => console.error("Permission WS error");
  ws.onclose = () => console.log("Permission WS closed");

  return {
    send: (data) => ws.send(JSON.stringify(data)),
    close: () => ws.close(),
  };
}
