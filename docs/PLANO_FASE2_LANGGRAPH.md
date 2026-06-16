# Fase 2 — LangGraph + Agentes: Orquestração com State Graph

**Data:** 2026-06-16 | **Plano macro:** `PLANO_ARQUITETURA.md`
**Decisão:** LangGraph (mais maduro, state graph, durable execution, checkpoint)
**Estado atual:** crewAI com agents/tasks + workflow DAG customizado (`workflow/engine.py`)
**Meta:** Substituir engine DAG por LangGraph, manter crewAI para agentes individuais

---

## 1. Por que LangGraph e não crewAI Flows

| Critério | crewAI Flows | LangGraph | Impacto |
|----------|-------------|-----------|---------|
| State explícito | ❌ Implícito (decorators) | ✅ StateGraph tipado (TypedDict) | Debugar é mais fácil |
| Checkpoint/durability | ✅ `@persist` (SQLite) | ✅ ✅ Durable execution (PostgreSQL) | Resiste a crash |
| Ciclos/loops | ❌ Linear | ✅ Branching, looping, human-in-loop | Pesquisa iterativa |
| Observabilidade nativa | ❌ (AMP, pago) | ✅ LangSmith + OpenTelemetry | Debug sem custo extra |
| Agente como nó | ❌ Só sequential | ✅ Qualquer topologia | Supervisor-worker natural |
| Maturidade | 🆕 1.14 (2025) | 🏆 2+ anos, 120k+ estrelas | Menos surpresas |
| Checkpoint incremental | ❌ | ✅ DeltaChannel beta | Checkpoint barato em graphs longos |
| Framework-agnóstico | ❌ Só crewAI | ✅ Qualquer LLM, qualquer tool | Não fica preso a ecossistema |

**Estratégia de migração:** Não precisa jogar crewAI fora — agents individuais continuam sendo criados com crewAI, mas a **orquestração** (quem chama quem, em que ordem, com que estado) vira LangGraph.

---

## 2. State Graph Design

### 2.1 Estado Global do Sistema

```python
from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages
from langgraph.managed import RemainingSteps

class ResearchState(TypedDict):
    """Estado compartilhado entre todos os nós do grafo."""
    
    # — Entrada do usuário —
    query: str                           # Pergunta original
    user_id: str                         # Quem perguntou
    
    # — Controle de fluxo —
    depth: int                           # Profundidade atual da pesquisa
    remaining_steps: RemainingSteps       # Limite de steps (evita loop infinito)
    
    # — Planejamento —
    sub_questions: List[str]             # Sub-questões geradas
    plan: Optional[str]                  # Plano de pesquisa
    
    # — Execução —
    research_results: Annotated[list, add_messages]  # Resultados acumulados
    sources: List[dict]                  # Fontes coletadas
    filtered_sources: List[dict]         # Fontes após source ranking
    
    # — Síntese —
    draft: Optional[str]                 # Rascunho do relatório
    final_report: Optional[str]          # Relatório final
    
    # — Metadados —
    cost_tracker: dict                   # Custo acumulado da pesquisa
    errors: List[str]                    # Erros ocorridos
    started_at: Optional[str]            # Timestamp ISO
```

### 2.2 Nós do Grafo

