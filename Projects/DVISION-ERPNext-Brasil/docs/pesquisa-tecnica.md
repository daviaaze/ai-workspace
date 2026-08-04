# Pesquisa de Bibliotecas e Integrações — DVISION ERPNext Brasil

> **Data:** pesquisa paralela em 30/07/2026 (sessão atual).
> **Frentes:** ERPNext/Frappe · Bibliotecas fiscais (nfelib, PyNFe, BrazilFiscalReport) · Calculadora RFB · Pluggy/Open Finance.
> Fontes: PyPI, GitHub, frappe.io, pluggy.ai, gov.br — verificadas nesta sessão.

---

## 1. ERPNext / Frappe Framework (v16)

### Status
- **ERPNext v16** lançado em **06/12/2025** (Frappeverse, Egito); beta em 15/11/2025.
- Lançamento mais estável da história: 600+ contribuidores, 50+ features novas, "up to 2x faster".
- **Versão atual: v16.30.0** (jul/2026) — cadência de releases contínua e ativa.
- Frappe Framework v16.28.0 (jul/2026) — framework ativo.

### Novidades que interessam ao nosso ICP (indústria)
| Feature | Relevância |
|---------|-----------|
| Financial Report Templates (P&L/DRE e Balanço customizáveis por fórmula) | Relatórios sob medida por cliente |
| **MRP aprimorado + subcontracting inward** (terceirização de etapas) | Vertical indústria — diferencial |
| Landed cost para stock entries | Custo real de importação/frete |
| Relatórios de rastreabilidade Serial & Batch | Indústria — compliance de lote |
| COGS e Service expense separados | Contabilidade mais precisa |
| POS aprimorado + novos reports de accounting | Varejo futuro |
| UI nova (desktop, sidebar persistente, list/form view) | Experiência do cliente final |
| Performance: cache de budget checks, pricing rules, estoque | Implantação mais rápida |

### Implicações para a DVISION
1. **Base em v16** (não v15): estável, com MRP/landed cost que sustentam o tier "Indústria".
2. Frappe Cloud (Frankfurt) roda v16 — sem fricção de versão.
3. O ecossistema (India Compliance, ~13,5k instalações) valida o modelo "app fiscal por país" — e segue o mesmo padrão Frappe v16.

---

## 2. Bibliotecas fiscais open source (verificadas, vivas)

### nfelib 2.5.2 — Akretion (MIT, Python ≥3.8)
- Bindings Python para **ler e gerar XML** de NF-e, NFS-e nacional, CT-e, MDF-e, BP-e.
- Mantém bindings atualizados para todos os serviços e eventos.
- `pip install nfelib` — PyPI ativo.
- **Nota:** mesmo autor/ecossistema da Odoo fiscal brasileira (Akretion) — referência do setor.

### PyNFe 0.6.5 — TadaSoftware (LGPL, Python ≥3.8)
- Interface com webservices da SEFAZ: **NF-e e NFC-e**, autorização, cancelamento, carta de correção, contingência (SVRS), inutilização.
- Também cobre NFS-e (Prefeituras) e MDF-e.
- `pip install PyNFe` — PyPI ativo.
- **Nota:** repositório original é `TadaSoftware/PyNFe`; há fork `benevides/PyNFe` (mesma base).

### BrazilFiscalReport 1.0.x — Engenere (LGPL-3.0, Python ≥3.8)
- Gera PDFs fiscais a partir do XML: **DANFE (NF-e), DACTE (CT-e), DAMDFE (MDF-e), DACCe (CC-e), DANFSe (NFS-e)**.
- Instalação modular: `pip install brazilfiscalreport` (DANFE + DACCe core); extras `[dacte]`, `[damdfe]`, `[danfse]`, `[cli]`.
- Docs: engenere.github.io/BrazilFiscalReport.

### PyTrustNFe — ❌ EVITAR
- Projeto estagnado (confirmado no plano original). Não usar.

### Resumo da stack fiscal validada
```
Emissão:      nfelib (XML) → PyNFe (transmissão SEFAZ) → BrazilFiscalReport (PDF)
Cálculo:      Calculadora RFB (CBS/IBS/IS) + motor próprio (ICMS/PIS/COFINS/IPI)
Atualização:  Agente Fiscal (monitor ENCAT/SEFAZ/SVRS + issues no repo)
```

---

## 3. Calculadora de Tributos RFB (CBS/IBS/Imposto Seletivo)

### O que é
- Ferramenta **oficial da Receita Federal**, open source (beta), para calcular CBS, IBS e Imposto Seletivo — padroniza e torna auditável o cálculo do novo IVA dual.
- Duas formas: **simulador online** + **componente local (offline)** integrável a ERPs via **API**.
- Inclui **"Assistente de Emissão"**: ajuda a gerar corretamente os campos IBS/CBS nas NF-e.

