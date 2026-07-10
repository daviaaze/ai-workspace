# Impacto de Negócio — Adequação LGPD + CIE v3.3 (Meia-Entrada)

> **Data:** 2026-07-03
> **Analista:** agente senior business analyst
> **Fontes:** Parecer Jurídico; Auditoria Segurança & LGPD; Auditoria CIE v3.3; Resume dos repositórios; Plano de Ação do Arquiteto `analysis/2026-07-03-plano-acao-arquitetura.md`.

---

## 0. Sumário Executivo

O Meia-Entrada é um **SaaS B2B2C** alugado a entidades estudantis (DCEs, UPEEs, escolas, IES) para gerenciar campanhas de carteirinhas. O Parecer Jurídico impõe mudanças que **redefinem o relacionamento comercial**: de "locatário de software" para **co-controladora de dados pessoais**, exigindo contratos, DPO, governança e possivelmente acreditação EEA.

**Top-3 riscos comerciais:**
1. **Churn de entidades** se o custo de compliance (DPO, contratos, EEA) for repassado de forma desproporcional.
2. **Inadmissibilidade de entidades sem CNPJ** se a co-controladoria exigir personalidade jurídica — cortando um segmento possivelmente grande.
3. **Perda de competitividade** se concorrentes migrarem para CIE oficial antes da Meia-Entrada.

**Top-3 oportunidades:**
1. **Diferenciação de confiança**: publicar segurança LGPD como vantagem de venda para entidades e estudantes.
2. **Nova linha de receita**: carteirinha CIE oficial pode ter preço premium ou taxa de emissão.
3. **Redução de fraude**: KYC de entidades e assinatura criptográfica reduzem carteirinhas falsas, protegendo a marca.

**Recomendação de leitura para o CEO:** o modelo de transição híbrida do Parecer é o caminho mais defensável: corrigir críticos em 24h, publicar LGPD em 7 dias, e **não prometer CIE oficial até ter EEA contratada**.

---

## 1. Mapa do Negócio Atual

### 1.1 Stakeholders

```mermaid
graph LR
    A[Meia-Entrada<br/>Controladora/Operador SaaS] -->|aluga plataforma| B[Entidade Emissora<br/>Co-controladora]
    B -->|coleta dados do vínculo| C[Estudante<br/>Titular]
    C -->|preenche formulário| A
    A -->|emite carteirinha PDF| C
    D[Estabelecimento<br/>Cinema/Teatro] -->|valida /V[token]| A
    E[Supabase Inc.] -->|operador cloud| A
    F[PostHog/E-mail/WhatsApp] -->|operadores futuros| A
    G[Responsável Legal] -->|consente p/ menor| C
```

### 1.2 Proposta de valor
Hoje: software + emissão de PDF de carteirinha estudantil privada. A entidade emissora (co-controladora) define as regras de quem é estudante. A Meia-Entrada fornece infraestrutura, formulário, geração de PDF/QR, logística opcional.

**O que está faltando no core:** nenhum produto ainda é a **CIE oficial** reconhecida nacionalmente.

### 1.3 Fontes de receita (a confirmar com fundador — {{TBD}})
Hipotese primária: **mensalidade/assinatura por entidade** ou **taxa por carteira emitida**. Possivelmente também receita de **impressão + entrega domiciliar**.

### 1.4 Estrutura de custos
| Categoria | Custo atual | Custo novo pós-Parecer |
|---|---|---|
| Infra (Supabase, Vercel, storage) | {{TBD}} | Mesmo + DPA/SCC |
| E-mail/PostHog/WhatsApp/SMS | {{TBD}} | + opt-in compliance |
| Impressão/entrega (se Meia-Entrada assume) | {{TBD}} | + custo de endereço (dado extra) |
| DPO/Encarregado | 0 | R$ 3k-15k/mês (fractional ou integral) |
| Contratos jurídicos (operador + co-controladoras) | 0 | R$ 5k-25k inicial + revisões |
| Acreditação EEA / integração EEA terceira | 0 | R$ 0 (API) até R$ 50k+ (acreditação própria) |
| Auditoria/pen-test | 0 | R$ 10k-30k/ano |

