# AI Workspace v2 — Comprehensive AI Workspace Architecture
*Omnichannel, browser-based AI agents with orchestration, calendar, workspaces, and knowledge*

## Vision: "Everything workspace from anywhere"
A single self-hostable platform that provides:
- **Omnichannel AI**: TUI, web dashboard, messaging bots (Telegram/Slack/WhatsApp), voice
- **Browser agents**: Research, form filling, data extraction via Playwright
- **Intelligent coding**: Write, debug, open PRs
- **Unified knowledge**: Research + code + tasks + calendar, all searchable (pgvector)
- **Agent swarms**: Supervisor-worker delegation with isolated workspaces
- **Multi-workspace**: Personal vs work separation with per-workspace MCP servers

---

## Core Principles
1. **Self-hostable**: Run on homelab or laptop — single binary, `FROM scratch` Docker image
2. **Extensible**: MCP-first integration, two-tier (Supervisor + Worker) architecture
3. **Persistent**: Long-term memory, session resumption, knowledge graph across sessions
4. **Multi-agent**: Orchestrate specialized agents with supervisor delegation
5. **Context-aware**: Understands calendar, tasks, system state, user preferences
6. **Human-in-the-loop**: Permission gating, real-time presence, mission-control collaboration
7. **TUI-first**: The terminal is the primary workstation. Web is secondary (mobile, quick checks).
8. **Information-dense**: See everything at once — tasks, agent outputs, thinking, session state.

---

## Stack Choices
| Area | Technology | Why |
|------|-----------|-----|
| Language | Go + Python | Go for infra/server, Python for LLM/agents |
| Agent Framework | Karna (inspired) | Multi-channel, actor-based |
| Browser Agent | browser-use + Playwright | MCP-powered autonomous browser |
| Memory | PostgreSQL + pgvector | Structured + semantic/vector search |
| Orchestration | NATS | Agent swarm event bus + mesh node discovery + cross-node RPC |
| Real-time UI | SSE (in-memory) + NATS (mesh) | Lightweight per-workspace event stream; NATS bridges cross-node agent streams |
| Frontend | Vue 3 + Pinia + Tailwind | PWA, secondary/mobile interface |
| TUI | Textual (Python) | **Primary interface** — agent operations center, multi-lane split view |
| Object Store | MinIO / S3-compatible | Shared file attachments across mesh nodes |
| MCP Tools | mcp.directory + apigene.ai | Discovery and marketplace |
| Node Discovery | NATS gossip + mDNS | Automatic mesh formation, zero-config on LAN |
| Auth | Google OAuth2 + JWT | OAuth2 for supervisor, token-based for workers |
| Mesh Security | NATS TLS + node tokens | Encrypted inter-node communication, mutual auth |
| Cache L1 | In-memory LRU (per-node) | Embedding cache, context assembly cache, MCP tool results |
| Cache L2 | Redis / Valkey (shared mesh) | Semantic response cache, session state, rate limits, retrieval cache |
| Container | Multi-stage `FROM scratch` | Single static binary, zero dependencies, <30MB |
| Config | YAML layering (base + env) | `base.yaml` → `development.yaml` / `production.yaml` merge |

---

## Architecture

### System Topology (Single Node)
```
┌─────────────────────────────────────────────────────────────────┐
│                        HTTP Server (Go/Fiber)                    │
│                         unified port :3000                       │
└────┬──────────────┬──────────────┬──────────────┬───────────────┘
     │              │              │              │
┌────▼─────┐  ┌─────▼──────┐  ┌───▼───────┐  ┌──▼──────────────┐
│ REST API │  │ Supervisor │  │ Per-WS    │  │  SSE Events     │
│ /api/v1  │  │ MCP Server │  │ MCP Srvrs │  │  /workspaces/   │
│          │  │ (coremcp)  │  │ /mcp/{id} │  │  {id}/events    │
└────┬─────┘  └─────┬──────┘  └───┬───────┘  └──▲──────────────┘
     │              │              │              │
     └──────────────┴──────────────┘              │
                    │                             │
          ┌─────────▼─────────┐        ┌─────────┴──────────┐
          │  CRUD Controller  │        │   EventBus (SSE)    │
          │  tasks, ws, msgs  │        │   in-memory pub/sub │
          └─────────┬─────────┘        └─────────▲──────────┘
                    │                             │
          ┌─────────▼─────────┐        ┌─────────┴──────────┐
          │  Repository (GORM)│        │  Central Forwarder  │
          │  SQLite / Postgres│        │  (PubSub → EventBus)│
          └─────────┬─────────┘        └─────────▲──────────┘
                    │                             │
          ┌─────────▼─────────────────────────────┴──────────┐
          │              PubSub (internal)                    │
          │         CRUD lifecycle + MCP telemetry            │
          └──────────────────────┬───────────────────────────┘
                                 │
          ┌──────────────────────▼───────────────────────────┐
          │            NATS (agent swarm + mesh bus)          │
          │      Agent coordination, node discovery, RPC      │
          └──────────────────────────────────────────────────┘
```

---

## Data Flows

