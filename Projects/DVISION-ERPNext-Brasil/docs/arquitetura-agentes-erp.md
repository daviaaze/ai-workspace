# Arquitetura: Agentes × ERPNext — Integração, Packs, Monitoramento

> **Data:** 30/07/2026 · **Contexto:** homelab (Dify + n8n + OmniRoute + Promptfoo) ↔ ERPNext v16 (produto, VPS Brasil)
> **Princípio:** agentes são externos ao Frappe — acessam via MCP/REST/Webhooks, nunca com acesso irrestrito de shell.

---

## 1. Vias de Integração (Agente → ERP)

```
┌─────────────────────────────────────────────────────────────────┐
│  AGENTE (Dify/n8n, homelab)                                     │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ ① MCP Server (recomendado)                                │  │
│  │   tools: criar_pedido, consultar_estoque, emitir_nfe      │  │
│  │   Auth: OAuth2 (cliente MCP)                              │  │
│  │   Endpoint: /api/method/app.mcp.handle_mcp                │  │
│  │   Schema: automático via docstrings (frappe_mcp)          │  │
│  │   Registro: cada tool = função no app Frappe              │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ ② REST API (whitelisted methods)                          │  │
│  │   @frappe.whitelist() em server scripts ou DocType events  │  │
│  │   Uso: operações simples, status, consultas rápidas        │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ ③ Webhooks (Event Streaming)                              │  │
│  │   ERP → Agente: "nota rejeitada", "venda criada"          │  │
│  │   Frappe configura URL de callback no webhook             │  │
│  │   Uso: notificações assíncronas (ideal para agente cron)  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.1 MCP Server — o caminho principal

- **Oficial:** `frappe/mcp` (github.com/frappe/mcp) — Streamable HTTP MCP server dentro do próprio app Frappe, tools com inputSchema automático, OAuth2.
- **Status:** ⚠️ experimental (só Tools, sem resources/prompts ainda, breaking changes sem aviso) — ideal para PoC.
- **Alternativa produção:** `mascor/frappe-mcp-server` (permissões granulares + audit logging, fork maduro da comunidade).
- **Cada tool roda no contexto do usuário Frappe** → permissões (roles) + audit log do Frappe salvam quem fez o quê.

### 1.2 REST API (whitelisted)

- **Frappe nativo:** `@frappe.whitelist()` expõe métodos como endpoint REST.
- **Uso típico:** consultar status de um documento, disparar script, validar dados.
- **Vantagem:** simples, não requer biblioteca extra, versão estável.
- **Desvantagem:** sem schema descoberta automática (o agente precisa saber o que chamar).

### 1.3 Webhooks (Event Streaming)

- **VPS Brasil** tem suporte nativo a webhooks (eventos como `on_submit`, `on_cancel`, `on_update`).
- **Uso típico:** agente cron (n8n) recebe notificação de nota rejeitada → dispara ação corretiva.
- **Vantagem:** comunicação assíncrona, não precisa de polling.

---

## 2. Vias de Integração (ERP → Agente)

```
┌─────────────────────────────────────────────────────────────────┐
│  ERPNext                                                         │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ ④ Event Streaming (webhook)                                │  │
│  │   "NF-e rejeitada" → webhook → n8n → Dify (agente fiscal)  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ ⑤ Error Log + Bench Exporter                               │  │
│   │   Frappe.Error.Log → n8n coleta → alerta no agente        │  │
│   │   bench-exporter → Prometheus → Grafana → alerta no n8n   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Packs Verticais (PME por modalidade)

### 3.1 Conceito

Cada modalidade de PME brasileira (indústria, comércio varejista, transportadora, agronegócio, prestador de serviços) tem um **pack** — um conjunto de parametrizações + templates que o Agente Produto instancia no ERPNext do cliente.

### 3.2 O que cada pack contém

