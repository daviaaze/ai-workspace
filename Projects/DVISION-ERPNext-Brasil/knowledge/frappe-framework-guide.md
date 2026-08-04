# Frappe Framework — Guia para Agentes

> **Propósito:** guia de referência rápida para os agentes gerarem código Frappe compatível e seguirem os padrões corretos.

---

## 1. Estrutura de um App Frappe

```
app_name/
├── app_name/
│   ├── __init__.py
│   ├── hooks.py                  ← configuração principal
│   ├── app_name/                 ← DocTypes, pages, reports
│   │   ├── doctype/
│   │   │   └── meu_doctype/
│   │   │       ├── __init__.py
│   │   │       ├── meu_doctype.py        ← controller
│   │   │       ├── meu_doctype.json      ← schema (JS Object)
│   │   │       ├── meu_doctype.js        ← client script
│   │   │       └── test_meu_doctype.py   ← testes
│   │   └── report/
│   ├── api/                      ← endpoint methods
│   ├── public/                   ← JS/CSS customizados
│   ├── fixtures/                 ← dados padrão (JSON)
│   ├── patches.txt               ← patches de migração
│   └── templates/                ← Jinja templates
├── setup.py
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 2. Hooks Essenciais

### 2.1 Document Events (hook em DocTypes padrão)
```python
doc_events = {
    "Sales Invoice": {
        "on_submit": "erpnext_br_compliance.events.sales_invoice.on_submit",
        "on_cancel": "erpnext_br_compliance.events.sales_invoice.on_cancel",
        "validate": "erpnext_br_compliance.events.sales_invoice.validate",
    },
    "Item": {
        "validate": "erpnext_br_compliance.events.item.validate",
    },
}
```

### 2.2 Fixtures (dados que acompanham o app)
```python
fixtures = ["NCM", "CFOP", "CST", "CEST"]
```
Os fixtures são carregados automaticamente no `bench migrate`.

### 2.3 Custom Fields
```python
custom_fields = {
    "Sales Invoice": [
        {
            "fieldname": "nfe_access_key",
            "fieldtype": "Data",
            "label": "Chave de Acesso NF-e",
            "insert_after": "taxes_and_charges",
            "read_only": 1,
        },
        {
            "fieldname": "nfe_status",
            "fieldtype": "Select",
            "label": "Status NF-e",
            "options": "Não Emitida\nAutorizada\nCancelada\nRejeitada",
            "insert_after": "nfe_access_key",
        },
    ],
}
```

### 2.4 Permissions
```python
# Adicionar role ao app
# No hooks.py:
# add_to_permissions = ["erpnext_br_compliance"]

# Ou criar DocType de permissão manual
# Ver: https://docs.frappe.io/framework/user/en/guides/app-development/executing-code-on-doctype-events
```

## 3. DocType Controller

### 3.1 Eventos de DocType
```python
import frappe
from frappe.model.document import Document

class NFe(Document):
    def before_save(self):
        # Antes de salvar (validações)
        self.validate_ncm()

    def after_insert(self):
        # Depois de inserir no banco
        pass

    def on_submit(self):
        # Ao submeter
        self.emit_nfe()

    def on_cancel(self):
        # Ao cancelar
        self.cancel_nfe()

    def validate(self):
        # Validação (antes de qualquer save, inclusive drafts)
        if not self.cnpj:
            frappe.throw("CNPJ é obrigatório")

    def validate_ncm(self):
        # Validação customizada
        pass
```

### 3.2 Whitelisted Methods (REST API)
```python
@frappe.whitelist()
def get_nfe_status(nfe_name):
    """Endpoint REST para consultar status de uma NF-e."""
    nfe = frappe.get_doc("NF-e", nfe_name)
    return {
        "status": nfe.status,
        "access_key": nfe.access_key,
        "protocol": nfe.protocol_number,
    }
```

## 4. Database API (v16)
```python
# Query Builder (recomendado v16+)
from frappe.query_builder import DocType

NFe = DocType("NF-e")
query = (
    frappe.qb.from_(NFe)
    .select(NFe.name, NFe.status, NFe.access_key)
    .where(NFe.status == "Autorizada")
    .limit(10)
)
results = query.run(as_dict=True)

# frappe.get_list (v16 tem breaking changes)
nfe_list = frappe.get_list("NF-e", filters={"status": "Autorizada"}, fields=["name", "access_key"])

# frappe.db.sql (apenas quando Query Builder não cobre)
frappe.db.sql("""
    SELECT name, access_key
    FROM `tabNF-e`
    WHERE status = %s
""", "Autorizada", as_dict=True)
```

## 5. REST API

### Endpoints
| Método | URL | Descrição |
|--------|-----|-----------|
| GET | `/api/resource/NFe/{name}` | Buscar NF-e |
| POST | `/api/resource/NFe` | Criar NF-e |
| PUT | `/api/resource/NFe/{name}` | Atualizar NF-e |
| DELETE | `/api/resource/NFe/{name}` | Deletar NF-e |
| GET | `/api/method/erpnext_br_compliance.api.nfe.get_nfe_status` | Método whitelisted |

### Auth
- **Token:** Header `Authorization: token {api_key}:{api_secret}`
- **OAuth2:** via `frappe.integrations.doctype.oauth_client`

## 6. MCP (Frappe MCP)

**Fonte:** https://github.com/frappe/mcp

- `frappe/mcp` (oficial, experimental) — Streamable HTTP MCP server
- Tools com inputSchema automático via docstrings + type annotations
- Cada tool roda no contexto do usuário Frappe (permissões + audit log)
- Alternativa produção: `mascor/frappe-mcp-server` (audit logging + permissões)

```python
# app/app/mcp.py
import frappe_mcp

mcp = frappe_mcp.MCP("erpnext-br-mcp")

@mcp.tool()
def consultar_nfe(access_key: str):
    """Consultar NF-e pela chave de acesso

    Args:
        access_key: Chave de acesso de 44 dígitos da NF-e
    """
    nfe = frappe.get_doc("NF-e", {"access_key": access_key})
    return {"status": nfe.status, "protocol": nfe.protocol_number}

# Endpoint: /api/method/app.mcp.handle_mcp
@mcp.register()
def handle_mcp():
    import erpnext_br_compliance.mcp_tools  # registra as tools
```

## 7. Erros Comuns e Boas Práticas

| Erro | Causa | Solução |
|------|-------|---------|
| `frappe.exceptions.DoesNotExistError` | DocType não encontrado | Verificar `app_name` e `required_apps` |
| PermissionError | Sem permissão para DocType | Adicionar role no hooks.py |
| `get_list` v16 quebra | Query Builder migration | Usar `frappe.qb` em vez de `get_list` |
| MCP não carrega tools | Tools não importadas | Chamar import no `@mcp.register()` |
| Webhook não dispara | URL não configurada ou evento errado | Verificar webhook no Frappe Cloud |

**Boas Práticas:**
- Sempre usar `frappe.qb` (Query Builder) em vez de `frappe.db.sql` para consultas novas
- DocTypes customizados devem estar em `app/app/doctype/`, não modificar DocTypes do ERPNext
- Usar `doc_events` para estender DocTypes padrão em vez de sobrescrever controllers
- Fixtures para dados de referência (NCM, CFOP, CST); patches para migrações de dados
- Testes unitários obrigatórios para cada novo DocType/method