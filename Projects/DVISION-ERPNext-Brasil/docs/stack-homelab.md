# Decisão de Stack — Plataforma de Agentes para a DVISION

> **Data:** 30/07/2026 · **Contexto:** homelab self-hosted, 1 founder, 7 agentes de negócio (Fiscal, Produto, Compliance, Comercial, Suporte, Financeiro, Growth), custo free-first via OmniRoute.
> **Exigências:** roles/contextos diferentes por agente · ver o trabalho dos agentes · testes A/B de prompts · evals · auditoria/R&D · provedores gratuitos primeiro.

---

## 1. Decisão executiva (TL;DR)

| Peça | Escolha | Licença | Por quê |
|------|---------|---------|---------|
| **Plataforma visual** | **Dify** | Apache-2.0 (core) | Cobre roles/agentes + RAG + tracing + prompt versionado + auditoria numa peça só; self-host Docker |
| **Cron/integrações** | **n8n** *(ou Sim)* | Fair-code ⚠️ / Apache-2.0 | Rotinas agendadas (monitores SEFAZ/ANPD, faturamento, SEO); **Sim** se licença limpa for requisito |
| **Gateway/custo** | **OmniRoute** | MIT | 268 providers, ~90 free tiers, auto-fallback em ms, free-first |
| **Evals/A-B de prompts** | **Promptfoo** | MIT | YAML + CI/CD, A-B de prompts, red teaming (usado pela OpenAI/Anthropic) |
| **Observabilidade** | Dify built-in + Langfuse (se precisar) | MIT | Tracing por agente, histórico = auditoria |
| **Memória persistente** | **Letta** (opcional) | Apache-2.0 | Contexto de longo prazo por agente, se necessário |
| **Framework de código** | **LangGraph** (opcional) | MIT | Fluxos fiscais com estado complexo que a plataforma não expressa |

**Princípio de custo:** free tiers para rotina tolerante a rate-limit (monitores, drafts, SEO); assinatura paga só para o crítico (interpretação fiscal, revisão de PR, incidente).

---

## 2. Plataformas visuais OSS self-hosted (comparativo completo)

| | **Dify** | **n8n** | **Sim (Studio)** | **Flowise** | **Langflow** | **Coze Studio** |
|---|---|---|---|---|---|---|
| Metáfora | LLMOps completa | Automação + agentes | Builder de agentes visual | Canvas LangChain.js | Canvas LangChain (Python) | Agentes all-in-one |
| Licença | **Apache-2.0** | **Fair-code ⚠️** | **Apache-2.0** | Apache-2.0 | MIT | MIT |
| Stars | 138k+ | 197k | 29k+ (YC) | ~50k | ~60k | ByteDance |
| Multi-agent com roles | ✅ | 🟡 (AI Agent node) | ✅ | 🟡 | ✅ | ✅ |
| RAG | ✅ nativo prod. | 🟡 via nodes | ✅ | ✅ | ✅ | ✅ |
| Tracing/logs | ✅ built-in | ✅ execução + n8nTrace | ✅ built-in | 🟡 | 🟡 | 🟡 |
| Evals | ✅ built-in | 🟡 | 🟡 | ❌ | ❌ | 🟡 |
| Auditoria (SSO/RBAC/audit) | ✅ Enterprise | 🟡 (n8nTrace) | 🟡 | ❌ | ❌ | ❌ |
| Model routing (100+ providers) | ✅ | ✅ via nodes | ✅ | 🟡 | 🟡 | ✅ |
| Self-host Docker | ✅ | ✅ | ✅ | ✅ | ✅ | 🟡 (CN-first) |

**Decisão:** Dify é o match mais direto para as exigências da DVISION (4 de 4). n8n entra só para cron/integrações; se a licença Fair-code incomodar (revenda SaaS), substitua por Sim (Apache-2.0).

---

## 3. Frameworks (camada de código — quando a plataforma não basta)

| | **LangGraph** | **MS Agent Framework** | **CrewAI** | **AG2** |
|---|---|---|---|---|
| Licença | MIT | MIT | MIT | MIT |
| Modelo | Grafo de estado, checkpointing | Graph + handoffs + group chat | Roles/backstory/goal | Conversacional multi-agente |
| Status | Vivo, 38k stars | **GA 1.0 abr/2026** (sucessor AutoGen) | Vivo, 44k stars | Vivo (fork AutoGen, v1.0) |
| Auditoria | ✅ por passo (checkpoint) | ✅ | 🟡 | 🟡 |
| Curva | 1–2 semanas | média | baixa | média |

**Avisos de manutenção:**
- ❌ **AutoGen** — maintenance mode (substituído por MAF)
- ✅ **Microsoft Agent Framework** — caminho oficial se quiser stack MS
- ✅ **AG2** — fork da comunidade que manteve o modelo original

