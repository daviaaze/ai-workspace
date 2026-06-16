# Fase 3 — Scraping + Ferramentas: Crawl4AI, OpenCLI, MCP

**Data:** 2026-06-16 | **Plano macro:** `PLANO_ARQUITETURA.md`
**Decisão:** Crawl4AI (scraping principal, local, $0) + OpenCLI (70+ sites adaptados, complementar)
**Complementares:** browser-use (navegador autônomo), MCP (ferramentas padronizadas), A2A (comunicação)

---

## 1. Stack de Scraping

```
Hierarquia de ferramentas (da mais barata pra mais cara):

1. WebFetchTool (existente)  → páginas HTML estáticas → $0
2. Crawl4AI                   → páginas JS + markdown estruturado → $0 (local)
3. HeadlessBrowserTool (exist.) → SPAs complexas (gov.br, Receita) → $0
4. OpenCLI                    → sites com adapters prontos → $0 (via Chrome)
5. browser-use                → navegação autônoma (login, formulários, multi-step) → $0
6. PaginatedScraperTool (exist.) → tabelas multi-página → $0
```

**Regra:** Sempre tentar a ferramenta mais barata primeiro. Só escala se falhar.

---

## 2. Crawl4AI (Scraping Principal)

### 2.1 Por que Crawl4AI

| Critério | WebFetchTool (atual) | Crawl4AI |
|----------|---------------------|----------|
| JavaScript rendering | ❌ Só HTML estático | ✅ Playwright embutido |
| Output | HTML bruto | **Markdown limpo** (perfeito pra LLM) |
| Extração estruturada | ❌ Manual | ✅ Schema-based (CSS, XPath, LLM) |
| Async | ❌ Sync | ✅ Async-first |
| Caching | ❌ | ✅ Cache de requisições |
| Rate limiting | ❌ | ✅ Built-in |
| Custom hooks | ❌ | ✅ Hooks pra logging, auth, etc. |
| Custo | $0 | $0 |

### 2.2 Integração

```python
# Uso como ferramenta no LangGraph
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy

class Crawl4AITool:
    """Ferramenta de scraping que retorna Markdown limpo pra LLM."""
    
    def __init__(self):
        self.crawler = AsyncWebCrawler()
    
    async def scrape(self, url: str, extraction_type: str = "markdown") -> dict:
        async with self.crawler:
            result = await self.crawler.arun(
                url=url,
                extraction_strategy=(
                    LLMExtractionStrategy() if extraction_type == "structured"
                    else None
                ),
                # Config pra SPAs
                wait_until="networkidle",
                # Cache pra não re-scrapear mesma URL
                cache_mode="by_url",
            )
        
        return {
            "url": url,
            "content": result.markdown,  # Markdown limpo!
            "metadata": {
                "title": result.metadata.get("title"),
                "description": result.metadata.get("description"),
                "domain": extract_domain(url),
                "scrape_time_ms": result.duration,
            }
        }
```

### 2.3 Crawl4AI no Grafo LangGraph

```python
# Nó de pesquisa que usa Crawl4AI
async def research_with_scrape(state: ResearchState, sub_question: str) -> dict:
    crawler = Crawl4AITool()
    
    # 1. Busca URLs relevantes (via Firecrawl ou Google Search)
    urls = await search_urls(sub_question)
    
    # 2. Scrapeia cada URL com Crawl4AI
    contents = []
    for url in urls[:5]:  # max 5 por sub-questão
        content = await crawler.scrape(url)
        if content["content"]:
            # 3. Source reputation check (Fase 1)
            score = await reputation.get_composite_score(url)
            if score >= 0.4:
                contents.append({**content, "credibility": score})
    
    # 4. Passa conteúdo pro LLM extrair resposta
    return extract_answer(sub_question, contents)
```

---

## 3. OpenCLI (Scraping Complementar — 70+ Sites)

### 3.1 O que é

OpenCLI transforma **qualquer site em um comando de terminal**. Ele conecta no seu Chrome logado via extensão e permite que agentes AI executem ações como navegar, clicar, preencher formulários e extrair dados de forma **determinística**.

### 3.2 Quando usar OpenCLI em vez de Crawl4AI

| Cenário | Ferramenta | Motivo |
|---------|-----------|--------|
| Página HTML/JS comum | Crawl4AI | Mais simples, markdown direto |
| **Site com adapter pronto** (Bilibili, Zhihu, Reddit, HackerNews, Twitter/X, Amazon, arXiv, etc.) | **OpenCLI** | Comando único, dados estruturados |
| Site que precisa de **login** | OpenCLI | Usa sessão do Chrome logado |
| Site que precisa de **navegação multi-passo** | browser-use | Agente autônomo decide os passos |
| **Formulários**, cliques, interações | OpenCLI + browser-use | Ambos controlam o Chrome |

