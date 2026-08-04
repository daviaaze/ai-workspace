# Plano de Ação — DVISION Serviços Digitais
## ERPNext Brasil · Empresa AI-First · 1 founder + agentes até 10 clientes pagantes

**Data:** 30/07/2026 · **Preparado para:** Davi Azevedo (founder/dev), Londrina/PR
**Método:** pesquisa e plano estruturados como a saída conjunta de 7 agentes especializados (Fiscal, Produto/Engenharia, Compliance-Jurídico, Comercial/Precificação, Operações/Suporte, Financeiro e Growth), cada um responsável pela sua seção.
**Premissas vinculantes do projeto (respeitadas em todo o documento):**
1. O core fiscal brasileiro **será construído por você + agentes de IA** — tratado como viável e planejado como tal.
2. Nenhuma decisão deste plano parte do pressuposto de que algo "não é possível".

---

## 1. Resposta direta

**É viável operar como empresa AI-First de 1 pessoa até ~10 clientes pagantes de ERPNext no Brasil, construindo o core fiscal próprio — desde que você (a) use as bibliotecas fiscais open source já maduras (nfelib + PyNFe + BrazilFiscalReport) em vez de escrever tudo do zero, (b) faseie as obrigações fiscais por prioridade de cliente em vez de tentar cobrir tudo no MVP, e (c) transforme cada função de negócio em um agente com automação real, mantendo humano apenas vendas consultivas, decisões de escopo e relacionamento com contadores-parceiros.** O gargalo não é técnico — é a demanda ainda não validada primariamente e a capacidade de suporte acima de ~8–10 clientes. O plano abaixo endereça os dois.

---

## 2. Status regulatório e de mercado em 30/07/2026

O que está acontecendo agora e muda o seu planejamento (todas as datas verificadas nesta sessão):

### 2.1 Reforma Tributária — a janela de oportunidade está aberta
- **NT 2025.002 v1.40 (NF-e/NFC-e com campos IBS/CBS):** homologação desde 01/07/2026, **produção obrigatória em 03/08/2026** (daqui a 4 dias) para empresas CRT=3 (regime normal). Campos novos: cClassTrib, CST-IBS/CBS, grupo de tributos IBS/CBS/IS. Fonte: TecnoSpeed, 14/07/2026.
- **NT 2025.002 v1.50 (combustíveis monofásicos):** homologação 01/09/2026, produção 03/11/2026. Fonte: TecnoSpeed, 14/07/2026.
- **Ato conjunto RFB/CGIBS ainda NÃO publicado em 29/07/2026** — prometido "até o fim de julho". Definirá prazos por documento fiscal, layouts (antecedência mínima de 60 dias) e um programa de estímulo à conformidade em 30 dias. **Incerteza ativa: verificar publicação nos próximos dias.** Fonte: Contábeis.com.br, 29/07/2026.
- **Tabelas cClassTrib/cCredPres oficiais** publicadas em 23/06/2026 (IT 2025.002 v1.60), disponíveis em JSON no portal SVRS (dfe-portal.svrs.rs.gov.br) — consumíveis por automação. Fonte: IT 2025.002 v1.60, 23/06/2026.
- **Alíquotas de transição 2026:** IBS 0,1% + CBS 0,9% (ano de "teste", compensáveis). Alíquotas 2027–2028 ainda não definidas (TBD). Cronograma de transição até 2033 (EC 132/2023).
- **LC 214/2025, art. 348:** regras do Simples Nacional na Reforma a partir de 2027.
- **LC 224/2025 (corte de 10% nos benefícios fiscais federais) desde 01/04/2026:** recomposição de alíquotas PIS/COFINS — cumulativo 0,065%/0,300%; não cumulativo 0,165%/0,760%. Seu ERP precisa parametrizar isso já.
- **Split payment e RAD (apuração assistida):** a partir de 2027 — planejar arquitetura, não implementar agora.

### 2.2 PAA — Provedor de Assinatura e Autorização (novo, estratégico)
- **NT 2026.001 v1.02a:** novo modelo de emissão de NF-e/NFC-e com assinatura híbrida (RSA + ICP-Brasil), séries 970–989, procEmi=4, grupo infPAA, autorização exclusiva SVRS. Homologação 03/08/2026, **produção em 05/10/2026**.
- **Restrição importante:** só para MEI, Simples Nacional (CRT=1) e produtor rural — empresas CRT=3 e CRT=2 recebem rejeição 1178/1179. **Ou seja: PAA não atende seu ICP principal (indústrias 20–80 funcionários, regime normal), mas abre um produto futuro para o segmento MEI/Simples/agro.** Homologação como PAA exige credenciamento na coordenação do ENCAT.

### 2.3 Calculadora de Tributos da RFB ("Tax as a Service")
- Open source, versão offline em Docker (Java/Springboot), API pensada para integração de ERPs; espelho com robô de atualização em github.com/nfe/rtc-calculadora-offline. **Elimina a necessidade de você manter o motor de cálculo IBS/CBS sozinho — plugue-a como serviço.**

### 2.4 Obrigações acessórias (SPED) — obrigatórias para seus clientes
- **EFD ICMS/IPI:** mensal, todas as indústrias/comércio com ICMS. **Bloco K** (controle de produção/estoque) obrigatório para indústrias de Lucro Real/Presumido; Simples dispensado.
- **EFD-Contribuições:** mensal, até o 10º dia útil do 2º mês subsequente (LR/LP).
- **EFD-Reinf:** mensal, dia 15. **DIRF extinta desde 2026** (IN RFB 2.181/2024) — EFD-Reinf absorveu.
- **Multas:** R$ 500–1.500/mês por obrigação ausente; divergência NF-e × SPED pode gerar multa de 75% sobre o tributo.
- **eSocial: fora do MVP** (é obrigação trabalhista do cliente, entregue normalmente pelo contador — declarar isso explicitamente na proposta).

