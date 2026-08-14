# aiw TUI Rewrite — Go Bubble Tea Implementation Plan

> **Baseado em:** `Research/aiw-tui-go-rust-planning.md`
> **Cobre:** Substituição completa do TUI v5 (Textual/Python) por um cliente Go (Bubble Tea)
> **Decisões:** Go ✅ | Substituição completa ✅ | Paridade total com v5 ✅

---

## Escopo

**In scope:**
1. Adicionar Go toolchain ao `flake.nix` / `shell.nix`
2. Criar subcomando `aiw tui-server --stdio` no backend Python (IPC sobre stdio)
3. Implementar Bubble Tea TUI completo com paridade de features
4. Remover TUI Python v5 (arquivos `tui/v5/` e `tui/app.py`)
5. Empacotar como `aiw-tui` no Nix

**Out of scope:**
- Alterar o backend agent_loop ou qualquer lógica de negócio
- Migrar o dashboard/CLI Python para Go
- Suporte a múltiplos TUIs simultâneos

---

## Arquitetura

```
┌──────────────────────────────────────────────────┐
│  Terminal                                        │
│  ┌──────────────────────────────────────────┐    │
│  │  aiw-tui (Go / Bubble Tea)               │    │
│  │  - Chat viewport + markdown (glamour)     │    │
│  │  - Input + autocomplete /commands         │    │
│  │  - Dashboard overlay (F3)                 │    │
│  │  - Context inspector (F4)                 │    │
│  │  - Git panel, file browser, sessions      │    │
│  │  - Status bar (model, cost, agent state)  │    │
│  └────────────┬─────────────────────────────┘    │
│               │ stdin/stdout (NDJSON)            │
└───────────────┼──────────────────────────────────┘
                │
┌───────────────┴──────────────────────────────────┐
│  aiw tui-server --stdio (Python)                 │
│  - Lê comandos JSON do stdin                     │
│  - Stream eventos NDJSON no stdout               │
│  - Comandos: chat, kb_search, cost, sessions,    │
│    models, context, dashboard, git, cancel       │
└──────────────────────────────────────────────────┘
```

### Protocolo IPC

```json
// TUI → Backend (stdin)
{"cmd":"chat","task":"explain this code","model":"qwen3:14b","session_id":"abc123"}
{"cmd":"kb_search","query":"database schema"}
{"cmd":"dashboard","section":"cost"}
{"cmd":"sessions","action":"list"}
{"cmd":"models","provider":"ollama"}
{"cmd":"cancel"}
{"cmd":"quit"}

// Backend → TUI (stdout)
{"type":"token","data":{"text":"Let me look..."}}
{"type":"thinking","data":{"text":"Analyzing file structure"}}
{"type":"tool_call","data":{"name":"read_file","args":{"path":"main.go"},"id":"call_1"}}
{"type":"tool_result","data":{"id":"call_1","result":"package main...","duration":0.3}}
{"type":"done","data":{"reason":"completed","tokens":1234,"cost":0.05,"model":"qwen3:14b"}}
{"type":"error","data":{"message":"Model unavailable"}}
{"type":"phase","data":{"phase":"planning"}}
{"type":"status","data":{"running":true,"tokens":500,"cost":0.02,"model":"qwen3:14b"}}
{"type":"result","data":{"value":"..."}}  // For non-streaming commands (dashboard, kb_search)
```

---

## File Map

### Backend (Python) — Modificações no workspace existente

| File | Action | Responsibility |
|------|--------|---------------|
| `src/ai_workspace/cli.py` | **Modify** | Adicionar subcomando `tui-server` com flag `--stdio` |
| `src/ai_workspace/tui/__init__.py` | **Modify** | Simplificar — remover lazy import de v5 |
| `src/ai_workspace/tui/server.py` | **Create** | Servidor IPC: lê stdin, roteia comandos, escreve NDJSON no stdout |
| `shell.nix` | **Modify** | Adicionar `pkgs.go` nos build inputs |
| `flake.nix` | **Modify** | Adicionar Go toolchain e package `aiw-tui` |