| Componente | Exemplo (pack_industria) |
|------------|--------------------------|
| DocTypes personalizados | Ordem de Produção customizada, Roteiro de Fabricação |
| Campos customizados | NCM, CEST, MVA, alíquota IBS/CBS por produto |
| Validações (server scripts) | CST × CFOP × regime tributário |
| Print formats | DANFE, etiqueta de produto, romaneio |
| Report templates | SPED Fiscal, SPED Contribuições |
| Automações (n8n) | Cron de apuração mensal, envio de SPED ao contador |
| Dashboard (insights) | Margem por produto, inadimplência, estoque crítico |
| Prompt do agente fiscal | Regras de tributação específicas da vertical |

### 3.3 Pipeline de criação de um pack

```
① DISCOVERY (consultor/agente de implantação)
   Cliente piloto → entrevista → NCMs usados, CFOPs, regime, MVA, impressos

② AGENTE PRODUTO (Dify)
   RAG na base fiscal + templates do pack genérico
   → Gera código: DocTypes, campos, validações, print formats
   → commit + PR no repo erpnext_br_compliance

③ CI/CD (GitHub Actions)
   bench build → migrate → test → Promptfoo eval (verifica prompt do agente)

④ DEPLOY
   bench homelab (staging) → valida com contador → VPS Brasil (produção)

⑤ EXTRAPOLAÇÃO (após 2+ pilotos na mesma vertical)
   Agente Produto analisa diferenças entre os 2 pilotos e extrai
   regras paramétricas → template v2 do pack
   Próximo cliente na mesma vertical: implanta em ~40h (era 80h)
```

### 3.4 Packs planejados (Fase 0–4)

| Pack | Vertical | Cliente típico | Prioridade | Roadmap |
|------|----------|----------------|------------|---------|
| `pack_industria` | Indústria geral (20-80 func.) | Moveleiro, metalúrgico, plástico | 🔴 Alta | Fase 0-1 |
| `pack_industria_moveleiro` | Indústria moveleira (sub) | Fábrica de móveis | 🟡 Média | Fase 2 |
| `pack_industria_vestuario` | Confecção/vestuário | Fábrica de roupas | 🟢 Baixa | Fase 3 |
| `pack_agro` | Agronegócio | Produtor rural, cooperativa | 🟢 Baixa | Fase 4 |
| `pack_servicos` | Prestador de serviços | Escritório, consultoria | 🟢 Baixa | Fase 2 |
| `pack_comercio` | Comércio varejista | Loja física, e-commerce | 🟢 Baixa | Fase 3 |

---

## 4. Monitoramento das Plataformas dos Clientes

### 4.1 Matriz de monitoramento

| Camada | Ferramenta | O que monitora | Alerta |
|--------|-----------|----------------|--------|
| **VPS Brasil** | Prometheus + Grafana + bench-exporter | CPU, requests, jobs, filas, deploys | Resource starvation, failed deploy |
| **Bench** | **bench-exporter** (Prometheus) | Memória, usuários ativos, apps por site | Pico de memória, site slow |
| **Host** (self-host) | Node exporter + Grafana + Uptime Kuma | Disco, rede, SSL, uptime | Queda, certificado expirando |
| **App** | Error Log do Frappe + frappe_sentry | Erros por DocType, rejeição fiscal, integração | Erro crítico no fiscal |
| **Agente Suporte** (n8n) | Consome todos os alertas + API Frappe | "certificado A1 expira em 30d", "fila NFE travada" | Ticket proativo pro cliente |
| **Product analytics** | **PostHog self-hosted** (no homelab) | Onboarding, funis, feature usage, sessões | Drop-off no onboarding |

### 4.2 Custo de observabilidade

| Ferramenta | Licença | Custo (ano 1) |
|------------|---------|---------------|
| Prometheus + Node exporter | Apache-2.0 | R$ 0 |
| Grafana | AGPL | R$ 0 |
| bench-exporter | MIT | R$ 0 |
| Uptime Kuma | MIT | R$ 0 |
| PostHog self-hosted | MIT | **~R$ 250/mês** (infra Hetzner) |
| Datadog | Comercial | **~R$ 3.000/mês** ❌ (inviável ano 1) |

**Decisão:** PostHog self-hosted no homelab para product analytics + Grafana/Prometheus para infra. Datadog apenas quando um cliente enterprise exigir e pagar por ele.

### 4.3 Roteiro de atualizações