### 3.3 Adapters Prontos do OpenCLI

O OpenCLI já tem **70+ sites adaptados**:

```bash
# Exemplos de comandos que funcionam hoje:
opencli hackernews top --limit 5
opencli arxiv search "llm agents" --limit 10
opencli reddit hot --subreddit "MachineLearning"
opencli twitter trending
opencli amazon search "raspberry pi 5"
opencli github trending --language python
opencli wikipedia search "LangGraph"
```

### 3.4 Integração com aiw

```python
import subprocess
import json

class OpenCLITool:
    """Wrapper pro OpenCLI como ferramenta no LangGraph."""
    
    async def run(self, site: str, command: str, **kwargs) -> dict:
        """Executa um comando OpenCLI e retorna resultado estruturado."""
        
        args = ["opencli", site, command]
        for k, v in kwargs.items():
            args.extend([f"--{k}", str(v)])
        
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=30,
        )
        
        # OpenCLI retorna JSON com --json
        if "--json" not in str(args):
            args.append("--json")
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {"text": result.stdout, "site": site, "command": command}
```

### 3.5 OpenCLI no Grafo

```python
async def research_with_opencli(state: ResearchState, sub_question: str) -> dict:
    """Tenta usar OpenCLI se o site tiver adapter."""
    
    cli = OpenCLITool()
    
    # Mapeia sub-questão pra site + comando OpenCLI
    site_map = {
        "código": ("github", "search"),
        "paper": ("arxiv", "search"),
        "notícia": ("hackernews", "top"),
        "preço": ("amazon", "search"),
        "wiki": ("wikipedia", "search"),
    }
    
    for keyword, (site, cmd) in site_map.items():
        if keyword in sub_question.lower():
            return await cli.run(site, cmd, query=sub_question)
    
    # Se não mapeou, usa Crawl4AI
    return await research_with_scrape(state, sub_question)
```

### 3.6 Instalação

```bash
# OpenCLI precisa de:
npm install -g @jackwener/opencli    # CLI
# Extensão Chrome: Chrome Web Store → "OpenCLI"
# Verificar instalação:
opencli doctor
```

---

## 4. browser-use (Navegador Autônomo)

### 4.1 Quando usar

- Sites que exigem **navegação multi-passo** (login → buscar → filtrar → extrair)
- Sites que o Crawl4AI não consegue renderizar bem
- Automação que **age no site** (não só extrai)

### 4.2 Integração

```python
from browser_use import Agent as BrowserAgent

class BrowserUseTool:
    """Agente de navegador autônomo para tarefas complexas."""
    
    async def run_task(self, task: str, max_steps: int = 20) -> str:
        agent = BrowserAgent(
            task=task,
            llm=self.llm,  # LLM que decide os passos (usa deepseek-chat pra economizar)
            max_actions_per_step=1,
        )
        history = await agent.run(max_steps=max_steps)
        return history.final_result()
```

### 4.3 Custo do browser-use

- Só gasta tokens quando o LLM decide o **próximo passo** do navegador
- Ação média: ~200 tokens por passo → 20 passos = ~4K tokens = ~$0.00006
- **Muito barato** comparado a gerar texto

---

## 5. MCP (Model Context Protocol)

### 5.1 O que é

MCP é o padrão da indústria (Anthropic) pra agentes **descobrirem e usarem ferramentas** de forma padronizada. Cada ferramenta vira um "MCP server" que expõe tools.

### 5.2 MCP Server Registry

```python
# src/ai_workspace/mcp_server/registry.py

class MCPServerRegistry:
    """Catálogo de MCP servers disponíveis."""
    
    servers = {
        "crawl4ai": {
            "command": "python",
            "args": ["-m", "ai_workspace.mcp_server.crawl4ai_server"],
            "tools": ["scrape_url", "search_and_scrape"],
        },
        "opencli": {
            "command": "opencli",
            "args": ["--mcp"],  # OpenCLI já tem MCP server nativo!
            "tools": ["run_command"],
        },
        "filesystem": {
            "command": "python",
            "args": ["-m", "ai_workspace.mcp_server.filesystem"],
            "tools": ["read_file", "write_file", "list_dir"],
        },
        "git": {
            "command": "python",
            "args": ["-m", "ai_workspace.mcp_server.git"],
            "tools": ["status", "diff", "commit", "pr"],
        },
    }
    
    def get_tools(self, server_name: str) -> list:
        """Retorna tools disponíveis num server."""
        return self.servers.get(server_name, {}).get("tools", [])
    
    def connect(self, server_name: str) -> MCPClient:
        """Conecta a um MCP server e retorna client."""
        config = self.servers[server_name]
        return MCPClient(
            command=config["command"],
            args=config["args"],
        )
```

### 5.3 Ferramentas como MCP (integração com LangGraph)

