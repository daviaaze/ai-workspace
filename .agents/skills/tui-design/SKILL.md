---
name: tui-design
description: >-
  Design and implement Textual TUI interfaces for terminal applications.
  Use when building terminal dashboards, agent interfaces, chat UIs,
  or any terminal-based user interface with Python's Textual framework.
  Covers Textual's API (App, Widgets, CSS, Screens, Actions, Workers, Testing)
  with patterns verified against official documentation.
compatibility: Python >= 3.9, Textual (latest), pytest-asyncio for testing
metadata:
  framework: textual
  language: python
  principles: discoverability, simplicity, safety, keyboard-first, reactive
---

# TUI Design — Textual Terminal Interfaces (verified against official docs)

Guia prático para construir interfaces de terminal com Textual.
Baseado na documentação oficial em https://textual.textualize.io/
e nos fontes dos apps Textual de produção (posting, frogmouth, elia).

---

## 1. App Basics — Estrutura Mínima

```python
from textual.app import App, ComposeResult
from textual.widgets import Static, Button

class MyApp(App):
    """App minimal: compose + run."""

    def compose(self) -> ComposeResult:
        yield Static("Hello, World!")
        yield Button("OK", id="ok", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Convenção: on_{widget}_{event} ou @on(Button.Pressed)."""
        self.exit(event.button.id)  # retorna str pro caller

if __name__ == "__main__":
    app = MyApp()
    reply = app.run()
    print(f"Returned: {reply}")
```

### Ciclo de vida

| Método | Quando |
|--------|--------|
| `compose()` | Montagem inicial dos widgets |
| `on_mount()` | Após compose, antes do primeiro render |
| `on_ready()` | Após primeiro render completo |
| `on_key` / `on_click` / handlers | Em resposta a eventos |
| `app.exit([return_code=0])` | Sai do modo aplicação |

### App.run() params relevantes

```python
app.run(inline=True)       # sem entrar em modo aplicação (>= 0.55.0)
app.run(headless=True)     # sem terminal (útil para testes)
```

---

## 2. Composição com Widgets

### Widgets Built-in (widget gallery oficial)

| Widget | Uso |
|--------|-----|
| `Static` | Texto estático / base para custom widgets |
| `Button` | Botão clicável (variants: primary, error, success, warning) |
| `Input` | Campo de texto |
| `TextArea` | Editor multi-linha com syntax highlight |
| `DataTable` | Tabela com cursor navegável |
| `ListView` / `ListItem` | Lista vertical navegável |
| `Tree` | Árvore expansível |
| `DirectoryTree` | Árvore de diretórios (fs real) |
| `RichLog` | Log scrollável com Rich renderables |
| `Markdown` / `MarkdownViewer` | Renderização de markdown |
| `Digits` | Números grandes estilo relógio |
| `Header` / `Footer` | Barra superior / inferior |
| `Tabs` / `TabbedContent` | Abas (usar com cautela) |
| `ProgressBar` | Barra de progresso com ETA |
| `LoadingIndicator` | Spinner de carregamento |
| `Sparkline` | Gráfico temporal simples |
| `ContentSwitcher` | Alterna visibilidade entre filhos |
| `Collapsible` | Seção expansível |
| `Select` / `SelectionList` / `RadioSet` | Seletores |
| `Placeholder` | Placeholder de design |
| `OptionList` | Lista de opções (Rich renderables) |

### Containers

```python
from textual.containers import Container, Horizontal, Vertical, VerticalScroll, Grid

# Compose aninhado:
def compose(self) -> ComposeResult:
    with Horizontal():
        yield Button("A")
        yield Button("B")
    with VerticalScroll(id="main"):
        yield Static("linha 1")
        yield Static("linha 2")
```

### Border Titles

```python
class MyWidget(Static):
    BORDER_TITLE = "Widget Title"  # título default
    def on_mount(self):
        self.border_subtitle = "Clique para mais"  # dinâmico
```

Requer `border: ... ;` no CSS para aparecer.

---

## 3. CSS no Textual

### Onde definir