### Frontend (Go) — Novo pacote

| File | Action | Responsibility |
|------|--------|---------------|
| `tui/go.mod` | **Create** | Módulo Go: `github.com/daviaaze/aiw-tui` |
| `tui/main.go` | **Create** | Entrypoint: spawn backend, init Bubble Tea app |
| `tui/app.go` | **Create** | Bubble Tea Model principal: composição de sub-modelos |
| `tui/types.go` | **Create** | Tipos compartilhados: Message, Event, Session, etc. |
| `tui/ipc.go` | **Create** | Cliente IPC: spawn processo, ler/escrever NDJSON |
| `tui/chat/chat.go` | **Create** | Modelo de chat: viewport + mensagens + streaming |
| `tui/chat/message.go` | **Create** | Tipos de mensagem: User, Assistant, ToolCall, Error, System |
| `tui/chat/stream.go` | **Create** | Gerenciamento de streaming: buffer + append em tempo real |
| `tui/input/input.go` | **Create** | Input field: textinput bubble + autocomplete /commands |
| `tui/input/commands.go` | **Create** | Definição de slash commands e handlers |
| `tui/dashboard/dashboard.go` | **Create** | Dashboard overlay: stats, health, activity, cost |
| `tui/dashboard/stats.go` | **Create** | Widgets de card de estatística |
| `tui/context/context.go` | **Create** | Context inspector: file tree, tokens, drift detection |
| `tui/sessions/sessions.go` | **Create** | Gerenciamento de sessões: listar, carregar, exportar |
| `tui/git/git.go` | **Create** | Git panel: branch, status, changes |
| `tui/filebrowser/filebrowser.go` | **Create** | File browser: navegação de diretórios |
| `tui/statusbar/statusbar.go` | **Create** | Status bar: model, cost, agent state |
| `tui/theme/theme.go` | **Create** | Tema: cores, estilos Lip Gloss |
| `tui/theme/theme_dark.go` | **Create** | Tema dark (paleta workstation) |
| `Makefile` (raiz) | **Modify** | Adicionar targets `build-tui`, `run-tui`, `test-tui` |

---

## Etapas de Implementação

### Etapa 1: Go Toolchain + Backend IPC (Dia 1)

**1.1** Adicionar Go ao `shell.nix`:
```nix
buildInputs = [ pkgs.go ];
```

**1.2** Criar `src/ai_workspace/tui/server.py` — servidor IPC:
- Lê linhas JSON do `sys.stdin`
- Roteia por `cmd`: `chat`, `kb_search`, `dashboard`, `sessions`, `models`, `cancel`, `quit`
- Para `chat`: executa `agent_loop()` e escreve eventos NDJSON no stdout
- Para outros: executa sync e retorna `{"type": "result", "data": {...}}`
- Mata processo em `quit` ou EOF

**1.3** Adicionar `tui-server` ao CLI em `cli.py`:
```python
@cli.command("tui-server")
@click.option("--stdio", is_flag=True, help="IPC mode over stdin/stdout")
def tui_server(stdio: bool):
    """Start the TUI IPC server for Go frontend."""
    from ai_workspace.tui.server import run_stdio_server
    run_stdio_server()
```

**Verificação:** `echo '{"cmd":"models"}' | python -m ai_workspace tui-server --stdio` retorna JSON.

---

### Etapa 2: Scaffold Go App (Dias 1-2)

**2.1** Criar `tui/go.mod`:
```
module github.com/daviaaze/aiw-tui

go 1.23

require (
    github.com/charmbracelet/bubbletea  v1.3.0
    github.com/charmbracelet/bubbles    v0.20.0
    github.com/charmbracelet/lipgloss   v1.0.0
    github.com/charmbracelet/glamour    v0.8.0
)
```