### 2.5 Fiscal — documentos e regras de mercadoria
- **NFS-e padrão nacional:** 3.400+ municípios aderidos (>80% da população). Londrina e região: verificar adesão município a município no ambiente nacional.
- **NFP-e obrigatória para produtores rurais desde 05/01/2026** — relevante para o futuro pack_agro.
- **Manifestação do destinatário:** NT 2020.001 (versão mais recente v1.60, 23/04/2026) — feature de alto valor percebido para indústrias (ciência de NF-e de entrada).
- NCM (obrigatório em toda NF-e), CEST (Convênio ICMS 142/18, para mercadorias sujeitas a ST), CFOP, ICMS-ST/MVA, DIFAL, IPI, Funrural — detalhados na seção 6.3.

### 2.6 Legal/digital
- **ANPD virou agência reguladora** (Lei 15.352/2026) e tinha 19 processos sancionadores em curso em jun/2026; o Mapa de Temas 2026–2027 inclui eixo de IA. Fiscalização real, não teórica.
- **Adequação UE ↔ Brasil:** Resolução CD/ANPD 32/2026 — hospedagem em Frankfurt (Frappe Cloud) está coberta; hospedagem nos EUA exigiria Cláusulas Contratuais Padrão (Res. CD/ANPD 19/2024).
- **Notificação de incidente:** 3 dias úteis (Res. CD/ANPD 15/2024). **DPO/encarregado obrigatório** (Res. CD/ANPD 18/2024) — para a DVISION pode ser você mesmo formalmente designado.
- **ECA Digital (Lei 15.211/2025):** só se houver usuários menores de idade — não é o caso do B2B, registrar como não aplicável.

### 2.7 Mercado
- Mercado de ERP no Brasil: ~US$ 4,9 bi, crescendo ~11%/ano (dos seus documentos de pesquisa). Oponente real no seu nicho: **Nomus (R$ 1.290–4.290/mês)** e Odoo partners — não TOTVS/SAP. India Compliance (app Frappe) com ~13,5 mil instalações prova o modelo "app fiscal open source por país" no ecossistema Frappe.

---

## 3. O que isso significa para você (Davi)

1. **A Reforma Tributária é o seu pitch de vendas.** Toda indústria CRT=3 do Brasil precisa emitir NF-e com campos IBS/CBS desde 03/08/2026. ERPs legados estão correndo para adaptar; você constrói já no layout novo. Sua mensagem: "seu ERP atual está pronto para a Reforma? O nosso nasceu pronto."
2. **Você não precisa construir o motor de cálculo tributário** — a Calculadora RFB (open source, Docker) resolve IBS/CBS; você constrói a camada DF-e (emissão, transmissão, contingência, DANFE) sobre nfelib/PyNFe, que já têm os schemas. Isso reduz o core fiscal próprio de "projeto de anos" para "projeto de meses com agentes de IA".
3. **O prazo de 03/08/2026 não é seu prazo de produto** — seus primeiros clientes-piloto (ano 1 = P&D pago) podem emitir em homologação e, em produção, começar pelos documentos mais simples. Mas o app precisa estar compatível com NT 2025.002 antes de qualquer cliente regime normal entrar em produção — coloque isso na Fase 2 (out/nov 2026), antes dos prazos de v1.50.
4. **PAA é opção, não prioridade.** Anotar no backlog de 2027: se você criar um produto low-touch para MEI/Simples/produtor rural, homologar a DVISION como PAA elimina a fricção do certificado digital do cliente (a assinatura híbrida passa pelo provedor). Diferencial real, mas só depois do ICP indústria estar validado.
5. **Sua obrigação LGPD é barata de fazer e cara de ignorar:** DPA + RoPA + runbook de incidente + cláusula de PI nos contratos = alguns dias de trabalho com templates + R$ 3–6 mil de revisão advocatícia. ISO 27001: **não certificar no ano 1** (R$ 80–180 mil); fazer gap assessment e adotar os controles-chave informalmente.
6. **Capacidade:** com ~2.000h/ano úteis, o plano fecha se cada implantação custar ≤60–80h (caindo para ~40h com templates verticais) e o suporte ficar <2h/cliente/mês via deflexão de L1 por agente. Acima de 8–10 clientes ativos, os gatilhos de contratação disparam — planejados na seção 8.

---

## 4. Organização AI-First: 7 agentes especializados + 1 founder

Desenho organizacional: cada função de empresa "de ponta" vira um agente (ou conjunto de automações) com dono, KPI e fronteira clara do que sobe para você.

