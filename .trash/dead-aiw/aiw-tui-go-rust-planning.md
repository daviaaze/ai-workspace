# aiw TUI — Go vs Rust: Planejamento de Arquitetura

> **Data:** 2026-07-03
> **Contexto:** Substituir o TUI atual (Textual/Python, ~2.500 linhas em v5) por um cliente nativo em Go (Bubble Tea) ou Rust (Ratatui), comunicando com o backend Python via IPC.

---

## Sumário Executivo

O TUI v5 atual tem **13 módulos, ~2.568 linhas**, e se comunica com o backend Python **in-process** (chamadas diretas a `agent_loop`, `CostService`, `KnowledgeStore`, `ContextManager`, etc.). Para migrar para Go ou Rust, o TUI precisa se tornar um **processo separado** que conversa com o backend via um protocolo IPC.

A escolha entre Go e Rust depende do **trade-off entre velocidade de desenvolvimento e performance bruta**.

---

## 1. O TUI Atual — O Que Ele Faz

### Features atuais (v5)

| Feature | Implementação | Complexidade |
|---|---|---|
| **Chat/Agent conversation** | `Conversation` widget com 6 subtipos de mensagem: User, AgentThought, ToolCall, AgentResponse, AgentError, SystemMessage | Alta — streaming, colapsar tool calls, estados |
| **Autocomplete** | `Autocomplete` widget overlay com filtro para slash commands e modelos | Média |
| **Agent loop streaming** | `agent_loop()` via async generator → eventos: `token`, `thinking`, `tool_call`, `tool_result`, `done`, `error`, `phase` | Alta — 7 tipos de evento com dados diferentes |
| **Slash commands** | `/help`, `/clear`, `/sessions`, `/model`, `/ctx`, `/git`, `/dashboard`, `/quit`, `/cost` | Média — 9 comandos |
| **Model selector** | `ModelSelect` ModalScreen — lista modelos Ollama + permite troca | Baixa |
| **Chat history** | `ChatScreen` — sessões anteriores | Baixa |
| **Dashboard** | `DashboardScreen` — stats, tools, knowledge, cost, health | Alta — 6 painéis de dados |
| **Context inspector** | `ContextInspector` — contexto por camadas L0/L1/L2 | Média |
| **Git panel** | `GitPanel` — branch atual, status | Baixa |
| **File browser** | `FileBrowser` — navegação de arquivos | Baixa |
| **Agent monitor** | `AgentMonitor` — health checks dos servidores | Baixa |
| **Status bar** | Modelo atual + custo (tokens) + estado do agente | Baixa |
| **Cost tracking** | Exibição de custo por sessão | Baixa |

### Protocolo de eventos do `agent_loop`

```python
async for event in agent_loop(params):
    # event.type in:
    #   "token"       → data: {"text": str}
    #   "thinking"    → data: {"text": str}
    #   "tool_call"   → data: {"name": str, "args": dict, "id": str}
    #   "tool_result" → data: {"id": str, "result": str, "duration": float}
    #   "done"        → data: {"reason": str, "tokens": int, "cost": float}
    #   "error"       → data: {"message": str, "traceback": str}
    #   "phase"       → data: {"phase": str, ...}
```

---

## 2. Arquitetura Proposta — TUI como Cliente Separado

```
┌─────────────────────────────────────┐
│  Terminal (usuário vê o TUI)        │
└──────────┬──────────────────────────┘
           │ stdin/stdout ou unix socket
           │ (JSON-Lines — NDJSON)
           ▼
┌─────────────────────────────────────┐
│  TUI Client (Go/Rust)               │
│  - Bubble Tea / Ratatui             │
│  - Renderização, input handling     │
│  - Cache de sessão local            │
└──────────┬──────────────────────────┘
           │ IPC: JSON-Lines sobre stdio
           │ ou Unix socket
           ▼
┌─────────────────────────────────────┐
│  aiw Backend (Python)               │
│  - agent_loop()                     │
│  - KnowledgeStore                   │
│  - CostService                      │
│  - MCP tools                        │
│  - ContextManager                   │
└─────────────────────────────────────┘
```

### IPC: CLI Gateway Existente

