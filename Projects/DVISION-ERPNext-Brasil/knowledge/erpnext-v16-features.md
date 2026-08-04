# ERPNext v16 — Features, Release Notes e Changelogs

> **Última atualização:** 30/07/2026 · **Versão atual:** v16.30.0 (lançada ~29/07/2026)
> **Release inicial:** 6/12/2025 (Final), 12/01/2026 (v16.0.0 tag)
> **Status:** Estável, produção-ready

---

## 1. Linha do Tempo de Lançamento

| Data | Evento |
|------|--------|
| 15/11/2025 | Beta Release |
| 06/12/2025 | Final Release (anunciado) |
| 12/01/2026 | v16.0.0 tag no GitHub |
| 29/07/2026 | v16.30.0 (mais recente) |

## 2. Destaques do v16 (fonte oficial: frappe.io/erpnext/version-16)

### 2.1 Accounting
- **Financial Report Templates:** P&L e Balanço Patrimonial com templates customizáveis, fórmula-driven, multi-empresa, compatível com IFRS
- **Purchase Expense Booking:** COGS visível com menos cliques
- **Automatic Closing Stock Posting:** para empresas que usam contabilidade periódica; "Get Balance" posta diferenças direto no razão
- **Consolidated Trial Balance Report:** visão consolidada de múltiplas empresas com conversão automática de moeda

### 2.2 Manufacturing
- **Material Requirements Planning (MRP):** workflow dedicado combinando forecasts, delivery schedules e lead times
- **Inward Subcontracting:** receber matéria-prima do cliente e manufaturar para ele
- **Serial and Batch Traceability Report:** rastreabilidade bidirecional (matéria-prima → cliente final)
- **Stock Reservation for Work Orders:** reserva de materiais para produção não ser interrompida
- **Landed Cost Voucher for Subcontracting Receipt:** frete, handling e duties em receipts de subcontratação

### 2.3 Performance (2x mais rápido)
- Cache de budget checks, pricing rules, stock quantities
- Cache de Authorization Control, Accounts Settings, Stock Settings
- Remoção de lookups redundantes em GL Entry, Stock Ledger Entry, Payment Ledger Entry
- Memória reduzida ~50% no relatório "Stock Ageing"
- Busca de preços usa cache, lookup único por item
- Carga de Customer/Supplier dashboards com permissão por empresa

### 2.4 Outras Novidades Relevantes
- **POS Improvements:** pagamento parcial, list-style item selector, Sales Invoice como opção
- **TDS refinado, Budgeting aprimorado, Print Formats melhorados**
- **SWIFT MT940 import** em Bank Statement Import
- **UTM Campaign/Source/Medium/Content** em documentos transacionais
- **Deprecation alerts** com data de remoção prevista
- **Permissão:** dashboard de Customer/Supplier só mostra empresas que o usuário pode acessar
- **Is Phantom BOM:** BOMs fantasma expandem para matéria-prima sem criar ordens de produção separadas

## 3. Release Cycle (v16.x)

O ERPNext segue um ciclo de releases contínuo. As releases v16.x são lançadas aproximadamente a cada 1-2 semanas com patches e features menores.

**Últimas releases (julho/2026):**
- v16.30.0 (29/07): Overdue Limit check, stock expense entries, Shipping Rule Cost Center opcional, várias correções
- v16.29.0: Project "On hold", Contact auto-link, Stock Summary sort, Bin recalculo
- v16.28.x: várias correções de stock, BOM, permissões

**Canais de release notes:**
- GitHub Releases: https://github.com/frappe/erpnext/releases
- Release Notes Workflow: https://github.com/frappe/erpnext/actions/workflows/release_notes.yml
- As release notes são geradas por IA (OpenAI gpt-5.4-mini), resumindo PRs e issues

## 4. Issues Abertas (relevantes)

- #57671: JV title issue (v16)
- #57603: Allocate Payment Entries to Sales Orders after Submit
- Issues tracker: https://github.com/frappe/erpnext/issues

## 5. Guia de Upgrade v15 → v16

**Fontes:**
- https://discuss.frappe.io/t/guide-to-upgrading-bench-frappe-and-erpnext-from-v15-to-v16-on-debian-12/159062
- https://github.com/frappe/erpnext/wiki/ (upgrade guide oficial)
- https://tcbinfotech.com/upgrade-erpnext-version-15-to-16/

**Passos resumidos:**
1. Atualizar bench e dependências
2. Backup completo (banco + arquivos)
3. Mudar branch para version-16
4. `bench update --patch`
5. `bench build`
6. Validar custom apps (podem quebrar)
7. Testar em staging antes de produção

**Cuidados conhecidos:**
- Custom apps podem precisar de atualizações de API
- Database migrations são irreversíveis
- Query Builder tem breaking changes em `get_list` e `get_all` (v16)
- Customer List View pode ficar vazia após upgrade (issue #52095)
- Atualizar Frappe junto com ERPNext é recomendado