```python
# 1) Arquivo .tcss externo (recomendado — permite live edit)
class MyApp(App):
    CSS_PATH = "app.tcss"           # arquivo único
    CSS_PATH = ["base.tcss"]        # ou lista de arquivos

# 2) CSS inline na classe
class MyApp(App):
    CSS = """
    Screen { align: center middle; }
    Button { width: 100%; }
    """

# 3) DEFAULT_CSS no widget (scoped por default)
class MyWidget(Static):
    DEFAULT_CSS = """
    MyWidget {
        border: solid $accent;
        padding: 1 2;
    }
    """
```

### Seletores

```css
/* Type selector — classe Python do widget (inclui ancestrais) */
Button { background: blue; }

/* ID selector — #id */
#dialog { border: thick $primary; }

/* Class selector — .class-name */
.success { background: green; }
.error.disabled { background: darkred; }  /* chained */

/* Universal */
* { outline: solid red; }

/* Pseudo-classes */
Button:hover { background: lightblue; }
Button:focus { border: wide $accent; }
ListView > ListItem:even { background: $boost; }

/* Child selector */
Screen > Static { width: 70; }
```

### Cores válidas

```css
/* System colors (ANSI) — sempre disponíveis */
$primary, $secondary, $accent, $error, $warning, $success
$background, $surface, $panel, $boost
$text, $text-disabled   /* ✅ existem sim no Textual! */

/* Opacity modifiers (CSS apenas) */
$text 40%
$primary 20%

/* Cores explícitas */
#888888
rgb(128, 128, 128)
rgba(255, 0, 0, 0.5)
```

### Em Python (`styles.`)

```python
# ✅ Válido
widget.styles.background = "#888888"
widget.styles.color = "rgb(128,128,128)"
widget.styles.border = ("solid", "blue")  # tuple (style, color)
widget.styles.width = "1fr"

# ❌ INVÁLIDO — opacity modifiers não funcionam em Python
# widget.styles.color = "$text 40%"
```

### Templates úteis

```css
/* App com header/footer docked */
Header { dock: top; height: 3; }
Footer { dock: bottom; height: 1; }
Screen { layout: grid; grid-size: 1; }

/* Centralizar */
Screen { align: center middle; }

/* Scrollbar */
#scroll-area { overflow: auto; height: 1fr; }

/* Grid */
#dialog {
    grid-size: 2;
    grid-gutter: 1 2;
    grid-rows: 1fr 3;
}
```

---

## 4. Eventos e Input

### Handlers de tecla

```python
# Método específico (conveniência)
def key_space(self) -> None:
    self.bell()

# Handler genérico
def on_key(self, event: events.Key) -> None:
    if event.key == "enter":
        self.action_submit()

# Atributos do evento Key
event.key          # "ctrl+p", "shift+home", "space"
event.character    # caractere Unicode ou None
event.name         # "ctrl_p", "upper_p" — seguro pra nomes de método
event.is_printable # bool
event.aliases      # ["tab", "ctrl+i"]
```

### Input Focus

```python
# Navegação: Tab / Shift+Tab
# CSS pseudo-seletor
Widget:focus { border: wide $accent; }
Widget:focus-within { border: solid $secondary; }

# Foco programático
widget.focus()
```

---

## 5. Actions — O Sistema de Comandos

### Action methods (prefixo `action_`)

```python
class MyApp(App):
    def action_set_background(self, color: str) -> None:
        self.screen.styles.background = color

    # Chamada via string
    # "set_background('red')"
```

### Bindings (BINDINGS class variable)

```python
class MyApp(App):
    BINDINGS = [
        ("r", "set_background('red')", "Red"),
        ("g,t", "set_background('green')", "Green"),  # multi-key
        ("b", "set_background('blue')", "Blue"),
    ]

    def action_set_background(self, color: str) -> None:
        self.screen.styles.background = color
```

### Binding com mais opções

```python
from textual.binding import Binding

BINDINGS = [
    Binding("ctrl+q", "quit", "Quit", show=False, priority=True),
    Binding("ctrl+s", "save", "Save", show=True),
]
```

### Dynamic actions (check_action)

```python
def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
    """Retorna True (ativo), False (escondido), None (desabilitado)."""
    if action == "go_prev" and self.page == 0:
        return False  # esconde o binding
    return True
```

### Namespaces

```python
"app.set_background('red')"      # action no App
"screen.set_background('red')"   # action no Screen
"focused.set_background('red')"  # action no widget focado
```

