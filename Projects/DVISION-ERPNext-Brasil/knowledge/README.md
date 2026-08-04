# Knowledge Base — ERPNext para Agentes da Fábrica DVISION

> **Propósito:** Repositório de conhecimento indexado sobre ERPNext, Frappe Framework, libs fiscais brasileiras, comunidade, e práticas de desenvolvimento.  
> **Uso:** Os agentes (Dify) consultam este repositório como RAG antes de gerar código, responder perguntas ou tomar decisões técnicas.  
> **Atualização:** Sempre que um novo release, NT fiscal ou mudança de API for detectada pelos agentes de monitoramento, este repositório deve ser atualizado.

---

## Estrutura

```
knowledge/
├── README.md                           ← este arquivo (índice + instruções)
├── erpnext-v16-features.md             ← release notes, novidades, changelogs
├── erpnext-docs-index.md               ← seções da documentação oficial indexadas
├── frappe-framework-guide.md           ← hooks, API, REST, DocTypes, permissões
├── brazil-fiscal-libs.md               ← nfelib, PyNFe, BrazilFiscalReport, Calculadora RFB
├── community-monitoring.md             ← canais, fóruns, issues, releases, eventos
├── upgrade-patches.md                  ← upgrade path, patches, segurança, migrações
├── india-compliance-reference.md       ← estrutura do India Compliance (padrão de referência)
├── development-patterns.md             ← padrões de desenvolvimento, hooks, DocTypes, MCP
└── erpnext-br-apps.md                  ← apps BR existentes, comparação, análise
```

## Fontes Indexadas

As seguintes fontes foram indexadas via `search_docs` e estão disponíveis para consulta contextual:

### Documentação Oficial
- **ERPNext Docs:** docs.erpnext.com (3 níveis de profundidade)
- **Frappe Framework Docs:** docs.frappe.io/framework (introdução, API, REST, hooks, bench)
- **Frappe Cloud Docs:** docs.frappe.io/cloud (monitoramento, deploy, arquitetura)
- **Frappe Bench Docs:** docs.frappe.io/framework/user/en/bench/bench-commands
- **ERPNext v16 Release:** frappe.io/releases/version-16, frappe.io/erpnext/version-16

### Comunidade
- **ERPNext Fiscal BR:** github.com/brunoobueno/erpnext_fiscal_br (estrutura, README, docstrings)
- **India Compliance:** github.com/resilient-tech/india-compliance (estrutura de referência)
- **Frappe MCP:** github.com/frappe/mcp (README, código, tools)
- **Calculadora RFB:** github.com/nfe/rtc-calculadora-offline

### Fóruns
- **Regional Brasileira (Brazil Compliance) NFE:** discuss.frappe.io/t/89121
- **Grupo ERPNext Brasil:** discuss.frappe.io/t/79310
- **BRASIL - Parceiros:** discuss.frappe.io/t/89838
- **v15 → v16 Upgrade Guide:** discuss.frappe.io/t/159062
- **Scaling Regional Localisation:** discuss.frappe.io/t/133795

## Como os Agentes Usam Este Repositório

1. **Agente Produto (geração de código):** consulta `development-patterns.md` + `india-compliance-reference.md` + `erpnext-docs-index.md` para gerar DocTypes, hooks, validações
2. **Agente Fiscal (NF-e, tributos):** consulta `brazil-fiscal-libs.md` + `erpnext-br-apps.md` + `community-monitoring.md` para regras fiscais, prazos de NT, bibliotecas
3. **Agente Suporte (implantações):** consulta `upgrade-patches.md` + `erpnext-v16-features.md` para roteiros de upgrade e troubleshooting
4. **Agente Growth (conteúdo):** consulta `community-monitoring.md` + `erpnext-v16-features.md` para novidades, releases, eventos
5. **Agente Compliance (LGPD, contratos):** consulta `community-monitoring.md` para riscos de licenciamento e mudanças regulatórias

## Fluxo de Atualização

1. **Agente Fiscal (n8n cron):** monitora releases do ERPNext + discuss.frappe.io + GitHub Issues → detecta mudança → abre PR no repositório → atualiza o arquivo relevante
2. **Agente Produto:** quando um novo padrão de desenvolvimento é descoberto, adiciona em `development-patterns.md`
3. **Reindexação:** sempre que um arquivo é atualizado substancialmente, reindexar via `index_docs` para manter a busca RAG fresca