| # | Agente | Função na empresa | O que automatiza (rotina) | O que fica com você (humano) | KPI |
|---|--------|-------------------|---------------------------|------------------------------|-----|
| 1 | **Fiscal/Tributário** | Engenharia fiscal | Monitorar ENCAT/SEFAZ/portal nacional (RSS + scraping agendado); baixar NTs, schemas XSD e tabelas cClassTrib/NCM/CEST/CFOP; abrir issues no repo com diff de layout; rodar suíte de testes contra webservices de homologação; validar XMLs | Decidir prioridade de adequação; revisar interpretação de NT ambígua; homologação presencial com cliente-piloto | 0 rejeições em produção por desatualização de layout; patch de NT aplicado em ≤5 dias úteis |
| 2 | **Produto/Engenharia** | Dev team | Geração de código Frappe (DocTypes, server scripts, testes), code review automatizado, CI/CD, migrações, documentação técnica, changelog | Arquitetura, decisões de produto, revisão final de PR fiscal | Lead time feature <1 semana; cobertura de testes no módulo fiscal |
| 3 | **Compliance-Jurídico** | Jurídico/DPO | Manter DPA/RoPA/termos atualizados; monitorar ANPD, diário oficial (LCs, INs RFB); checklist de conformidade por cliente; templates de resposta a titular | Relação com advogado; decisão em incidente; assinatura de contratos | 100% contratos com cláusula PI + DPA; incidente respondido em <3 dias úteis |
| 4 | **Comercial/Precificação** | Vendas/CS | Qualificação de leads, geração de proposta com cálculo de ROI (template), follow-ups, CRM atualizado, calculadora de preço por escopo | Reunião de descoberta, negociação, fechamento, gestão do canal contador | Proposta em <24h após discovery; CAC dentro do alvo (seção 7.4) |
| 5 | **Operações/Suporte** | Customer ops | L1 com base de conhecimento (deflexão alvo ≥60%); monitoramento de instâncias (uptime, filas de emissão, certificados a vencer); runbooks de contingência SEFAZ; alertas proativos ao cliente | L2/L3, incidentes fiscais em produção, relacionamento | Suporte <2h/cliente/mês; ticket L1 resolvido sem humano ≥60% |
| 6 | **Financeiro** | Financeiro/admin | Faturamento recorrente, cobrança/régua de inadimplência, conciliação, dashboard de unit economics (MRR, churn, LTV:CAC), DRE simplificado | Precificação final, decisões de caixa, impostos da DVISION com o contador | Inadimplência <2%; DRE mensal no dia 5 |
| 7 | **Growth/Conteúdo** | Marketing | SEO/conteúdo sobre Reforma Tributária + ERP, cases públicos dos pilotos, newsletter para contadores, monitoramento de menções a Nomus/Odoo | Posicionamento, parcerias, participação em comunidade Frappe | 4 conteúdos/mês; pipeline inbound ≥30% dos leads |

**Infraestrutura dos agentes (tudo com ferramentas que você já usa ou open source):** repositório Git com CI como "sistema nervoso"; cron jobs para os monitores (SEFAZ/ANPD/ENCAT); LLM com RAG sobre a base de conhecimento fiscal e de suporte; Frappe Cloud como runtime multi-tenant; vault de segredos para certificados A1 dos clientes.

**Regra de ouro de escalonamento:** todo trabalho repetido 3 vezes vira automação/agente; toda automação que falha 2 vezes seguidas no mesmo ponto vira runbook com alerta para você.

---

## 5. Core fiscal próprio: arquitetura e roadmap

> Premissa do projeto: **construído por você + agentes de IA.** O desenho abaixo torna isso exequível em meses, não anos, porque ~70% do risco técnico já está resolvido em bibliotecas open source vivas (verificadas nesta sessão, 30/07/2026).

### 5.1 Arquitetura

```
erpnext_br_compliance (app Frappe — seu produto open core)
├── Emissão DF-e
│   ├── nfelib 2.5.2 (MIT) — schemas/bindings NF-e, NFS-e nacional, CT-e, MDF-e, BP-e
│   ├── PyNFe 0.6.5 (LGPL) — transmissão webservices SEFAZ (autorização, cancelamento, carta de correção, contingência SVRS)
│   └── BrazilFiscalReport 1.0.1 (LGPL-3.0) — DANFE/DACTE em PDF
├── Cálculo de tributos
│   ├── Calculadora de Tributos RFB (Docker, Java/Springboot) — IBS/CBS "Tax as a Service"
│   └── Motor próprio leve para ICMS/PIS/COFINS/IPI vigentes (regras por CFOP/CST, parametrizável)
├── Tabelas de referência (atualizadas pelo Agente Fiscal)
│   ├── cClassTrib / CST-IBS/CBS / cCredPres (JSON SVRS, IT 2025.002 v1.60, 23/06/2026)
│   ├── NCM, CEST (Convênio 142/18), CFOP, MVA por UF
│   └── Municípios NFS-e (padrão nacional + provedores regionais da sua área de atuação)
├── Obrigações acessórias (geração de arquivo/integração)
│   └── EFD ICMS/IPI (com Bloco K), EFD-Contribuições — faseadas
└── Camada paga (open core)
    ├── Templates verticais (pack_industria, pack_moveleiro, pack_vestuario, pack_agro)
    ├── Monitor de Reforma Tributária (compliance contínuo como serviço)
    └── Suporte/SLA + implantação
```

**Decisões de licença:** MIT/LGPL são compatíveis com open core — você pode distribuir o app e manter módulos proprietários (verificar cláusulas de linking LGPL na revisão do advogado; é análise de 1 hora, não um bloqueio). **PyTrustNFe: evitar** (projeto estagnado — verificado 30/07/2026).

### 5.2 Roadmap faseado (datado)