### 1.5 Funil de campanha (status da carteira)
`Cadastrada → Autorizada → Em Produção → Enviada → Entregue → Removida`

O Parecer insere gates no funil:
- Antes de **Autorizada**: consentimentos LGPD (L-01, L-02, F-02).
- Antes de **Em Produção**: contrato de co-controladora vigente (F-03).
- Antes de **Entregue**: endereço só se domiciliar (minimização).

---

## 2. Matriz de Impacto de Negócio

| ID Finding | Pedacinho do modelo afetado | Tipo comercial | Severidade | Ação recomendada |
|---|---|---|---|---|
| S-08 PostHog | Confiança; exposição a ANPD | Risco/Reputação | 🔴 | Hotfix imediato; comunicar se houve vazamento |
| S-02 service_role | Toda a operação; confiança de entidades | Risco/Operação | 🔴 | Remover em 24h; considerar notificação ANPD |
| S-03 rotas públicas | Validador; risco de scraping massivo | Risco/Operação | 🔴 | Token assinado; limitar exposição |
| L-01/L-02 consentimento | Taxa de conversão do formulário | Receita/Processo | 🟠 | 2 checkboxes; testar A/B; alternativa retirada |
| L-03 política | Transparência; confiança | Reputação/Processo | 🟠 | Publicar em 7 dias; integrar ao formulário |
| L-04 retenção/direitos | Governança; custo operacional | Custo/Processo | 🟡 | Política + portal de direitos (F-01) |
| L-05 rate-limit | Disponibilidade; segurança | Custo/Operação | 🟡 | Captcha/Redis |
| L-06 DPO | Custo fixo mensal; governança | Custo/Processo | 🟡 | Nomear DPO; decidir modelo central/por entidade |
| F-03 co-controladoria | Contrato comercial; onboarding | Receita/Processo | 🟠 | Novo contrato padronizado; gate técnico de emissão |
| F-02 menor | Segmento fundamental/médio | Receita/Processo | 🟡 | Fluxo de tutelante; UX mais longa |
| CIE v1-v3 | Produto; competitividade | Receita/Estratégia | 🟠 | Decidir EEA; roadmap premium |
| M-01 copy marketing | Publicidade; risco CDC | Risco/Reputação | 🟡 | Reescrever copy; disclaimer dinâmico |

---

## 3. Segmentação de Cliente — Impacto Diferenciado

| Segmento | Exemplo | CNPJ? | Esfera | Consent. responsável? | Ação do Parecer | Complexidade | Decisão sugerida |
|---|---|---|---|---|---|---|---|
| 1. Universidade federal formal | DCE/UPEE da UFPB, UFRJ | Sim | Federal | Não (maiores) | Co-controladora; DPO central | Média | **Servir com contrato** |
| 2. Entidade estadual estudantil | UPE estadual | Sim | Estadual | Não | Co-controladora; contrato estadual | Média | **Servir com contrato** |
| 3. Coordenação de curso sem CNPJ | Grêmio de curso | Não | Federal/Estadual | Sim (menores) | F-02 + F-03 | Alta | **Servir com mitigação** (exigir associação formal) ou **recusar** |
| 4. Escola privada fundamental/médio | Colégio particular | Sim | Privado | Sim (menores) | Consentimento do responsável; contrato | Média | **Servir com contrato** |
| 5. Rede pública municipal/estadual | Escola pública | Sim (prefeitura/estado) | Pública | Sim | Co-controladoria pública; licitação | Alta | **Servir com mitigação** (processo burocrático longo) |
| 6. IES privada superior | Universidade particular | Sim | Privado | Não | Co-controladora; contrato simples | Baixa | **Servir com contrato** |

**Observação:** o segmento 3 (sem CNPJ) é o mais vulnerável. Se a decisão for recusar, impacta volume. Se for aceitar, exige KYC robusto e termo do responsável legal.

---