Cada ferramenta que o agente usa **pode ser um MCP server**. No LangGraph, isso vira:

```python
# Tools expostas como MCP são registradas como nós do grafo
from langgraph.prebuilt import ToolNode

# Tools MCP disponíveis
mcp_tools = [
    Crawl4AITool(),
    OpenCLITool(),
    WebFetchTool(),
    HeadlessBrowserTool(),
    BrowserUseTool(),
]

# Nó que executa tools
tool_node = ToolNode(mcp_tools)

# Agente decide qual tool chamar
graph.add_node("agent", call_model)   # LLM decide qual tool
graph.add_node("tools", tool_node)    # Executa a tool escolhida
graph.add_edge("agent", "tools")
graph.add_conditional_edges("tools", should_continue, ...)
```

### 5.4 CRED-1 já tem MCP Server!

```json
{
  "mcpServers": {
    "cred1": {
      "command": "npx",
      "args": ["-y", "@aloth/cred1", "--mcp"]
    }
  }
}
```

Isso significa que qualquer agente compatível com MCP (Claude, Cursor, Windsurf, e o nosso) pode **consultar credibilidade de domínio** via MCP diretamente.

---

## 6. A2A (Agent-to-Agent Protocol)

### 6.1 O que é

A2A é o protocolo do Google/Linux Foundation pra **agentes se comunicarem entre si**. Enquanto MCP conecta agente → ferramenta, A2A conecta agente → agente.

### 6.2 Quando usar

- Um agente **delega** uma tarefa pra outro agente especializado
- Um agente **descobre** as capacidades de outro agente
- Cross-workspace: agente do workspace "pessoal" consulta agente do workspace "trabalho"

### 6.3 A2A no Grafo

```python
# Em vez de chamar um LLM diretamente, o nó do grafo
# pode delegar pra outro agente via A2A

async def delegate_to_specialist(state: ResearchState, specialist: str) -> dict:
    """Delega sub-tarefa pra um agente especializado via A2A."""
    
    a2a_client = A2AClient()
    
    # Descobre agente especialista
    agent_card = await a2a_client.discover(specialist)
    # {"name": "coder-agent", "skills": ["python", "react", "rust"], "endpoint": "..."}
    
    # Delega tarefa
    response = await a2a_client.send_task(
        agent_url=agent_card.endpoint,
        task={
            "type": "code_review",
            "payload": state["code_to_review"],
        }
    )
    
    return {"code_review": response.result}
```

### 6.4 Prioridade: MCP > A2A

MCP é mais imediato (tools) e já tem ecossistema maduro. A2A faz sentido quando tivermos **múltiplos agentes especializados** rodando em paralelo.

---

## 7. Matriz de Decisão: Qual Ferramenta Usar

| Cenário | Ferramenta | Custo | Prioridade |
|---------|-----------|-------|------------|
| Página HTML comum | WebFetchTool | $0 | 1ª tentativa |
| Página com JS (blog, docs) | Crawl4AI | $0 | 2ª tentativa |
| Site com adapter OpenCLI | OpenCLI | $0 | 3ª tentativa |
| SPA complexa (gov.br) | HeadlessBrowserTool | $0 | 4ª tentativa |
| Tabela multi-página | PaginatedScraperTool | $0 | 5ª tentativa |
| Login + navegação multi-passo | browser-use | ~$0.00006 | 6ª tentativa |
| Pesquisa semântica em texto | Gemini free (extração) | $0 | Após coleta |

---

## 8. Métricas de Sucesso da Fase 3

| Métrica | Atual | Meta | Como Medir |
|---------|-------|------|------------|
| Crawl4AI integrado | ❌ | ✅ | Tool disponível no LangGraph |
| OpenCLI disponível | ❌ | ✅ | `opencli doctor` no setup |
| Sites acessíveis via OpenCLI | — | ≥ 30 | Comandos OpenCLI registrados |
| browser-use integrado | ❌ | ✅ | Tool disponível |
| MCP registry funcional | ❌ | ✅ | `mcp_server.list_servers()` |
| Fontes scraped com sucesso | ~70% | ≥ 90% | Taxa de sucesso das ferramentas |

---

## 9. Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| OpenCLI precisa de Chrome com extensão | Média | Documentar setup. `opencli doctor` valida |
| Site muda layout e OpenCLI quebra | Alta | Adapters são mantidos pela comunidade OpenCLI |
| Crawl4AI com Playwright pesado (300MB) | Média | Instalação opcional (`pip install crawl4ai[playwright]`) |
| browser-use consome muitos tokens decidindo passos | Média | Limitar `max_steps=10`. Usar deepseek-chat pra decisões |
| Sites bloqueiam scraping | Alta | Rotação de user-agent + delays respeitosos + `respect_robots_txt=True` |