```
                    ┌──────────────┐
                    │   User Input  │
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │   Planner     │ ← deepseek-chat (barato)
                    │ (sub-questões)│
                    └──────┬───────┘
                           ↓
                    ┌──────────────┐
                    │  Supervisor   │ ← decide se precisa de mais ou já pode sintetizar
                    └──────┬───────┘
                           ↓
              ┌────────────┴────────────┐
              ↓                         ↓
      ┌──────────────┐         ┌──────────────┐
      │ Research Nó 1 │  ...    │ Research Nó N │ ← cada nó pesquisa 1 sub-questão
      │ (crewAI agent)│         │ (crewAI agent)│
      └──────┬───────┘         └──────┬───────┘
              ↓                         ↓
              └────────────┬────────────┘
                           ↓
                    ┌──────────────┐
                    │ Source Filter │ ← Fase 1: ignora fontes com score < 0.4
                    └──────┬───────┘
                           ↓
              ┌────────────┴────────────┐
              ↓                         ↓
      ┌──────────────┐         ┌──────────────┐
      │ Synthesizer  │         │   Critic      │ ← verifica qualidade, cross-ref
      │ (relatório)  │         │ (revisão)     │
      └──────┬───────┘         └──────┬───────┘
              ↓                         ↓
              └────────────┬────────────┘
                           ↓
                    ┌──────────────┐
                    │ Human Review  │ ← human-in-the-loop (opcional)
                    │ (aprova?)     │
                    └──────┬───────┘
                     ↓            ↓
                  Aprovado    Recusado → volta pro synthesizer
                     ↓
              ┌──────────────┐
              │   Output      │
              │ (relatório)   │
              └──────────────┘
```

### 2.3 Código do Grafo (esqueleto)

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver

# Inicializa o grafo
graph = StateGraph(ResearchState)

# Adiciona nós
graph.add_node("planner", plan_research)           # Gera sub-questões
graph.add_node("supervisor", supervise)             # Decide próximos passos
graph.add_node("researcher", conduct_research)      # Pesquisa (crewAI agent)
graph.add_node("source_filter", filter_sources)     # Source ranking
graph.add_node("synthesizer", synthesize_report)    # Gera relatório
graph.add_node("critic", review_quality)            # Revisa qualidade
graph.add_node("human_review", human_approval)      # Aprovação humana

# Define arestas
graph.add_edge(START, "planner")
graph.add_edge("planner", "supervisor")

# Supervisor pode:
# 1. Spawnar mais pesquisadores (se precisa de mais info)
# 2. Ir pra source_filter (se já tem info suficiente)
# 3. Ir pra END (se erro irreparável)
graph.add_conditional_edges(
    "supervisor",
    decide_next_step,
    {
        "research_more": "researcher",
        "filter_sources": "source_filter",
        "end": END,
    }
)

# Researcher → sempre volta pro supervisor
graph.add_edge("researcher", "supervisor")

# Source filter → synthesizer
graph.add_edge("source_filter", "synthesizer")

# Synthesizer → critic
graph.add_edge("synthesizer", "critic")

# Critic pode aprovar ou pedir revisão
graph.add_conditional_edges(
    "critic",
    decide_quality,
    {
        "approve": "human_review",
        "revise": "synthesizer",
    }
)

# Human review pode aprovar ou recusar
graph.add_conditional_edges(
    "human_review",
    decide_human_approval,
    {
        "approved": END,
        "rejected": "synthesizer",
    }
)

# Configura checkpoint (durable execution)
checkpointer = PostgresSaver(connection_string=AIW_DB_URL)

# Compila
app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_review"],  # Pausa pra aprovação humana
)
```

---

## 3. Supervisor Pattern

### 3.1 Função do Supervisor

O supervisor é o **cérebro da operação** — decide:

1. **Quando parar de pesquisar** — se já tem info suficiente, vai pra síntese
2. **Se precisa aprofundar** — se info é superficial, spawna mais pesquisadores
3. **Qual direção seguir** — se achou um tópico promissor, prioriza ele
4. **Se algo deu errado** — se uma sub-questão falhou, decide se retenta ou ignora

### 3.2 Lógica de Decisão

```python
def decide_next_step(state: ResearchState) -> str:
    """Decide o próximo passo baseado no estado atual."""
    
    remaining = state.get("sub_questions", [])
    results = state.get("research_results", [])
    
    # Critérios pra parar
    if not remaining:
        return "filter_sources"  # todas as sub-questões foram respondidas
    
    if len(results) >= len(remaining) * 2:
        return "filter_sources"  # já tem respostas em excesso
    
    if state.get("remaining_steps", 10) <= 2:
        return "filter_sources"  # tá gastando muitos steps
    
    # Ainda tem perguntas pra responder
    return "research_more"