O `aiw` já tem um CLI de ~3.855 linhas. O backend pode expor um **subcomando `aiw tui-server`** que:
1. Abre um Unix socket ou usa stdin/stdout
2. Escuta comandos JSON
3. Retorna eventos NDJSON (Newline-Delimited JSON)

```json
// Comando do TUI → Backend
{"cmd": "chat", "task": "find the bug in parser.py", "model": "qwen3:14b"}
{"cmd": "kb_search", "query": "database schema"}
{"cmd": "cost_status", "session_id": "abc123"}
{"cmd": "list_models", "provider": "ollama"}
{"cmd": "dashboard_stats"}

// Resposta do Backend → TUI (streaming)
{"type": "token", "data": {"text": "Let me look at parser.py..."}}
{"type": "thinking", "data": {"text": "Examining file structure"}}
{"type": "tool_call", "data": {"name": "read_file", "args": {"path": "parser.py"}}}
{"type": "tool_result", "data": {"id": "call_1", "result": "..."}}
{"type": "done", "data": {"reason": "completed", "tokens": 1234, "cost": 0.05}}
{"type": "error", "data": {"message": "..."}}
```

### Por que stdio?

- **Zero dependência de rede** — funciona offline, sem portas, sem auth
- **Pipe-friendly** — `aiw tui-server | aiw-tui` (separação de concerns)
- **Simples de debugar** — `aiw tui-server --log /tmp/ipc.log`
- **Mesmo padrão do** Claude Code, pi, e outros agentes

---

## 3. Comparação: Go (Bubble Tea) vs Rust (Ratatui)

### Bubble Tea (Go)