| Fase | Prazo | Escopo | Por quê nesta ordem |
|------|-------|--------|---------------------|
| **0 — Fundação** | Semanas 1–4 (ago/2026) | App Frappe esquelético; NF-e modelo 55 saída (CRT=1 e CRT=3, venda interna simples) em homologação; DANFE PDF; gestão de certificado A1 do cliente com alerta de vencimento | Documento de maior volume e menor complexidade; prova a cadeia inteira (XML → assinatura → SEFAZ → DANFE) |
| **1 — Operação mínima do piloto** | Semanas 5–10 (ago–set/2026) | NFS-e (padrão nacional; fallback para provedor do município do piloto); manifestação do destinatário; contingência SVRS; cancelamento/CC-e; inutilização | Tudo que um piloto indústria/serviços precisa para operar de verdade |
| **2 — Reforma Tributária** | Out–nov/2026 | Campos IBS/CBS (NT 2025.002 v1.40) em produção; integração Calculadora RFB; atualização v1.50 (combustíveis) até 03/11/2026; LC 224 (alíquotas PIS/COFINS recomposição) parametrizada | Cliente CRT=3 só pode entrar em produção com isso; prazo legal duro |
| **3 — Expansão DF-e + SPED** | Dez/2026–mar/2027 | CT-e/MDF-e (se cliente com transporte); geração de EFD ICMS/IPI (sem Bloco K inicialmente); EFD-Contribuições; BP-e se varejo | Abre verticais comércio/transporte; SPED é o que o contador-parceiro mais pede |
| **4 — Verticalização + avançado** | Abr–jul/2027 | Bloco K (quando cliente indústria LR/LP exigir); ICMS-ST/MVA por UF; DIFAL automático; NFP-e + Funrural (pack_agro); avaliação de homologação PAA | Só com 2+ clientes pagantes por vertical — regra de produto, não entusiasmo |

**Cadência regulatória permanente (Agente Fiscal):** toda NT nova vira issue em ≤48h; patch de layout em ≤5 dias úteis; teste de homologação antes de cada release; release notes para clientes em linguagem de contador.

**Riscos técnicos e mitigações:**
- *Instabilidade SEFAZ/contingência* → SVRS + fila de retransmissão com idempotência (Fase 1).
- *NFS-e fora do padrão nacional em município de cliente* → priorizar clientes em municípios aderidos; adaptador por provedor só quando houver cliente pagante nele.
- *Mudança de layout com 60 dias de antecedência (ato conjunto)* → monitor + parametrização por versão de layout no código (não hardcoded).

---

## 6. Matriz de compliance

Versão resumida aqui; a tabela completa e filtrável está no CSV anexo `Matriz_Compliance_e_Mercadoria_DVISION_2026-07-30.csv`.

### 6.1 Documentos fiscais eletrônicos (DF-e)

| Documento | Quem precisa | Status MVP | Prazo crítico | Risco/multa |
|-----------|--------------|-----------|---------------|-------------|
| NF-e (mod. 55) | Toda indústria/comércio | **Fase 0** | Layout IBS/CBS em produção 03/08/2026 | Nota rejeitada = venda parada; multas por escrituração incorreta |
| NFC-e (mod. 65) | Varejo B2C | Fase 1 (se cliente varejo) | Idem | Idem |
| NFS-e padrão nacional | Prestadores de serviço | Fase 1 | Adesão municipal contínua (3.400+ municípios) | Multas municipais; cliente não fatura serviço |
| CT-e / MDF-e | Transporte próprio ou contratado | Fase 3 | — | Multas por transporte sem documento |
| BP-e | Bilhete de passagem | Fase 4 (só se nicho) | — | — |
| Manifestação do destinatário | Indústrias (NF-e de entrada) | Fase 1 | NT 2020.001 v1.60 (23/04/2026) | Créditos de ICMS perdidos; passivo |
| NFP-e | Produtor rural (clientes agro) | Fase 4 | Obrigatória desde 05/01/2026 | Multas estaduais |

### 6.2 Obrigações acessórias (SPED & cia.) — escopo do seu produto vs. escopo do contador

| Obrigação | Periodicidade | Quem entrega hoje | No seu produto? | Multa por ausência |
|-----------|---------------|-------------------|-----------------|--------------------|
| EFD ICMS/IPI | Mensal | Cliente/contador | **Fase 3 (geração do arquivo)** | R$ 500–1.500/mês (varia por UF) |
| Bloco K (EFD) | Mensal (indústrias LR/LP) | Cliente | Fase 4 (só com cliente que exija) | Multa por registro incorreto/ausente |
| EFD-Contribuições | Mensal, 10º dia útil do 2º mês | Contador | Fase 3 (arquivo) | Multas por atraso/omissão |
| EFD-Reinf | Mensal, dia 15 | Contador | Não gerar — integrar/exportar dados | Multas; substituiu DIRF (extinta 2026, IN RFB 2.181/2024) |
| ECD (contábil) | Anual | Contador | Exportar dados; não gerar | Multas |
| PGDAS-D / DCTFWeb | Mensal (Simples) | Contador | Não | — |
| eSocial | Contínua | Contador/RH | **Fora do MVP — declarado na proposta** | Multas trabalhistas do cliente |
| DIRBI | Conforme benefício | Contador | Não (170+ benefícios, escopo contábil) | — |

**Posicionamento comercial correto:** "entregamos os dados prontos e os arquivos fiscais principais; o contador do cliente continua responsável pelas declarações" — isso torna o contador seu aliado (canal), não concorrente.

### 6.3 Regras de mercadoria (o que o ERP precisa parametrizar)