### Links em markup

```python
TEXT = """
Click here: [@click=app.bell]Bell[/]
Or here: [@click=set_background('red')]Red[/]
"""
```

---

## 6. Reatividade com reactive / var

### reactive (watcher automático)

```python
from textual.reactive import reactive

class StatusWidget(Static):
    data: reactive[list[str]] = reactive([])

    def watch_data(self, old: list[str], new: list[str]) -> None:
        """Chamado automaticamente quando data muda."""
        self.update("\n".join(new))

    def add_item(self, item: str) -> None:
        self.data = [*self.data, item]  # trigger automático
```

### var (reactive sem watcher, pra computação)

```python
from textual.reactive import var

class CalculatorApp(App):
    numbers = var("0")
    value = var("")

    def watch_numbers(self, value: str) -> None:
        """Watcher com nome watch_{var_name}."""
        self.query_one("#display", Digits).update(value)

    def compute_show_ac(self) -> bool:
        """compute_{var_name} — computa valor derivado."""
        return self.value in ("", "0") and self.numbers == "0"

    show_ac = var(default=False, compute="compute_show_ac")
```

### Mutate para objetos mutáveis

```python
from textual.reactive import mutate

class ListWidget(Static):
    items: reactive[list[str]] = reactive([])

    def add(self, item: str):
        with mutate(self.items):
            self.items.append(item)
```

---

## 7. Screens e Navegação

### Screen Stack

```python
from textual.screen import Screen

# App define screens nomeadas
class MyApp(App):
    SCREENS = {
        "home": HomeScreen,
        "settings": SettingsScreen,
        "help": HelpScreen,
    }

    BINDINGS = [
        ("h", "push_screen('help')", "Help"),
        ("escape", "pop_screen", "Back"),
    ]

# Actions de navegação
self.push_screen("help")          # empilha (nome)
self.push_screen(HelpScreen())    # empilha (objeto)
self.pop_screen()                 # desempilha
self.switch_screen("settings")    # substitui o topo
self.dismiss()                    # pop + retorna valor pro caller
```

### ModalScreen (diálogo modal)

```python
from textual.screen import ModalScreen

class QuitDialog(ModalScreen[bool]):
    """Modal que retorna True ou False."""

    def compose(self) -> ComposeResult:
        with Grid(id="dialog"):
            yield Label("Quit?")
            yield Button("Yes", id="yes", variant="error")
            yield Button("Cancel", id="cancel", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

# Uso:
self.push_screen(QuitDialog(), callback=self.on_quit_result)

def on_quit_result(self, result: bool) -> None:
    if result:
        self.exit()
```

### Screen opacity

```python
class MyScreen(Screen):
    CSS = """
    MyScreen {
        background: rgba(0, 0, 0, 0.5);  /* vê a tela de baixo */
    }
    """
```

### Instalação dinâmica

```python
self.install_screen(HelpScreen(), name="help")
self.uninstall_screen("help")
```

---

## 8. Workers — Concorrência

### Problema: chamada bloqueante na UI

```python
# ❌ RUIM — trava a UI até a resposta
async def on_input_changed(self, message: Input.Changed) -> None:
    response = await httpx.AsyncClient().get(f"https://api/{message.value}")
    self.query_one("#output").update(response.text)
```

### Solução 1: run_worker

```python
# ✅ BOM — não trava
async def on_input_changed(self, message: Input.Changed) -> None:
    self.run_worker(
        self.update_weather(message.value),
        exclusive=True,  # cancela workers anteriores
    )

async def update_weather(self, city: str) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://wttr.in/{city}")
        self.query_one("#weather", Static).update(response.text)
```

### Solução 2: @work decorator

```python
from textual import work

@work(exclusive=True)
async def update_weather(self, city: str) -> None:
    """@work faz com que chamar o método NÃO precise de await."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"https://wttr.in/{city}")
        self.query_one("#weather", Static).update(response.text)

# Uso — sem await! o decorator já cria o worker
self.update_weather(message.value)
```

### Opções do worker

```python
@work(
    exclusive=True,      # cancela workers anteriores com mesmo método
    group="api",         # agrupa workers pra cancelar em lote
    exit_on_error=False, # não derruba o app se o worker falhar
    thread=False,        # True = thread separada (não async)
)
```

