# TUI v5 Design — AI Workstation

> **Status:** 📋 Design | **Data:** 2026-06-18
> **Refs:** tui-design skill, lazygit VISION.md, Posting.sh, Textual docs, aiw v2/v3/v4

---

## Princípios (do skill tui-design)

1. **Discoverability** — Usuário vê o que pode fazer sem ler docs (help bar visível)
2. **Simplicity** — Uma tela principal, overlays para secundário (Router pattern)
3. **Safety** — Confirmar ações destrutivas, nunca perder trabalho do usuário
4. **Keyboard-first** — Power users voam sem mouse
5. **Reactive** — Estado muda → UI atualiza automaticamente

---

## Anti-patterns que já cometemos (não repetir)

| Erro | Por que falhou | O que fazer |
|------|---------------|-------------|
| 7+ tabs com conteúdo vazio | Usuário vê telas mortas | **1 tela principal + overlays** |
| Dashboard com 6 cards "No data" | Espaço desperdiçado | **Mostrar só o que tem dados** |
| Spawn de agente requer 3 serviços | Muitos pontos de falha | **Degradação graciosa** |
| `except: pass` nos widgets | Bugs invisíveis | **Log + fallback UI** |
| Layout multi-painel complexo | Terminal é 80×24 | **Painel único + bottom bar** |

---

## Layout

### Tela principal: Chat-first com Agent Monitor

```
┌─ Header ──────────────────────────────────────────────────────────┐
│ aiw  ~/project  qwen3:14b  ⚡2 agents  💰$0.005  💾6,049t  12:16 │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌─ Agent Monitor (colapsável, visível quando agentes ativos) ─┐  │
│  │ agent-1 🔵 coding  "Fix auth middleware"     3 steps  80%   │  │
│  │ agent-2 🟡 research "MCP tools comparison"   1 step   20%   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  Conversation                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                                                              │  │
│  │  ▸ You: Research Rust async vs Go goroutines                 │  │
│  │                                                              │  │
│  │  🤖 agent-1 (research):                                      │  │
│  │  ┌─ Step 1 ─────────────────────────────────────────────┐   │  │
│  │  │ 🤔 Thought: Need to find recent benchmarks and        │   │  │
│  │  │   ecosystem comparisons                               │   │  │
│  │  │ 🔧 Action: web_search("Rust async vs Go 2026 bench")  │   │  │
│  │  │ 👁 Observation: Found 5 results. Top: blog post with  │   │  │
│  │  │   benchmarks showing Go 15% faster for I/O...         │   │  │
│  │  └───────────────────────────────────────────────────────┘   │  │
│  │  ┌─ Step 2 ─────────────────────────────────────────────┐   │  │
│  │  │ 🤔 Thought: Reading the top 3 sources for details     │   │  │
│  │  │ 🔧 Action: web_fetch(url1)                             │   │  │
│  │  │ ⏳ Waiting...                                           │   │  │
│  │  └───────────────────────────────────────────────────────┘   │  │
│  │                                                              │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│  /search  /code  /files  /git  /model  /help     Enter send  ^Q  │
└────────────────────────────────────────────────────────────────────┘
```

### Estados da tela

**Estado 1: Idle (sem agentes)**
```
┌─ Header ──────────────────────────────────────────────────────────┐
│                                                                    │
│            🤖 AI Workstation                                      │
│            ~/Projects/ai-workspace                                │
│                                                                    │
│     Type a task — agent spawns and researches/codes/builds        │
│                                                                    │
│     ▸ [________________________________________________]         │
│                                                                    │
│     /help commands   /model switch   Ctrl+O workspace             │
│                                                                    │
├────────────────────────────────────────────────────────────────────┤
│  /search  /code  /files  /git  /model  /help     Enter send  ^Q  │
└────────────────────────────────────────────────────────────────────┘
```