| Regra | O que é | Onde entra no ERP | Prioridade |
|-------|---------|-------------------|-----------|
| **NCM** | Classificação fiscal de 8 dígitos, obrigatória em todo item de NF-e | Cadastro de item + validação + tabela atualizada | MVP |
| **CFOP** | Código fiscal da operação (entrada/saída, interna/interestadual/exterior) | Regras por tipo de operação, parametrizável por vertical | MVP |
| **CST/CSOSN** | Situação tributária (regime normal / Simples) | Motor de tributos, por CFOP+NCM+UF | MVP |
| **CEST** | Código de mercadoria sujeita a ST (Convênio ICMS 142/18) | Cadastro de item; obrigatório quando ST | Fase 2–3 |
| **ICMS-ST / MVA** | Substituição tributária com margem de valor agregado por UF | Cálculo na emissão + tabela MVA por UF/NCM | Fase 3 |
| **DIFAL** | Diferencial de alíquota interestadual | Cálculo na venda interestadual B2C/B2B | Fase 3 |
| **IPI** | Imposto sobre produto industrializado | Cálculo + destaque na NF-e de indústria | MVP (indústria) |
| **PIS/COFINS (LC 224/2025)** | Alíquotas recomposição desde 01/04/2026: cumulativo 0,065%/0,300%; não cumulativo 0,165%/0,760% | Motor de tributos parametrizado | Fase 2 |
| **IBS/CBS/IS (Reforma)** | Novos tributos — campos cClassTrib, CST-IBS/CBS na NF-e | NT 2025.002 + Calculadora RFB | Fase 2 (obrigatório 03/08/2026 p/ CRT=3) |
| **Funrural / NFP-e** | Contribuição rural + nota do produtor | pack_agro | Fase 4 |

### 6.4 Legal e digital (a DVISION como empresa)

| Item | Obrigação | Custo estimado | Quando | Fonte (data) |
|------|-----------|----------------|--------|--------------|
| **DPA com cada cliente** | LGPD art. 42 — você é operador, cliente é controlador; responsabilidade solidária | Template + revisão (dentro dos R$ 3–6k do advogado) | Antes do 1º cliente | Res. ANPD; verificado 30/07/2026 |
| **RoPA** (registro de operações de tratamento) | LGPD | 1–2 dias com template | Antes do 1º cliente | — |
| **Runbook de incidente** | Notificação à ANPD em 3 dias úteis | 1 dia | Antes do 1º cliente | Res. CD/ANPD 15/2024 |
| **Encarregado/DPO formalizado** | Obrigatório | Você mesmo, designado em documento | Agora | Res. CD/ANPD 18/2024 |
| **Hospedagem na UE (Frankfurt)** | Adequação UE↔Brasil reconhecida; EUA exigiria CPCs | Incluído no Frappe Cloud | Decisão de arquitetura — tomar agora | Res. CD/ANPD 32/2026 (UE OK) / 19/2024 (CPCs) |
| **Cláusula de PI nos contratos** | Lei do Software 9.609/98 art. 4º presume código do contratante — **inverter explicitamente**: customizações do cliente são do cliente; seu app core é seu | Dentro da revisão advocatícia | Antes do 1º contrato | Lei 9.609/98 |
| **Contrato de certificado digital A1 do cliente** | Termo de guarda/responsabilidade | Template | 1º cliente | — |
| **ISO 27001:2022** | Não obrigatória; exigida por alguns clientes maiores | R$ 80–180 mil ciclo completo + R$ 12–25 mil/ano manutenção | **Não no ano 1.** Gap assessment informal agora; certificar no ano 2–3 se um contrato ≥R$ 100k/ano exigir | decripte.com 27/06/2026; consultoriaiso.com 24/07/2026 |
| **ISO 9001** | Não obrigatória | R$ 8–20 mil (microempresa) | Opcional, ano 2 | consultoriaiso.com 24/07/2026 |
| **Seguro RC profissional (E&O) + cyber** | Não obrigatório; protege de erro fiscal em produção | RC geral desde ~R$ 620–920/mês; E&O tech sob cotação | Ao fechar o 3º–4º cliente | comparalatam.com, jul/2026 (faixa indicativa) |
| **CNAE correto + alvará** | Obrigatório | Contador | Verificar agora | Checklist da sua pesquisa anterior |
| **ECA Digital (Lei 15.211/2025)** | Só B2C com menores | — | **Não aplicável** — registrar no RoPA | Lei 15.211/2025 |
| **INPI (marca DVISION)** | Proteção de marca | ~R$ 355–700 taxas + opcional despachante | Ano 1 | INPI |

---

## 7. Precificação

### 7.1 O que a pesquisa de modelos mostrou (jul/2026)

Modelos B2B vigentes: cost-plus, **value-based**, **tiered (good-better-best)**, assinatura, **usage-based**, contrato e **híbridos**. Dois sinais fortes de 2026:
- 76% dos líderes de vendas dizem que **usage-based** ficou mais importante para os clientes no último ano (Salesforce, survey 4.000+ profissionais, 2026); o padrão vencedor é **híbrido: assinatura base + metragem de uso**.
- Em soluções complexas configuradas por cliente (seu caso), **value-based** supera cost-plus: ancore o preço no ROI mensurável (horas de escrituração economizadas, multas evitadas, prazo de fechamento) — pesquisa ScienceDirect 2025 e guias CRV/2026 apontam na mesma direção, com a ressalva de que value-based exige dados do cliente na discovery.
- Tiered em 3 níveis explora "aversão aos extremos": o plano do meio concentra a maioria das vendas — desenhe o tier do meio como o mais rentável.

### 7.2 Benchmarks de mercado (verificados jul/2026)

| Player / referência | Preço | Escopo | Fonte (data) |
|---------------------|-------|--------|--------------|
| **Nomus ERP Industrial** | R$ 1.290–4.290/mês | SaaS para indústria PME — seu concorrente direto | site Nomus, jul/2026 |
| **FocusNFe** (API fiscal) | R$ 89,90 (Solo, 1 CNPJ/100 notas) · R$ 113,90 (Start, 3 CNPJs) · R$ 548 (Growth, ilimitado/4.000 notas) · município novo NFS-e R$ 199 em 15 dias | Só emissão DF-e — mostra o "preço do componente fiscal" | site FocusNFe, jul/2026 |
| **NFE.io** | R$ 190–375/mês | API/emissor fiscal | site NFE.io, jul/2026 |
| **TOTVS** (implantação) | R$ 40–300 mil | Implantação ERP tradicional | sua pesquisa de mercado, 2026 |
| **SAP Business One** | R$ 70–150 mil implantação; parceiros cobram ex.: R$ 35 mil adesão + R$ 12.990/mês | Mid-market | sua pesquisa, 2026 |
| **Odoo** | Licença por usuário + Success Packs de implantação | Concorrente direto no open source | sua pesquisa, 2026 |
| **ERPNext/Frappe** | Licença R$ 0 (GPLv3); Frappe Cloud US$ 40–150/mês por servidor dedicado | Sua base | frappe.io, jul/2026 |