## 4. Fluxo de Entrega — Retirada vs. Domiciliar

**Conferência no código:** `web/src/components/form/steps/step-endereco.tsx` coleta endereço **independentemente** do canal de entrega. Isso é uma violação de minimização (art. 6º III LGPD).

**Recomendação:**
- Perguntar canal de entrega **antes** de pedir endereço.
- Se **retirada**: não coletar CEP/rua/número/complemento/bairro/cidade/UF.
- Se **domiciliar**: coletar apenas o endereço de entrega; explicar na política a finalidade (execução de contrato — art. 7º V).

**Custo:** quem paga a entrega domiciliar? Opções:
1. **Meia-Entrada absorve** — reduz margem; pode ser vantagem competitiva.
2. **Entidade repassa** — adiciona item na mensalidade/taxa.
3. **Estudante paga** — no checkout (menos atrativo).

**Recomendação do analista:** Opção 2 ou 3, dependendo de segmento. IES privadas podem absorver; escolas públicas devem repassar ou optar por retirada.

---

## 5. Roadmap de Comunicação Outbound (e-mail / WhatsApp / SMS)

| Canal | Caso de uso | Tipo | Base legal | Consentimento? | Restrição | Custo | Recomendação |
|---|---|---|---|---|---|---|---|
| **E-mail** | Status do pedido, validade expirando, reemissão | Transacional | Art. 7º V (execução contrato) | Implícito no consentimento geral | Descadastro fácil (CDC art. 30) | Baixo | **Habilitar primeiro** — mais seguro e barato |
| **E-mail** | Marketing de novas campanhas | Marketing | — | Opt-in explícito (art. 8º) | Descadastro | Baixo | Só após opt-in separado |
| **WhatsApp** | Status do pedido, lembrete de validade | Transacional | Art. 7º V | Opt-in para WhatsApp (ToS Meta) | Meta exige template aprovado; proíbe spam | Médio | **Habilitar em S2** com templates aprovados |
| **WhatsApp** | Marketing | Marketing | — | Opt-in duplo (LGPD + Meta) | Restrições severas | Médio | **Evitar** até maturidade de compliance |
| **SMS** | Código de validação, alerta crítico | Transacional | Art. 7º V | Implícito | Alto custo por msg | Alto | **Reservar para crítico** |

**Recomendação geral:** começar com **e-mail transacional**; adicionar WhatsApp transacional em S2; marketing em qualquer canal só com opt-in separado e registro no `lgpd_consents`.

---

## 6. Pricing & Modelo Comercial Pós-Parecer

### 6.1 Custos novos a repassar
| Custo | Estimativa mensal/anual | Como repassar |
|---|---|---|
| DPO fractional | R$ 3k-8k/mês | Taxa de compliance por entidade (R$ 50-200/mês) |
| Contratos jurídicos (revisão) | R$ 10k-30k/ano | Setup fee inicial no onboarding |
| Auditoria/pen-test | R$ 10k-30k/ano | Aumento de mensalidade padrão |
| Captcha/Redis rate-limit | R$ 50-300/mês | Incluir no plano base |
| EEA integração | R$ 0-5k/mês | Taxa por carteira CIE oficial |

### 6.2 Opções de repasse (≥3)

**Opção A — Taxa de compliance por entidade (recomendada)**
- Adiciona R$ 50-200/mês por entidade, escalonado por volume de carteiras.
- **Prós:** transparente; justo (quem emite mais paga mais).
- **Contras:** pode causar churn em entidades pequenas.
- **Impacto por segmento:** IES privadas absorvem fácil; escolas públicas podem questionar.

**Opção B — Aumento geral de mensalidade**
- Aumenta 15-30% no plano base.
- **Prós:** simples de implementar.
- **Contras:** entidades pequenas pagam proporcionalmente mais; dificulta venda.

**Opção C — Taxa por carteira emitida**
- Adiciona R$ 0,50-2,00 por carteira (com ou sem CIE).
- **Prós:** alinha custo ao volume/risco; atrativo para entidades pequenas.
- **Contras:** receita menos previsível; exige controle rigoroso.