**Estado 2: Agent running (monitor visível)**
```
┌─ Header ──────────────────────────────────────────────────────────┐
│  ┌─ Agent Monitor ──────────────────────────────────────────────┐ │
│  │ agent-1 🔵 coding  "Fix auth"  Step 3/5  60%  ⏸ pause  ✕ kill│ │
│  └────────────────────────────────────────────────────────────────┘ │
│  ▸ You: Fix the auth middleware bug                               │
│  ┌─ agent-1 ────────────────────────────────────────────────────┐ │
│  │ Step 1  🔧 read_file("auth.py")               ✓ done  0.3s  │ │
│  │ Step 2  🤔 Analyzing...                       ✓ done  2.1s  │ │
│  │ Step 3  🔧 edit_file("auth.py", ...)          ● running     │ │
│  └────────────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────┤
│  Ctrl+S spawn  Space pause  Ctrl+K kill  F2 chat  ^Q quit        │
└────────────────────────────────────────────────────────────────────┘
```

### Overlays (ModalScreen)

```
Chat (F2)        — Chat direto com LLM, sem agentes
Files (Ctrl+O)   — File browser com git status
Git (Ctrl+G)     — Git log, diff, status
Search (/search) — Pesquisa profunda (modo tela cheia)
Help (F1)        — Referência de comandos
Dashboard (F3)  — Visão geral: stats, activity, cache
```

---

## Navegação

### Router pattern (do skill)

```python
class AIWorkspaceApp(App):
    """Uma tela principal. Overlays para o resto."""
    
    def compose(self):
        yield Header()
        yield AgentMonitor()    # visível só com agentes ativos
        yield Conversation()     # scroll infinito
        yield HelpBar()          # sempre visível
    
    # Overlays (ModalScreen)
    def action_chat(self):       self.push_screen(ChatScreen())
    def action_files(self):      self.push_screen(FileBrowser())
    def action_git(self):        self.push_screen(GitPanel())
    def action_search(self):     self.push_screen(SearchScreen())
    def action_help(self):       self.push_screen(HelpScreen())
    def action_dashboard(self):  self.push_screen(DashboardScreen())
```

**Por que isso é melhor que tabs:**
- Sem tabs vazias visíveis (problema da v2)
- Contexto preservado (chat fica embaixo do overlay)
- Escape para dismiss (modelo mental natural)
- Menos complexidade de DOM

### Atalhos de teclado

| Tecla | Ação | Frequência |
|-------|------|-----------|
| `Enter` | Enviar input | Alta |
| `Ctrl+S` | Spawn agent | Alta |
| `F2` | Chat overlay | Média |
| `Ctrl+O` | File browser | Média |
| `Ctrl+G` | Git panel | Média |
| `F3` | Dashboard overlay | Baixa |
| `F1` | Help | Baixa |
| `Space` | Pause/resume agent | Média |
| `Ctrl+K` | Kill agent | Baixa |
| `Ctrl+Q` | Quit | — |

---

## Componentes

### 1. Header (`header.py` — resgatar da v2)

```
aiw  ~/project  qwen3:14b  ⚡2 agents  💰$0.005  💾6,049t  12:16
```

Dados reativos: path, model, agent_count, cost_today, cache_tokens, clock

### 2. AgentMonitor (`agent_monitor.py` — NOVO)

```python
class AgentMonitor(Vertical):
    """Barra colapsável. Visível só quando há agentes ativos."""
    
    agents: reactive[list[AgentState]] = reactive([])
    
    def render(self):
        if not self.agents:
            return ""  # colapsado, altura 0
        # Mostra cards compactos dos agentes ativos
        ...
```

Cada card mostra: nome, tipo (ícone), task, step atual, progresso, ações (pause/kill)

### 3. Conversation (`conversation.py` — evoluir do chat.py)

```python
class Conversation(VerticalScroll):
    """Scroll infinito de mensagens e passos de agente."""
    
    messages: reactive[list[Message]] = reactive([])
    
    def add_user_message(self, text): ...
    def add_agent_step(self, step: LoopStep): ...  # 🤔→🔧→👁
    def add_agent_result(self, result): ...
    def add_error(self, error): ...
    def add_system(self, text): ...  # "agent-1 spawned"
```