**Leitura estratégica:** o mercado separa "componente fiscal" (R$ 90–550/mês) de "ERP industrial" (R$ 1.290+/mês) de "implantação" (R$ 40–300 mil). Seu espaço: **ERP industrial completo a preço de componente + implantação 5–10× mais barata que TOTVS** — possível porque seu custo marginal é infraestrutura + seus agentes, não consultores alocados.

### 7.3 Modelo recomendado: híbrido de 3 camadas

**Camada 1 — Implantação (serviço, pago uma vez):** escopo fechado por vertical, preço fixo.
- Ano 1 (fase de cases): **R$ 8–15 mil** com 30–50% de desconto em troca de case público + depoimento + referência ativa.
- Ano 2: **R$ 15–30 mil** conforme templates maduros (seu custo cai, o preço sobe — value-based: o cliente economiza R$ 40 mil+ vs. implantação tradicional).

**Camada 2 — Assinatura tiered (SaaS + compliance fiscal contínuo):**

| Tier | Preço-alvo | Inclui | Para quem |
|------|-----------|--------|-----------|
| **Essencial** | R$ 790/mês | ERP core + NF-e/NFS-e + DANFE + atualizações fiscais + suporte assíncrono | Serviços/comércio pequeno |
| **Indústria** ⭐ | R$ 1.490/mês | Essencial + MRP + pack vertical + manifestação destinatário + IPI + Bloco K quando exigido | Seu ICP (indústria 20–80 func.) — posicionado contra Nomus R$ 1.290+ com mais compliance |
| **Indústria Plus** | R$ 2.490/mês | Indústria + multi-CNPJ + CT-e/MDF-e + SLA prioritário + horas de consultoria/mês | Indústria maior/multi-planta |

O tier do meio é o produto — âncora R$ 2.490 torna R$ 1.490 "óbvio".

**Camada 3 — Usage-based sobre a base:** franquia de documentos fiscais por tier (ex.: 500/2.000/5.000 DF-e mês); excedente a R$ 0,05–0,10/documento. Alinha receita a valor, captura crescimento do cliente sem renegociação e segue a tendência usage-based de 2026. Infra multi-tenant no Frappe Cloud mantém seu custo marginal por cliente baixo (US$ 40–150/mês por servidor dedicado comporta vários tenants).

**Canal contador:** comissão recorrente de 10–15% da assinatura (modelo Omie). O contador indica, você implanta, ele continua dono das declarações (seção 6.2) — alinhamento total.

**Guardrails de desconto:** desconto só por (a) case público no ano 1, (b) anualidade (10–12%), (c) volume multi-CNPJ. Nunca por pressão de fechamento — registre no CRM o motivo de cada desconto (Agente Comercial audita).

### 7.4 Unit economics de referência (da sua pesquisa anterior, cenário base)
- Receita ano 1: R$ 265 mil (cenário base; pessimista R$ 143,8 mil / otimista R$ 405,9 mil); break-even M12 (base); CAC ~R$ 8,9 mil; LTV:CAC ~14×. **Revisitar esses números após os 2 primeiros pilotos** — são projeções, não medições.

---

## 8. Capacidade: 1 founder + agentes até 10 clientes

### 8.1 A matemática das horas

Orçamento anual útil: **~2.000h** (da sua pesquisa anterior).

| Demanda | Premissa | Carga anual (10 clientes) |
|---------|----------|---------------------------|
| Implantações novas | 60–80h cada ano 1 → 40h com templates; ~6–8 novas no ano 1 | 400–640h |
| Suporte recorrente | <2h/cliente/mês com deflexão L1 ≥60% | 240h |
| Core fiscal (build) | Fases 0–2 nos meses 1–5 | 400–500h |
| Manutenção fiscal contínua | Agente Fiscal executa; você revisa: ~4h/semana | ~200h |
| Vendas/relacionamento | 2–4 reuniões/semana | ~300h |
| Gestão/overflow | buffer 15% | ~250h |
| **Total** | | **~1.800–2.100h — fecha, sem folga** |

**Conclusão da matemática:** 10 clientes é o teto real do modelo 1-pessoa — como você mesmo definiu. O plano não depende de heroísmo; depende de duas alavancas: (1) templates verticais derrubarem implantação de 80h para 40h; (2) deflexão de suporte ≥60%. Se qualquer uma falhar, o teto cai para 6–7 clientes.

### 8.2 KPIs semanais (o Agente Financeiro monta o dashboard; você olha 30 min/sexta)

1. Horas por implantação (alvo: ≤60h caindo para 40h)
2. Horas de suporte por cliente/mês (alvo: <2h)
3. Deflexão L1 (alvo: ≥60%)
4. Rejeições fiscais em produção (alvo: 0 por layout desatualizado)
5. MRR, churn mensal (gate SaaS: <3%), NPS (≥8)
6. Pipeline: leads qualificados/semana; tempo discovery→proposta (<24h)

### 8.3 Gatilhos de contratação (decisão por dados, não por cansaço)

