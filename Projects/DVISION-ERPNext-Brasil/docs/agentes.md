# Agentes AI-First — Organização

Cada função de empresa "de ponta" vira um agente com dono, KPI e fronteira clara do que sobe para o humano.

## Tabela de agentes

| # | Agente | Função | Automatiza | Fica com você | KPI |
|---|--------|--------|------------|---------------|-----|
| 1 | **Fiscal/Tributário** | Eng. fiscal | Monitorar ENCAT/SEFAZ/portal nacional (RSS + scraping); baixar NTs, XSDs, tabelas; abrir issues com diff de layout; rodar suíte de testes em homologação; validar XMLs | Prioridade de adequação; NT ambígua; homologação presencial | 0 rejeições por layout desatualizado; patch ≤5 dias úteis |
| 2 | **Produto/Engenharia** | Dev team | Geração de código Frappe (DocTypes, server scripts, testes); code review; CI/CD; migrações; docs; changelog | Arquitetura; decisões de produto; revisão final de PR fiscal | Lead time feature <1 semana; cobertura de testes fiscal |
| 3 | **Compliance-Jurídico** | Jurídico/DPO | Manter DPA/RoPA/termos; monitorar ANPD e diário oficial; checklist por cliente; templates de resposta | Relação com advogado; incidentes; assinatura de contratos | 100% contratos c/ PI + DPA; incidente <3 dias úteis |
| 4 | **Comercial/Precificação** | Vendas/CS | Qualificar leads; gerar proposta com ROI (template); follow-ups; CRM; calculadora de preço | Discovery; negociação; fechamento; canal contador | Proposta <24h; CAC no alvo |
| 5 | **Operações/Suporte** | Customer ops | L1 com base de conhecimento (deflexão ≥60%); monitoramento (uptime, filas, certificados); runbooks de contingência; alertas | L2/L3; incidentes fiscais; relacionamento | Suporte <2h/cliente/mês; L1 sem humano ≥60% |
| 6 | **Financeiro** | Financeiro | Faturamento recorrente; cobrança; conciliação; dashboard unit economics; DRE | Precificação final; caixa; impostos com contador | Inadimplência <2%; DRE no dia 5 |
| 7 | **Growth/Conteúdo** | Marketing | SEO sobre Reforma + ERP; cases públicos; newsletter contadores; monitoramento Nomus/Odoo | Posicionamento; parcerias; comunidade Frappe | 4 conteúdos/mês; inbound ≥30% dos leads |

## Infraestrutura dos agentes

- Repositório Git com CI como "sistema nervoso"
- Cron jobs para monitores (SEFAZ/ANPD/ENCAT)
- LLM com RAG sobre base de conhecimento fiscal e de suporte
- Frappe Cloud como runtime multi-tenant
- Vault de segredos para certificados A1 dos clientes

## Regra de ouro de escalonamento

- Todo trabalho repetido **3 vezes** vira automação/agente
- Toda automação que falha **2 vezes seguidas** no mesmo ponto vira runbook com alerta para você