**Decisão:** LangGraph como framework de referência (fluxos fiscais longos + auditoria fina), rodando *dentro* da plataforma via tool se necessário. MAF como alternativa se preferir ecossistema Microsoft.

---

## 4. Evals / A-B de prompts / auditoria (exigência central)

| | **Promptfoo** | **DeepEval** | **Opik** | **Langfuse** | **Portkey** |
|---|---|---|---|---|---|
| Modelo | CLI/YAML + CI | Lib Python | OSS + cloud $19/mês | OSS MIT (ClickHouse) | Gateway + observ. |
| A-B de prompts | ✅ forte | ✅ | ✅ | ✅ | ✅ |
| Evals (métricas) | ✅ + red team | ✅ agentes/RAG | ✅ | ✅ | 🟡 |
| Red teaming (injeção) | ✅ (usado OpenAI/Anthropic) | 🟡 | 🟡 | ❌ | ❌ |
| Self-host | ✅ | lib | ✅ | ✅ | ✅ |
| **Status** | ✅ vivo | ✅ vivo | ✅ **crescendo** | ✅ vivo | ✅ vivo |

**Aviso:** ❌ **Helicone** — maintenance mode desde mar/2026 (adquirida pela Mintlify). Não escolher.

**Decisão:** Promptfoo no CI (Git = sistema nervoso) para A-B de prompts + red teaming nos agentes que recebem entrada externa (Fiscal lê XML, Suporte lê ticket). Langfuse self-host como camada de observabilidade unificada se o tracing do Dify não bastar.

---

## 5. Gateway — OmniRoute vs. alternativas

| | **OmniRoute** | **Portkey** | **LiteLLM** |
|---|---|---|---|
| Providers | **268 (90+ free)** | 100+ | 100+ |
| Free tiers agregados | ✅ ~1.4B tok/mês honestos | 🟡 | 🟡 |
| Auto-fallback | ✅ 3 camadas (breaker/cooldown/lockout) | ✅ | ✅ |
| Compressão de tokens | ✅ 15–95% | 🟡 | ❌ |
| Dashboard/custo | ✅ | ✅ | 🟡 |
| MCP/A2A server | ✅ | 🟡 | cliente |
| Licença | MIT | MIT + Com | MIT + Com |

**Decisão:** OmniRoute (MIT, self-host, free-first, dashboard). Portkey como alternativa madura se a comunidade do OmniRoute não manter o ritmo (projeto jovem, 500+ contribuidores).

**Cuidado com free tiers (honestidade):** "unlimited free" é marketing. ~90 providers com free tier, ~11 free forever, todos com rate limit. Suficiente para monitores/drafts/SEO; **crítico fiscal vai para pago** (o OmniRoute roteia automaticamente quando o free esgota).

---

## 6. Arquitetura final (homelab)

```
┌───────────────────────────────────────────────────────────────┐
│                     Git + CI  (sistema nervoso)                │
│        Promptfoo → evals/A-B em todo PR de prompt             │
└──────────────────────────┬────────────────────────────────────┘
                           │
   ┌───────────────────────▼──────────────────────┐
   │              Dify (Docker)                    │
   │   7 agentes com roles · RAG · tracing · audit │
   │   Fiscal  Produto  Compliance  Comercial      │
   │   Suporte  Financeiro  Growth                 │
   └───────────────────────┬──────────────────────┘
                           │  chamadas LLM → gateway
   ┌───────────────────────▼──────────────────────┐
   │            OmniRoute (gateway MIT)            │
   │   free tiers (Gemini/Groq/Cerebras/Mistral)   │
   │   → fallback pago (Claude/OpenAI) no crítico  │
   └───────┬───────────────────────────┬───────────┘
           │                           │
   ┌───────▼──────┐           ┌────────▼─────────┐
   │ n8n (cron)   │           │  Letta (memória) │
   │ monitores    │           │  por agente      │
   │ faturamento  │           │  (opcional)      │
   └──────────────┘           └──────────────────┘
```

**Compliance/LGPD (vantagem do homelab):** dados fiscais de clientes nunca saem da sua infraestrutura → argumento de venda (dados em território/controle do operador), sem depender da região Frankfurt do Frappe Cloud para os agentes.

---

## 7. Plano de PoC (faseado)

### Fase A — Fundação (1 semana)
- [ ] Docker Compose: Dify + OmniRoute + PostgreSQL/Redis
- [ ] Conectar 2–3 providers free no OmniRoute (Gemini, Groq, Cerebras) + `model: auto`
- [ ] Criar 2 agentes no Dify: **Fiscal Monitor** (monitora ENCAT/SEFAZ/ANPD) e **Growth Conteúdo** (rascunho de posts)
- [ ] Verificar tracing por agente no Dify

### Fase B — Evals/A-B (2ª semana)
- [ ] Promptfoo: repo de testes com dataset dos 2 agentes
- [ ] A-B entre prompts v1/v2 do agente Fiscal (extração de prazo de NT)
- [ ] Rodar em CI (PR de prompt = evals obrigatórios)