### Componente offline (o que vamos usar)
- **Backend Java/Spring Boot (Serpro)** + Flyway migrations; banco com tabelas de cClassTrib, NCM, NBS, municípios, alíquotas, tratamentos tributários, monofasia, Imposto Seletivo.
- Endpoints principais (controllers): `BaseCalculo`, `CalculadoraTributo`, `DadosAbertos`, `Nfse`, `Pedagio`, `VersaoOffline`, `XML`.
- Modelo de domínio completo: IBS (UF/municipal), CBS, IS, crédito presumido (incl. ZFM), diferimento, monofasia, devolução de tributos, estorno de crédito.
- **Robô de espelho**: `github.com/nfe/rtc-calculadora-offline` roda GitHub Action diária, baixa a versão nova, publica release — nunca ficamos presos a link morto.
- Download: `https://piloto-cbs.tributos.gov.br/servico/calculadora-consumo/api/calculadora/download/url?platform=default`

### Integração com a DVISION
- Subir em **Docker** junto ao Frappe Cloud (ou no tenant do cliente) e chamar via API REST — confirma a arquitetura do plano (seção 5.1).
- Controllers de `DadosAbertos` expõem tabelas (NCM, cClassTrib, alíquotas) — substituem scraping manual de tabelas.
- **Risco de versão:** RFB publica novas versões com frequência → o Agente Fiscal deve monitorar o repositório espelho e pinar versão + testar em homologação antes de release.

---

## 4. Pluggy — Open Finance Brasil (novo ponto de venda)

### O que é
- **Infraestrutura de Open Finance para o Brasil**: uma API única para **+130 instituições financeiras** (bancos, corretoras, cartões).
- **Regulada pelo Banco Central** como ITP (Iniciador de Transação de Pagamento) + LGPD; backed by **Y Combinator (S21)**; +1 milhão de conexões/mês.
- Caso de prova: **MarketUP** (ERP+PDV, 250k CNPJs) usa Pluggy para **conciliação bancária integrada** — exatamente o nosso pitch.

### Produtos e preços (pluggy.ai, verificados)
| Produto | Preço | Inclui |
|---------|-------|--------|
| **Dados** | **a partir de R$ 2.500/mês** | Open Finance + acesso direto; extrato, saldo, cartões, investimentos; identidade e KYC; webhooks; enriquecimento (categorização, merchants, recorrências) |
| **Pagamentos** | a partir de R$ 500/mês | Iniciação de Pix (D+0), cobranças únicas (QR dinâmico + link), **Pix Automático** (recorrência), cash management (sweeping, top-up) |
| Ambos | — | Sandbox completo, teste grátis 14 dias (produção), suporte por ticket, Discord |

> Fontes de terceiros indicam faixas variadas (US$ 29/mês tier inicial reportado pela Shyft; US$ 500/mês reportado pela Cubbie; R$ 2.500/mês confirmado na página oficial e no TabNews). **Tratar R$ 2.500/mês (Dados) como preço real de produção**; negociar/validar no contato comercial.

### Integração técnica
- **SDKs oficiais:** Node.js, .NET, Java (pluggy-sdk). **Python não tem SDK oficial** — integrar via **REST direto** (docs.pluggy.ai) ou usar o pacote `pluggy-sdk` do PyPI (gerado por OpenAPI Generator — não oficial, validar).
- ⚠️ **Atenção:** existe o pacote PyPI `pluggy` que é o **framework de plugins do pytest** (pytest-dev/pluggy) — não confundir com a API Pluggy. Para a API, o nome no PyPI é `pluggy-sdk`.
- Fluxo típico: criar conexão via token API → widget/connect de onboarding do cliente (embed no produto) → webhooks de atualização → sincronizar contas/transações no ERP.

### Oportunidade de venda para a DVISION
1. **Conciliação bancária automática** para indústria (o case MarketUP prova a demanda: PME odeia conciliar extrato manualmente).
2. **Pix Automático** para cobrança recorrente dos próprios clientes e dos clientes da DVISION.
3. **Enriquecimento**: categorização automática de despesas → fechamento mensal mais rápido (argumento value-based: economia de horas de escrituração).
4. Posicionamento: "ERP com Open Finance nativo" contra Nomus/Odoo que exigem integração manual ou extra.

### Open Finance "nativo" vs. agregador (decisão estratégica)

**Não existe "implementar Open Finance nativo" como quem implementa uma biblioteca — é uma licença bancária.** Ser participante direto do ecossistema exige:

| Papel | O que faz | Autorização necessária |
|-------|-----------|----------------------|
| **IT** (Transmissora) | Detém os dados do cliente | Licença de instituição financeira |
| **IR** (Receptora) | Consome dados alheios | Licença/autorização como IR |
| **ITP** (Iniciadora) | Inicia Pix em nome do cliente | **Autorização específica do Bacen** (Res. BCB 80/2021, IN BCB 77/2021, Res. CMN 5.131/2024) |

