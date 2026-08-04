# India Compliance — Estrutura de Referência

> **Propósito:** referência de como um compliance app bem estruturado é feito no ecossistema Frappe/ERPNext.
> **Fonte:** https://github.com/resilient-tech/india-compliance

---

## 1. Por que India Compliance é Referência

- Mantido pela Resilient Tech (especialistas em compliance)
- Aprovado e listado no Frappe Cloud Marketplace
- Validado pela Frappe como padrão de compliance app (Frappe Build 2026)
- Cobre GST (India) — análogo ao nosso IBS/CBS/NFe
- Mais de 100+ estrelas, uso em produção comprovado

## 2. Estrutura do App

```
india_compliance/
├── india_compliance/
│   ├── __init__.py
│   ├── hooks.py                      ← configuração do app
│   ├── patcher.py                    ← patches de migração
│   ├── api/                          ← REST endpoints
│   ├── events/                       ← doc_events handlers
│   ├── gst_integration/              ← módulo específico GST
│   │   ├── doctype/                  ← DocTypes próprios
│   │   ├── api/                      ← API de integração
│   │   └── utils/                    ← utilitários
│   ├── overrides/                    ← override de DocTypes padrão
│   ├── public/                       ← JS/CSS
│   ├── gst_india/                    ← templates de relatório
│   └── patchers/                     ← patches de migração
├── setup.py
├── requirements.txt
└── README.md

```

## 3. Padrões que Devemos Copiar

### 3.1 Hooks
```python
# hooks.py
app_name = "india_compliance"
app_title = "India Compliance"
app_publisher = "Resilient Tech"
app_description = "ERPNext app to simplify compliance with Indian Rules and Regulations"
app_icon = "folder"
app_color = "grey"
app_email = "hello@indiacompliance.app"
app_license = "GNU General Public License (v3)"
required_apps = ["frappe/erpnext"]
app_home = "/desk/gst-india"  # workspace dedicado
```

### 3.2 DocTypes Próprios (não modificar ERPNext)
- `GST Settings` — configuração global
- `GST Inward Supply` — entrada de mercadoria
- `GST Return` — apuração periódica
- DocTypes de cadastro fiscal (análogo a NCM, CFOP, CST)

### 3.3 Overrides (extensão de DocTypes padrão)
```python
# overrides/ — métodos que estendem DocTypes do ERPNext
# Usa doc_events em vez de modificar o controller original
```

### 3.4 Fixtures
```python
fixtures = [
    "GST HSN Code",     # análogo a NCM
    "GST Rate",         # análogo a alíquota IBS/CBS
    "GST Category",     # análogo a CST
]
```

## 4. Lições do Frappe Build 2026 (Nikhil Kothari)

**Talk:** "Building Compliance Software"  
**URL:** https://www.youtube.com/watch?v=MN4hPiliN6A

### Erros Comuns em Compliance Apps
1. **Hooks pesados:** não colocar lógica pesada em hooks de `validate`/`on_submit` — usar background jobs
2. **Falta de permissões:** toda DocType customizada precisa de roles e permissões explícitas
3. **Extension patterns errados:** não sobrescrever controllers do ERPNext diretamente — usar `doc_events`
4. **Performance:** evitar consultas SQL dentro de hooks de formulário — usar cache ou batch
5. **Segurança:** whitelisted methods precisam de verificação de permissão

## 5. Estrutura Recomendada para o `erpnext_br_compliance`

```
erpnext_br_compliance/
├── erpnext_br_compliance/
│   ├── __init__.py
│   ├── hooks.py
│   ├── api/
│   │   ├── nfe.py               ← emissão, cancelamento, CC-e
│   │   ├── nfce.py              ← NFC-e (consumidor)
│   │   ├── sped.py              ← SPED Fiscal/Contribuições
│   │   └── setup.py             ← configuração inicial
│   ├── events/
│   │   ├── sales_invoice.py     ← doc_events para Sales Invoice
│   │   ├── purchase_invoice.py  ← doc_events para Purchase Invoice
│   │   ├── item.py              ← validação de NCM/CEST
│   │   ├── customer.py          ← validação de CNPJ/CPF
│   │   └── company.py           ← configuração fiscal da empresa
│   ├── fiscal_br/               ← módulo principal
│   │   ├── doctype/
│   │   │   ├── configuracao_fiscal/
│   │   │   ├── certificado_digital/
│   │   │   ├── nfe/
│   │   │   ├── nfe_item/
│   │   │   └── evento_fiscal/
│   │   └── report/
│   ├── services/
│   │   ├── xml_builder.py       ← geração de XML (nfelib)
│   │   ├── transmitter.py       ← transmissão SEFAZ (PyNFe)
│   │   ├── signer.py            ← assinatura digital
│   │   ├── danfe.py             ← geração de DANFE PDF
│   │   └── validators.py        ← validações fiscais
│   ├── utils/
│   │   ├── tax_tables.py        ← tabelas de alíquotas
│   │   ├── cnpj_cpf.py          ← validação de CNPJ/CPF
│   │   └── ibge.py              ← código IBGE de municípios
│   ├── fixtures/
│   │   ├── ncm.json
│   │   ├── cfop.json
│   │   ├── cst.json
│   │   └── cest.json
│   ├── public/
│   │   ├── js/
│   │   └── css/
│   └── patches.txt
├── requirements.txt
├── pyproject.toml
└── README.md
```