### Worker Thread (CPU-bound)

```python
@work(thread=True)
def heavy_compute(self, data: list[int]) -> None:
    result = cpu_intensive(data)
    self.call_from_thread(self.update_ui, result)

def update_ui(self, result: int) -> None:
    self.query_one("#output").update(str(result))
```

### Worker return values

```python
worker = self.run_worker(self.my_task())
await worker.wait()
result = worker.result  # valor retornado pela task
```

---

## 9. Sistema de Eventos (Decorator @on)

### Padrão recomendado: `@on`

```python
from textual import on

class MyApp(App):
    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Button("Red", id="red")
            yield Button("Green", id="green")

    @on(Button.Pressed, "#red")
    def handle_red(self, event: Button.Pressed) -> None:
        self.screen.styles.background = "red"

    @on(Button.Pressed, "#green")
    def handle_green(self, event: Button.Pressed) -> None:
        self.screen.styles.background = "green"

    # Sem CSS selector — pega todos os Button.Pressed
    @on(Button.Pressed)
    def any_button(self, event: Button.Pressed) -> None:
        self.log(f"Button {event.button.id} pressed")
```

### Convenção `on_{widget}_{event}` (alternativa)

```python
class MyApp(App):
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Textual chama automaticamente."""
        if event.button.id == "quit":
            self.exit()
```

---

## 10. CSS Classes Dinâmicas

```python
widget.add_class("active")          # adiciona classe CSS
widget.remove_class("active")       # remove
widget.toggle_class("active")       # alterna
widget.set_class(condition, "on")   # True = add, False = remove
widget.has_class("active")          # bool
```

Útil pra estados visuais:

```css
Card { background: $surface; }
Card.active { background: $primary; color: $text; }
```

---

## 11. Testing com Pilot

### Setup

```
pip install pytest pytest-asyncio
```

No `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Teste básico

`app.run_test()` roda o app em modo **headless** (sem terminal real).
Retorna um `Pilot` que simula interações do usuário.

```python
import pytest
from myapp import MyApp

@pytest.mark.asyncio
async def test_keys():
    app = MyApp()
    async with app.run_test(size=(80, 24)) as pilot:
        # Simular tecla
        await pilot.press("r")
        assert app.screen.styles.background.hex == "#ff0000"

        # Simular clique em widget pelo seletor CSS
        await pilot.click("#red")
        assert app.screen.styles.background.hex == "#ff0000"
```

### Pilot.press — teclas

```python
await pilot.press("r", "g", "b")        # teclas em sequência
await pilot.press("ctrl+q")              # combinação com Ctrl
await pilot.press("h", "e", "l", "l", "o")  # digitar "hello"
```

### Pilot.click — clique

```python
await pilot.click("#my-button")          # por seletor CSS
await pilot.click(Button)                # por tipo de widget
await pilot.click()                      # clica na tela em (0, 0)
```

Com **offset** (relativo ao widget ou tela):
```python
await pilot.click(offset=(10, 5))        # clica em (10, 5) na tela
await pilot.click(Button, offset=(0, -1))  # clica 1 linha acima do Button
```

Double/triple click:
```python
await pilot.click(Button, times=2)       # double click
await pilot.click("#slider", times=3)    # triple click
```

Com modifier keys:
```python
await pilot.click("#slider", control=True)  # ctrl+click
await pilot.click("#item", shift=True)      # shift+click
```

### Pilot.pause — esperar UI processar

```python
await pilot.pause(0.3)   # espera 0.3s + processa mensagens pendentes
await pilot.pause()      # só processa mensagens, sem delay adicional
```

### size — simular terminal diferente

```python
async with app.run_test(size=(100, 50)) as pilot:
    ...
```

### Snapshot testing (visual)

O pacote `pytest-textual-snapshot` gera SVGs da tela do app pra
comparar visualmente entre versões.

```
pip install pytest-textual-snapshot
```

```python
# Em tests/conftest.py
def pytest_collection_modifyitems(items):
    from pytest_textual_snapshot import plugin
    plugin.pytest_collection_modifyitems(items)