| Tipo | Disparo | Quem aplica | Janela |
|------|---------|-------------|--------|
| NT nova (SEFAZ) | Agente Fiscal detecta | Dev (via bench update) | ≤48h |
| Patch de segurança | Agente Fiscal agenda + dev aplica | Dev (via bench update) | ≤5 dias úteis |
| Minor release (v16.x) | Agente Fiscal agenda | Dev (via bench update) | ≤5 dias úteis |
| Major release (v17) | Roadmap + testes | Dev + PoC em staging | 30 dias |

### 4.4 Acesso remoto (segurança)

- **Clientes em VPS Brasil:** apenas API REST + MCP — nenhum acesso SSH.
- **Clientes self-host (futuro):** chave SSH por cliente, nunca senha; todas as ações registradas em audit log.
- **Automação via bench:** `bench update` agendado pelo Agente Fiscal via SSH controlado, com log de saída no homelab.

---

## 5. Observabilidade e Métricas de Produto (PostHog)

### 5.1 Por que PostHog self-hosted

- **LGPD:** dados de uso dos clientes ficam no homelab (nunca saem do país/controle do operador).
- **Custo:** self-host = ~R$ 250/mês de infra (contra R$ 3.000+ de Datadog).
- **Funcionalidades:** product analytics, session replay, feature flags, experimentação (A/B tests de UI), surveys.
- **Eventos que PostHog captura:**
  - `nfe_emitida` — quantas, tempo médio, taxa de rejeição
  - `sped_gerado` — frequência, erros
  - `onboarding_step` — onde o cliente trava
  - `feature_usage` — quais módulos mais usam
  - `error_occurred` — correlação com feature flag

### 5.2 Integração com o ERP

```python
# Frappe app → PostHog via webhook ou script
import requests

def track_event(event_name, properties):
    """PostHog capture via API (self-hosted)."""
    POSTHOG_HOST = "https://posthog.homelab.internal"  # no homelab
    POSTHOG_API_KEY = "phc_xxx"

    requests.post(
        f"{POSTHOG_HOST}/capture/",
        json={
            "api_key": POSTHOG_API_KEY,
            "event": event_name,
            "properties": properties,
            "distinct_id": frappe.session.user,
        },
    )
```

---

## 6. MCP — O Elo Central

### 6.1 Opções de MCP Server para Frappe

| Projeto | Mantenedor | Status | Diferencial |
|---------|-----------|--------|-------------|
| `frappe/mcp` | Frappe (oficial) | ⚠️ experimental | Tools com schema automático, OAuth2, roda no app |
| `mascor/frappe-mcp-server` | Comunidade | ✅ produção | Permissões granulares + audit logging |
| `vyogotech/frappe-mcp-server` | Comunidade | ✅ produção | Suporta qualquer LLM via OpenAI-compat |
| `m7amedenho/mcp-frappe` | Comunidade | ✅ produção | Foco em ERPNext 16 via REST API |

### 6.2 Como o agente usa MCP

```
Dify Agent (workflow) → MCP tool → frappe_mcp → ERPNext
                                    │
                                    │ OAuth2 → permissões do usuário
                                    │ Audit log → quem fez o quê
                                    │ Schema → agente sabe os parâmetros
                                    │
                                    └─ tools: consultar_pedido, emitir_nfe,
                                      criar_cliente, status_fiscal
```

**Exemplo real:** Agente Financeiro (Dify) tem uma tool MCP `consultar_contas_pagar` que executa `frappe.get_list("Purchase Invoice", filters={"status": "To Pay"})` no contexto do usuário do cliente. O resultado volta como JSON → agente decide se dispara alerta de fluxo de caixa.

### 6.3 Decisão

- **PoC (Fase 0):** usar `frappe/mcp` oficial (experimental, mas é o caminho oficial do Frappe).
- **Produção (Fase 1+):** migrar para `mascor/frappe-mcp-server` (audit logging + permissões granulares).
- **Dify já suporta MCP nativamente** → adiciona MCP como tool de agente sem código extra.

---