| Gatilho | Contratar | Perfil | Quando provável |
|---------|-----------|--------|-----------------|
| Suporte >25% do seu tempo por 4 semanas seguidas | 1º | Suporte N1/implantação júnior (remoto, PJ) | 7º–9º cliente |
| Implantação média >90h após 3 clientes na mesma vertical | Revisar template antes de contratar | — | — |
| Churn >3%/mês ou NPS <8 | Parar vendas, corrigir produto | — | — |
| Fila de implantação >2 clientes pagantes esperando >30 dias | 1º ou 2º | Dev Frappe júnior | 9º–10º cliente |
| 10 clientes ativos + 3 na fila | 2º | Customer success/implantação | Transição ano 2 |

**Gate para virar SaaS self-service (da sua estratégia anterior, mantido):** ≥10 clientes, churn <3%/mês, suporte <2h/cliente/mês, NPS ≥8 — só então investir em onboarding sem humano.

---

## 9. Plano de ação datado (ago/2026 → jul/2027)

### Mês 0–1 (agosto/2026) — Fundação
- [ ] **Semana 1:** verificar publicação do **ato conjunto RFB/CGIBS** (prometido até fim de julho — ainda não publicado em 29/07); registrar o que muda nos prazos
- [ ] Semana 1: stack legal da DVISION — CNAE, DPO formalizado, contratação do advogado (R$ 3–6 mil) para pacote: contrato de implantação + cláusula PI (invertendo art. 4º Lei 9.609/98) + DPA + termo A1 + NDA
- [ ] Semana 1–2: Frappe Cloud **região Frankfurt** (adequação UE, Res. 32/2026); repositório + CI; Agente Fiscal v1 (monitores ENCAT/SEFAZ/ANPD com alertas)
- [ ] Semana 2–4: **Fase 0 fiscal** — NF-e modelo 55 em homologação (nfelib + PyNFe), DANFE (BrazilFiscalReport), gestão de certificado A1
- [ ] Semana 3–4: lista de 30 prospects (indústrias 20–80 func. em Londrina/Cambé/Arapongas/Apucarana — base CEMPRE da sua pesquisa: ~650 empresas, intervalo 545–718); mapear 10 contadores para o canal

### Mês 2 (setembro/2026) — Piloto 1
- [ ] Fechar **piloto 1** (ideal: indústria metal-mecânica ou moveleira, CRT=3, NPS-alto-potencial, dono acessível) — preço case R$ 8–12 mil + R$ 790–1.190/mês
- [ ] Fase 1 fiscal: NFS-e do município do piloto, manifestação do destinatário, contingência SVRS
- [ ] RoPA + DPA assinado com o piloto; runbook de incidente testado (simulado de 2h)

### Mês 3 (outubro/2026) — Reforma no código
- [ ] **Fase 2:** campos IBS/CBS (NT 2025.002 v1.40) + Calculadora RFB integrada; v1.50 (combustíveis) antes de 03/11/2026; alíquotas LC 224 parametrizadas
- [ ] Piloto 1 operando NF-e em produção; começar case público
- [ ] Piloto 2 fechado (vertical diferente para testar transferência de template)

### Meses 4–6 (nov/2026–jan/2027) — Repetibilidade
- [ ] Template vertical v1 (a vertical do piloto 1); implantação-alvo ≤60h
- [ ] Agente de Suporte com base de conhecimento; deflexão medida desde o 1º ticket
- [ ] 3–4 clientes pagantes; **Gate 1 (fim jan/2027):** ≥3 clientes ativos, ≥1 case público, implantação ≤80h, 0 incidentes fiscais graves → continuar; senão, corrigir antes de escalar vendas

### Meses 7–9 (fev–abr/2027) — Canal e SPED
- [ ] Fase 3 fiscal: EFD ICMS/IPI (geração) + EFD-Contribuições; CT-e se houver demanda de cliente
- [ ] Canal contador ativado: 3–5 contadores com material + comissão 10–15%; meta: 30% dos leads via canal
- [ ] 5–7 clientes; **Gate 2 (fim abr/2027):** MRR ≥R$ 8 mil, churn <3%, suporte <2h/cliente/mês

### Meses 10–12 (mai–jul/2027) — Teto do modelo 1-pessoa
- [ ] 8–10 clientes; template vertical v2; horas/implantação ≤50h
- [ ] Decisão estruturada: contratar 1º colaborador (gatilhos 8.3) ou segurar crescimento
- [ ] Avaliações ano 2: ISO 27001 gap assessment formal; PAA (se decidir produto MEI/Simples/agro); pack_agro (NFP-e/Funrural) se 2+ clientes agro
- [ ] **Gate 3 (jul/2027):** 10 clientes, NPS ≥8, MRR ≥R$ 13 mil, LTV:CAC medido (não projetado) ≥5× → plano ano 2 (SaaS self-service ou time enxuto)

---

## 10. Custos reais (tabela item | valor | fonte | data)