**Custos/requisitos da integração direta:** capital mínimo de até **R$ 30 mi**, estrutura societária + PLD/FT + KYC + governança, certificação de conformidade no diretório Open Finance (segurança FAPI + funcional), certificados mTLS (RSA 4096), OAuth 2.0 + PKCE, jornada de consentimento seguindo o Guia UX do Bacen, onboarding via Service Desk com testes + detentoras voluntárias, e **manutenção contínua de conectores por banco** (800+ instituições).

| Critério | Direta (nativa) | Agregador (Pluggy) |
|----------|-----------------|--------------------|
| Autorização | ITP/IR própria | Delegada ao agregador (Pluggy é ITP) |
| Prazo do 1º fluxo | Semanas por banco | Dias úteis |
| Capital inicial | Até R$ 30 mi | Zero (assinatura) |
| Custo mensal | Equipe dedicada + compliance | R$ 500–2.500/mês |
| Conectores | Construir e manter por banco | +130 prontos |
| Responsabilidade regulatória | Integral | Dividida por contrato/DPA |

**Conclusão para a DVISION:** quem vende "Open Finance nativo" hoje (ex.: MarketUP) usa agregador. A única opção realista no ano 1 é o ERP com **agregador regulado embutido** — o marketing deve dizer "**Open Finance embutido no seu ERP**" (verdadeiro e diferenciado), não "nativo". Repensar integração direta só no ano 3–4+ se houver produto financeiro próprio com investimento externo.

### ⚠️ Impacto no modelo de negócio (importante)
- **Custo mínimo de R$ 2.500/mês (Dados)** é significativo contra o tier Essencial (R$ 790/mês) e até o Indústria (R$ 1.490/mês).
- **Opções a decidir:**
  1. **Repasse por cliente** — cobrar conectividade financeira como add-on (ex.: R$ 150–300/mês/cliente) cobrindo o custo; viável com 8–10 clientes.
  2. **Tier superior** — Open Finance entra no "Indústria Plus" (R$ 2.490/mês) como diferencial.
  3. **Aguardar** — colocar na Fase 3+ (após validação dos pilotos), sem custo no ano 1.
- **Recomendação:** validar com o piloto 1 se conciliação bancária é dor nº 1; se sim, avaliar contrato comercial Pluggy (negociar por volume/conexões) antes de fixar preço.

---

## 5. Decisões e pendências (próximos passos)

| # | Decisão | Status | Próxima ação |
|---|---------|--------|--------------|
| 1 | Base ERPNext **v16** (não v15) | ✅ Confirmada | Criar app esqueleto em v16 |
| 2 | Stack fiscal: nfelib + PyNFe + BrazilFiscalReport | ✅ Confirmada e viva | Fase 0: NF-e 55 em homologação |
| 3 | Calculadora RFB em Docker | ✅ Confirmada (API REST + dados abertos) | Definir onde roda (tenant vs. dedicado) |
| 4 | Pluggy como produto Open Finance | 🟡 Validar demanda com piloto | Discovery: perguntar sobre conciliação bancária |
| 5 | Custo Pluggy (R$ 2.500/mês) no modelo de preço | 🟡 Aberta | Decidir repasse vs. tier vs. adiar (seção 4) |
| 6 | SDK Python Pluggy (não oficial) | 🟡 Validar | Testar REST direto no sandbox (14 dias grátis) |
| 7 | Monitor de versões da Calculadora RFB | 🟡 A implementar | Agente Fiscal: watch `nfe/rtc-calculadora-offline` |
| 8 | Posicionamento de mercado | ✅ Decidido | "Open Finance embutido no ERP" (agregador regulado), nunca "nativo" |

---

## 6. Fontes

- Frappe: frappe.io/erpnext/version-16 · github.com/frappe/erpnext (v16.30.0, jul/2026) · frappe.io/blog
- nfelib: pypi.org/project/nfelib (v2.5.2) · github.com/akretion/nfelib
- PyNFe: pypi.org/project/PyNFe (v0.6.5) · github.com/TadaSoftware/PyNFe
- BrazilFiscalReport: github.com/Engenere/BrazilFiscalReport · engenere.github.io/BrazilFiscalReport
- Calculadora RFB: github.com/nfe/rtc-calculadora-offline · piloto-cbs.tributos.gov.br · FAQ v1.4 (gov.br)
- Pluggy: pluggy.ai (planos e preços) · developer.pluggy.ai · github.com/pluggyai/quickstart · blog (MarketUP, Open Finance + ERP) · TabNews/Securo/Cubbie (faixas de preço de terceiros)
