# Apps Brasileiros para ERPNext — Análise e Comparação

> **Propósito:** analisar apps BR existentes para decidir o que referenciar, o que evitar e onde construir do zero.

---

## 1. erpnext_fiscal_br (brunoobueno)

| Campo | Valor |
|-------|-------|
| Versão | **v15** (não compatível com v16) |
| Funcionalidades | NF-e, NFC-e, cancelamento, CC-e, inutilização, DANFE PDF |
| Licença | MIT |
| Status | ✅ Ativo (v15) |
| GitHub | https://github.com/brunoobueno/erpnext_fiscal_br |
| Contato | contato@alquimiaindustria.com.br |

### Análise
**Pontos fortes:**
- Estrutura completa (DocTypes, API, services, fixtures, public)
- Suporte a múltiplos regimes tributários (Simples Nacional, Lucro Presumido, Lucro Real)
- Suporte a múltiplas empresas
- DANFE PDF funcional
- Fixtures de CFOP

**Pontos fracos:**
- **v15 apenas** — sem suporte a v16 (Query Builder, breaking changes)
- **Sem IBS/CBS** — não implementa NT 2025.002 (Reforma Tributária)
- Sem suporte a CT-e/MDF-e
- Código pode ter padrões questionáveis (não passou pelo review do Frappe Build)
- Documentação em português apenas

**Decisão:** ❌ **Não usar como base.** Referenciar para regras fiscais já resolvidas (CFOP/CST, DANFE), mas construir do zero em v16 com suporte a IBS/CBS.

## 2. ECOSIRE Brazil NF-e / SPED Compliance

| Campo | Valor |
|-------|-------|
| Tipo | Comercial (build-to-order) |
| Preço | a partir de US$ 299 |
| Versão | v15, v16 (sob encomenda) |
| URL | https://ecosire.com/ur/apps/erpnext/erpnext-brazil-nfe-sped |

**Análise:** Solução comercial, feita sob encomenda. Cobre NF-e, DANFE, SPED Fiscal e Contábil. Não é open source — sem acesso ao código para auditoria ou customização.

**Decisão:** ❌ **Não usar.** Preço incompatível com modelo open core (R$ 1.600+ por cliente), sem acesso ao código.

## 3. India Compliance (referência estrutural)

| Campo | Valor |
|-------|-------|
| Versão | v15/v16 |
| Funcionalidades | GST (India), GSTR-1, e-invoicing |
| Licença | GPL v3 |
| GitHub | https://github.com/resilient-tech/india-compliance |
| Status | ✅ Produção, Frappe Cloud Marketplace |

**Análise:** Usado como referência de estrutura (ver `india-compliance-reference.md`). O padrão de compliance app que a Frappe aprova.

## 4. Conclusão e Estratégia

| App | Uso | Motivo |
|-----|-----|--------|
| erpnext_fiscal_br | **Referência** (regras fiscais, fixtures) | Único app BR open source funcional, mas v15 |
| India Compliance | **Padrão estrutural** | Aprovado pela Frappe, estrutura limpa |
| ECOSIRE | ❌ Descartado | Comercial fechado |
| erpnext_br_compliance | **Construir do zero** | v16, IBS/CBS, Reforma Tributária, MCP, audit-ready |

**O que aproveitar do erpnext_fiscal_br:**
- Fixtures de CFOP (JSON)
- Lógica de validação de CNPJ/CPF
- Estrutura de DANFE (PDF)
- Mapeamento de CST × CFOP × regime tributário

**O que construir do zero:**
- DocTypes em v16 com Query Builder
- Suporte a IBS/CBS (NT 2025.002 v1.40)
- Integração com Calculadora RFB (Docker)
- MCP tools para agentes
- SPED Fiscal/Contribuições
- CT-e/MDF-e (Fase 3)
- Bloco K (Fase 4)