**Opção D — Híbrida (recomendada para transição)**
- Plano base sobe 10%; taxa de compliance por entidade a partir de N carteiras/ano; taxa premium por CIE oficial.
- **Prós:** equilibra previsibilidade e justiça; incentiva migração para CIE.
- **Contras:** mais complexa de comunicar.

**Recomendação do analista:** Opção D para novos contratos; manter clientes antigos em transição por 90 dias.

### 6.3 Risco de churn estimado
- Opção A: churn 5-10% em entidades pequenas.
- Opção B: churn 10-15% em entidades pequenas.
- Opção C: churn 2-5% (mas menor margem).
- Opção D: churn 3-7% (mais equilibrado).

---

## 7. Decisões de Produto/Negócio Pendentes

| ID | Decisão | Owner | Prazo | O que acontece se não decidir |
|---|---|---|---|---|
| **N-1** | DPO centralizado (1 pessoa) ou por entidade? | CEO + DPO | S2 | Gate F-03 e contratos não fecham; ANPD notificada sem encarregado |
| **N-2** | Atender entidades sem CNPJ? | CEO + Jurídico | S2 | F-03 fica sem regra; risco de co-controlador sem personalidade jurídica |
| **N-3** | CIE: EEA própria, terceira ou documento privado? | CEO + Produto | 45d | S4 não inicia; concorrência pode tomar mercado |
| **N-4** | Quem paga entrega domiciliar? | CEO + Vendas | S1 | UX de endereço mal desenhada; viola minimização |
| **N-5** | Priorizar e-mail ou diversificar para WhatsApp/SMS desde já? | Produto | S2 | Canal de comunicação sem governança; risco de ToS |
| **N-6** | Absorver custos de compliance ou repassar? | CEO + Financeiro | S2 | Pricing não fecha; vendas sem margem |

---

## 8. Entrevistas a Marcar

| Quem | Perguntas | O que esperamos extrair |
|---|---|---|
| **Fundador/CEO** | Qual modelo de receita atual? Margem por entidade? Capacidade de investir em compliance? | Definir N-3, N-6, D-1 |
| **Vendas/CS** | Quais segmentos mais rentáveis? Quais entidades não têm CNPJ? Taxa de churn atual? | Segmentação real; impacto N-2 |
| **Operações/Logística** | Quem paga entrega domiciliar hoje? Volume retirada vs domiciliar? | Definir N-4; fluxo de endereço |
| **Financeiro** | Custo atual de infra? Budget para DPO/auditoria? | Pricing; repasse de custos |
| **DPO indicado** | Preferência centralizado ou por entidade? | Decisão N-1; D-6 |

---

## 9. KPIs de Acompanhamento Pós-Parecer

| KPI | Alvo | Como medir |
|---|---|---|
| % entidades com contrato vigente | 100% em 30 dias | `lgpd_contracts` |
| Taxa de drop-off pós-consentimento | < 15% | Analytics do formulário |
| Tempo onboarding entidade → 1ª emissão | < 7 dias | `created_at` entidade vs 1ª carteira |
| Custo de compliance por carteira | R$ X (a definir) | Financeiro |
| Tempo médio resposta DPO | ≤ 15 dias | `lgpd_subject_requests.resolved_at` |
| % comunicação outbound com opt-in válido | 100% | `lgpd_consents` |
| NPS de entidades (confiança em segurança) | > 50 | Pesquisa |
| Incidentes reportados | 0 críticos | Runbook |

---

## 10. Initiation Checklist

- [ ] Marcar entrevistas da §8 (CEO, vendas, operações, financeiro, DPO)
- [ ] Revisar plano do arquiteto e alinhar decisões N-1..N-6 com ADRs D-1..D-7
- [ ] Confirmar modelo de receita atual (planilha/fonte)
- [ ] Mapear entidades ativas sem CNPJ
- [ ] Definir owner de cada decisão N-x com data

---

*Relatório v1.0. Atualizar após entrevistas e decisões do fundador.*