```

### Padrão: testar lógica sem UI + UI com Pilot

```python
# test_lógica.py — sem app rodando, rápido
def test_conversation_entry_render():
    entry = ConversationEntry(role="user", content="Hello")
    assert "You:" in entry.render()

# test_ui.py — com app headless, mais lento
@pytest.mark.asyncio
async def test_user_message_appears():
    app = MyApp()
    async with app.run_test() as pilot:
        conv = app.screen.query_one("#conversation")
        conv.add_user_message("Hello")
        await pilot.pause()
        assert conv.log is not None  # sem erro de markup
```

---

## 12. Erros Comuns e Soluções

| Problema | Causa | Solução |
|----------|-------|---------|
| `ColorParseError` | Cor inválida no CSS | Usar cores do sistema (`$text`, `$primary`) ou hex |
| `NoMatches` ao fazer query | Widget não montou ainda | `await self.mount(widget)` antes de query |
| Tela em branco | `compose()` não definido ou vazio | Implementar `compose()` ou `on_mount()` com mount |
| Input trava | Chamada bloqueante no handler | Usar `@work` ou `run_worker` |
| Tabs não trocam conteúdo | Tab IDs auto-gerados | Usar `Tab("Label", id="explicit-id")` |
| `ScreenStackError` | Tentou pop da única tela | Verificar `len(self.screen_stack)` antes |
| Footer vazio | `BINDINGS` sem `show=True` | Bindings com `show=True` aparecem no Footer |
| Widget não focado | `can_focus` é False | Subclasse com `can_focus = True` |

---

## 13. Padrões de Layout por Tipo de App

### Chat Interface (AI agent)

```
┌─ Header: workspace, model, cost ────────────────────────────────┐
│                                                                  │
│  ScrollableChat (RichLog ou ListView custom)                     │
│  ┌──────────────────────────────────────────────────────────────┐│
│  │ User: Research X                                             ││
│  │ Agent: Results (markdown, code, tool calls)                  ││
│  └──────────────────────────────────────────────────────────────┘│
│                                                                  │
│  InputBar: > _                                    [Enter] send   │
├──────────────────────────────────────────────────────────────────┤
│  /model  /search  /help          Ctrl+C cancel  Ctrl+Q quit     │
└──────────────────────────────────────────────────────────────────┘
```

**Implementação**: `Input` + `RichLog` (append mensagens) + `Footer`
**Workers**: `@work` pra chamadas de API/LLM
**Estados**: loading (spinner), error (notify), streaming (RichLog incremental)

### Dashboard (monitoring)

```
┌─ StatsRow ── ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│              │ Agents 3 │ │ Tasks 12 │ │ Cost $0.05│ │ Cache 85%│
│              │ running  │ │ active   │ │ today    │ │ hit rate │
├──────────────┴──────────┴────────────┴──────────────┴──────────┤
│  Active Agents (DataTable ou ListView)                          │
│  name       status    task                        progress     │
│  coding-1   ● run     Fix auth middleware         80% ████░    │
│  research   ● run     MCP tools comparison        40% ██░░░    │
├────────────────────────────────────────────────────────────────┤
│  Activity Feed (RichLog)                                        │
│  20:45 ✓ Research completed                                    │
│  20:30 ✗ Agent error: timeout                                 │
├────────────────────────────────────────────────────────────────┤
│  Ctrl+S spawn  Ctrl+R research  Ctrl+F find  Ctrl+Q quit       │
└────────────────────────────────────────────────────────────────┘
```

**Implementação**: `Grid` pra stats, `DataTable` pra agentes, `RichLog` pra feed
**Reatividade**: `reactive` pra stats em tempo real
**Refresh**: `set_interval(5, self.refresh_data)` pra polling

### Modal Dialog (confirmação)

```python
class ConfirmDelete(ModalScreen):
    CSS = """
    ConfirmDelete { align: center middle; }
    #dialog {
        width: 50; height: auto;
        border: thick $error;
        background: $surface;
        padding: 1 2;
    }
    """
    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Delete this item?")
            with Horizontal():
                yield Button("Delete", variant="error", id="delete")
                yield Button("Cancel", variant="primary", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "delete")
```

---

## 14. Debugging

```bash
# DevTools — console separado pra debug
textual run --dev my_app.py

# Em outro terminal:
textual console