| Aspecto | Nota |
|---|---|
| **Framework** | [charmbracelet/bubbletea](https://github.com/charmbracelet/bubbletea) — Elm architecture (Model-Update-View) |
| **Componentes prontos** | [Bubbles](https://github.com/charmbracelet/bubbles): spinner, text input, viewport, table, list, progress bar, pagination, help, filepicker, stopwatch, timer |
| **Estilo** | [Lip Gloss](https://github.com/charmbracelet/lipgloss) — CSS-like styling inline |
| **Performance** | Excelente para TUIs de chat/dashboard (centenas de eventos/segundo) |
| **Binário** | ~8-15 MB, single binary, sem runtime |
| **Curva de aprendizado** | Baixa — Elm model é intuitivo. Go é simples. |
| **Ecossistema** | Maturidade alta. Usado por: Charm Cloud, Glow, VHS,诸多 ferramentas CLI |
| **Comunidade** | Ativa. Charm Labs mantém. |
| **Build time** | Segundos |
| **Cross-compile** | `GOOS=linux GOARCH=amd64 go build` — trivial |
| **JSON/stdin parsing** | `encoding/json` + `bufio.Scanner` — nativo, sem dependências |

**Exemplo mental** (chat message render):

```go
type Model struct {
    messages []Message
    textInput textinput.Model
    viewport viewport.Model
    loading  bool
    err      error
}

func (m Model) View() string {
    return lipgloss.JoinVertical(
        lipgloss.Top,
        m.viewport.View(),
        m.textInput.View(),
    )
}
```

### Ratatui (Rust)

| Aspecto | Nota |
|---|---|
| **Framework** | [ratatui](https://github.com/ratatui-org/ratatui) — sucessor do tui-rs. Immediate mode, layout declarativo |
| **Componentes prontos** | Paragraph, Table, List, Tabs, Gauge, Sparkline, Chart, Block, Scrollbar, LineGauge |
| **Estilo** | `style::Style` + palettes — programático, sem CSS |
| **Performance** | Máxima — zero-copy rendering, buffer diffing, subsistema de terminal mais rápido |
| **Binário** | ~3-6 MB, single binary, sem runtime |
| **Curva de aprendizado** | Alta — Rust ownership, lifetimes, `Result`/`?` handling |
| **Ecossistema** | Maduro, mas menos componentes de alto nível que Bubble Tea |
| **Comunidade** | Ativa, mas menor que Bubble Tea |
| **Build time** | Minutos (compilação Rust) |
| **Cross-compile** | Precisa de toolchain cross — mais complexo |
| **JSON/stdin parsing** | `serde_json` + `serde` — excelente, mas com `derive(Deserialize)` (mais código boilerplate) |

**Exemplo mental** (chat message render):

```rust
fn render(frame: &mut Frame, area: Rect, messages: &[Message]) {
    let lines: Vec<Line> = messages.iter().map(|m| {
        Line::from(Span::styled(
            &m.text,
            Style::default().fg(Color::Cyan),
        ))
    }).collect();
    frame.render_widget(Paragraph::new(lines), area);
}
```

### Comparação Direta

| Critério | Go (Bubble Tea) | Rust (Ratatui) |
|---|---|---|
| **Velocidade de desenvolvimento** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Performance de render** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Componentes prontos** | ⭐⭐⭐⭐⭐ (Bubbles) | ⭐⭐⭐ |
| **Input handling** | ⭐⭐⭐⭐⭐ (textinput nativo) | ⭐⭐⭐ (precisa custom) |
| **Markdown rendering** | ⭐⭐⭐ (glamour ou custom) | ⭐⭐⭐ (termimad ou custom) |
| **Tamanho do binário** | ~10 MB | ~4 MB |
| **Tempo de compilação** | 2-5s | 30s-2min |
| **Curva de aprendizado** | Baixa | Alta |
| **Debug/prototipagem** | Rápida (iteração segundos) | Lenta (iteração minutos) |
| **Maturidade ecosistema** | Muito alta (Charm Labs) | Alta |
| **Tooling já instalado?** | ❌ (não tem go no nix) | ❌ (não tem rust no nix) |
| **Referências relevantes** | Glow (terminal markdown), Charm Cloud | bottom (tui monitor), zellij |

---

## 4. Riscos Específicos

### Risco 1: Markdown Rendering

O TUI precisa renderizar markdown formatado (código inline, blocos de código, links, listas). É o componente mais crítico para um **chat agent**.

| Solução | Bubble Tea | Ratatui |
|---|---|---|
| **Nativa** | [glamour](https://github.com/charmbracelet/glamour) — render markdown para ANSI. Mantido pela Charm. Excelente. | [termimad](https://github.com/Canop/termimad) — template markdown para terminal. Mantido pelo autor do broot/bacon. |
| **Custom** | Simples — glamour já faz tudo | Possível, mas mais trabalho |
| **Qualidade** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

### Risco 2: IPC / Stdio Bidirecional

O backend Python precisa falar **para** o TUI (streaming de eventos) e o TUI precisa falar **para** o backend (comandos). Isso é bidirecional sobre o mesmo pipe.

| Bubble Tea | Ratatui |
|---|---|
| `os.Stdin` + `bufio.Scanner` lê linhas. Go rotina separada `go reader()` que envia `tea.Cmd` para o loop. Padrão bem documentado. | `std::io::BufReader` + `serde_json::Deserializer`. Precisa de thread separada + `mpsc::channel` para o loop de eventos. |

### Risco 3: Session State / Persistência

O TUI atual carrega/ salva sessões via Python (`tui_sessions`). No modelo cliente separado, o TUI precisaria:

1. **Opção A** (recomendada): Backend mantém sessões — TUI só exibe
2. **Opção B**: TUI cacheia localmente em JSON (~/.cache/aiw-tui/sessions.json)

Opção A é mais simples — o TUI envia `{"cmd": "list_sessions"}` e recebe a lista.

### Risco 4: Nix Integration

Nem Go nem Rust estão no `flake.nix` ou `shell.nix` atuais. Seria necessário:

```nix
# Para Go
buildInputs = [ pkgs.go ];

# Para Rust
nativeBuildInputs = [ pkgs.rustc pkgs.cargo ];
```

E adicionar um package separado para o TUI binário:

```nix
aiw-tui = pkgs.buildGoModule { ... };  # ou buildRustPackage { ... }
```

Ou, mais modular: o TUI vira um **repositório separado** (`aiw-tui`) com sua própria flake.

---

## 5. Recomendação

### 🏆 Go (Bubble Tea) — Recomendado

**Motivos:**

1. **Bubbles** tem componentes de alto nível que cobrem 80% do que o TUI atual faz: `textinput` (input com autocomplete), `viewport` (scroll de conversa), `spinner` (loading state), `table` (dashboard stats), `list` (model selector, file browser), `help` (help screen). O TUI v5 atual levou **semanas** para implementar essas coisas manualmente no Textual — com Bubbles sai em **dias**.

2. **Glamour** resolve markdown rendering perfeitamente — é o mesmo motor que o Glow (terminal markdown reader) usa. Para um chat agent, markdown bem renderizado é essencial.

3. **Velocidade de desenvolvimento** é o fator decisivo: Go é simples, compila em segundos, e o loop Model-Update-View do Bubble Tea é instintivo para qualquer pessoa que já escreveu um event loop.

4. **Binário único** de ~10MB que pode ser distribuído como `nix run github:daviaaze/aiw-tui`.

5. **IPC sobre stdio** é trivial em Go — uma goroutine lê stdin, outra escreve stdout, o modelo Bubble Tea recebe mensagens via `tea.Cmd`.

**O trade-off que você aceita:** Performance de render ligeiramente inferior ao Rust em cenários de ~10k+ eventos/segundo (que não é o caso de um chat agent).

### Quando Rust (Ratatui) faria sentido

- Se o TUI precisasse processar **streaming de alta frequência** (logs em tempo real, monitoramento de sistema)
- Se o binário mínimo fosse requisito (Rust faz ~4MB vs Go ~10MB)
- Se você já soubesse Rust (curva de aprendizado é real)

---

## 6. Plano de Implementação Sugerido

### Fase 1 — Prova de Conceito (1-3 dias)

```
Goal: "aiw-tui" binary que conecta no backend e mostra chat ao vivo
```

- [ ] Criar repositório `aiw-tui` (ou módulo no workspace)
- [ ] Adicionar Go toolchain ao flake.nix
- [ ] Implementar Bubble Tea app mínimo:
  - Viewport + textinput + spinner
  - IPC sobre stdio: `go run .` executa `aiw tui-server` como subprocesso
  - Ler eventos NDJSON do stdout do backend
  - Renderizar tokens em tempo real
- [ ] Adicionar `aiw tui-server` subcomando no backend Python
  - Aceitar task via stdin JSON
  - Stream eventos NDJSON via stdout
  - Suportar: chat, list_models, cancel

### Fase 2 — Paridade de Features (1 semana)

- [ ] Slash commands (/help, /clear, /model, /ctx, /dashboard)
- [ ] Chat history (session save/load)
- [ ] Model selector (lista + seleção)
- [ ] Dashboard (cost, tools, knowledge stats)
- [ ] Context inspector
- [ ] Cancelamento de agente (Ctrl+C)

### Fase 3 — Polimento (contínuo)

- [ ] Markdown rendering com glamour
- [ ] Tool call cards colapsáveis
- [ ] Syntax highlight em blocos de código
- [ ] Temas (dark/light)
- [ ] Nix package + flake
- [ ] Testes

---

## 7. Decisões Tomadas

| Decisão | Escolha |
|---|---|
| **Linguagem** | Go — Bubble Tea ✅ |
| **Estratégia** | Substituir completamente o TUI v5 Python ✅ |
| **Escopo MVP** | Paridade total com v5 ✅ |

## 8. Próximos Passos Imediatos

1. ✅ **Decidido**: Go (Bubble Tea)
2. **Setup**: Adicionar Go toolchain ao `flake.nix` / `shell.nix`
3. **Backend**: Criar `aiw tui-server --stdio` no CLI Python
4. **Frontend**: Escrever o Bubble Tea app completo com paridade de features
5. **Testar**: Sessão de chat completa, dashboard, context inspector

---

## Apêndice: Dependências Go

```go
// go.mod
module github.com/daviaaze/aiw-tui

go 1.23

require (
    github.com/charmbracelet/bubbletea  v1.3.0
    github.com/charmbracelet/bubbles    v0.20.0
    github.com/charmbracelet/lipgloss   v1.0.0
    github.com/charmbracelet/glamour    v0.8.0   // markdown rendering
)
```

~200KB de dependências totais. Bubble Tea e Bubbles são módulos puramente Go (zero CGO).