**2.2** Criar `tui/main.go`:
- Parse flags: `--backend` (caminho do binário python)
- Spawn `aiw tui-server --stdio` como subprocesso
- Inicializar Bubble Tea program
- Defer kill do subprocesso

**2.3** Criar `tui/ipc.go`:
- `type IPCClient struct` com `stdin io.WriteCloser`, `stdout io.ReadCloser`
- `NewIPCClient(backendCmd string) (*IPCClient, error)` — spawn processo
- `Send(cmd Command) error` — escreve JSON + newline no stdin
- `ReadEvent() (*Event, error)` — lê linha do stdout, parseia JSON
- `Close()` — fecha pipes, mata processo

**2.4** Criar `tui/types.go`:
```go
type Command struct {
    Cmd       string `json:"cmd"`
    Task      string `json:"task,omitempty"`
    Model     string `json:"model,omitempty"`
    Query     string `json:"query,omitempty"`    // kb_search
    SessionID string `json:"session_id,omitempty"`
    Section   string `json:"section,omitempty"`  // dashboard
    Action    string `json:"action,omitempty"`   // sessions
    Provider  string `json:"provider,omitempty"` // models
}

type Event struct {
    Type string          `json:"type"`
    Data json.RawMessage `json:"data"`
}
```

**Verificação:** `go run .` abre Bubble Tea vazio, conecta no backend.

---

### Etapa 3: Chat + Streaming (Dias 2-3)

**3.1** Criar `tui/chat/message.go`:
```go
type MessageType int
const (
    MsgUser MessageType = iota
    MsgAssistant
    MsgThinking
    MsgToolCall
    MsgToolResult
    MsgError
    MsgSystem
)

type Message struct {
    Type    MessageType
    Content string
    Step    int
    ToolID  string
    ToolName string
    ToolArgs map[string]any
    Collapsed bool
}
```

**3.2** Criar `tui/chat/chat.go`:
- Model: `messages []Message`, `viewport viewport.Model`, `currentStream *StreamState`
- Init: setup viewport
- Update: handle IPC events (token, thinking, tool_call, tool_result, done, error)
- View: render messages via glamour, viewport wrapping, tool calls como cards colapsáveis

**3.3** Criar `tui/chat/stream.go`:
- `StreamState`: buffer de tokens, accumulated text, flag de finalizado
- `AppendToken(text string)`: append + atualiza última mensagem
- `Finalize()`: marca conclusão, adiciona à lista de mensagens

**3.4** Criar `tui/app.go`:
- Model principal: composição de `chat.Model`, `input.Model`, `ipc.IPCClient`
- Update: roteia `tea.Msg` para sub-modelos
- Eventos IPC chegam como `tea.Msg` custom (via goroutine → `tea.Program.Send()`)

**Verificação:** `aiw tui` abre chat, digita pergunta, vê streaming de tokens com markdown renderizado.

---

### Etapa 4: Input + Comandos (Dias 3-4)

**4.1** Criar `tui/input/input.go`:
- Usar `bubbles/textinput` ou `bubbles/textarea` (multi-linha)
- Autocomplete de /commands
- Submit envia comando IPC ou task de chat

**4.2** Criar `tui/input/commands.go`:
```go
var SlashCommands = map[string]SlashHandler{
    "/help":     {desc: "Show command reference", handler: showHelp},
    "/model":    {desc: "Switch model", handler: switchModel},
    "/clear":    {desc: "Clear conversation", handler: clearConv},
    "/sessions": {desc: "List sessions", handler: showSessions},
    "/export":   {desc: "Export session", handler: exportSession},
    "/cost":     {desc: "Show cost stats", handler: showCost},
    "/git":      {desc: "Show git status", handler: showGit},
    "/ctx":      {desc: "Context inspector", handler: showContext},
    "/dashboard": {desc: "Show dashboard", handler: showDashboard},
    "/quit":     {desc: "Exit", handler: quitApp},
}
```

**Verificação:** `/help` mostra lista de comandos, `/model qwen3:14b` troca modelo, `/clear` limpa conversa.