| Item | Valor | Periodicidade | Fonte | Data |
|------|-------|---------------|-------|------|
| Frappe Cloud (servidor dedicado, Frankfurt) | US$ 40–150/mês (~R$ 220–830) | Mensal | frappe.io | jul/2026 |
| Ferramentas de IA/LLM (agentes) | R$ 200–800/mês (conforme uso) | Mensal | estimativa de uso típico | jul/2026 |
| Certificado e-CNPJ A1 (DVISION) | R$ 100–400/ano (ex.: Certisign R$ 186,90–263,90; promoções de R$ 79–110) | Anual | Certisign; Serasa; varejistas de certificado | jul/2026 |
| Advogado (pacote contratos + PI + DPA) | R$ 3.000–6.000 | Uma vez | sua pesquisa anterior | jul/2026 |
| Contador da DVISION | R$ 300–800/mês (LTDA Simples) | Mensal | faixa de mercado Londrina | jul/2026 |
| Seguro RC/E&O | ~R$ 620–920/mês (RC geral, faixa indicativa; E&O sob cotação) | Mensal, a partir do 3º–4º cliente | comparalatam.com | jul/2026 |
| ISO 27001 (ano 2–3, se exigida) | R$ 80–180 mil + R$ 12–25 mil/ano | Uma vez + anual | decripte.com; consultoriaiso.com | jun–jul/2026 |
| ISO 9001 (opcional) | R$ 8–20 mil | Uma vez | consultoriaiso.com | jul/2026 |
| INPI marca | R$ 355–700 (taxas) | Uma vez | INPI | jul/2026 |
| **Total ano 1 (sem ISO, com seguro a partir do mês 7)** | **~R$ 25–45 mil** | | | |

---

## 11. Riscos e incertezas (marcados explicitamente)

| # | Risco/incerteza | Status | Impacto | Mitigação |
|---|-----------------|--------|---------|-----------|
| 1 | **Ato conjunto RFB/CGIBS não publicado** em 29/07/2026 | **Aberto — verificar nos próximos dias** | Pode mudar prazos e layouts com 60 dias de antecedência | Agente Fiscal monitorando; arquitetura parametrizável por versão de layout |
| 2 | Alíquotas IBS/CBS 2027+ não definidas | Aberto | Cálculo de 2027 depende de lei/ato futuro | Calculadora RFB absorve; comunicação proativa aos clientes |
| 3 | **Demanda não validada primariamente** | Aberto | Todo o plano assume 6–8 vendas no ano 1 | Os 2 pilotos são o teste; Gate 1 mata ou corrige a tese antes de grande investimento |
| 4 | Conflito de prazo reportado na sua pesquisa anterior (CZ-01: prazo 03/08 "em revisão") | Parcialmente resolvido | Fontes de jul/2026 (TecnoSpeed) confirmam 03/08/2026 p/ CRT=3; o ato conjunto pode alterar | Tratar 03/08 como vigente até ato em contrário |
| 5 | NFS-e fora do padrão nacional em município-alvo | Médio | Adaptador específico = 1–3 semanas | Priorizar clientes em municípios aderidos; checar adesão na discovery |
| 6 | Licenças LGPL (PyNFe, BrazilFiscalReport) no open core | Baixo, mas analisar | Linking/derivação exige cuidado | 1h com o advogado na revisão de contratos |
| 7 | Responsabilidade solidária LGPD (art. 42) por erro no ERP | Médio | Incidente no cliente pode respingar na DVISION | DPA bem delimitado + runbook + seguro E&O a partir do 3º cliente |
| 8 | Concorrência reage (Nomus/Odoo cortam preço na Reforma) | Médio | Pressão no tier do meio | Diferencial é compliance nativo + implantação 5–10× mais barata + vertical; não competir por preço |
| 9 | Capacidade: premissas de horas otimistas | Médio | Teto cai de 10 para 6–7 clientes | KPIs semanais; gatilhos de contratação não são fracasso, são design |
| 10 | PAA pode não valer o esforço de homologação | Baixo | Escopo restrito (MEI/Simples/rural) | Decisão adiada a 2027 com dados — zero investimento agora |

---

## 12. O que fazer agora (checklist priorizado — próximas 2 semanas)

1. **[Hoje–sexta]** Verificar se o ato conjunto RFB/CGIBS foi publicado; ajustar seção 2.1 e Fase 2 conforme o texto
2. **[Semana 1]** Contratar advogado para o pacote contratual (contrato + PI + DPA + NDA + termo A1) — R$ 3–6 mil; é o único gasto que não pode esperar cliente
3. **[Semana 1]** Abrir Frappe Cloud em **Frankfurt**; subir repositório `erpnext_br_compliance` com CI; criar Agente Fiscal v1 (3 monitores com alerta: ENCAT/portal NF-e, ANPD, portal SVRS tabelas cClassTrib)
4. **[Semana 1–2]** NF-e modelo 55 autorizando em homologação PR (nfelib + PyNFe + certificado A1 de teste) — o "hello world" do core fiscal
5. **[Semana 2]** Formalizar-se como encarregado/DPO; RoPA v1; runbook de incidente de 1 página
6. **[Semana 2]** Lista de 30 prospects + 10 contadores; agendar 5 conversas de discovery (meta: piloto 1 fechado até meados de setembro)
7. **[Semana 2]** Publicar o 1º conteúdo: "Reforma Tributária: sua NF-e está pronta para 03/08/2026?" — começa o canal inbound

---

## 13. Fronteira profissional

Este plano informa decisões de negócio com dados datados e fontes citadas, mas **não substitui** (a) advogado para contratos, LGPD e licenças — o pacote de R$ 3–6 mil é parte do plano, não opcional; (b) contador para o enquadramento fiscal da DVISION e dos clientes; (c) contador/auditor para interpretação definitiva de obrigações acessórias por UF. Onde a lei está em transição (Reforma Tributária, ato conjunto pendente), o plano marca a incerteza em vez de fingir certeza — revalide os pontos datados a cada gate de 90 dias.

---

*Documento gerado em 30/07/2026. Anexos: `Matriz_Compliance_e_Mercadoria_DVISION_2026-07-30.csv`, `Benchmarks_Precificacao_ERP_Brasil_2026-07-30.csv`, `Custos_Operacionais_DVISION_Ano1_2026-07-30.csv`.*