```

### 3.3 Roteamento de Pesquisadores

```python
def route_research(state: ResearchState, sub_question: str) -> str:
    """Decide qual ferramenta/tool usar pra cada sub-questão."""
    
    if any(kw in sub_question.lower() for kw in ["preço", "valor", "custo", "mercadolivre"]):
        return "mercadolivre_search"
    if any(kw in sub_question.lower() for kw in ["notícia", "último", "recente"]):
        return "web_search"
    if any(kw in sub_question.lower() for kw in ["código", "github", "api", "implementação"]):
        return "github_search"
    
    return "deep_search"  # fallback: pesquisa geral com crawl4ai + deepseek
```

---

## 4. Durable Execution + Checkpoint

### 4.1 PostgreSQL Checkpointer

```python
# LangGraph salva o estado a cada step no PostgreSQL
# Se o processo morrer, retoma do último checkpoint

checkpointer = PostgresSaver(
    connection_string=AIW_DB_URL,
    # Configuração do pool
    pool_kwargs={
        "min_size": 2,
        "max_size": 5,
    }
)

# Checkpoint incremental (economiza storage)
# Só salva o delta, não o estado inteiro a cada step
config = {
    "configurable": {
        "thread_id": "research-20260616-001",
        "checkpoint_mode": "delta",  # incremental
    }
}
```

### 4.2 Resumabilidade

```python
# Se a pesquisa caiu no meio:
# Simplesmente continua com o mesmo thread_id

# Recuperar estado anterior
thread = {"configurable": {"thread_id": "research-20260616-001"}}
state = app.get_state(thread)
print(f"Último nó executado: {state.next}")

# Continuar de onde parou
for event in app.stream(None, thread):
    print(event)
```

### 4.3 Tabela de Checkpoints

```sql
-- LangGraph cria automaticamente no PostgreSQL
-- (via PostgresSaver, não precisa criar manual)
-- 
-- checkpoints: estado em cada passo
-- writes: saída de cada nó
-- checkpoint_blobs: blobs grandes (opcional)
```

---

## 5. Integração com Fase 1 (Source Ranking)

### 5.1 Nó de Source Filter

```python
async def filter_sources(state: ResearchState) -> dict:
    """Filtra fontes com score < threshold antes de passar pro synthesizer."""
    
    raw_sources = state.get("sources", [])
    reputation = SourceReputationManager()
    
    filtered = []
    ignored = []
    
    for src in raw_sources:
        score = await reputation.get_composite_score(src["url"])
        src["credibility_score"] = score
        
        if score >= 0.4:  # threshold configurável
            filtered.append(src)
        else:
            ignored.append(src)
            log.info(f"Ignored source: {src['url']} (score: {score:.2f})")
    
    return {
        "sources": filtered,        # só fontes confiáveis vão pro LLM
        "filtered_sources": filtered,
        "ignored_sources": ignored,  # log pra debug
        "tokens_saved": len(ignored) * avg_tokens_per_source,
    }
```

---

## 6. Integração com Fase 0 (Custo Zero)

### 6.1 Cache no Grafo

```python
from ai_workspace.cost import SemanticCache

cache = SemanticCache()

@cache.cache_response(task_type="research")
async def planner_node(state: ResearchState) -> dict:
    """Cacheia o plano de pesquisa pra queries similares."""
    # ... lógica do planner ...
```

### 6.2 Roteamento por Nó

```python
# Cada nó usa o modelo mais barato que resolve
# Configurado via SmartRouter da Fase 0

