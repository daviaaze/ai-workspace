# Bibliotecas Fiscais Brasileiras — Integração com ERPNext

> **Atualizado:** 30/07/2026 · **Contexto:** app `erpnext_br_compliance` para emissão de DF-e

---

## 1. nfelib 2.5.2

| Campo | Valor |
|-------|-------|
| Licença | MIT |
| Status | ✅ Ativo |
| Python | ✅ 3.10+ |
| Dependência | lxml (XML parsing/validação) |
| PyPI | https://pypi.org/project/nfelib/ |

**Uso no app:** geração e validação de XML de NF-e, NFC-e, CT-e, MDF-e, NFS-e.

```python
from nfelib.nfe.bindings import TEnviNFe, TNFe
from nfelib.nfe.leiaute import NFe

# Gerar XML de NF-e
nfe = TNFe(
    infNFe=TNFe.InfNFe(
        ide=TNFe.InfNFe.Ide(...),
        emit=TNFe.InfNFe.Emit(...),
        dest=TNFe.InfNFe.Dest(...),
        det=[...],
        total=TNFe.InfNFe.Total(...),
    )
)
xml = nfe.xml()  # bytes
```

## 2. PyNFe 0.6.5

| Campo | Valor |
|-------|-------|
| Licença | LGPL |
| Status | ✅ Ativo |
| Função | Transmissão/consulta/distribuição DF-e via webservice SEFAZ |
| PyPI | https://pypi.org/project/PyNFe/ |

**Uso no app:** comunicação com SEFAZ (autorização, cancelamento, CC-e, inutilização, manifestação do destinatário, download XML, DPEC).

## 3. BrazilFiscalReport 1.0.1

| Campo | Valor |
|-------|-------|
| Licença | LGPL-3.0 |
| Status | ✅ Ativo |
| Função | Geração de SPED Fiscal (ECD/EFD) e SPED Contribuições |
| PyPI | https://pypi.org/project/BrazilFiscalReport/ |

**Uso no app:** geração dos arquivos SPED para entrega ao Fisco (obrigações acessórias dos clientes).

## 4. Calculadora de Tributos RFB (rtc-calculadora-offline)

| Campo | Valor |
|-------|-------|
| Stack | **Java/Spring Boot** (Serpro) |
| Licença | Open Source (beta) |
| GitHub | https://github.com/nfe/rtc-calculadora-offline |
| Docker | ✅ (componente Docker) |
| Status | ✅ Ativo, beta |

**Uso no app:** API REST para cálculo de IBS/CBS conforme a Reforma Tributária. Componente externo ao Frappe (roda em container separado). Fornecido pelo Serpro (RFB) como "Tax as a Service".

**Endpoints disponíveis:**
- `CalculadoraTributo` — cálculo de IBS/CBS
- `BaseCalculo` — base de cálculo
- `DadosAbertos` — tabelas públicas
- `Nfse` — cálculos para NFS-e
- `VersaoOffline` — versão e atualizações
- `XML` — assistente de emissão com campos IBS/CBS

## 5. Arquitetura de Integração no App

```
ERPNext (Sales Invoice)
    │
    ▼
erpnext_br_compliance (hooks.py → doc_events.on_submit)
    │
    ├── nfelib → gera XML da NF-e (TNFe)
    ├── PyNFe → transmite para SEFAZ (autorização)
    ├── BrazilFiscalReport → gera SPED (periódico)
    └── Calculadora RFB (Docker) → calcula IBS/CBS
```

```python
# Exemplo: fluxo de emissão de NF-e
# hooks.py
doc_events = {
    "Sales Invoice": {
        "on_submit": "erpnext_br_compliance.api.nfe.emitir_nfe"
    }
}

# api/nfe.py
import frappe
from nfelib.nfe.bindings import TNFe
from pynfe.processamento import certificado, comunicacao

@frappe.whitelist()
def emitir_nfe(doc, method):
    # 1. Buscar configuração fiscal da empresa
    config = frappe.get_doc("Configuracao Fiscal", {"company": doc.company})

    # 2. Carregar certificado digital A1
    cert = certificado.Certificado(
        arquivo=config.certificado_a1,
        senha=config.get_password("certificado_senha"),
    )

    # 3. Montar XML com nfelib
    nfe = montar_nfe(doc)
    xml = nfe.xml()

    # 4. Transmitir com PyNFe
    con = comunicacao.ComunicacaoSefaz(
        certificado=cert,
        ambiente=config.ambiente,  # 1=producao, 2=homologacao
    )
    resposta = con.autorizacao(xml)

    # 5. Salvar resultado
    nfe_doc = frappe.get_doc({
        "doctype": "NF-e",
        "sales_invoice": doc.name,
        "access_key": resposta.chave_acesso,
        "protocol": resposta.protocolo,
        "xml": xml.decode(),
        "status": "Autorizada" if resposta.cStat == "100" else "Rejeitada",
    })
    nfe_doc.insert()
```

## 6. Observações Importantes

- **PyTrustNFe:** ❌ EVITAR — projeto estagnado (não atualiza para NT 2025.002)
- **nfelib + PyNFe:** stack testada, compatível com Python 3.10+ e Frappe
- **Calculadora RFB:** Java/Spring Boot via Docker (não roda dentro do Frappe)
- **Certificado A1:** gerenciado via DocType `Certificado Digital` (upload .pfx + senha criptografada)
- **Ambiente:** homologação (SEFAZ) vs produção — controlado por campo na Configuracao Fiscal
- **NT 2025.002 v1.40:** IBS/CBS obrigatório desde 03/08/2026 para CRT=3 — nosso app precisa nascer com suporte