# Padrões de Desenvolvimento — erpnext_br_compliance

> **Propósito:** regras e padrões que os agentes devem seguir ao gerar código para o app fiscal brasileiro.

---

## 1. Princípios

1. **Nunca modificar DocTypes do ERPNext** — usar `doc_events` e `custom_fields`
2. **Cada DocType novo em app_name/doctype/ próprio** — não poluir namespace do ERPNext
3. **Fixtures para dados de referência** (NCM, CFOP, CST) — patches apenas para migração de dados
4. **Testes obrigatórios** para cada novo DocType e método whitelisted
5. **Permissões explícitas** — toda DocType customizada precisa de roles
6. **MCP tools para agentes** — cada operação fiscal deve ter uma tool MCP

## 2. Hooks (hooks.py)

```python
app_name = "erpnext_br_compliance"
app_title = "ERPNext BR Compliance"
app_publisher = "DVISION Serviços Digitais"
app_description = "Brazilian fiscal compliance for ERPNext"
app_icon = "folder"
app_color = "green"
app_email = "contato@dvision.com.br"
app_license = "GNU General Public License (v3)"
required_apps = ["frappe/erpnext"]

# Document Events
doc_events = {
    "Sales Invoice": {
        "on_submit": "erpnext_br_compliance.events.sales_invoice.on_submit",
        "on_cancel": "erpnext_br_compliance.events.sales_invoice.on_cancel",
        "validate": "erpnext_br_compliance.events.sales_invoice.validate",
    },
    "Purchase Invoice": {
        "on_submit": "erpnext_br_compliance.events.purchase_invoice.on_submit",
    },
    "Item": {
        "validate": "erpnext_br_compliance.events.item.validate",
    },
    "Customer": {
        "validate": "erpnext_br_compliance.events.customer.validate",
    },
}

# Fixtures
fixtures = ["NCM", "CFOP", "CST", "CEST", "Configuracao Fiscal"]

# Custom Fields
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
            "options": "Não Emitida\nAutorizada\nCancelada\nRejeitada\nEm Processamento",
            "insert_after": "nfe_access_key",
            "default": "Não Emitida",
        },
    ],
}
```

## 3. DocType Controller

### 3.1 Estrutura
```python
# erpnext_br_compliance/fiscal_br/doctype/nfe/nfe.py
import frappe
from frappe.model.document import Document

class NFe(Document):
    def before_save(self):
        self.validate_cnpj()
        self.validate_ncm()

    def on_submit(self):
        self.transmitir_sefaz()

    def on_cancel(self):
        self.cancelar_sefaz()

    def validate_cnpj(self):
        from erpnext_br_compliance.utils.cnpj_cpf import validar_cnpj
        if not validar_cnpj(self.cnpj_destinatario):
            frappe.throw("CNPJ do destinatário inválido")
```

### 3.2 Permissions
```json
{
    "roles": ["Fiscal BR Manager", "Fiscal BR User", "System Manager"],
    "permissions": [
        {
            "role": "Fiscal BR Manager",
            "select": 1, "read": 1, "write": 1, "create": 1,
            "delete": 1, "submit": 1, "cancel": 1, "amend": 1,
            "email": 1, "print": 1, "report": 1, "import": 1, "export": 1
        },
        {
            "role": "Fiscal BR User",
            "select": 1, "read": 1, "write": 1, "create": 1,
            "submit": 1, "cancel": 1,
            "email": 1, "print": 1
        }
    ]
}
```

## 4. MCP Tools

### 4.1 Registro
```python
# erpnext_br_compliance/mcp.py
import frappe_mcp

mcp = frappe_mcp.MCP("erpnext-br-compliance")

@mcp.tool()
def consultar_status_nfe(access_key: str):
    """Consultar status de NF-e pela chave de acesso

    Args:
        access_key: Chave de acesso de 44 dígitos
    """
    nfe = frappe.get_doc("NF-e", {"access_key": access_key})
    return {
        "status": nfe.status,
        "protocol": nfe.protocol_number,
        "sales_invoice": nfe.sales_invoice,
    }

@mcp.tool()
def emitir_nfe(sales_invoice: str):
    """Emitir NF-e para uma Sales Invoice já submetida

    Args:
        sales_invoice: Nome da Sales Invoice
    """
    from erpnext_br_compliance.api.nfe import emitir_nfe as emitir
    return emitir(sales_invoice)

@mcp.register()
def handle_mcp():
    import erpnext_br_compliance.mcp_tools  # noqa: F401
```

### 4.2 Tools Planejadas
- `consultar_nfe` — status por chave de acesso
- `emitir_nfe` — emitir NF-e para Sales Invoice
- `cancelar_nfe` — cancelar NF-e autorizada
- `criar_cce` — carta de correção
- `consultar_certificado` — validade do certificado A1
- `gerar_sped` — gerar SPED de um período
- `calcular_imposto` — calcular IBS/CBS via Calculadora RFB
- `listar_ncm` — consultar NCM por código
- `consultar_cfop` — consultar CFOP por código

## 5. Testes

```python
# erpnext_br_compliance/tests/test_nfe.py
import frappe
from frappe.tests.utils import FrappeTestCase

class TestNFe(FrappeTestCase):
    def setUp(self):
        # Criar configuração fiscal de teste
        self.config = frappe.get_doc({
            "doctype": "Configuracao Fiscal",
            "company": "_Test Company",
            "ambiente": "2",  # homologação
            "serie_nfe": "1",
        }).insert()

    def test_emitir_nfe(self):
        # Criar Sales Invoice de teste
        si = frappe.get_doc({
            "doctype": "Sales Invoice",
            "customer": "_Test Customer",
            "company": "_Test Company",
            "items": [{"item_code": "_Test Item", "qty": 1, "rate": 100}],
        }).submit()

        # Chamar emissão
        result = frappe.call("erpnext_br_compliance.api.nfe.emitir_nfe", si.name)
        self.assertIn("status", result)
```

## 6. REST API

```python
@frappe.whitelist()
def get_nfe_status(nfe_name: str) -> dict:
    """Endpoint REST para consultar status de NF-e.

    Args:
        nfe_name: Nome do documento NF-e

    Returns:
        dict com status, chave de acesso, protocolo
    """
    frappe.has_permission("NF-e", "read", throw=True)
    nfe = frappe.get_doc("NF-e", nfe_name)
    return {
        "status": nfe.status,
        "access_key": nfe.access_key,
        "protocol": nfe.protocol_number,
        "created_at": str(nfe.creation),
    }
```

## 7. Padrões de Commit

Seguir conventional commits (conforme AGENTS.md):
- `feat:` nova funcionalidade (ex: emissão NF-e, tool MCP)
- `fix:` correção de bug
- `refactor:` mudança sem mudança de comportamento
- `test:` adição ou correção de teste
- `docs:` documentação
- `chore:` manutenção

## 8. Checklist de Review (para o Agente Produto)

Antes de gerar PR, verificar:
- [ ] DocType tem permissões definidas?
- [ ] Hooks de `doc_events` são leves (não bloqueiam UI)?
- [ ] Há testes unitários?
- [ ] MCP tool registrada e documentada?
- [ ] REST endpoint com `@frappe.whitelist()` e verificação de permissão?
- [ ] Fixtures para dados de referência (não hardcoded)?
- [ ] Código segue o padrão India Compliance (estrutura limpa)?
- [ ] Breaking changes no Query Builder v16 evitados?
- [ ] Certificado A1 gerenciado com senha criptografada?