### Fase C — Expansão (3ª–4ª semana)
- [ ] n8n: cron dos monitores (ou Sim, se Fair-code incomodar)
- [ ] Agentes 3–7 no Dify (Compliance, Comercial, Suporte, Financeiro)
- [ ] Langfuse self-host se tracing do Dify não bastar (decisão de gate)
- [ ] Letta se algum agente precisar de memória de longo prazo

### Gate de PoC (fim do mês 1)
**Aprovado se:** agentes rodam 7 dias sem intervenção · evals passam em CI · custo LLM ≈ R$ 0 (só free tiers) · auditoria mostra o que cada agente fez.
**Falhou se:** rate limits dos free tiers inviabilizam a rotina → decidir quais agentes sobem para pago (e com qual orçamento).

---

## 8. Riscos e mitigações

| Risco | Mitigação |
|-------|-----------|
| Free tiers mudam/expira (providers cortam) | OmniRoute roteia para fallback; revisar catálogo mensalmente |
| Dify vira muito complexo para 1 pessoa | Começar com 2 agentes; code escape hatches quando precisar |
| n8n Fair-code limita revenda SaaS | Substituir por Sim (Apache-2.0) na mesma metáfora |
| Projeto OSS morre (como Helicone/AutoGen) | Escolher padrões (OpenAI-compat, MCP); documentar migração |
| Dados fiscais em homelab = responsabilidade | Backups + criptografia em repouso + runbook de incidente (já no plano) |

---

## 10. Decisão de Hosting ERPNext

**Decisão final (02/08/2026):** Homelab (dev/staging) → VPS Brasil (produção). Frappe Cloud como opção premium.

### Comparativo

| Fator | Frappe Cloud Frankfurt | VPS Brasil |
|-------|----------------------|------------|
| **Latência pra cliente** | 150–200ms | **<10ms** |
| **Custo com 10 clientes** | $250–500/mês (10 sites) | **~$50–100/mês** (1 VPS, 10 benches) |
| **App custom** | Requer plano ≥$25/mês | **Sem restrição** |
| **DevOps** | Zero (eles fazem) | **Já temos** (homelab NixOS) |
| **LGPD** | Adequação UE | **Dados no Brasil = sem transferência internacional** |
| **Upgrade major** | 1 clique | 4h anuais |

### Por que não Frappe Cloud (agora)

1. **Latência importa pra ERP** — cliente industrial em Londrina num servidor em Frankfurt sente os 200ms em cada transação
2. **Custo escala mal** — com 10 clientes seriam $250-500/mês vs $50-100/mês de uma VPS
3. **Você já tem a skill** — o custo real do seu DevOps é marginal porque você já opera o homelab
4. **App custom sem restrição** — `erpnext_br_compliance` roda sem precisar de tier pago

### Quando Frappe Cloud entra

- Se um cliente **exigir** managed hosting com SLA
- Se o custo do seu tempo superar $50/h (20+ clientes)
- Se você quiser terceirizar upgrades major (v16→v17)

### Fluxo de deploy

```
┌──────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Homelab     │────▶│  Homelab     │────▶│ VPS Brasil       │
│  Dev bench   │     │  Staging     │     │ Produção cliente │
│  codar +     │     │  validar com │     │ bench + site     │
│  homologação │     │  cliente     │     │ monitor + backup │
└──────────────┘     └──────────────┘     └──────────────────┘
```

---

## 11. Fontes (hosting)

- Frappe Cloud Pricing: frappe.io/cloud/pricing
- ECOSIRE: erpnext-hosting-options-compared (ecosire.com)
- Frappe Forum: discuss.frappe.io (self-hosting vs cloud)
- Res. CD/ANPD 32/2026: transferência internacional de dados
- Hetzner: hetzner.com (CPX31 ~$16/mês)

- Dify: github.com/langgenius/dify (138k stars) · dify.ai · reviews 2026
- n8n: github.com/n8n-io/n8n · n8nTrace · n8n-sentinel · blog n8n (audit trail)
- Sim: sim.ai · 29k stars · Apache-2.0 · YC X25
- Langflow/Flowise: comparativos 2026 (DataStax/IBM)
- LangGraph: github.com/langchain-ai/langgraph (MIT, 38k) · LangSmith Platform self-host (Enterprise)
- MS Agent Framework: GA 1.0 abr/2026 · AutoGen maintenance mode · AG2 fork
- Evals: promptfoo.dev (usado OpenAI/Anthropic) · DeepEval · Opik · Langfuse (MIT, ClickHouse) · Helicone (maintenance mar/2026)
- OmniRoute: github.com/diegosouzapw/OmniRoute · omniroute.online · free tiers wiki
- Portkey: gateway ativo · LiteLLM: alternativa