### 4. HelpBar (`help_bar.py` — evoluir do bottom_bar.py)

```
/search  /code  /files  /git  /model  /help     Enter send  ^Q quit
```

Sempre visível. Context-aware: muda conforme estado (idle vs agent running).

### 5. InputBar (`input_bar.py` — NOVO)

```python
class InputBar(Horizontal):
    """Input + botão send. Suporta /commands e texto livre."""
    
    def on_input_submitted(self, text):
        if text.startswith("/"):
            self.handle_slash_command(text)
        else:
            self.app.spawn_agent(text)  # ou envia pro agente ativo
```

---

## Data Flow

```
AgentLoop.on_step(callback)
  │
  ├─→ AgentMonitor: atualiza card do agente (estado, step, progresso)
  ├─→ Conversation: append step (🤔 Thought → 🔧 Action → 👁 Observation)
  ├─→ Header: atualiza cost, tokens
  └─→ HelpBar: atualiza shortcuts contextuais
  
AgentWorker (thread separada)
  │
  ├─→ AgentLoop.run(task)
  └─→ callback → UI (main thread)
```

Conexão com o AgentLoop (Fase 2 do plano):
```python
class AgentLoop:
    def __init__(self, on_step: Callable):
        self.on_step = on_step  # TUI se inscreve aqui
    
    async def run(self, task):
        for step in self._execute():
            await self.on_step(step)  # TUI recebe cada passo
```

---

## Estados e transições

```
                    ┌─────────┐
                    │  IDLE   │  splash screen, input pronto
                    └────┬────┘
                         │ user types task + Enter
                         ▼
                    ┌─────────┐
                    │ RUNNING │  agent monitor visível, conversation ativa
                    └────┬────┘
                    ┌────┴────┐
                    │         │
                    ▼         ▼
               ┌────────┐ ┌────────┐
               │  DONE  │ │ ERROR  │  resultado ou falha
               └────────┘ └────────┘
                    │         │
                    └────┬────┘
                         ▼
                    ┌─────────┐
                    │  IDLE   │  (monitor colapsa, conversation mantém)
                    └─────────┘
```

---

## Plano de implementação

### Passo 1: Resgatar componentes da v2 (1-2h)
- `header.py` — já existe, adaptar para reactive
- `dashboard.py` — virar overlay (F3), não tela principal
- `agent_grid.py` — lógica de lista de agentes

### Passo 2: Construir novos componentes (2-3h)
- `agent_monitor.py` — barra colapsável
- `conversation.py` — chat + agent steps
- `input_bar.py` — input + slash commands

### Passo 3: Integrar com AgentLoop (Fase 2 do plano)
- Callback `on_step` conecta loop → TUI
- Cada step (Thought → Action → Observation) aparece na conversation

### Passo 4: Overlays (1-2h)
- ChatScreen, FileBrowser, GitPanel, SearchScreen, HelpScreen, DashboardScreen

### Passo 5: Testes e polish (1h)
- Testes de renderização
- CSS validation
- Keyboard navigation test

**Total estimado:** 5-8 horas

---

## O que NÃO incluir (para manter simplicidade)

- ❌ Tabs fixas (anti-pattern da v2)
- ❌ 6 cards de "no data" (anti-pattern)
- ❌ Multi-painel complexo (terminal é pequeno)
- ❌ Canvas/Diagram (v4, desnecessário)
- ❌ Cyberpunk theme (distrai, manter tema profissional)

---

## Referências

- [tui-design skill](./SKILL.md) — princípios e patterns
- [lazygit VISION.md](https://github.com/jesseduffield/lazygit/blob/master/VISION.md) — 7 princípios
- [Posting.sh](https://github.com/darrenburns/posting) — Textual app de referência
- [Textual docs](https://textual.textualize.io/) — API reference
- aiw v2 (`9434c99`) — arquitetura componentizada
- aiw v3 (`27a00ca`) — chat-first, slash commands