---

### Etapa 5: Dashboard (Dias 4-5)

**5.1** Criar `tui/dashboard/dashboard.go`:
- ModalScreen ou overlay (tecla F3)
- Envia `{"cmd":"dashboard"}` via IPC
- Renderiza: StatsRow (agentes, tasks, custo, cache, health) + HealthRow (DB, Ollama, MCP, Circuit) + ActivityLog
- Atalhos: `r` refresh, `Esc`/`q` close

**5.2** Criar `tui/dashboard/stats.go`:
- `StatCard` widget: label + valor, cor baseada no status
- Grid de cards 3x2

**Verificação:** F3 abre dashboard com dados reais do backend.

---

### Etapa 6: Context Inspector (Dias 5-6)

**6.1** Criar `tui/context/context.go`:
- ModalScreen (tecla F4 ou `/ctx`)
- Envia `{"cmd":"context","action":"list"}`
- Renderiza: file tree com tokens, status (pinned, excluded, stale, drift)
- Atalhos: `p` pin, `x` exclude, `a` add, `t` sort by tokens, `s` sort by status, `r` refresh

**6.2** Lógica de contexto:
```go
type ContextFile struct {
    Path    string `json:"path"`
    Tokens  int    `json:"tokens"`
    Status  string `json:"status"` // active, pinned, excluded, stale, drift
    Lines   int    `json:"lines"`
}
```

**Verificação:** `/ctx` abre inspetor com arquivos do contexto atual.

---

### Etapa 7: Sessions, Git, File Browser (Dias 6-7)

**7.1** Criar `tui/sessions/sessions.go`:
- ListView com sessões (id, modelo, sumário, data, entry count)
- Load: carrega histórico no chat
- Export: salva texto
- Delete: remove sessão

**7.2** Criar `tui/git/git.go`:
- Envia `{"cmd":"git"}` → recebe branch, status, changes, log
- View: branch atual (destaque), arquivos modified/staged/untracked, últimas N mensagens de commit

**7.3** Criar `tui/filebrowser/filebrowser.go`:
- ListView de diretório atual
- Navegação: enter → entra, backspace → sobe
- Suporta `{"cmd":"filebrowser","path":"..."}`

**Verificação:** `/sessions` lista sessões, `/git` mostra status, file browser navega.

---

### Etapa 8: Status Bar + Temas (Dia 7)

**8.1** Criar `tui/statusbar/statusbar.go`:
- Barra inferior: modelo atual | tokens usados | custo sessão | estado agente (idle/running/cancelled)
- Atualiza a cada `{"type":"status"}` event

**8.2** Criar `tui/theme/theme.go` e `tui/theme/theme_dark.go`:
```go
type Theme struct {
    Primary   lipgloss.Color
    Secondary lipgloss.Color
    Accent    lipgloss.Color
    Warning   lipgloss.Color
    Error     lipgloss.Color
    Success   lipgloss.Color
    BG        lipgloss.Color
    Surface   lipgloss.Color
    Text      lipgloss.Color
    Faint     lipgloss.Color
}

var WorkstationDark = Theme{
    Primary:   lipgloss.Color("#5B8DEE"),
    Surface:   lipgloss.Color("#1D1F2B"),
    BG:        lipgloss.Color("#0F1117"),
    Text:      lipgloss.Color("#A0A5B8"),
    // ... mesma paleta do TUI v5
}
```

**Verificação:** TUI renderiza com tema escuro workstation, igual ao v5.

---

### Etapa 9: Limpeza + Nix Packaging (Dia 8)

**9.1** Remover arquivos mortos do TUI Python:
- `src/ai_workspace/tui/v5/` (13 arquivos, ~2.568 linhas)
- `src/ai_workspace/tui/app.py` (v1 deprecado, ~650 linhas)
- `src/ai_workspace/tui/_graveyard/` (arquivos mortos)
- Manter `tui/__init__.py` simplificado apontando para `server.py`

