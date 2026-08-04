# Índice da Documentação Oficial do ERPNext

> **Fonte:** docs.erpnext.com (indexado em 30/07/2026, 100+ páginas)
> **Uso:** consulta rápida pelos agentes sobre módulos, configuração e fluxos

---

## 1. ERPNext User Manual (docs.erpnext.com)

### Módulos Cobertos
- **Accounting:** AP/AR, General Ledger, Budget, Tax Rules, Cost Centers
- **Manufacturing:** BOM, Work Order, Job Card, Production Plan, MRP
- **Stock:** Warehouse, Stock Entry, Stock Reconciliation, Serial/Batch
- **Selling:** Quotation, Sales Order, Sales Invoice, POS, Pricing Rule
- **Buying:** Material Request, Purchase Order, Purchase Invoice, Supplier
- **CRM:** Lead, Opportunity, Customer, Campaign
- **HR:** Employee, Leave, Attendance, Payroll, Expense Claim
- **Projects:** Project, Task, Timesheet
- **Assets:** Asset, Asset Movement, Depreciation
- **Support:** Ticket, Warranty, Service Level Agreement

### Seções Importantes
- **Setup:** Company, Chart of Accounts, Fiscal Year, Tax Templates
- **Regional:** Localizações por país (incluindo India GST, UK, EUA, etc.)
- **Reports:** Todos os reports padrão do ERPNext
- **Print Formats:** Customização de DANFE, Nota Fiscal, etc.

## 2. Frappe Framework Docs (docs.frappe.io/framework)

### 2.1 Conhecimento Essencial
- **Hooks:** https://docs.frappe.io/framework/user/en/python-api/hooks — todos os hooks do framework
- **Document API:** https://docs.frappe.io/framework/user/en/api/document — `frappe.get_doc()`, `frappe.new_doc()`, etc.
- **Database API:** https://docs.frappe.io/framework/user/en/api/database — `frappe.db.get_list()`, `frappe.db.sql()`, Query Builder (v16 tem breaking changes)
- **Developer API:** https://docs.frappe.io/framework/user/en/api — overview da API Python
- **REST API:** https://docs.frappe.io/framework/user/en/api/rest — API REST gerada automaticamente para todos os DocTypes

### 2.2 Frappe Hooks (mais usados)
```python
# hooks.py
app_name = "erpnext_br_compliance"
app_title = "ERPNext BR Compliance"
app_publisher = "DVISION Serviços Digitais"
app_description = "Brazilian fiscal compliance for ERPNext"
app_license = "GNU General Public License (v3)"
required_apps = ["frappe/erpnext"]

# Document Events — hook em DocTypes padrão do ERPNext
doc_events = {
    "Sales Invoice": {
        "on_submit": "erpnext_br_compliance.api.nfe.on_sales_invoice_submit",
        "on_cancel": "erpnext_br_compliance.api.nfe.on_sales_invoice_cancel",
    },
    "Purchase Invoice": {
        "on_submit": "erpnext_br_compliance.api.nfe.on_purchase_invoice_submit",
    },
}

# Permissions
permissions = "erpnext_br_compliance.permissions"

# Fixtures
fixtures = ["NCM", "CFOP", "CST"]

# Custom fields
custom_fields = {
    "Sales Invoice": [
        {"fieldname": "nfe_access_key", "fieldtype": "Data", "label": "Chave de Acesso NF-e"},
    ]
}
```

### 2.3 Bench Commands
**Fonte:** https://docs.frappe.io/framework/user/en/bench/bench-commands

```bash
bench new-app erpnext_br_compliance
bench get-app https://github.com/dvision/erpnext_br_compliance
bench --site site.local install-app erpnext_br_compliance
bench migrate
bench build
bench restart
bench --site site.local console
bench --site site.local run-tests
```

### 2.4 REST API
- Toda DocType tem CRUD automático via REST
- Endpoint: `/api/resource/{doctype}/{name}`
- Métodos whitelisted: `/api/method/{dotted.path}`
- Auth: Token (API Key + Secret) ou OAuth2

## 3. Frappe Cloud Docs (docs.frappe.io/cloud)

- **Monitoramento:** https://docs.frappe.io/cloud/sites/monitoring — CPU, requests, jobs, background jobs
- **Bench Analytics:** https://docs.frappe.io/cloud/bench-analytics — métricas por bench
- **Arquitetura:** https://www.youtube.com/watch?v=KIohic6ML5o — How Frappe Cloud works
- **Frappe Cloud Hybrid:** https://docs.frappe.io/cloud/servers/frappe-cloud-hybrid — self-host + Frappe Cloud
- **Security/FAQ:** https://docs.frappe.io/cloud/faq/architecture-and-security — RPO 24h, RTO <15min

## 4. Frappe Bench (github.com/frappe/bench)

- **Bench CLI:** https://docs.frappe.io/framework/user/en/bench/bench-commands
- **Bench Usage:** https://github.com/frappe/bench/blob/develop/docs/bench_usage.md
- **bench-exporter (Prometheus):** https://github.com/athul/bench-exporter — métricas para Grafana