PLANNER_MODEL = "deepseek-chat"        # planejamento não precisa de reasoning
RESEARCHER_MODEL = "deepseek-reasoner" # pesquisa precisa raciocinar
SYNTHESIZER_MODEL = "deepseek-chat"    # síntese é texto estruturado
CRITIC_MODEL = "gemini-2.5-flash"      # crítica é barato, Gemini free resolve
```

---

## 7. Human-in-the-Loop

### 7.1 Pontos de Interrupção

```python
# O grafo pausa automaticamente antes de ações que precisam aprovação
app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=[
        "human_review",       # Aprovação do relatório final
        # Opcionais:
        # "expensive_research",  # Se estimativa de custo > $0.05
        # "code_execution",      # Se agente for executar código
    ]
)
```

### 7.2 CLI de Aprovação

```bash
aiw research review <id>
# 📋 Relatório gerado, revise:
#   Confiança geral: 82%
#   Fontes: 12 (3 ignoradas por baixo score)
#   Custo: $0.0034
#   Tokens: 4.567
# 
# ❓ Aprovar? [Y/n] Y
# ✅ Relatório finalizado!
```

---

## 8. Plano de Migração (crewAI → LangGraph)

### 8.1 Não precisa refazer tudo

| O que fica | O que muda |
|------------|-----------|
| ✅ Criação de agentes individuais (crewAI Agent) | ❌ `Crew` + `Task` + `kickoff()` → vira nó do LangGraph |
| ✅ Ferramentas (web_fetch, browser, etc.) | ❌ Orquestração sequential → state graph |
| ✅ DeepSearchEngine (lógica de pesquisa) | ❌ Engine DAG customizado → nós do LangGraph |
| ✅ ProviderRegistry (LLM clients) | ❌ Chamada direta ao LLM → router do LangGraph |
| ✅ PostgreSQL + pgvector | — |
| ✅ Huey scheduler | — |

### 8.2 Passos

```
1. Criar StateGraph com ResearchState
2. Mover planner logic pra nó "planner"
3. Mover research logic pra nó "researcher" (wrapper do crewAI agent)
4. Adicionar nó "source_filter" (Fase 1)
5. Mover synthesis logic pra nó "synthesizer"
6. Adicionar supervisor + critic
7. Configurar checkpointer (PostgreSQL)
8. Adicionar human-in-the-loop
9. Remover engine DAG customizado (workflow/engine.py)
10. Atualizar CLI (agora usa app.invoke() em vez de DeepSearchEngine.research())
```

---

## 9. Métricas de Sucesso da Fase 2

| Métrica | Atual | Meta | Como Medir |
|---------|-------|------|------------|
| Pesquisas com checkpoint | 0% | 100% | `checkpoints` por research_id |
| Supervisor decide parar corretamente | — | ≥ 80% | Precisão das decisões do supervisor |
| Human-in-the-loop ativo | — | ≥ 50% pesquisas críticas | `interrupts` no grafo |
| Migração do engine DAG | ❌ | ✅ Completa | engine.py removido ou deprecated |
| Tempo médio de pesquisa | ~2min | < 1min | LangSmith tracing |

---

## Anexo: Exemplo de Execução Completa

```python
# 1. Usuário invoca
aiw search "Melhores frameworks para agentes AI em 2026"

# 2. LangGraph executa:
#    planner → deepseek-chat → ["quais frameworks?", "comparação de performance?", "quem usa?"]
#    supervisor → research_more
#    researcher (crewAI) → pesquisa sub-questão 1 com crawl4ai + web
#    supervisor → research_more
#    researcher → pesquisa sub-questão 2
#    supervisor → research_more
#    researcher → pesquisa sub-questão 3
#    supervisor → filter_sources (já respondeu tudo)
#    source_filter → ignora 2 fontes com score < 0.4, passa 10
#    synthesizer → deepseek-chat → gera relatório
#    critic → gemini-2.5-flash → "relatório bom, aprova"
#    human_review → PAUSA (esperando usuário)
#    [usuário aprova]
#    → END

# Custo total: ~$0.004
# Tempo: ~45s
# Checkpoints salvos: 12
```