**9.2** Adicionar `tui-tui` ao `flake.nix`:
```nix
aiw-tui = pkgs.buildGoModule {
    pname = "aiw-tui";
    version = "0.1.0";
    src = ./tui;
    vendorHash = "sha256-...";
    subPackages = ["."];
};
```

**9.3** Atualizar `Makefile`:
```makefile
.PHONY: build-tui run-tui

build-tui:
	cd tui && go build -o ../dist/aiw-tui .

run-tui:
	cd tui && go run .

test-tui:
	cd tui && go test ./...
```

**9.4** Atualizar `shell.nix` para incluir Go toolchain + `aiw-tui`.

---

### Etapa 10: Self-Review + Testes (Dia 8-9)

**Checklist de verificação:**
- [ ] Chat streaming com markdown (glamour)
- [ ] Tool calls colapsáveis (expand/reduce)
- [ ] Suporte a múltiplas mensagens simultâneas
- [ ] Autocomplete de /commands
- [ ] Slash commands: /help, /clear, /model, /sessions, /export, /cost, /git, /ctx, /dashboard, /quit
- [ ] Dashboard (F3) com stats reais
- [ ] Context inspector (F4) com file tree
- [ ] Sessions: list, load, export, delete
- [ ] Git panel: branch, status, changes
- [ ] File browser: navegação
- [ ] Status bar: modelo, custo, estado
- [ ] Ctrl+C cancelamento de agente
- [ ] Tema escuro workstation
- [ ] Testes Go: pelo menos IPC e message types
- [ ] Testes Python: `tui-server` subcomando

---

## Dependências

| Dependência | Versão | Finalidade |
|---|---|---|
| `github.com/charmbracelet/bubbletea` | v1.3+ | Framework TUI (Elm architecture) |
| `github.com/charmbracelet/bubbles` | v0.20+ | Componentes: textinput, viewport, spinner, table, list, help |
| `github.com/charmbracelet/lipgloss` | v1.0+ | Estilização inline de cores/bordas |
| `github.com/charmbracelet/glamour` | v0.8+ | Renderização de markdown → ANSI |

Sem dependências CGO — build completamente estático.

---

## Resumo

| Etapa | Esforço | Artefato Principal | Depende de |
|-------|---------|--------------------|------------|
| 1. Backend IPC | ~100 linhas | `tui/server.py` + `cli.py` modificação | Nenhuma |
| 2. Go scaffold | ~150 linhas | `main.go`, `ipc.go`, `types.go` | Etapa 1 |
| 3. Chat + streaming | ~400 linhas | `chat/*.go` | Etapa 2 |
| 4. Input + comandos | ~200 linhas | `input/*.go` | Etapa 3 |
| 5. Dashboard | ~250 linhas | `dashboard/*.go` | Etapa 2 |
| 6. Context inspector | ~250 linhas | `context/*.go` | Etapa 2 |
| 7. Sessions, Git, Browser | ~300 linhas | `sessions/*.go`, `git/*.go`, `filebrowser/*.go` | Etapa 2 |
| 8. Status bar + temas | ~100 linhas | `statusbar/*.go`, `theme/*.go` | Etapa 3 |
| 9. Limpeza + Nix | ~50 linhas | `flake.nix`, `Makefile`, remoção v5 | Todas |
| 10. Review + testes | ~200 linhas | Testes Go + Python | Todas |

**Total estimado:** ~2.000 linhas (Go) + ~200 linhas (Python) + ~50 linhas (Nix)

---

## Plano de Execução

**Fase A (Etapas 1-3):** MVP funcional — chat streaming com markdown funcionando
**Fase B (Etapas 4-6):** Comandos + ferramentas — dashboard, context, input completo
**Fase C (Etapas 7-8):** Polimento — sessions, git, filebrowser, status bar, temas
**Fase D (Etapas 9-10):** Entrega — limpeza, packaging, testes, review final