# search_knowledge Tool — Output Format Requirement

> **Data:** 2026-06-17 | **Status:** ❌ Open | **Prioridade:** Média
> **Origem:** Sessão com pi (agente coding) — observação direta de usabilidade

---

## 🎯 Problema

O output da ferramenta `search_knowledge` é renderizado como **tabelas ASCII/unicode** (`┏━━┳━━┓`) que acumulam três problemas:

1. **Baixa densidade de informação** — caracteres de borda ocupam ~40% do output sem transmitir dados úteis.
2. **Fontes misturadas** — Quando `source: "all"` é usado, resultados de KB, memórias e tarefas são concatenados com layouts inconsistentes, sem separação clara entre categorias.
3. **Sem metadados estruturados** — O agente consumidor (pi, ou qualquer outro) recebe texto renderizado em vez de dados limpos como `{title, content, importance, category, timestamp}`, forçando regex-parsing para extrair informações.

---

## 🧠 Solução Desejada

O `search_knowledge` deve expor os resultados em formato **limpo e estruturado**, agrupado por fonte, com metadados relevantes e sem ruído visual.

### Formato de output preferido

```
Knowledge entries (2):
  • [fact] "Project uses Next.js 14 with shadcn/ui" (confidence: 0.85)
  • [learning] "User prefers Tailwind over CSS modules" (confidence: 0.7)

Memories (1):
  • "Decided to use PostgreSQL for persistence" (importance: 0.9)

Tasks (2):
  • [completed] Test task 1
  • [failed] Daily review
```

### Requisitos funcionais

| # | Requisito | Prioridade |
|---|-----------|------------|
| 1 | Agrupar resultados por fonte (KB, memórias, tarefas) com cabeçalhos claros | Alta |
| 2 | Exibir metadados relevantes entre parênteses — confiança (KB), importância (memórias), status (tarefas) | Alta |
| 3 | Remover caracteres de borda de tabela (`┏━━┳━━┓`, linhas de separação, etc.) | Alta |
| 4 | Usar marcadores concisos (`•` ou `-`) em vez de linhas de grade | Média |
| 5 | Se tabelas forem realmente necessárias (ex: muitas tarefas), usar formato legível em plano — sem unicode box-drawing | Baixa |
| 6 | Quando `source: "all"`, omitir fontes com zero resultados em vez de mostrar seções vazias | Média |

### Anti-requisitos (o que NÃO deve ser feito)

- ❌ Não usar `┏━┳━┓` / `┡━╇━┩` / `└━┴━┘` — zero valor informativo
- ❌ Não misturar fontes no mesmo bloco sem separação
- ❌ Não truncar resultados críticos (especialmente memórias) por limitação de caracteres do output

---

## 🔗 Contexto

Este requisito afeta diretamente a usabilidade do agente pi quando ele consulta o knowledge base do AI Workspace. O formato atual dificulta a leitura rápida e aumenta o risco de o agente perder informações relevantes escondidas em meio a caracteres de borda.

### Dependências
- `search_knowledge` tool (back-end do AI Workspace)
- Agentes consumidores: pi, coding agent, research agent

### Impacto
- **Positivo:** Agentes interpretam resultados mais rapidamente, menos ruído no contexto, respostas mais precisas
- **Negativo:** Pequeno esforço de refatoração no formato de saída da ferramenta

---

## 📋 Histórico

| Data | Evento |
|------|--------|
| 2026-06-17 | Requisito levantado durante sessão de uso com pi |
| 2026-06-17 | Registrado como memória do agente (#49) |
| 2026-06-17 | Documentado formalmente neste arquivo |