### Flow 1: Task Creation → Agent Execution → Completion

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FLOW: Human creates task → Agent picks up → Agent executes → Complete       │
│                                                                              │
│  HUMAN (TUI/Web)                                                             │
│  │  POST /api/v1/workspaces/{id}/tasks                                       │
│  │  { title, body, assignee:"agent", cron_schedule? }                        │
│  ▼                                                                            │
│  REST API Handler                                                            │
│  │  Validate input, extract JWT user_id, rate-limit check                    │
│  ▼                                                                            │
│  CRUD Controller                                                             │
│  │  Generate monoflake ID, set status="notstarted" (or "cron")              │
│  │  If cron: validate granularity (minute must be single integer)            │
│  ▼                                                                            │
│  Repository (GORM)                                                           │
│  │  INSERT INTO tasks (...), INSERT INTO messages (system note)              │
│  ▼                                                                            │
│  PubSub (internal)                                                           │
│  │  Publish: PubSubTopicCRUD → { ActionTaskCreate, ActorHuman, OriginREST }  │
│  │  Consumed by:                                                             │
│  │    • Central Forwarder → EventBus → SSE → TUI/Web UI update               │
│  │    • Slack/Telegram controller → post task to messaging channel           │
│  │    • Telemetry service → record task.created event                        │
│  ▼                                                                            │
│  MCP Workspace Server (per-workspace)                                         │
│  │  Poller (every 60s): detects new notstarted agent-assigned tasks          │
│  │  If no ongoing tasks → pushes to agent via notifications/claude/channel    │
│  │  Agent can also call getNextTask() actively                               │
│  ▼                                                                            │
│  AGENT (Claude/Gemini/Codex via MCP)                                         │
│  │  1. updateTaskStatus(taskId, "ongoing")                                   │
│  │     → MCP handler → CRUD Controller → DB UPDATE → PubSub → SSE            │
│  │  2. [work happens — tool calls, file reads, shell exec]                   │
│  │  3. reply(chatId, "progress update...")                                   │
│  │     → MCP handler → CRUD → DB INSERT message → PubSub → SSE → TUI lane    │
│  │  4. reply(chatId, "final result...")                                      │
│  │  5. updateTaskStatus(taskId, "completed")                                 │
│  ▼                                                                            │
│  HUMAN (TUI)                                                                 │
│  │  Sees: agent lane shows live reply() output in real time                  │
│  │  Task panel: status dot changes green, progress bar hits 100%             │
│  │  Toast: "Task 'Fix auth' completed"                                       │
│                                                                              │
│  Key: ──▶ sync request    - - -▶ async event    ═══▶ stream                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Flow 2: Context Assembly (What the Agent Sees)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FLOW: How agent context is built before each task                           │
│                                                                              │
│  Trigger: Agent calls getNextTask() or Poller pushes a task                  │
│                                                                              │
│  1. CHECK CACHE                                                              │
│     L1 Context Assembly Cache                                               │
│     │  Key: hash(workspace_id + task_id + context_template_version)          │
│     │  HIT → return assembled context (latency <1ms)                         │
│     │  MISS → continue assembly                                              │
│                                                                              │
│  2. LOAD STATIC CONTEXT                                                      │
│     Repository.GetWorkspace(workspaceID)                                    │
│     │  → workspace.Name, workspace.Description                               │
│     │  → workspace.SelfLearningLoopNote (agent behavior guidelines)          │
│     │  → workspace.AutoAllowedTools (pre-approved tool patterns)             │
│     Repository.GetTask(taskID)                                              │
│     │  → task.Title, task.Body, task.AllowAllCommands flag                   │
│     │  → task.Messages (last 5 for conversation continuity)                  │
│                                                                              │
│  3. VECTOR SEARCH (pgvector)                                                 │
│     Query embedding = embed(task.Title + " " + task.Body)                   │
│     │  CHECK L1 Embedding Cache → SHA256(text)                               │
│     │  HIT → use cached embedding                                            │
│     │  MISS → call embedding model → cache → proceed                         │
│     │                                                                        │
│     SELECT * FROM knowledge_nodes                                           │
│     WHERE workspace_id = $1                                                  │
│     ORDER BY embedding <=> $query_embedding                                  │
│     LIMIT $top_k                                                             │
│     │  CHECK L2 Retrieval Cache: hash(query + top_k + threshold)             │
│     │  HIT → use cached results                                              │
│     │  MISS → execute query → cache results → return                         │
│     │                                                                        │
│     Results: [                                                               │
│       { type: "note", title: "JWT Expiry Handling", similarity: 0.89 },     │
│       { type: "doc",  title: "Auth Middleware Architecture", sim: 0.82 },   │
│       { type: "code", title: "middleware.go", similarity: 0.75 }            │
│     ]                                                                        │
│                                                                              │
│  4. ASSEMBLE CONTEXT                                                         │
│     Template render: system_prompt + workspace_notes + task + knowledge      │
│     │  → count tokens (warning if > 80% of model limit)                     │
│     │  → store in L1 Context Assembly Cache (invalidate on any source change) │
│     │  → return to MCP server                                               │
│                                                                              │
│  5. DELIVER TO AGENT                                                         │
│     MCP server injects context as:                                           │
│     • Server Instructions (system prompt + rules)                            │
│     • notifications/claude/channel (task description + knowledge)            │
│     • getWorkspace() tool response (stats + mission)                         │
│     • getTaskMessages() tool response (recent conversation)                  │
│                                                                              │
│  Cache invalidation triggers:                                                │
│    • Task body/title edited → clear context cache for task_id                │
│    • Workspace notes edited → clear all context caches for workspace_id      │
│    • New knowledge node added with high relevance to active tasks            │
│    • Context template version changed                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Flow 3: Permission Gating (Human-in-the-Loop)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FLOW: Agent needs permission → Human approves/denies → Agent continues      │
│                                                                              │
│  AGENT (Claude Code via MCP)                                                 │
│  │  Agent tries: Bash("git push origin main")                                │
│  │  Claude Code sends: notifications/claude/channel/permission_request       │
│  │  { request_id, task_id?, tool_name, description, input_preview }          │
│  ▼                                                                            │
│  MCP Workspace Server (notification middleware)                              │
│  │  1. Store request in memory: permissionRequests[request_id] = sessionID   │
│  │  2. Resolve taskID (3-stage fallback):                                    │
│  │     a. From payload.task_id                                               │
│  │     b. From sessionTasks[sessionID] mapping                               │
│  │     c. From DB: query workspace's current ongoing/blocked task            │
│  │                                                                           │
│  │  3. CHECK AUTO-ALLOW (3 tiers):                                           │
│  │     Tier 1: tool in workspace.AutoAllowedTools?                           │
│  │       → checkAutoAllow(toolName, inputPreview)                            │
│  │       → pattern match: "Bash:git *" matches "Bash:git push origin main"  │
│  │       → YES: auto-approve, publish permission_auto_allow telemetry        │
│  │       → Agent continues without interruption                              │
│  │     Tier 2: task.AllowAllCommands == true? (YOLO mode)                    │
│  │       → YES: auto-approve                                                 │
│  │     Tier 3: requires human approval                                       │
│  │       → CONTINUE to step 4                                                │
│  │                                                                           │
│  │  4. CREATE PERMISSION REQUEST MESSAGE                                     │
│  │     reply(chatId, "Permission requested: Bash", attachments?, metadata)   │
│  │     metadata: { type:"permission_request", request_id, tool_name,         │
│  │                 description, input_preview, status:"pending" }             │
│  │     → CRUD Controller → DB INSERT message → PubSub MessageCreate          │
│  ▼                                                                            │
│  EVENT DISTRIBUTION                                                           │
│  │  PubSub → Central Forwarder → EventBus → SSE                              │
│  │  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  │ TUI:     permission modal overlay appears in agent lane           │    │
│  │  │          [a] Allow Once  [A] Always Allow  [d] Deny               │    │
│  │  │                                                                   │    │
│  │  │ Web:     inline permission card in task detail view               │    │
│  │  │          [Allow Once]  [Always Allow]  [Deny]                     │    │
│  │  │                                                                   │    │
│  │  │ Slack:   interactive buttons in thread                            │    │
│  │  │          [Allow] [Deny]                                            │    │
│  │  └──────────────────────────────────────────────────────────────────┘    │
│  ▼                                                                            │
│  HUMAN RESPONDS (any channel)                                                 │
│  │  TUI: presses 'a'                                                          │
│  │  → POST /api/v1/workspaces/{id}/tasks/{tid}/permission                     │
│  │    { requestId, behavior: "allow" }                                        │
│  │  or Web: clicks "Always Allow"                                             │
│  │    { requestId, behavior: "allow_always" }                                 │
│  │  or Slack: clicks "Deny" → Slack controller → CRUD                         │
│  ▼                                                                            │
│  CRUD Controller                                                              │
│  │  → MCP Manager.SendPermissionVerdict(workspaceID, requestID, behavior)     │
│  ▼                                                                            │
│  MCP Workspace Server                                                         │
│  │  1. If behavior == "allow_always":                                         │
│  │     buildAutoAllowRule(toolName, params) → "Bash:git *"                    │
│  │     append to workspace.AutoAllowedTools                                   │
│  │     persist to DB                                                          │
│  │  2. Find session by requestID: permissionRequests[requestID]               │
│  │  3. Send verdict to agent:                                                 │
│  │     sess.Notify("notifications/claude/channel/permission",                 │
│  │                 { request_id, behavior })                                   │
│  │  4. Update message metadata: status → "allow" | "deny"                    │
│  │  5. Cleanup in-memory maps: delete permissionRequests[requestID]           │
│  │  6. Publish telemetry: permission_manual_allow | permission_manual_deny    │
│  ▼                                                                            │
│  EVENT DISTRIBUTION                                                           │
│  │  PubSub MessageUpdate → Central Forwarder → EventBus → SSE                │
│  │  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  │ TUI:     permission modal dismissed, agent lane resumes            │    │
│  │  │ Web:     card collapses to "✅ Allowed" summary                    │    │
│  │  │ Slack:   buttons replaced with "✅ Allowed by @user"              │    │
│  │  └──────────────────────────────────────────────────────────────────┘    │
│  ▼                                                                            │
│  AGENT                                                                        │
│  │  Receives verdict → executes or skips the tool                            │
│  │  If denied: agent notified, can try alternative approach                  │
│  │  Origin tracking: Slack controller sets OriginSlack to prevent echo       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Flow 4: Knowledge Graph Ingestion

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FLOW: Agent output → parse → embed → store → link → cache                   │
│                                                                              │
│  TRIGGERS                                                                    │
│  │  • Agent completes task → markdown output                                 │
│  │  • Human writes note (TUI/Web/Obsidian sync)                              │
│  │  • Agent research report generated                                        │
│  │  • Code file indexed                                                      │
│  │  • Decision record created                                                │
│  ▼                                                                            │
│  1. PARSE & CHUNK                                                            │
│     Content → split into semantic chunks (by headers, paragraphs)            │
│     │  chunk_size: ~500 tokens, overlap: 50 tokens                           │
│     │  extract metadata: title, tags (from frontmatter), links, code blocks  │
│  ▼                                                                            │
│  2. DEDUPLICATE                                                              │
│     CHECK L1 Embedding Cache: SHA256(chunk.text)                             │
│     │  EXISTS → skip (duplicate content)                                      │
│     │  NEW → continue                                                         │
│  ▼                                                                            │
│  3. EMBED                                                                     │
│     CHECK L1 Embedding Cache → SHA256(chunk.text)                            │
│     │  HIT → use cached vector                                                │
│     │  MISS → call embedding model (local or API) → cache → proceed           │
│  ▼                                                                            │
│  4. STORE (PostgreSQL + pgvector)                                            │
│     INSERT INTO knowledge_nodes (id, workspace_id, type, title,               │
│       content, embedding, tags, created_by, source_task_id, metadata)         │
│     │  Returns: node_id                                                       │
│  ▼                                                                            │
│  5. LINK (auto-detect edges)                                                  │
│     For each existing node in same workspace:                                 │
│     │  • If source_task_id matches → edge: "produced_by"                      │
│     │  • If mentions other task IDs → edge: "references"                      │
│     │  • If same tag → edge: "relates_to" (weak, threshold-based)             │
│     │  • If implements a decision → edge: "implements" (from frontmatter)     │
│     │  INSERT INTO knowledge_edges (from_id, to_id, type, confidence)         │
│  ▼                                                                            │
│  6. CACHE INVALIDATION                                                        │
│     Publish NATS: aiw.cache.invalidate { type: "knowledge_node_added",        │
│       node_id, workspace_id, embedding (for similarity check) }               │
│     │  Each node: checks if new node would rank in top_k for any active       │
│     │  task's context query → if yes, clear that task's context cache         │
│     │  L2 Retrieval Cache: mark entries for this workspace as stale           │
│  ▼                                                                            │
│  7. OBSIDIAN SYNC (if configured)                                             │
│     Write markdown file to vault path:                                        │
│     ~/vault/aiw/{workspace}/{type}/{slug}.md                                  │
│     Frontmatter: type, tags, source_task_id, aiw_node_id, created_at          │
│     │  Bidirectional: changes in Obsidian → file watcher → re-index node      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Flow 5: Mesh Node Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FLOW: Node joins mesh → registers → gets work → heartbeats → leaves         │
│                                                                              │
│  NODE STARTUP                                                                │
│  │  aiw serve --join nats://homelab.local:4222                               │
│  ▼                                                                            │
│  1. NATS CONNECTION                                                          │
│     Connect to NATS cluster (TLS + node token auth)                          │
│     │  Subscribe: aiw.cache.invalidate (for cache sync)                      │
│     │  Subscribe: aiw.rpc.placement.* (respond to placement queries)          │
│  ▼                                                                            │
│  2. CAPABILITY REGISTRATION                                                  │
│     Publish: aiw.nodes.{node_id}.capabilities (retained message)              │
│     {                                                                         │
│       node: { id, hostname, ip, status: "online" },                           │
│       resources: { cpu, memory, gpu, disk },                                  │
│       capabilities: ["llm-inference", "docker", "browser"],                  │
│       mcp_tools: ["browser-use", "kubectl"],                                 │
│       workspaces: ["coding", "devops"],                                      │
│       labels: { env, zone, tier }                                             │
│     }                                                                         │
│  ▼                                                                            │
│  3. HEARTBEAT LOOP (every 5s)                                                │
│     Publish: aiw.nodes.{node_id}.heartbeat                                    │
│     { node_id, timestamp, load: { cpu, memory, gpu_vram }, agent_count }      │
│     │  Other nodes monitor for timeout (15s no heartbeat → node offline)      │
│  ▼                                                                            │
│  4. AGENT PLACEMENT REQUEST                                                  │
│     Human spawns agent → NATS request: aiw.rpc.placement.request              │
│     {                                                                         │
│       task_id, workspace_id, agent_type,                                      │
│       required_capabilities: ["gpu-compute"],                                 │
│       preferred_labels: { zone: "homelab" },                                  │
│       exclude_nodes: []                                                       │
│     }                                                                         │
│     │                                                                         │
│     Each eligible node responds: aiw.rpc.placement.response                   │
│     { node_id, available: true, score: 0.85, resources: {...} }               │
│     │                                                                         │
│     Scheduler selects highest-scoring node:                                   │
│       score = (capability_match * 0.4) + (resource_available * 0.3)          │
│             + (label_match * 0.2) + (latency_score * 0.1)                     │
│     │                                                                         │
│     Winner gets: aiw.rpc.agent.spawn { task_id, context }                     │
│     │  → Node creates agent MCP session → agent lane appears in TUI           │
│     │  → TUI shows: agent_name @ node_id                                      │
│  ▼                                                                            │
│  5. CROSS-NODE MCP TOOL CALL                                                  │
│     Agent on Node A calls tool only available on Node C:                      │
│     │  MCP server: check local capabilities → NOT FOUND                       │
│     │  NATS request: aiw.rpc.mcp.resolve.tool.{tool_name}                     │
│     │  Node C responds: { node_id, available: true, latency_ms: 12 }          │
│     │                                                                         │
│     NATS request: aiw.rpc.mcp.call                                            │
│     { tool_name, params, caller_node, caller_agent, task_id }                 │
│     │  Node C executes tool locally → returns result                           │
│     │  Node A → returns result to agent as if local                           │
│     │  Agent never knows tool was remote                                      │
│  ▼                                                                            │
│  6. NODE FAILURE DETECTION                                                    │
│     Node B heartbeat timeout (15s no message):                                │
│     │  NATS: node B connection closed → Last Will message published           │
│     │  All nodes: mark Node B as "offline"                                    │
│     │  For each agent running on Node B:                                      │
│     │    • Mark task status → "notstarted" (re-queue)                        │
│     │    • Publish event → TUI shows ⚠️ in agent lane                        │
│     │    • If auto-retry enabled: re-run placement for that task              │
│     │  TUI status bar: "agents:3⚡ → 2⚡ 1⚠️"                                 │
│  ▼                                                                            │
│  7. NODE GRACEFUL SHUTDOWN                                                    │
│     aiw serve --stop  or  SIGTERM:                                            │
│     │  Publish: aiw.nodes.{node_id}.status = "draining"                       │
│     │  Complete in-flight agent tasks (wait up to 30s)                        │
│     │  Re-queue pending tasks to other nodes                                  │
│     │  Publish: aiw.nodes.{node_id}.status = "offline"                        │
│     │  Disconnect NATS                                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Flow 6: Cache Lifecycle (Write-Through + Invalidation)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FLOW: Data written → L1 populated → L2 populated → invalidation broadcast   │
│                                                                              │
│  WRITE PATH (e.g., task created/updated)                                     │
│  │                                                                           │
│  1. CRUD Controller writes to PostgreSQL (source of truth)                   │
│  2. WRITE-THROUGH to L2:                                                     │
│     • Context assembly: not written (assembled on read)                      │
│     • Embedding: SET emb:sha256 → vector (no expiry)                         │
│     • Session state: SET session:user_id → {...} EX 3600                     │
│     • Rate limit: INCR rate:user_id:tool_name, EXPIRE window                 │
│  3. INVALIDATE L1:                                                           │
│     • Task updated → delete context assembly cache for task_id               │
│     • Workspace edited → delete all context caches for workspace_id          │
│     • New knowledge node → re-check active task contexts                     │
│  4. PUBLISH INVALIDATION (NATS):                                             │
│     aiw.cache.invalidate { type, entity_id, workspace_id, scope }            │
│     • All mesh nodes receive → clear matching L1 entries                     │
│     • L2 marks entries as stale (lazy re-validation on next access)          │
│                                                                              │
│  READ PATH (e.g., context assembly for agent)                                │
│  │                                                                           │
│  1. CHECK L1 (in-memory, <1ms):                                              │
│     key = hash(task_id + workspace_id + template_version)                    │
│     HIT → return immediately, record cache_hit telemetry                     │
│     MISS → continue                                                          │
│  2. CHECK L2 (Redis, <5ms):                                                  │
│     For semantic queries: FT.SEARCH idx:semantic_cache                       │
│       @embedding:[VECTOR_RANGE 0.05 $query_vector]                           │
│     For retrieval: GET retrieval:hash(query + top_k + threshold)             │
│     HIT → populate L1 → return, record cache_hit                             │
│     MISS → continue                                                          │
│  3. COMPUTE (PostgreSQL + LLM, 50-200ms):                                    │
│     Execute vector search, assemble context, render template                  │
│  4. POPULATE CACHES:                                                         │
│     L1: store assembled context (TTL: 5min, extended on access)              │
│     L2: store retrieval results (TTL: 5min)                                  │
│     L2: store semantic response (TTL: task type dependent)                   │
│  5. RETURN result to caller, record cache_miss telemetry                     │
│                                                                              │
│  EVICTION (automatic)                                                        │
│  │  L1: LRU eviction when max_entries reached                                │
│  │  L2: Redis maxmemory-policy: allkeys-lru                                  │
│  │  L3: never evicted (persistent, manual cleanup only)                      │
│                                                                              │
│  ANALYTICS (flushed every 60s to PostgreSQL)                                 │
│  │  cache_events: { timestamp, tier, type, key, hit, latency_us }            │
│  │  Aggregated for dashboard: hit rate by type, cost savings, top queries    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Flow 7: Supervisor Delegation (Multi-Agent Workflow)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FLOW: Human creates high-level task → Supervisor breaks down → Workers run  │
│                                                                              │
│  HUMAN                                                                       │
│  │  Creates task in supervisor workspace:                                    │
│  │  "Write, document, and publish auth module"                               │
│  ▼                                                                            │
│  SUPERVISOR AGENT (connected to coremcp, OAuth2, cross-workspace)            │
│  │  1. getTask(supervisor_ws, task_id) → reads the high-level goal           │
│  │  2. updateTaskStatus(supervisor_ws, task_id, "ongoing")                   │
│  │  3. listWorkspaces() → discovers: coding_ws, docs_ws, publish_ws          │
│  │     Response includes each workspace's mcpURL for worker connection        │
│  │  4. For each sub-task:                                                     │
│  │     createTask(coding_ws, "Implement auth module in Go",                  │
│  │                body="...", assignee="agent")                               │
│  │     createTask(docs_ws, "Write auth module documentation", ...)           │
│  │     createTask(publish_ws, "Publish release v2.1.0", ...)                 │
│  │  5. POLL: listTasks(coding_ws, status="completed")                        │
│  │     → waits for all subtasks to complete                                  │
│  │  6. replyToTask(supervisor_ws, task_id, "All subtasks complete...")       │
│  │  7. updateTaskStatus(supervisor_ws, task_id, "completed")                 │
│  ▼                                                                            │
│  WORKER AGENTS (each connected to their workspace MCP, isolated)              │
│  │  Worker A (coding_ws):  getNextTask() → "Implement auth module"            │
│  │  Worker B (docs_ws):    getNextTask() → "Write auth module documentation" │
│  │  Worker C (publish_ws): getNextTask() → "Publish release v2.1.0"          │
│  │                                                                           │
│  │  Each worker: ongoing → reply(progress) → reply(result) → completed        │
│  │  Each status change → PubSub → SSE → TUI lanes update                     │
│  ▼                                                                            │
│  TUI                                                                          │
│  │  Shows 4 agent lanes:                                                     │
│  │    supervisor @ node-a:  "Monitoring 3 subtasks... 2/3 complete"          │
│  │    coding @ node-b:      "✅ Implement auth module — done"                │
│  │    docs @ node-c:        "Writing documentation... 60%"                   │
│  │    publish @ node-a:     "Creating release... 30%"                        │
│  │                                                                           │
│  │  Task panel shows parent/child hierarchy:                                 │
│  │    ● Write, document, publish auth [supervisor]                           │
│  │      ✅ Implement auth module [coding]                                    │
│  │      ● Write documentation [docs]                                         │
│  │      ○ Publish release [publish]                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Flow 8: Real-Time Event Propagation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  FLOW: Any state change → PubSub → Central Forwarder → EventBus → SSE → UI   │
│                                                                              │
│  EVENT SOURCES                                                               │
│  │  REST API    → Task CRUD, workspace CRUD, reply, permission               │
│  │  MCP Server  → Agent tool calls (createTask, updateTaskStatus, reply)     │
│  │  Scheduler   → Cron task spawn                                            │
│  │  Slack Ctrl  → Inbound messages, button clicks                            │
│  │  Mesh        → Node join/leave, cross-node agent events                   │
│  ▼                                                                            │
│  PubSub (internal, in-process)                                               │
│  │  Topics:                                                                  │
│  │  • PubSubTopicCRUD  → entity lifecycle (create/update/delete)             │
│  │  • PubSubTopicMCP   → tool call telemetry                                 │
│  │                                                                           │
│  │  Event format: { action, workspace_id, user_id, resource_type,            │
│  │                   resource_id, actor, origin, timestamp }                  │
│  │                                                                           │
│  │  Consumers:                                                               │
│  │  ┌──────────────────────────────────────────────────────────────────┐    │
│  │  │ Central Forwarder ← translates PubSub → EventBus (next step)      │    │
│  │  │ Slack Controller   ← OnTaskCreated, OnMessageCreated, etc.        │    │
│  │  │ Telegram Ctrl      ← same pattern, different platform              │    │
│  │  │ Push Service       ← web push notifications (PWA)                 │    │
│  │  │ Email Service      ← email notifications (if configured)           │    │
│  │  │ Telemetry Service  ← batch-write analytics to DB (every 5s)       │    │
│  │  └──────────────────────────────────────────────────────────────────┘    │
│  ▼                                                                            │
│  Central Forwarder                                                            │
│  │  Translates PubSub CRUD events → workspace-scoped SSE events:             │
│  │                                                                           │
│  │  PubSub: ActionTaskCreate, ResourceTask, OriginMCP                         │
│  │    → EventBus: { type: "task.created",                                    │
│  │                  payload: mapper.FromModelTaskToView(task) }               │
│  │                                                                           │
│  │  PubSub: ActionTaskStatusUpdate → EventBus: { type: "status.updated" }    │
│  │  PubSub: ActionMessageCreate   → EventBus: { type: "message.created" }    │
│  │  PubSub: ActionWorkspaceUpdate → EventBus: { type: "workspace.updated" }  │
│  ▼                                                                            │
│  EventBus (SSE, in-memory channels per workspace + user)                      │
│  │  Publish(workspaceID, userID, event) → sends to all subscribers           │
│  │  Non-blocking: slow consumers are dropped (no back-pressure)               │
│  │  Subscribers:                                                              │
│  │    • TUI: SSE client → updates lanes, task panel, status bar              │
│  │    • Web: EventSource → updates Vue reactive state                        │
│  │    • Agent: MCP notification (for cross-agent communication)               │
│  ▼                                                                            │
│  UI UPDATES                                                                   │
│  │  TUI:                                                                      │
│  │    task.created     → add to task panel, push to agent lane                │
│  │    task.updated     → update status dot, progress bar, move between groups │
│  │    status.updated   → show toast notification                              │
│  │    message.created  → append to agent lane output stream                   │
│  │    agent.connected  → update presence indicator (green/red dot)            │
│  │    workspace.updated → update status bar, cached metadata                  │
│  │    permission.*     → show/dismiss permission modal                        │
│  │                                                                           │
│  │  Web (Vue):                                                                │
│  │    Same events → update Pinia stores → reactive component re-renders      │
│  │    SSE reconnection with 3s backoff on error                               │
│  │    401 → redirect to /login                                                │
│  │                                                                           │
│  │  Origin tracking prevents loops:                                           │
│  │    If event.origin == OriginSlack → Slack controller skips (don't echo)    │
│  │    If event.origin == OriginMCP  → Agent doesn't re-receive own events     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Interaction Matrix

```
┌──────────────────┬────┬─────┬──────┬──────┬──────┬──────┬──────┬──────┬──────┐
│ From ↓ / To →    │REST│ CRUD│ Repo │ PubSub│Event│ MCP  │ NATS │Redis │  PG  │
│                  │ API│ Ctrl│      │      │ Bus │Server│      │      │      │
├──────────────────┼────┼─────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│ REST API         │ -  │sync │  -   │  -   │  -   │  -   │  -   │  -   │  -   │
│ CRUD Controller  │ ←  │  -  │sync  │async │  -   │callbk│  -   │  -   │  -   │
│ Repository       │ -  │ ←   │  -   │  -   │  -   │  -   │  -   │  -   │sync  │
│ PubSub           │ -  │ ←   │  -   │  -   │via FW│  -   │  -   │  -   │  -   │
│ EventBus         │ -  │  -  │  -   │  ←   │  -   │pub   │  -   │  -   │  -   │
│ MCP Server       │ -  │via F│  -   │emit  │pub   │  -   │  -   │  -   │  -   │
│ NATS             │ -  │  -  │  -   │  -   │  -   │  -   │  -   │  -   │  -   │
│ Redis/Valkey     │ -  │  -  │  -   │  -   │  -   │r/w   │  -   │  -   │  -   │
│ PostgreSQL       │ -  │  -  │  ←   │  -   │  -   │  -   │  -   │  -   │  -   │
│ TUI (SSE client) │POST│  -  │  -   │  -   │sub   │  -   │  -   │  -   │  -   │
│ Web (fetch+SSE)  │fetch│  -  │  -   │  -   │sub   │  -   │  -   │  -   │  -   │
│ Agent (MCP)      │  -  │  -  │  -   │  -   │  -   │stream│  -   │  -   │  -   │
│ Slack Controller │  -  │sync │sync  │sub   │  -   │call  │  -   │  -   │  -   │
│ Scheduler        │  -  │  -  │sync  │emit  │pub   │  -   │  -   │  -   │  -   │
│ Telemetry        │  -  │  -  │  -   │sub   │  -   │  -   │  -   │  -   │batch │
│ Cleanup Service  │  -  │  -  │  -   │  -   │  -   │  -   │  -   │  -   │read  │
└──────────────────┴────┴─────┴──────┴──────┴──────┴──────┴──────┴──────┴──────┘

Legend: sync=synchronous call, async=fire-and-forget, stream=persistent connection
        pub=publish events, sub=subscribe to events, call=remote procedure call
        callback=function callback, via FW=via Central Forwarder, r/w=read/write
        batch=batched writes, POST/fetch=HTTP request
```

---

### Two-Tier MCP Architecture (Supervisor + Worker)

The most critical architectural decision: split MCP into two tiers with different auth scopes.

```
Supervisor MCP (coremcp) — OAuth2, user-scoped, cross-workspace
├── listWorkspaces(includeArchived?)
├── createWorkspace(name, description, ...)
├── getWorkspace(id) → returns mcpURL for worker connection
├── listTasks(workspaceId, filter, status, limit)
├── listAllTasks(filter, status, limit) → cross-workspace visibility
├── createTask(workspaceId, title, body, assignee, cronSchedule)
├── getTask(workspaceId, taskId)
├── replyToTask(workspaceId, taskId, text)
├── respondToTask(workspaceId, taskId, action) → allow/deny permissions
├── updateTaskStatus(workspaceId, taskId, status)
├── updateTaskAssignee(workspaceId, taskId, assignee)
├── updateTaskAllowAll(workspaceId, taskId, allowAll)
├── updateScheduledTask(workspaceId, taskId, ...)
└── getAttachment(workspaceId, attachmentId)

Worker MCP (per workspace) — token-authenticated, single-workspace
├── getWorkspace() → name, description, task stats
├── getNextTask() → dequeues next notstarted agent-assigned task
├── getTaskMessages(taskId, cursor?, limit?) → paginated chat history
├── createTask(title, body, assignee?, cronSchedule?)
├── updateTaskStatus(taskId, status)
├── reply(chatId, text, attachments?)
└── downloadAttachment(attachmentId, taskId)
```

**Security boundaries:**
- Supervisor ↔ Core MCP: OAuth2 JWT (audience `"coremcp"`, user-scoped)
- Worker ↔ Per-Workspace MCP: Encrypted workspace token (AES-GCM at rest)
- Workers CANNOT see other workspaces — no cross-workspace tool calls possible
- Workspace tokens encrypted with server-side key, never stored in plaintext

### Lazy Workspace MCP Server Manager
Per-workspace MCP servers are created **on first agent connection**, not at startup:
```go
func (m *Manager) Get(workspaceID int64, userID string) *WorkspaceServer {
    m.mu.RLock()
    if srv, ok := m.servers[workspaceID]; ok { return srv }
    m.mu.RUnlock()
    m.mu.Lock()
    defer m.mu.Unlock()
    if srv, ok := m.servers[workspaceID]; ok { return srv } // double-check
    srv = m.newFn(workspaceID, userID)
    m.servers[workspaceID] = srv
    return srv
}
```
This scales to hundreds of workspaces with zero overhead for inactive ones.

### Dual Event System
| Layer | Purpose | Implementation |
|-------|---------|---------------|
| **EventBus** (SSE) | Real-time UI updates, per-workspace/per-user | In-memory pub/sub, buffered channels, non-blocking sends |
| **PubSub** (Internal) | System concerns: CRUD lifecycle, MCP telemetry | Async, topic-based, consumed by notification/push controllers |
| **NATS** | Agent swarm coordination, handoff, discovery | External message broker for cross-agent communication |

A **Central Forwarder** subscribes to PubSub and translates entity events into workspace-scoped SSE events on the EventBus.

---

## Agent-Human Collaboration Model

### Philosophy: Human as Mission Controller
The human is a **mission controller** overseeing multiple AI agents working in parallel — not a chat partner. Like an air traffic controller or a DevOps engineer watching dashboards, the human sees all agents' live output simultaneously, intervenes when needed, and maintains situational awareness across the entire swarm.

**Key shift from chat-centric design:**
- Chat implies one conversation at a time. Mission control means watching 2-5 agents work in parallel.
- Chat hides information behind scroll. Mission control shows everything in lanes, always visible.
- Chat buries thinking. Mission control lets you toggle reasoning visibility per agent or globally.
- Chat is reactive (you wait for a message). Mission control is ambient (you glance and know the state).

### Task Lifecycle
```
notstarted → ongoing → completed
                ↓
             blocked → ongoing
                ↓
             rejected

cron → spawns child → notstarted → ...
```

### Agent Task Execution Loop
```
Agent connects via MCP
  → getNextTask()          ← dequeues first notstarted task
  → updateTaskStatus(ongoing)
  → [work happens]
  → reply(chatId, "...")   ← intermediate progress updates
  → reply(chatId, result)  ← final output
  → updateTaskStatus(completed)
```

### MCP Server Instructions (Agent SOPs)
Every workspace MCP server injects behavioral instructions:
```
You are connected to AI Workspace "{name}".

HOW THIS WORKS:
- Messages from the human arrive as channel notifications
- You reply using the `reply` tool
- The human is REMOTE and can ONLY see what you send via `reply`

RULES (follow strictly):
1. START: Immediately call updateTaskStatus to 'ongoing'
2. SHARE EVERYTHING: Proactively share what you're doing, file paths,
   commands and their output, decisions, and trade-offs
3. PROGRESS UPDATES: Send a reply every few steps — don't go silent
4. ASK VIA REPLY: Use reply to ask for permission, clarification, or info
5. COMPLETE: Send a summary of all changes via reply, then mark completed
   Use 'blocked' if stuck and need human help
```

---

## Human Interface

### Interface Tiers

| Tier | Interface | Use Case | Information Density |
|------|-----------|----------|---------------------|
| **Primary** | TUI (Textual/Python) | Daily workstation. Multi-agent monitoring, task management, intervention. | Maximum — all agents, tasks, and system state visible at once. |
| **Secondary** | Web Dashboard (Vue 3) | Mobile check-ins, quick replies, permission approvals on the go. | Medium — single task focus, simplified layout. |
| **Tertiary** | Messaging Bots (Telegram/Slack/WhatsApp) | Notifications, one-line replies, permission buttons. | Minimal — single action at a time. |

### Design Philosophy: Agent Operations Center

The TUI is not a chat app. It's an **agent operations center** — like `htop` meets `tmux` meets a trading terminal. The human watches multiple agents work in parallel across split lanes, with task state, session context, and agent thinking all visible simultaneously.

```
┌─ aiw ── ws:personal ── claude-3.7 ── tasks:3/12 ── agents:2⚡ ── 14:32 ───────────┐
│                                                                                     │
│  ┌─ Tasks ──────────────────────────────────────────────────────────────────────┐  │
│  │ ● Fix auth bug         [coding]    ████████░░ 80%   Running tests...          │  │
│  │ ○ Add integration tests [coding]   ══════════   0%   waiting                  │  │
│  │ ● Research MCP tools   [research]  ████░░░░░░ 40%   Filtering results...      │  │
│  │ ✅ Init repo            [coding]    ██████████ 100%  done                     │  │
│  │ 🕐 Daily backup         [sys]       scheduled 02:00                           │  │
│  │ 🕐 Weekly report        [docs]      scheduled Mon 09:00                       │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│  ┌─ coding (claude-3.7) ───────────────────────────┬─ research (gemini-2.5) ──────┐│
│  │ ▸ Fix auth bug                     [ongoing] 80%│ ▸ Research MCP tools [ongoing]││
│  │                                                │                    40%        ││
│  │  > Reading src/auth/middleware.go              │  > Querying mcp.directory     ││
│  │    Found the nil-check issue at line 42.       │    for "browser scraping"     ││
│  │    The JWT extraction doesn't handle           │    tools. Found 23 results.   ││
│  │    expired tokens correctly.                   │                               ││
│  │                                                │  > Filtering by capability    ││
│  │  > Fixing: wrapping extractJWT() with          │    Keeping 8 servers with     ││
│  │    a token expiry check before the             │    Playwright/Puppeteer       ││
│  │    claims parsing block.                       │    support. Cross-referencing ││
│  │                                                │    with apigene.ai ratings.   ││
│  │  > Running: go test ./internal/auth/...        │                               ││
│  │    ✅ TestExtractJWT_ExpiredToken PASS         │  > Writing report...          ││
│  │    ✅ TestExtractJWT_ValidToken PASS           │    ## Top MCP Scraping Tools  ││
│  │    ✅ TestMiddleware_NoAuthHeader PASS         │    1. browser-use-mcp (4.8★)  ││
│  │    12/12 tests passing                         │    2. playwright-mcp (4.6★)  ││
│  │                                                │    3. scrapegraph-mcp (4.5★) ││
│  │  ── thinking ────────────────────────────      │                               ││
│  │  I should also check if the refresh token      │  ── thinking ──────────────   ││
│  │  logic has the same issue. The middleware      │  I should prioritize tools    ││
│  │  calls extractJWT which doesn't distinguish    │  with MCP-native support      ││
│  │  between access and refresh tokens. This       │  over REST APIs, since our    ││
│  │  could be a security concern if refresh        │  agents connect via MCP.      ││
│  │  tokens are leaked to the Auth header.         │  browser-use-mcp wins here.   ││
│  └────────────────────────────────────────────────┴──────────────────────────────┘│
│                                                                                     │
│  ┌─ 🔒 Permission Required ─────────────────────────────────────────────────────┐  │
│  │ Agent: coding │ Task: Fix auth bug                                           │  │
│  │ Tool: Bash    │ git push origin fix/auth-middleware-expiry                    │  │
│  │                                                                              │  │
│  │ [a] Allow Once    [A] Always Allow    [d] Deny    [Esc] dismiss             │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                     │
│  > _                                                        [^T] think [^P] perm   │
│  [Tab] agents  [^K] tasks  [^W] workspace  [^S] spawn  [^D] detail  [^Q] quit     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### TUI Layout System

The TUI is composed of **resizable, toggleable panels**:

| Panel | Position | Default Size | Toggle | Content |
|-------|----------|-------------|--------|---------|
| **Status Bar** | Top (full width, 1 row) | Fixed | Always visible | Workspace name, model, task counts, agent statuses, clock |
| **Task Panel** | Left | 25% width | `Ctrl+K` | Task tree grouped by status with progress bars |
| **Agent Lanes** | Center/right | Fills remaining space | Always visible | Split panes showing each agent's live output |
| **Thinking Overlay** | Below each agent lane | 0-40% of lane height | `Ctrl+T` | Agent reasoning in dimmed text, per-agent or global toggle |
| **Permission Modal** | Overlay (centered) | Auto-sized | Appears on demand | Tool name, command, keybinding options |
| **Command Bar** | Bottom (full width, 1 row) | Fixed | Always visible | Input line + keybinding hints |
| **Detail View** | Full screen | Full terminal | `Ctrl+D` on task/agent | Expanded view of selected task or agent |

### Agent Lanes (Multi-Agent Split View)

This is the core innovation of the TUI. Each agent gets its own **lane** — a vertically scrollable panel showing its live output stream.

**Auto-arrangement:**
- 1 agent → full width
- 2 agents → side-by-side (50/50)
- 3 agents → 3 columns (33/33/33)
- 4+ agents → 2×2 grid, scrolls to reveal more

**Lane anatomy:**
```
┌─ agent_name (model) ──────────────────────────────┐
│ ▸ current_task_title                   [status] XX%│  ← header (always visible)
│                                                     │
│  > Live output stream...                           │  ← main output (scrolls)
│    Agent messages appear here as they're emitted.   │
│    Each reply() call appends a new block.           │
│    Tool calls show as: > Running: command           │
│    Results show as:   ✅ / ❌ / 📊 output           │
│                                                     │
│  ── thinking ──────────────────────────────────     │  ← dimmed, collapsible
│  Agent's reasoning stream. Shown in darker/dimmer   │
│  text. Toggle with Ctrl+T per agent or globally.     │
│  Auto-collapses when task completes.                 │
└─────────────────────────────────────────────────────┘
```

**Lane interactions (when lane is focused):**
| Key | Action |
|-----|--------|
| `↑`/`↓` | Scroll agent output |
| `Ctrl+T` | Toggle thinking for THIS agent |
| `Ctrl+D` | Expand agent to full-screen detail |
| `Enter` | Focus the command bar with agent pre-selected |
| `p` | Pause/unpause agent (hold task execution) |
| `x` | Kill agent / disconnect |

**Visual states per lane:**
- **Working** (ongoing task): Green header, animated spinner or progress bar
- **Idle** (no task, connected): Dim header, "waiting for task..."
- **Blocked** (task blocked): Yellow header, "🛑 Blocked: reason"
- **Thinking** (currently reasoning): Purple dot in header
- **Permission pending**: Orange header with 🔒 icon, output paused
- **Offline**: Gray header, "disconnected"
- **Completed**: Green checkmark, output frozen (scrollable history)

### Task Panel

Always-visible tree of tasks with at-a-glance status:

```
┌─ Tasks ─────────────────────────────┐
│ FILTER: [a]ll [o]ngoing [n]otstarted│
│         [b]locked  [c]ompleted      │
│                                      │
│ ● Fix auth bug        [coding]  80% │
│ ○ Add tests           [coding]   0% │
│ ● Research MCP        [research] 40%│
│ ✅ Init repo           [coding]   ✓ │
│ 🛑 Deploy staging      [devops]   ⏸ │
│ 🕐 Daily backup        [sys]   2:00 │
│                                      │
│ [+ New Task] [^N]                    │
└──────────────────────────────────────┘
```

**Task indicators:**
- `●` ongoing (green)
- `○` not started (gray)
- `✅` completed (green)
- `🛑` blocked (red/yellow)
- `🕐` scheduled/cron (cyan)
- Progress bar: `████░░░░ 40%` from agent's reported progress

**Selecting a task:**
- Highlights the task in the panel
- Jumps the relevant agent lane into view (scrolls if needed)
- The agent lane header pulses briefly to show the connection
- If the task has no agent assigned, shows the task detail in a modal

### Thinking Visibility

Agent reasoning is a **separate stream** from agent output. The system distinguishes:

| Stream | Source | Default Visibility | Visual Style |
|--------|--------|-------------------|-------------|
| **Output** | `reply()` MCP calls | Always visible | Normal text, agent lane body |
| **Thinking** | Agent's internal reasoning | Hidden by default | Dimmed/smaller text, italic if terminal supports |
| **Tool calls** | MCP tool invocations | Always visible | `> Running: command` prefix |

**Toggle modes:**
- `Ctrl+T` once → show thinking for the focused agent only
- `Ctrl+T` twice → show thinking for ALL agents
- `Ctrl+T` again → hide all thinking

**Thinking panel** (alternative): A global bottom panel that shows thinking from ALL agents in a single scrollable view, with agent name prefixes. Toggle with `Ctrl+Shift+T`.

### Permission Gating in the TUI

When an agent requests permission for a sensitive action, the lane **pauses** and a modal overlay appears:

```
┌─ 🔒 Permission Required ─────────────────────────────────────────┐
│ Agent: coding          │ Task: Fix auth bug                       │
│ Tool: Bash             │ git push origin fix/auth-middleware      │
│                                                                   │
│ ┌─ Input Preview ──────────────────────────────────────────────┐ │
│ │ { "command": "git push origin fix/auth-middleware-expiry",   │ │
│ │   "description": "Push the auth middleware fix to remote" }   │ │
│ └───────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ [a] Allow Once    [A] Always Allow    [d] Deny                   │
└───────────────────────────────────────────────────────────────────┘
```

**Keybinding-driven permission flow:**
- Modal appears → agent lane pauses (orange header, 🔒 icon, output stops scrolling)
- `a` → allow once, modal dismissed, lane resumes
- `A` → always allow (persists rule to workspace), modal dismissed
- `d` → deny, modal dismissed, agent notified, lane resumes
- `Esc` → defer decision, modal minimized to a notification in the status bar

**Auto-allowed tools** flash briefly in the lane (`⚡ auto-allowed: Bash:git status`) then continue — no interruption.

### Session & Workspace Context

The Status Bar provides persistent situational awareness:

```
┌─ aiw ── ws:personal ── claude-3.7 ── tasks:3/12 ── agents:2⚡ ── 1🔒 ── 14:32 ─┐
```

| Segment | Meaning |
|---------|--------|
| `aiw` | Application name |
| `ws:personal` | Current workspace (`Ctrl+W` to switch) |
| `claude-3.7` | Default model (per-workspace override shown per agent) |
| `tasks:3/12` | Active tasks / total tasks |
| `agents:2⚡` | Connected agents (⚡ = all online, 🟡 = some offline, ○ = all offline) |
| `1🔒` | Pending permission requests count (blinks if any are waiting) |
| `14:32` | Current time |

### Command Bar & Global Keybindings

```
> _                                                        [^T] think [^P] perm   │
[Tab] agents  [^K] tasks  [^W] workspace  [^S] spawn  [^D] detail  [^Q] quit     │
```

**Global keybindings (available from anywhere):**

| Key | Action |
|-----|--------|
| `Tab` | Cycle focus between panels (tasks → agent lanes → command bar) |
| `Ctrl+K` | Toggle task panel visibility |
| `Ctrl+W` | Switch workspace (opens fuzzy-find dropdown) |
| `Ctrl+S` | Spawn new agent (opens dialog: type, model, task, workspace) |
| `Ctrl+T` | Toggle thinking visibility (once=focused agent, twice=all, again=hide) |
| `Ctrl+Shift+T` | Toggle global thinking panel (bottom dock) |
| `Ctrl+D` | Expand focused item to detail/fullscreen |
| `Ctrl+P` | View pending permissions (jump to next unresolved) |
| `Ctrl+N` | Create new task (opens form in modal) |
| `Ctrl+F` | Fuzzy-find: tasks, agents, workspaces, commands |
| `Ctrl+Z` | Toggle YOLO mode for current task |
| `Ctrl+R` | Reorder focused task (opens up/down arrows) |
| `Ctrl+L` | Cycle layout (2-col, 3-col, grid, stacked) |
| `Esc` | Close modal / return to previous focus |
| `:` | Enter command mode (vim-style command palette) |
| `Ctrl+Q` | Quit |

### Command Palette (`:`)

Vim-style command mode for power users:
```
:task "Fix login timeout" --workspace work --agent coding
:spawn research --model gemini-2.5 --task "Research MCP tools"
:workspace personal
:thinking on
:yolo task-abc123 on
:layout grid
:quit
```

### Web Dashboard (Secondary Interface)

The web dashboard is a **simplified, mobile-friendly view** for when you're away from the terminal:

**Features retained from TUI:**
- Task list with status indicators and progress bars
- Single-task detail view with chat-like message history
- Permission request cards with Allow/Deny buttons
- Agent presence indicators (green/red dot)
- Workspace switching
- PWA with update banner, dark/light theme

**Features intentionally omitted (TUI-only):**
- Multi-agent lane split view (too complex for mobile)
- Thinking visibility toggle (not critical on the go)
- Command palette (keybindings don't translate to touch)
- Agent spawning dialog (do that from the TUI)

**Web-specific advantages:**
- Rich attachment previews (images, PDFs, videos in browser)
- Copy-paste setup configs for connecting agents
- OAuth flows for Slack/Google integration
- Drag-and-drop file uploads
- Toast notifications for background events

### Messaging Bots (Tertiary Interface)

Notifications and quick actions via Telegram/Slack/WhatsApp:
- Task created → message with title + status
- Agent requests permission → interactive Allow/Deny buttons
- Agent completes task → summary message
- Reply to bot message → forwarded as task reply
- Slash commands → create tasks, check status

---

## Distributed Mesh Architecture

### Philosophy: Your Compute, Anywhere

A single aiw cluster spans multiple physical machines — homelab servers, laptops, cloud VMs — connected via NATS mesh. Agents run where the resources are, tasks route to the best node, and the human sees a unified view regardless of where the work happens.

### Mesh Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AIW MESH                                           │
│                                                                              │
│  ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐         │
│  │    NODE A         │   │    NODE B         │   │    NODE C         │        │
│  │    homelab         │   │    laptop          │   │    cloud VM        │       │
│  │                    │   │                    │   │                    │       │
│  │  GPU: RTX 4090    │   │  GPU: Apple M2    │   │  GPU: T4 (AWS)    │       │
│  │  RAM: 64GB         │   │  RAM: 32GB         │   │  RAM: 16GB         │       │
│  │  DISK: 2TB NVMe   │   │  DISK: 512GB       │   │  DISK: 100GB       │       │
│  │                    │   │                    │   │                    │       │
│  │  Agents:           │   │  Agents:           │   │  Agents:           │       │
│  │  • coding (GPU)   │   │  • research        │   │  • browser (Chrome)│       │
│  │  • inference       │   │  • docs            │   │  • scraper         │       │
│  │  • training        │   │  • TUI session     │   │  • webhook handler │       │
│  │                    │   │                    │   │                    │       │
│  │  MCP tools:        │   │  MCP tools:        │   │  MCP tools:        │       │
│  │  • local GPU       │   │  • local files     │   │  • playwright      │       │
│  │  • docker          │   │  • git repos       │   │  • selenium        │       │
│  │  • kubernetes      │   │                    │   │  • public APIs     │       │
│  └────────┬───────────┘   └────────┬───────────┘   └────────┬───────────┘   │
│           │                        │                        │                │
│           └────────────────────────┼────────────────────────┘                │
│                                    │                                         │
│                         ┌──────────▼──────────┐                              │
│                         │    NATS Cluster      │                             │
│                         │                      │                             │
│                         │  • Node discovery    │                             │
│                         │  • Agent RPC         │                             │
│                         │  • Capability registry│                            │
│                         │  • Health pings      │                             │
│                         │  • Work distribution │                             │
│                         └──────────┬──────────┘                              │
│                                    │                                         │
│                         ┌──────────▼──────────┐                              │
│                         │   PostgreSQL (HA)    │                             │
│                         │   + pgvector         │                             │
│                         │                      │                             │
│                         │  Shared: tasks,      │                             │
│                         │  workspaces,         │                             │
│                         │  knowledge graph,    │                             │
│                         │  agent state         │                             │
│                         └─────────────────────┘                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Node Types & Capabilities

Each node advertises its capabilities to the mesh via NATS:

```yaml
# Node self-registration (published on NATS subject: aiw.nodes.<node_id>.capabilities)
node:
  id: "node-homelab-01"
  hostname: "homelab.local"
  ip: "192.168.1.100"
  status: "online"
resources:
  cpu:
    cores: 16
    available: 12
  memory:
    total_gb: 64
    available_gb: 48
  gpu:
    - name: "NVIDIA RTX 4090"
      vram_gb: 24
      available: true
  disk:
    total_gb: 2048
    available_gb: 1500
capabilities:
  - "llm-inference"      # can run local LLMs
  - "gpu-compute"        # has CUDA/ROCm
  - "docker"             # can run containers
  - "kubernetes"         # has kubectl access
  - "browser"            # has Chrome/Playwright
mcp_tools:
  - "browser-use"
  - "docker-exec"
  - "kubectl"
  - "local-files"
workspaces:
  - "coding"             # pre-configured workspaces on this node
  - "devops"
labels:
  env: "production"
  zone: "homelab"
  tier: "compute"
```

### Agent Placement (Scheduling)

When the human spawns an agent (or a supervisor delegates work), the system chooses the best node:

```
Placement decision tree:
1. Does the task REQUIRE specific hardware? (GPU, browser, local files)
   → Filter to nodes with that capability
2. Does the agent type have an affinity label? (coding → gpu-compute, browser → browser)
   → Prefer matching nodes
3. Which node has the most available resources?
   → Least-loaded node wins (weighted by CPU, RAM, GPU VRAM)
4. Is the human's TUI session on a specific node?
   → Prefer co-location for lower latency on interactive tasks
5. Manual override always takes precedence
```

**Placement examples:**
- `:spawn coding --task "refactor auth"` → Node A (has GPU, least loaded)
- `:spawn browser --task "scrape site"` → Node C (only node with Chrome/Playwright)
- `:spawn research --task "find papers"` → Node B (API-only task, laptop is fine)
- `:spawn coding --node node-b --task "quick fix"` → manual override to Node B

### Cross-Node Communication

```
┌──────────────────────────────────────────────────────────────────┐
│                     NATS Subject Space                            │
│                                                                   │
│  aiw.nodes.{id}.heartbeat         — liveness pings (every 5s)    │
│  aiw.nodes.{id}.capabilities       — node capability registry     │
│  aiw.nodes.{id}.status             — online/offline/degraded      │
│                                                                   │
│  aiw.agents.{id}.output            — agent live output stream     │
│  aiw.agents.{id}.thinking          — agent reasoning stream       │
│  aiw.agents.{id}.status            — agent lifecycle events       │
│  aiw.agents.{id}.permission        — permission requests          │
│                                                                   │
│  aiw.tasks.{id}.created            — task lifecycle events        │
│  aiw.tasks.{id}.updated                                           │
│  aiw.tasks.{id}.completed                                         │
│                                                                   │
│  aiw.rpc.placement.request         — ask mesh: where to run?      │
│  aiw.rpc.placement.response        — node responds with bid       │
│  aiw.rpc.agent.spawn               — request node to spawn agent  │
│  aiw.rpc.mcp.call                  — cross-node MCP tool call     │
└──────────────────────────────────────────────────────────────────┘
```

### TUI Across the Mesh

```
┌─ aiw ── ws:work ── mesh:3 nodes ── tasks:8/31 ── agents:4⚡ ── 14:32 ────────┐
│                                                                                │
│  ┌─ Nodes ──────────────────────────────────────────────────────────────────┐ │
│  │ ● homelab (node-a)      CPU:25%  RAM:48/64GB  GPU:✓  agents:2  [focus]   │ │
│  │ ● laptop (node-b)       CPU:60%  RAM:18/32GB  GPU:✓  agents:1            │ │
│  │ ● cloud-vm (node-c)     CPU:10%  RAM:8/16GB   GPU:✓  agents:1            │ │
│  └───────────────────────────────────────────────────────────────────────────┘ │
│                                                                                │
│  ┌─ coding (claude) @ homelab ─────────────────┬─ browser (gemini) @ cloud ───┐│
│  │ ▸ Fix auth middleware           [ongoing]    │ ▸ Scrape competitor prices    ││
│  │                                              │                    [ongoing] ││
│  │  > Reading src/auth/middleware.go...         │  > Navigating to site...      ││
│  │  > Running tests... 12/12 pass               │  > Extracting product grid... ││
│  │                                              │  > Found 234 products         ││
│  └──────────────────────────────────────────────┴──────────────────────────────┘│
│                                                                                │
│  ┌─ research (claude) @ laptop ───────────────────────────────────────────────┐│
│  │ ▸ Research MCP tools              [ongoing]                                ││
│  │  > Querying APIs... filtering results...                                   ││
│  └────────────────────────────────────────────────────────────────────────────┘│
│                                                                                │
│  > _                                                          [^N] nodes       │
│  [Tab] agents  [^K] tasks  [^W] workspace  [^S] spawn  [^N] nodes  [^Q] quit  │
└────────────────────────────────────────────────────────────────────────────────┘
```

**The TUI connects to any node in the mesh.** If the TUI's local node goes down, it reconnects to another node transparently. All state is in the shared PostgreSQL database.

### Mesh Resilience

| Scenario | Behavior |
|----------|----------|
| **Node goes offline** (graceful) | Node publishes `status: offline`. Agents on that node are marked `failed`. Pending tasks re-queued to other nodes. |
| **Node crashes** (ungraceful) | Heartbeat timeout after 15s. Other nodes detect via NATS. Same recovery as graceful. |
| **NATS cluster partition** | Split-brain: each partition continues independently. On heal, state reconciled from PostgreSQL (source of truth). |
| **PostgreSQL unavailable** | Nodes operate in degraded mode: can continue running existing agents but can't create new tasks or query knowledge graph. |
| **TUI node disconnects** | TUI reconnects to any available node. Session state (scroll position, open panels) restored from local cache. |

### Local-First Tools

Some MCP tools only make sense on specific nodes:

```
┌─ Cross-Node MCP Tool Routing ─────────────────────────────────────────────────┐
│                                                                                │
│  Agent on Node B (laptop) calls: mcp_browser_navigate(url="...")              │
│                                                                                │
│  1. Agent's MCP server checks: is browser-use available locally?               │
│     → No. Node B has no Chrome/Playwright.                                     │
│                                                                                │
│  2. NATS query: aiw.rpc.mcp.resolve.tool.browser-use                           │
│     → Node C (cloud-vm) responds: "I have browser-use, latency 12ms"           │
│                                                                                │
│  3. Request forwarded: aiw.rpc.mcp.call → Node C                               │
│     → Node C executes browser-use, captures result                             │
│                                                                                │
│  4. Response returned: aiw.rpc.mcp.response ← Node C                           │
│     → Agent receives result as if tool was local                               │
│                                                                                │
│  The agent doesn't know or care which node executed the tool.                  │
│  The mesh abstracts physical location.                                          │
└────────────────────────────────────────────────────────────────────────────────┘
```

### Data Locality & State

| Data | Location | Rationale |
|------|----------|-----------|
| Tasks, workspaces | PostgreSQL (shared) | Must be consistent across nodes |
| Knowledge graph | PostgreSQL + pgvector (shared) | Single source of truth for embeddings |
| Agent output streams | NATS (ephemeral) + PostgreSQL (persisted) | Live streaming via NATS, history in DB |
| File attachments | Object store (MinIO/S3) or shared NFS | Files accessible from any node |
| MCP tool state | Local to node | Browser sessions, Docker containers are node-local |
| TUI session state | Local disk (SQLite) | Scroll position, layout, preferences |

### Deployment: From Single Node to Mesh

```bash
# Single node (development)
aiw serve

# Join existing mesh (add a node)
aiw serve --join nats://homelab.local:4222

# Bootstrap new mesh (first node)
aiw serve --mesh-bootstrap

# Node with specific role
aiw serve --role compute --join nats://homelab.local:4222
aiw serve --role browser --join nats://homelab.local:4222
aiw serve --role gateway --join nats://homelab.local:4222  # API-only, no agents
```

---

## Caching Architecture

### Philosophy: Never Compute the Same Thing Twice

AI agents are expensive — LLM inference, embedding computation, vector search, and tool execution all consume compute and (for cloud models) money. A multi-tier caching strategy ensures that repeated or semantically similar work is served from cache, not recomputed.

### Three-Tier Cache Hierarchy

```
┌─ Caching Architecture ───────────────────────────────────────────────────────┐
│                                                                               │
│  L1: In-Memory (per-node, Go `sync.Map` + LRU)                               │
│  │ ▸ Embedding cache          keyed by content SHA256, no expiry              │
│  │ ▸ Context assembly cache   keyed by task_id, invalidated on task update    │
│  │ ▸ MCP tool result cache    keyed by tool+params hash, TTL-based            │
│  │ ▸ Access pattern cache     keyed by agent+workspace, predicts next tasks   │
│  │ ▸ Latency: <1ms            Hit rate target: 60-80%                         │
│                                                                               │
│  L2: Redis / Valkey (shared, mesh-wide)                                       │
│  │ ▸ Semantic response cache   embedding similarity match ± TTL               │
│  │ ▸ Knowledge retrieval cache query → top_k results, TTL 5min                │
│  │ ▸ Session state             distributed across mesh nodes                  │
│  │ ▸ Rate limit counters       sliding window per user/IP/tool                │
│  │ ▸ Pub/sub change stream     cache invalidation events across nodes         │
│  │ ▸ Latency: <5ms             Hit rate target: 30-50%                        │
│                                                                               │
│  L3: PostgreSQL (persistent, source of truth)                                  │
│  │ ▸ Materialized embeddings   pre-computed for known documents               │
│  │ ▸ Cache analytics           hit/miss rates, cost savings, latency         │
│  │ ▸ Audit log                 every cache decision for debugging             │
│  │ ▸ Latency: <20ms            Always consulted on L2 miss                    │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Semantic Response Cache (The Key Innovation)

Unlike traditional key-value caches, the semantic cache matches queries by **meaning**, not exact text. This is critical for AI agents — two different phrasings of the same task should hit the same cache entry.

```
Flow:
1. Agent executes task: "Research top 5 MCP scraping tools with Playwright support"
2. Task text → embedding vector (via local embedding model, cached in L1)
3. Redis query: FT.SEARCH idx:semantic_cache 
     "@embedding:[VECTOR_RANGE 0.05 $query_vector]" 
     => returns cached response if cosine_similarity > 0.95
4. Cache HIT → return cached result immediately, record $0.00 cost
5. Cache MISS → execute task via LLM, store result + embedding in Redis, TTL 24h
```

**Cache entry structure:**
```json
{
  "key": "semantic:task:abc123hash",
  "query_text": "Research top 5 MCP scraping tools with Playwright support",
  "query_embedding": [0.023, -0.451, ...],
  "response": "## Top MCP Scraping Tools\n1. browser-use-mcp...",
  "model": "claude-3.7-sonnet",
  "tokens_used": 1247,
  "cost_saved": 0.018,
  "workspace": "research",
  "created_at": "2026-06-16T14:32:00Z",
  "ttl": 86400,
  "hit_count": 3
}
```

**Similarity matching:**
- Uses pgvector-compatible operators via Redis vector search
- Similarity threshold configurable per workspace: strict (0.95) for code, relaxed (0.85) for research
- Cache key includes model name → different models get different cache entries for same query
- TTL varies by task type: 1h for news/time-sensitive, 24h for research, 7d for reference docs

### Embedding Cache (L1)

Computing embeddings is the hidden cost of semantic search. Cache embeddings aggressively:

```go
type EmbeddingCache struct {
    cache *lru.Cache[string, []float32]
}

func (c *EmbeddingCache) GetEmbedding(text string) ([]float32, bool) {
    key := sha256Hex(text)
    return c.cache.Get(key)
}

func (c *EmbeddingCache) SetEmbedding(text string, emb []float32) {
    key := sha256Hex(text)
    c.cache.Add(key, emb)
    // Also publish to L2 for other nodes
    redis.Set("emb:" + key, marshalProto(emb), 0) // no expiry
}
```

**What gets embedded:**
- Knowledge graph nodes (on creation, cached permanently in L3)
- Task descriptions (on creation, cached in L1)
- Agent queries (on execution, cached in L1 → L2 if semantic hit)
- MCP tool descriptions (at startup, cached in L1)

### MCP Tool Result Cache (L1)

Many MCP tool calls are deterministic and expensive. Cache results with context-aware TTLs:

| Tool Type | Cache TTL | Invalidation |
|-----------|-----------|-------------|
| `browser-use` (scrape) | 15 min | URL + params hash |
| `file-read` | Invalidate on file change (inotify) | File path hash |
| `api-call` (GET) | Respect `Cache-Control` header | URL + headers hash |
| `api-call` (POST) | No cache (mutations) | — |
| `git-status` | 30s | Repository path |
| `docker-ps` | 10s | — |
| `shell-exec` (idempotent) | Configurable | Command + cwd hash |
| `shell-exec` (mutation) | No cache | — |

```go
// MCP middleware: check cache before executing tool
func (s *WorkspaceServer) withCache(toolName string, handler ToolHandler) ToolHandler {
    return func(ctx context.Context, params any) (*ToolResult, error) {
        if cacheTTL := s.getCacheTTL(toolName, params); cacheTTL > 0 {
            key := toolName + ":" + hashParams(params)
            if cached := s.cache.Get(key); cached != nil {
                s.emitTelemetry(ctx, "cache_hit", toolName)
                return cached, nil
            }
            result, err := handler(ctx, params)
            if err == nil {
                s.cache.Set(key, result, cacheTTL)
            }
            return result, err
        }
        return handler(ctx, params)
    }
}
```

### Context Assembly Cache (L1)

Agent context assembly (system prompt + workspace notes + retrieved knowledge + task + tool list) is expensive — especially the vector search. Cache the assembled context per task:

```
Context assembly cost: ~50-200ms (vector search + template rendering)
Cache hit: <1ms
Invalidation: 
  → Task updated (body, title, status change)
  → Workspace notes edited
  → New knowledge node added that would rank in top_k for this query
  → System prompt template changed
  → Auto-allow rules changed
```

### Distributed Cache Invalidation

In a mesh, cache entries on one node must be invalidated when another node changes data:

```
NATS subject: aiw.cache.invalidate

Node B updates task: "Fix auth middleware" → status = ongoing
  → Publishes: { type: "task_updated", task_id: "abc123", workspace: "work" }
  → All nodes receive event, invalidate L1 context cache for that task
  → L2 semantic cache entries referencing this task are marked stale

Invalidation events:
  task_updated / task_deleted → clear context assembly cache for that task
  workspace_updated → clear all context caches for that workspace
  knowledge_node_added → re-check if it affects any active task contexts
  embedding_model_changed → clear all embedding caches (rare, controlled)
```

### Cache Analytics & Cost Tracking

Every cache event is recorded for observability:

```
┌─ Cache Dashboard ── ws:work ── last 24h ─────────────────────────────────────┐
│                                                                               │
│  Overall Hit Rate                    Savings                                  │
│  L1: ████████████████░░ 82%          Tokens saved: 847,231                     │
│  L2: ██████░░░░░░░░░░░░ 35%          Cost saved:   $12.47                      │
│                                       Avg latency reduction: 1,847ms → 3ms     │
│                                                                               │
│  By Cache Type                        Top Cached Queries                      │
│  Embedding:    ██████████ 94%         "Research MCP tools" (hit 12x)           │
│  Context:      ████████░░ 78%         "Fix auth middleware" (hit 8x)            │
│  Semantic:     ██████░░░░ 58%         "Summarize README" (hit 5x)              │
│  Tool Result:  ████░░░░░░ 42%         "List Docker containers" (hit 3x)        │
│  Retrieval:    ████░░░░░░ 40%                                                  │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Cache Configuration

```yaml
# _config/base.yaml
cache:
  l1:
    embedding:
      max_entries: 10000
      eviction: lru
    context_assembly:
      max_entries_per_workspace: 50
      ttl: 300  # 5min, extended on access
    mcp_tool_result:
      max_entries: 5000
      default_ttl: 60  # 1min default
  l2:
    redis:
      host: "${REDIS_HOST:localhost}"
      port: "${REDIS_PORT:6379}"
      db: 0
      max_memory: "${REDIS_MAX_MEMORY:512mb}"
      eviction_policy: allkeys-lru
    semantic:
      similarity_threshold: 0.92
      ttl:
        research_tasks: 86400   # 24h
        coding_tasks: 3600      # 1h
        reference_docs: 604800  # 7d
        time_sensitive: 1800    # 30min
    retrieval:
      ttl: 300  # 5min
  analytics:
    enabled: true
    flush_interval: 60s  # batch-write cache stats to PostgreSQL
```

---

## Permission Gating System

Three-tier auto-approval:
```
1. Tool in workspace.AutoAllowedTools? → auto-approve (flash in lane, no interruption)
2. Task has AllowAllCommands = true? ("YOLO mode") → auto-approve
3. Otherwise → pause agent lane, show permission modal
```

**Auto-allow rules are command-aware for shell tools:**
- `Bash:git *` auto-allows all git commands
- `Bash:npm *` auto-allows all npm commands
- `mcp_browser_navigate` auto-allows a specific MCP tool
- `Bash:*` auto-allows everything (dangerous, explicit opt-in only)

**"Always Allow" persistence:** saves tool+command pattern to `workspace.AutoAllowedTools`. Future matching requests auto-approved. Telemetry event recorded for audit.

**YOLO Mode:** Per-task toggle (`Ctrl+Z` in TUI, button in web). Bypasses ALL checks for that task. Visual indicator: orange header in TUI lane, glowing button in web.

---

## Messaging Bridge (Multi-Channel)

Bidirectional bridge for each messaging platform (Slack, Telegram, WhatsApp):

**Outbound:**
- Task creation → platform thread/channel message
- Agent messages → thread replies
- Permission requests → interactive buttons (Allow/Deny)
- Status updates → formatted notifications

**Inbound:**
- Platform mentions in threads → reply to task
- Slash commands → create tasks
- Button clicks (Allow/Deny) → permission verdicts sent to MCP agent

**Bidirectional sync:**
- Human approves in platform → verdict sent to agent, UI updates
- Human approves in web UI → platform buttons replaced with result text
- Origin tracking prevents echo loops (`entity.OriginSlack` / `entity.OriginTelegram`)

**Auto-provisioning:**
- OAuth install → auto-creates private channel/group → invites user
- Graceful error handling: if channel deleted, auto-removes the link

---

## Scheduled Tasks (Cron)

5-field cron syntax: `minute hour dom month dow`

**Parent/Child model:**
- Scheduled task templates have `status = "cron"`
- Scheduler polls every 60 seconds
- When current minute matches, spawns a **child task** (copies title, body, attachments, `AllowAllCommands`; sets `ParentID`, `status = "notstarted"`)
- **One-time tasks** (fixed dom and month): parent template deleted after spawning
- **Recurring tasks** (wildcards in dom/month): parent persists for future runs
- **Anti-duplicate**: before spawning, checks if any child with same parent is already in `notstarted` or `ongoing`

**Granularity enforcement:**
- Minute field must be a single integer 0-59 for recurring tasks (enforces ≥ hourly)
- One-time tasks can have minute-level precision
- Wildcards, steps, ranges, and comma-lists in minute field are rejected

---

## Agent Swarm Orchestration

### Supervisor → Worker Pattern

```
Supervisor Agent
└── MCP Session → coremcp (/mcp)              [OAuth2, user-scoped]
    ├── listWorkspaces()         → discovers all workspaces + mcpURLs
    ├── createTask(ws=B)         → assigns task to coding agent
    ├── createTask(ws=C)         → assigns task to docs agent
    ├── createTask(ws=D)         → assigns task to publishing agent
    └── listTasks(ws)            → monitors progress cross-workspace

Worker Agents (one per workspace, isolated)
├── MCP Session → /mcp/{workspaceB}           [workspace token]
├── MCP Session → /mcp/{workspaceC}           [workspace token]
└── MCP Session → /mcp/{workspaceD}           [workspace token]
```

### Session ↔ Task Context Mapping
Every MCP tool call updates a session→task mapping:
```go
ps.sessionTasksMu.Lock()
ps.sessionTasks[sessID] = taskID
ps.sessionTasksMu.Unlock()
```

Permission requests without explicit taskID resolve via 3-stage fallback:
1. From the permission request payload
2. From the session→task map
3. From the DB (query workspace's current ongoing/blocked task)

### Agent Liveness & Idle Polling

**Connection tracking** (atomic counter):
- SSE connect → `agentConnections.Add(1)` → publish `agent.connected: true`
- SSE disconnect → `agentConnections.Add(-1)` → publish `agent.connected: false`

**Idle poller** (every 60s):
- If unstarted tasks exist + no ongoing tasks → push next task to agent
- If ongoing task exists for >1 hour → send "Status check" nudge

**Health checks** (every 60s):
- Ping all MCP sessions; evict dead ones (timeout, stream closed, already closed)
- Prevents stale sessions from accumulating and showing false "online" status

### PubSub Origin Tracking
```go
ctx = entity.WithOrigin(ctx, entity.OriginSlack)
// Controllers check origin to prevent echo loops:
if event.Origin == entity.OriginSlack { return } // don't echo back
```

---

## Data & Persistence

### ID Generation: Monoflake
K-sortable, Base62-encoded snowflake-style IDs:
```
"0ZzhYQG2qtl" = workspace ID (URL-safe, time-sortable, distributed-safe)
```
No central sequencer needed — each process generates unique, ordered IDs independently.

### Workspace Token Encryption
```go
encToken, nonce, _ := security.Encrypt(token, serverKey)
// Stored encrypted in DB, decrypted only on agent connection
```
Tokens are AES-GCM encrypted at rest with a server-side key from config.

### Cleanup Service
Runs daily at midnight UTC:
- Deletes orphaned attachment files older than configured retention period (`"7d"` or `"168h"`)
- Skips database files (`.db` extension)
- Logs deleted file count

### Config System (YAML Layering)
```yaml
# base.yaml → shared defaults
# development.yaml → dev overrides (merged on top of base)
# production.yaml → prod overrides
# ENV var expansion with defaults: ${VAR:default_value}
```
Superior to flat `.env` files for multi-environment self-hosted deployments.

---

## Browser Agent (browser-use)
```python
from browser_use.beta import Agent, ChatBrowserUse

agent = Agent(
    task="Extract AI job postings from LinkedIn",
    llm=ChatBrowserUse(model="claude-3-7-sonnet"),
    browser_profile=BrowserProfile(help_text="Use LinkedIn filters"),
)
agent.run()  # Returns markdown summaries
```

*MCP server:* `mcpx run --stdio` exposes Playwright control as MCP tools

---

## MCP Marketplace
```bash
aiw workspace add --name scrape --mcp apigene.ai/mcp/47aa3f
# Connects browser MCP server
aiw task add --workspace scrape "Scrape latest AI papers" --agent scrape/browser
```

Discover MCP tools: [`mcp.directory`](https://mcp.directory), [`apigene.ai`](https://apigene.ai)

---

## Workspaces
```yaml
# ~/.config/aiw/workspaces.yml
workspaces:
  personal:
    allowed_models: ["llama-3", "gemini-3"]
    mcp_servers: ["browser-personal", "calendar-personal"]
    auto_allowed_tools: ["Bash:git *", "Bash:npm *"]
    context_tags: ["#family", "#hobbies"]
  work:
    allowed_models: ["claude-3-7-team", "codestral"]
    mcp_servers: ["github-internal", "jira", "corporate-calendar"]
    auto_allowed_tools: ["Bash:docker *", "Bash:kubectl *"]
    workspace_tags: ["#sensitive"]
```
Each workspace gets its own MCP server, token, and auto-allow rules. Archived workspaces are read-only but preserved.

---

## Sample User Journeys

### Morning Standup: Multi-Agent Workspace (TUI)
```
$ aiw
┌─ aiw ── ws:work ── claude-3.7 ── tasks:5/23 ── agents:0○ ── 08:52 ─────────┐
│                                                                              │
│ Human types Ctrl+S to spawn agents:                                          │
│   :spawn coding --model claude-3.7 --task "Fix auth middleware expiry bug"   │
│   :spawn research --model gemini-2.5 --task "Research MCP scraping tools"    │
│   :spawn docs --model claude-3.7 --task "Update API documentation for v2.1"  │
│                                                                              │
│ Three agent lanes appear. Human watches all three work simultaneously:       │
│                                                                              │
│  coding lane:     "Reading src/auth/middleware.go..."                        │
│  research lane:   "Querying mcp.directory for browser scraping tools..."     │
│  docs lane:       "Scanning openapi.yaml for new endpoints..."               │
│                                                                              │
│ coding agent requests permission: 🔒 "Bash: git push"                        │
│ Human presses 'a' to allow once. Agent continues.                            │
│                                                                              │
│ Human presses Ctrl+T to see reasoning: research agent evaluates MCP tools.   │
│ docs agent finishes → ✅ completed. coding finishes → ✅ completed.           │
│ 30 minutes later: all tasks complete. Human reviews summaries per lane.      │
└──────────────────────────────────────────────────────────────────────────────┘
```

### On-the-Go Check-in (Web Dashboard / Mobile)
```
Human opens phone → PWA dashboard shows:
  - 2 agents online, 1 permission pending
  - coding: "Fixed auth bug, 12/12 tests pass, waiting for review"
  - research: 🔒 Permission required: "Bash: npm install browser-use"

Human taps "Allow Once" → agent resumes. Human checks progress bars,
replies "Great, merge it" to coding agent. Closes phone.
```

### Supervisor Delegation (Autonomous)
```
Human creates: "Write, document, and publish auth module" → supervisor workspace
  → Supervisor agent (connected to coremcp) picks up the task
  → Supervisor calls listWorkspaces() to discover available worker workspaces
  → createTask(ws=coding, "Implement auth module in Go")
  → createTask(ws=docs, "Write auth module documentation")
  → createTask(ws=publish, "Publish release v2.1.0")
  → Each worker agent picks up its task via getNextTask()
  → Human watches all three lanes in the TUI, intervenes only if needed
  → Supervisor monitors via listTasks(status="completed")
  → When all complete, supervisor calls replyToTask with summary
```

### Mesh Workload: GPU on Homelab, Browser on Cloud
```
$ aiw serve                           # Node A: homelab (GPU)
$ aiw serve --join nats://homelab     # Node B: laptop (TUI session)
$ aiw serve --role browser --join ... # Node C: cloud VM (Playwright)

Human at TUI (laptop) types:
  :spawn coding --task "Fine-tune embedding model" --gpu required
  :spawn browser --task "Scrape competitor pricing"
  :spawn research --task "Summarize latest papers"

Placement decisions:
  coding agent    → Node A (homelab, RTX 4090 GPU available)
  browser agent   → Node C (cloud VM, only node with Playwright)
  research agent  → Node B (laptop, API-only, local is fine)

TUI shows all three agent lanes, each labeled with @ nodename:
  coding @ homelab:    "Loading model weights... GPU: 18/24GB VRAM"
  browser @ cloud-vm:  "Navigating to competitor site... 234 products found"
  research @ laptop:   "Querying arxiv API... 47 papers matched"

Cloud VM node goes offline → browser lane shows ⚠️ disconnected.
Task auto-requeued. Human sees notification:
  "No browser nodes available. Start one with: aiw serve --role browser"
```

---

## Docker Deployment

### Multi-Stage Build (`FROM scratch`)
```dockerfile
FROM node:22-alpine AS frontendbuild
# Build Vue app, compress with gzip + brotli

FROM golang:1.25 AS build
# Build static Go binary with CGO_ENABLED=0

FROM scratch
# Single binary, zero dependencies, <30MB
COPY --from=build /app/aiw /
USER nobody
CMD ["/aiw"]
```

---

## Roadmap

### Phase 1: Foundation
1. [ ] Port aiw v1 knowledge engine (PostgreSQL + pgvector)
2. [ ] Build two-tier MCP architecture (Supervisor + Worker servers)
3. [ ] Implement lazy workspace MCP server manager
4. [ ] Implement permission gating system (auto-allow rules + human approval flow)
5. [ ] Multi-stage Docker build (`FROM scratch`)
6. [ ] L1 in-memory cache (embedding, context assembly, MCP tool results)
7. [ ] L2 Redis/Valkey cache (semantic response, retrieval, sessions, rate limits)

### Phase 2: TUI — Agent Operations Center
6. [ ] Build TUI framework (Textual/Python) with panel system
7. [ ] Implement multi-agent lane split view (auto-arrange, resize, scroll)
8. [ ] Build task panel with tree view, progress bars, status indicators
9. [ ] Implement thinking visibility toggle (per-agent + global)
10. [ ] Build command palette (`:`) and global keybinding system
11. [ ] Implement permission modal overlay with keyboard shortcuts
12. [ ] Session/workspace context bar with real-time status

### Phase 3: Knowledge & Visualization
13. [ ] Build knowledge graph engine (pgvector + edge relationships)
14. [ ] Implement TUI graph navigation (ASCII/Unicode, arrow keys)
15. [ ] Rich content rendering pipeline (Mermaid → ASCII, PlantUML → text, sparklines)
16. [ ] Web interactive graph (D3.js/Cytoscape force-directed layout)
17. [ ] Obsidian vault sync (bidirectional markdown + frontmatter tags)

### Phase 4: Web & Channels
18. [ ] Build web dashboard (Vue 3, PWA) — secondary/mobile interface
19. [ ] Multi-channel messaging bridge (Telegram → Slack → WhatsApp)
20. [ ] Copy-paste setup configs for Claude, Gemini, Codex agents

### Phase 5: Mesh & Distribution
21. [ ] NATS cluster setup with TLS and node authentication
22. [ ] Node capability registry and heartbeat/liveness system (every 5s)
23. [ ] Agent placement/scheduling (capability-aware, least-loaded, manual override)
24. [ ] Cross-node MCP tool routing (transparent proxy to capable nodes)
25. [ ] Mesh-aware TUI (node panel, agent@node labels, multi-node lanes)
26. [ ] Mesh resilience (node failure detection, agent re-queue, auto-reconnect)
27. [ ] Shared object store for attachments (MinIO/S3)

### Phase 6: Intelligence
28. [ ] Agent swarm orchestration (NATS bus + supervisor-worker delegation)
29. [ ] Workspace separation logic (personal vs work)
30. [ ] Calendar MCP integration
31. [ ] Integrate browser-use MCP server
32. [ ] Cron scheduler with parent/child spawning
33. [ ] Agent liveness monitoring, health checks, idle polling

### Phase 7: Context Workbench & Optimization
34. [ ] Context assembly inspector (show all sources, edit each)
35. [ ] Retrieval tuning interface (top_k, threshold, re-rank, pin/exclude)
36. [ ] Context templates system (YAML-defined, versioned, workspace-scoped)
37. [ ] Context performance tracking (success rate, interventions, confidence)
38. [ ] A/B context comparison mode

---

## Resources
- Agent Orchestration: [Karna](https://github.com/MukundaKatta/karna)
- Browser Agents: [browser-use](https://github.com/browser-use/browser-use)
- MCP Tools: [MCP.directory](https://mcp.directory) + [apigene.ai](https://apigene.ai)
- Reference Implementation: [AgentRQ](https://github.com/agentrq/agentrq) — task orchestration, permission gating, chat-centric UI, two-tier MCP
