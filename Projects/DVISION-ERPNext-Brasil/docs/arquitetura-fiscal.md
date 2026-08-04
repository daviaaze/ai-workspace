# Arquitetura Fiscal — Core Brasileiro

## Stack tecnológica

```
erpnext_br_compliance (app Frappe)
├── Emissão DF-e
│   ├── nfelib 2.5.2 (MIT) — schemas/bindings NF-e, NFS-e nacional, CT-e, MDF-e, BP-e
│   ├── PyNFe 0.6.5 (LGPL) — transmissão webservices SEFAZ
│   └── BrazilFiscalReport 1.0.1 (LGPL-3.0) — DANFE/DACTE em PDF
├── Cálculo de tributos
│   ├── Calculadora de Tributos RFB (Docker, Java/Springboot) — IBS/CBS
│   └── Motor próprio leve para ICMS/PIS/COFINS/IPI vigentes
├── Tabelas de referência (atualizadas pelo Agente Fiscal)
│   ├── cClassTrib / CST-IBS/CBS / cCredPres (JSON SVRS)
│   ├── NCM, CEST, CFOP, MVA por UF
│   └── Municípios NFS-e
├── Obrigações acessórias (geração de arquivo)
│   └── EFD ICMS/IPI (c/ Bloco K), EFD-Contribuições
└── Camada paga (open core)
    ├── Templates verticais (pack_industria, pack_moveleiro, etc.)
    ├── Monitor de Reforma Tributária
    └── Suporte/SLA + implantação
```

## Bibliotecas open source verificadas (30/07/2026)

| Biblioteca | Versão | Licença | Função | Status |
|-----------|--------|---------|--------|--------|
| nfelib | 2.5.2 | MIT | Schemas/bindings DF-e | ✅ Viva |
| PyNFe | 0.6.5 | LGPL | Transmissão webservices SEFAZ | ✅ Viva |
| BrazilFiscalReport | 1.0.1 | LGPL-3.0 | DANFE/DACTE PDF | ✅ Viva |
| Calculadora RFB | — | Open source | Motor IBS/CBS (Docker) | ✅ Oficial RFB |
| PyTrustNFe | — | — | — | ❌ Projeto estagnado — evitar |

## Documentos fiscais eletrônicos (DF-e)

| Documento | Mod | Quem precisa | Fase | Prazo crítico |
|-----------|-----|--------------|------|---------------|
| NF-e | 55 | Toda indústria/comércio | Fase 0 | Layout IBS/CBS 03/08/2026 |
| NFC-e | 65 | Varejo B2C | Fase 1 | Idem |
| NFS-e | — | Prestadores de serviço | Fase 1 | Adesão municipal contínua |
| CT-e | — | Transporte | Fase 3 | — |
| MDF-e | — | Transporte | Fase 3 | — |
| BP-e | — | Passagem | Fase 4 | — |
| NFP-e | — | Produtor rural | Fase 4 | Obrigatória desde 05/01/2026 |

## Obrigações acessórias (SPED) — escopo do produto

| Obrigação | Periodicidade | No produto? | Fase |
|-----------|--------------|-------------|------|
| EFD ICMS/IPI | Mensal | Geração do arquivo | Fase 3 |
| Bloco K | Mensal (indústrias LR/LP) | Geração do arquivo | Fase 4 |
| EFD-Contribuições | Mensal, 10º dia útil | Geração do arquivo | Fase 3 |
| EFD-Reinf | Mensal, dia 15 | Exportar dados (não gerar) | — |
| eSocial | Contínua | **Fora do MVP** | — |

**Posicionamento:** "entregamos os dados prontos e os arquivos fiscais principais; o contador do cliente continua responsável pelas declarações" — o contador é aliado (canal), não concorrente.

## Regras de mercadoria

| Regra | Descrição | Prioridade |
|-------|-----------|-----------|
| NCM | Classificação fiscal 8 dígitos em todo item NF-e | MVP |
| CFOP | Código fiscal da operação | MVP |
| CST/CSOSN | Situação tributária (regime normal / Simples) | MVP |
| CEST | Código ST (Convênio 142/18) | Fase 2–3 |
| ICMS-ST / MVA | Substituição tributária por UF | Fase 3 |
| DIFAL | Diferencial interestadual | Fase 3 |
| IPI | Produto industrializado | MVP (indústria) |
| PIS/COFINS | LC 224/2025 desde 01/04/2026 | Fase 2 |
| IBS/CBS/IS | Reforma Tributária — NT 2025.002 | Fase 2 |
| Funrural | Contribuição rural | Fase 4 |

## Riscos técnicos e mitigações

| Risco | Mitigação |
|-------|-----------|
| Instabilidade SEFAZ / contingência | SVRS + fila de retransmissão com idempotência (Fase 1) |
| NFS-e fora do padrão nacional | Priorizar municípios aderidos; adaptador por provedor só com cliente pagante |
| Mudança de layout com 60 dias | Monitor + parametrização por versão de layout (não hardcoded) |