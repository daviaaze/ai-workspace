# DVISION ERPNext Brasil

**ERPNext AI-First para o mercado brasileiro — core fiscal próprio, 1 founder + agentes, até 10 clientes pagantes.**

| Campo | Valor |
|-------|-------|
| **Founder** | Davi Azevedo, Londrina/PR |
| **Data do plano** | 30/07/2026 |
| **Modelo** | Open core (GPLv3 + módulos proprietários) |
| **ICP** | Indústrias 20–80 funcionários, regime normal (CRT=3) |
| **Concorrente direto** | Nomus ERP Industrial (R$ 1.290–4.290/mês) |

## Missão

ERP industrial completo a preço de componente fiscal + implantação 5–10× mais barata que TOTVS/SAP, viabilizado por arquitetura AI-First onde cada função de negócio é um agente.

## Estrutura do projeto

```
DVISION-ERPNext-Brasil/
├── README.md              ← este arquivo
├── docs/
│   ├── plano-de-acao.md   ← plano completo (original)
│   ├── roadmap.md         ← roadmap faseado com datas
│   ├── arquitetura-fiscal.md  ← core fiscal, DF-e, SPED, tributos
│   ├── modelo-negocio.md  ← precificação, tiers, unit economics
│   ├── compliance.md      ← LGPD, contratos, ISO, riscos
│   ├── agentes.md         ← 7 agentes AI-First + infraestrutura
│   ├── capacity-plan.md   ← horas, KPIs, gatilhos de contratação
│   ├── pesquisa-tecnica.md ← ERPNext v16, libs fiscais, Calculadora RFB, Pluggy/Open Finance
│   ├── stack-homelab.md   ← decisão da stack de agentes (Dify/OmniRoute/Promptfoo) + hosting
│   ├── arquitetura-agentes-erp.md ← integração agentes × ERPNext (MCP, REST, webhooks, packs, monitoramento, PostHog)
│   └── deploy-homelab.md   ← guia de deploy: Dify, n8n, Frappe bench, PostHog, VPS Brasil
├── knowledge/
│   ├── README.md                   ← índice + instruções de consulta
│   ├── erpnext-v16-features.md     ← release notes, novidades, changelogs
│   ├── erpnext-docs-index.md       ← seções da documentação oficial indexadas
│   ├── frappe-framework-guide.md   ← hooks, API, REST, DocTypes, permissões
│   ├── brazil-fiscal-libs.md       ← nfelib, PyNFe, BrazilFiscalReport, Calculadora RFB
│   ├── community-monitoring.md     ← canais, fóruns, issues, releases, eventos
│   ├── upgrade-patches.md          ← upgrade path, patches, segurança, migrações
│   ├── india-compliance-reference.md ← estrutura do India Compliance (padrão de referência)
│   ├── development-patterns.md     ← padrões de desenvolvimento, hooks, DocTypes, MCP
│   └── erpnext-br-apps.md          ← apps BR existentes, comparação, análise
├── data/
│   ├── Matriz_Compliance_e_Mercadoria_DVISION_2026-07-30.csv
│   ├── Benchmarks_Precificacao_ERP_Brasil_2026-07-30.csv
│   └── Custos_Operacionais_DVISION_Ano1_2026-07-30.csv
└── tasks/
    └── CHECKLIST.md        ← tarefas priorizadas do plano
```

## Gates do plano

| Gate | Prazo | Critério | Ação se falhar |
|------|-------|----------|----------------|
| **Gate 1** | Jan/2027 | ≥3 clientes, ≥1 case, implantação ≤80h, 0 incidentes graves | Corrigir antes de escalar vendas |
| **Gate 2** | Abr/2027 | MRR ≥R$ 8k, churn <3%, suporte <2h/mês/cliente | — |
| **Gate 3** | Jul/2027 | 10 clientes, NPS ≥8, MRR ≥R$ 13k, LTV:CAC ≥5× | Plano ano 2 (self-service ou time) |

## Próximos passos imediatos (2 semanas)

1. Verificar ato conjunto RFB/CGIBS (prometido jul/2026)
2. Contratar advogado — pacote contratos + PI + DPA (R$ 3–6k)
3. VPS Brasil + repositório + CI + Agente Fiscal v1
4. NF-e modelo 55 em homologação (hello world do core fiscal)
5. DPO formalizado + RoPA v1 + runbook de incidente
6. Lista de 30 prospects + 10 contadores
7. Primeiro conteúdo: "Reforma Tributária: sua NF-e está pronta?"