# Command palette (Ctrl+P)
# Hot-reload de CSS: textual run --dev
# Inspetor: Ctrl+\ (mostra DOM tree)
# Ver teclas: textual keys
```

```python
# Logging
def on_mount(self) -> None:
    self.log("App started", screen=self.screen)

# Notify (toast)
self.notify("Erro ao carregar", severity="error", timeout=3)
```

---

## 15. Roadmap — Funcionalidades Planejadas

### Skills (alinhar com pi)
- O projeto já tem `.agents/skills/` com arquivos markdown que definem
  comportamento especializado por domínio (code review, pesquisa, etc.)
- O agente da TUI ainda **não lê** skills automaticamente
- PI carrega skills como instruções de sistema para guiar o comportamento
- Planejado: `/skill <name>` carrega uma skill, agente usa como system prompt

### Prompt Templates
- PI tem sistema de prompt templates reutilizáveis
- Planejado: templates em `~/.aiw/templates/` com placeholders como
  `{task}`, `{model}`, `{workspace}`
- Comando `/template <name>` carrega um template como prompt base

### Priority Queue
- A fila atual (`_agent_queue`) é linear — mensagens executam em ordem FIFO
- Steering (`!task`) cancela o atual, mas não suporta níveis de prioridade
- PI suporta priority queue com `MessagePriority` (normal, high, urgent)
- Planejado: 3 níveis — normal (append), high (prepend), urgent (interrupt+prepend)

### Temas
- Apenas 1 tema implementado (`workstation`: dark blue/slate)
- Planejado: sistema de temas com `Theme` class, suporte a Dracula, Nord,
  Tokyo Night, Catppuccin
- Comando `/theme <name>` troca o tema em runtime

### Agent Swarm (multi-agente)
- Suporte básico existe via crewAI (`agents/swarm.py`)
- Planejado: supervisor observa tasks, spawna sub-agentes (coding, research,
  general) com ferramentas especializadas por tipo
- Visualização: AgentMonitor mostrando árvore de agentes ativos

### MCP Client
- O projeto tem um MCP server (`mcp_server/`) mas o TUI não consome
  ferramentas de servidores MCP externos
- Planejado: `/mcp connect <url>` conecta a um servidor MCP, lista tools,
  injeta no agente como ferramentas adicionais

### Session Branching
- Sessões atualmente são arquivos JSON lineares (`~/.aiw/tui-sessions/`)
- PI suporta branching (árvore de conversas, editar/continuar de qualquer ponto)
- Planejado: interface de árvore com `Tree` widget, criar branches,
  merge, navegar histórico

### Command Palette (Ctrl+P)
- Textual tem command palette built-in (`textual-dev`)
- Planejado: registrar comandos customizados no palette do Textual
  (`/model`, `/clear`, `/export`, etc.) com busca fuzzy

### Dashboard com Dados Reais
- O módulo `dashboard.py` existe como overlay (F3) mas mostra dados
  estáticos ou placeholder
- Planejado: stats em tempo real de agentes ativos, custo acumulado,
  cache hit rate, pesquisa recente, gráfico de uso de tokens

### Code Agent Especializado
- Agente atual é generalista (todas as ferramentas disponíveis)
- Planejado: agente de código com ferramentas otimizadas (read_file,
  write_file, search_files, git_diff, run_command) + system prompt
  específico para edição de código, diff review, commit

### Auto-scroll na Conversa
- O Conversation (VerticalScroll) não rola automaticamente pro final
  durante streaming
- Planejado: `conv.scroll_end(animate=False)` chamado a cada `append_token`
  para manter a conversa sempre visível na mensagem mais recente

---

## Referências

- **Documentação oficial**: https://textual.textualize.io/
- **Guia CSS**: https://textual.textualize.io/guide/CSS/
- **Widget gallery**: https://textual.textualize.io/widget_gallery/
- **Guia de Screens**: https://textual.textualize.io/guide/screens/
- **Guia de Actions**: https://textual.textualize.io/guide/actions/
- **Guia de Workers**: https://textual.textualize.io/guide/workers/
- **Guia de Testing**: https://textual.textualize.io/guide/testing/
- **Repositório**: https://github.com/Textualize/textual
- **Exemplos**: https://github.com/Textualize/textual/tree/main/examples
