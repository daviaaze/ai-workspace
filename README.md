# AI Workspace

AI Workspace (`aiw`) is your self-hosted **everything agent** — knowledge, research, automation, coding, and collaboration.

> *From research helper to fully autonomous daily workspace* ⬇️

## 🎯 Where We Started: `aiw` v1
- **Knowledge backbone**: PostgreSQL + pgvector, Obsidian sync
- **Research pipeline**: crewAI → sub-questions → parallel research → report
- **Task manager**: Cron-scheduled tasks + CLI
- **Workflow engine**: DAG-based execution with retry

👉 Sep 2024: Focused on **research + knowledge** for pi agents.

## 🚀 Where We're Going: `aiw` v2
> *“Everything workspace from anywhere, with agents that work alongside you”

### Key Upgrades
| Area | `v1` | `v2` |
|------|------|------|
| **Channels** | CLI | ✅ Omnichannel: TUI, Web, Telegram/Slack/WhatsApp, Voice
| **Browser Agent** | web_fetch only | ✅ Playwright-controlled browser via `browser-use` → research, scrape, fill forms
| **Agent Swarm** | Single-task | ✅ Supervisor-worker delegation, spawn agents, handoff protocol
| **Workspaces** | Single context | ✅ Personal/work separation with isolated MCP models/tools
| **Calendar** | No | ✅ MCP-powered calendar injection, meeting booking, auto-responder
| **Coding** | No | ✅ Order-driven coding agent: opens PRs, debugs, writes code
| **MCP Discovery** | Research tools | ✅ 60+ MCP tools from `mcp.directory` + `apigene.ai`

### Architecture
```
gateway
├─ cli (typer)
├─ web (next.js)
├─ messaging (Matrix/Slack/WhatsApp adapters)
└─ api

nats
├─ orchestrator → agent swarm
├─ workspace-personal → data + MCP tools
└─ workspace-work → isolated context

agents
├─ research (crewAI)
├─ browser (browser-use)
├─ calendar (caldav-mcp)
└─ coding (crewAI + git)
```

---
## Quick Start
### 1. Run the knowledge backbone (v1)
```bash
createdb ai_workspace
# Install pgvector: sudo -u postgres psql -p 2284 -d ai_workspace -c "CREATE EXTENSION vector;"
aiw init
```

### 2. Explore MCP tools
```bash
# List MCP servers
aiw mcp list

# Add browser MCP 
aiw workspace add --name browser --mcp apigene.ai/mcp/47aa3f --workspace personal
```

### 3. Run a browser agent
```bash
# Spawn browser agent via MCP
# Uses browser-use under the hood
aiw task add "Extract AI startup funding rounds from Crunchbase"
```

---
## What Makes aiw Unique
- 🔁 **Self-hosted**: Runs on homelab → no SaaS dependency
- 🧠 **Long-term memory**: Knowledge graph across sessions
- ⚡ **Actor-based orchestration**: Resilient agent swarms (no central LLM)
- ⚠️ **Workspace isolation**: Personal/work contexts with different MCP tools/models
- 🌐 **Browser-native**: browser-use provides deterministic browser control

---
## Roadmap
- [x] `v1`: Knowledge backbone + research
- [ ] `v2-dev`: Omnichannel gateway + browser MCP
- [ ] Agent swarm framework
- [ ] Calendar & meeting injection
- [ ] Web dashboard
- [ ] Workspace isolation

---
## License
MIT

---
> Ready to move from research helper → daily productivity hub?

- Follow [design doc v2 →](/docs/aiw-spec-v2.md)
- Try the MCP browser agent → `aiw task add "Research latest MCP trends"`