## 7. Visão Geral (Diagrama de Contexto)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HOMELAB (fábrica)                              │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Dify (plataforma de agentes)                                        │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │  │
│  │  │Fiscal│ │Produ.│ │Compl.│ │Comer.│ │Suport│ │Finan.│ │Growth│   │  │
│  │  └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘ └──┬───┘   │  │
│  │     │        │        │        │        │        │        │        │  │
│  │     └────────┴────┬───┴────────┴───┬────┴────────┴───┬────┘        │  │
│  │                   │               │                 │              │  │
│  │            ┌──────▼──────┐  ┌─────▼──────┐  ┌───────▼──────┐      │  │
│  │            │  MCP Client │  │ REST API   │  │  Webhooks    │      │  │
│  │            └──────┬──────┘  └─────┬──────┘  └───────┬──────┘      │  │
│  └───────────────────┼───────────────┼──────────────────┼─────────────┘  │
│                      │               │                  │                │
│  ┌───────────────────┼───────────────┼──────────────────┼─────────────┐  │
│  │  n8n (cron)       │               │                  │              │  │
│  │  Monitores/integrações           │                  │              │  │
│  │  ┌────────────────┘              │                  │              │  │
│  │  │  webhook_handler ←────────────┘                  │              │  │
│  └──┼──────────────────────────────────────────────────┘              │  │
│      │                                                                  │
│  ┌───▼──────────────────────────────────────────────────────────────┐  │
│  │  OmniRoute (gateway LLM)                                         │  │
│  │  free tiers → fallback pago                                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Observabilidade                                                 │  │
│  │  PostHog (product analytics) · Grafana/Prom (infra)              │  │
│  │  Promptfoo (evals/A-B em CI) · Langfuse (tracing)               │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                          │
                          │ MCP / REST / Webhooks
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       ERPNext (produto)                                 │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  VPS Brasil = produção dos clientes                             │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │  erpnext_br_compliance                                     │  │  │
│  │  │  ├── frappe_mcp (tools MCP)                                │  │  │
│  │  │  ├── whitelisted API (REST)                                │  │  │
│  │  │  ├── webhooks (Event Streaming)                            │  │  │
│  │  │  ├── PostHog integration (capture events)                  │  │  │
│  │  │  └── bench-exporter → Prometheus                           │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                                                                  │  │
│  │  Client 1 │ Client 2 │ ... │ Client N (até 10)                  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  Bench homelab (staging/desenvolvimento)                                │
│  └─ erpnext_br_compliance (mesmo repo, branch dev)                     │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Decisões e Justificativas

| Decisão | Opção | Por quê |
|---------|-------|---------|
| Via principal de integração | **MCP** (frappe_mcp oficial) | Schema descoberta automática, OAuth2, audit log, Dify suporta nativamente |
| Fallback de integração | REST API (whitelisted) | Simples, estável, sem dependência extra |
| Notificações do ERP | Webhooks (Event Streaming) | Assíncrono, sem polling, n8n consome |
| Produtor de código (packs) | Agente Produto (Dify) como gerador + CI | Reproduzível, versionado, auditável |
| Padrão do pack | India Compliance (referência estrutura) | Frappe valida como padrão de compliance app |
| Monitoramento | Grafana/Prometheus + bench-exporter | Cobertura completa, custo zero de licença |
| Product analytics | PostHog self-hosted | LGPD, custo ~R$ 250/mês, feature flags + experimentação |
| MCP PoC | frappe/mcp oficial | Experimental, mas é o caminho oficial do Frappe |
| MCP produção | mascor/frappe-mcp-server | Audit logging + permissões granulares |
| Updates automáticos | Bench update via script (Agente Fiscal) | ≤48h para NT, ≤5 dias úteis para patch |
| Acesso remoto | API + SSH controlado por chave | Nunca acesso irrestrito de shell |

---

## 9. Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| MCP oficial experimental quebra | Dify pode cair para REST API (whitelisted) no mesmo dia |
| Pack de um cliente quebra outro | Cada pack é um app Frappe separado em sites isolados |
| PostHog self-host vira custo alto | Crossover ~2M events/mês; abaixo disso, cloud é mais barato |
| Cliente exige Datadog | É custo do cliente, repassado na mensalidade |
| Ferramenta OSS morre (Helicone syndrome) | Padrões abertos (MCP, OpenAI-compat); documentar migração |