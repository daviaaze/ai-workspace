# Consolidação Geral — Meia-Entrada: LGPD + CIE v3.3

> **Data:** 2026-07-03
> **Propósito:** Sintetizar 19 documentos (~300KB) num mapa único de achados, riscos, decisões pendentes e próximos passos.
> **Leia isto primeiro** se entrou agora no projeto.

---

## 0. TL;DR (1 minuto)

A Meia-Entrada tem **dois problemas distintos**, em prazos diferentes:

| Problema | Prazo | Risco atual | Custo se ignorar |
|---|---|---|---|
| 🔴 **LGPD** (privacidade, segurança, contratos) | **Imediato — S1/S2 (30 dias)** | Vazamento de PII ativo (service_role exposta, PostHog exfiltra foto biométrica, rota pública vaza dados) | Multa ANPD até R$ 50MM + ação civil + dano reputacional |
| 🟡 **CIE v3.3** (carteirinha oficial) | **Médio prazo — S3-S5 (45-180 dias)** | Carteirinha atual é privada, não é a CIE oficial | Concorrentes podem migrar antes; perda de diferencial competitivo |

**⚠️ A LGPD é urgência — a CIE é estratégia.** Não confundir os dois.

---

## 1. LGPD — O Que Está Errado (e o Que Já Fizemos)

### 1.1 🔴 Achados Críticos (ação imediata)

| ID | Achado | Gravidade | Status |
|---|---|---|---|
| **S-08** | PostHog autocapture + session recording exfiltra foto biométrica + PII para servidores nos EUA sem consentimento | **CRÍTICO** | 🔧 **Hotfix commitado** (`fix/posthog-autocapture-privacy`) |
| **S-01** | `SUPABASE_SERVICE_KEY` exposta no frontend — bypass total de RLS | **CRÍTICO** | ❌ Pendente |
| **S-02** | Rotas `/v/[uuid]` e `/V/[token]` vazam PII + foto sem autenticação | **CRÍTICO** | ❌ Pendente |
| **S-03** | Sem `middleware.ts` — refresh de sessão quebrado, rotas desprotegidas | **CRÍTICO** | ❌ Pendente |
| **L-02** | Sem Política de Privacidade publicada | **ALTO** | ✅ **Documento pronto** (subprompt 01) |
| **L-03** | Sem Termos de Uso | **ALTO** | ✅ **Documento pronto** (subprompt 02) |
| **F-03** | Entidades atuam como co-controladoras sem contrato | **ALTO** | ✅ **Documento pronto** (subprompt 04) |
| **S-07** | Stored XSS via `dangerouslySetInnerHTML` em campos editáveis | **ALTO** | ❌ Pendente |
| **S-05** | Cloud sem headers de segurança (CSP, HSTS) | **MÉDIO** | ❌ Pendente |

### 1.2 Documentos Jurídicos Produzidos (10/10 — ✅ Prontos)

| # | Documento | Pendente |
|---|---|---|
| 01 | Política de Privacidade + Consentimento | Preencher `{{ }}` placeholders |
| 02 | Termos de Uso + Disclaimer | Preencher `{{ }}` placeholders |
| 03 | Contrato de Operador (DPA) — Supabase | Preencher `{{ }}` placeholders |
| 04 | Contrato de Co-controladora — Entidades | Preencher `{{ }}` placeholders |
| 05 | RIPD (Relatório de Impacto à Proteção de Dados) | Preencher `{{ }}` placeholders |
| 06 | Runbook de Resposta a Incidentes | Agendar tabletop (S5) |
| 07 | Política de Retenção (prazos por tipo de dado) | Preencher `{{ }}` placeholders |
| 08 | RDM (Registro de Dados Mestres) | Preencher `{{ }}` placeholders |
| 09 | Auditoria + Rewrite de Copy Marketing | CI gate pendente |
| 10 | Governança de Pessoas e Processos | NDA + treinamento pendentes |

> ⏳ **Todos os 10 documentos existem mas precisam de dados reais** (CNPJ, DPO, foro, advogado OAB, multas). Isso é trabalho de 1-2 horas com o CEO.

---

## 2. CIE v3.3 — O Que Precisa Acontecer

### 2.1 Situação Hoje

A carteirinha atual **não é a CIE oficial**. É um **documento privado de identificação estudantil** — sem validade jurídica como CIE.

| Requisito CIE v3.3 | Hoje | Precisa |
|---|---|---|
| Certificado de Atributo ICP-Brasil | ❌ Não tem | Emitido por EEA credenciada |
| Assinatura criptográfica (PKCS#7/CAdES) | ❌ Não assina | Assinar o QR + dados |
| QR Code normatizado | ❌ Só URL com token previsível | Payload canônico + assinatura + versão protocolo |
| Validação offline | ❌ Só online | Verificar assinatura sem internet |
| Campos INEP/MEC nas entidades | ❌ Só nome/sigla | Adicionar códigos oficiais |
| Layout padronizado MEC/ITI | ❌ Layout próprio | Seguir especificação |

### 2.2 A Grande Decisão: D-1 (3 Caminhos)

Com base na pesquisa EEA, há **3 caminhos**, com trade-offs claros:

```
Caminho A — Documento Privado (status quo melhorado)
├── Custo: R$ 0
├── Timeline: Imediato
├── Risco: MÉDIO — publicidade enganosa se chamar de CIE
└── Ação: Apenas limpar copy + disclaimers + LGPD

Caminho B — Integração com EEA Terceira ⭐ RECOMENDADO
├── Custo: R$ 5k-30k setup + R$ 2-10/certificado emitido
├── Timeline: 2-4 meses
├── Risco: BAIXO — EEA já credenciada
└── Ação: Contratar EEA, desenvolver API, homologar ITI

Caminho C — Credenciamento como EEA Própria
├── Custo: R$ 90k-240k
├── Timeline: 6-12 meses
├── Risco: ALTO — startup de pequeno porte
└── Ação: Auditoria, HSM, infraestrutura PKI
```

**Recomendação do Arquiteto + Pesquisa:** **Caminho B** (integração EEA terceira) é o equilíbrio ideal: viável financeiramente, timeline razoável, risco regulatório baixo.

### 2.3 As Outras Decisões (D-2 a D-7)

| ADR | Decisão | Opções | Recomendação |
|---|---|---|---|
| **D-1** | Caminho CIE | EEA própria / terceira / privado | 🟢 **EEA terceira** |
| **D-2** | Custódia de chaves | KMS cloud / HSM / EEA parceira | 🟢 **EEA parceira assume** |
| **D-3** | Validador CIE | PWA web / app nativo / integração | 🔴 **Sem decisão** |
| **D-4** | Estrutura repos | Monorepo / 2 repos | 🟢 **Monorepo (quando possível)** |
| **D-5** | Retenção de dados | Prazos por categoria | 🟢 **Proposto nos docs** |
| **D-6** | Modelo DPO | Central / por entidade / híbrido | 🔴 **Sem decisão** |
| **D-7** | Entidades sem CNPJ | Atender / só com CNPJ / não atender | 🔴 **Sem decisão** |

---

## 3. Linha do Tempo (Sprints S1-S5)

```
SEMANA 1-2 (S1 — AGORA)
├── 🔧 Aplicar hotfix PostHog (commitado — falta revisar + deploy)
├── 🔧 Rotacionar service_role + remover do web
├── 🔧 Adicionar middleware.ts (proteção de rotas)
├── 🔧 Adicionar gitleaks (secret scanning no CI)
├── 📄 Publicar Política de Privacidade + Termos de Uso
└── 📄 Aplicar NDAs à equipe atual

SEMANA 2-3 (S2)
├── 🔧 Implementar consentimento (2 checkboxes: geral + foto)
├── 🔧 Canal de direitos do titular (art. 18/19)
├── 🔧 Log de acesso a PII (access_audit_log)
├── 🔧 Headers de segurança (CSP, HSTS)
├── 📄 Contratos com operador (Supabase DPA)
├── 📄 Contratos com entidades (co-controladora)
└── 📄 Definir DPO + preencher placeholders dos 10 docs

MÊS 2 (S3 — Depende da Decisão D-1)
├── 🔍 Contratar EEA terceira (se caminho B)
├── 🔧 Schema migration: campos CIE + certificado
├── 🔧 API de integração com EEA
└── 🧪 Testes de emissão CIE

MÊS 3 (S4)
├── 🔧 QR Code com assinatura criptográfica
├── 🔧 Geração de Certificado de Atributo
├── 🔧 Validação offline
└── 🧪 Homologação ITI

MÊS 4-6 (S5)
├── 🔧 Go-live CIE oficial
├── 👥 Tabletop exercise (runbook incidente)
├── 📄 Postmortem + revisão geral
└── 📄 Treinamento LGPD anual
```

---

## 4. O Que Só Tu Podes Decidir (CEO)

### Decisões Bloqueantes (responder para S2/S3 andarem)

| Decisão | Opções | Impacto |
|---|---|---|
| **Caminho CIE (D-1)** | EEA terceira / própria / privado | Bloqueia S3 inteiro |
| **DPO (D-6)** | Centralizado (ME contrata) / Por entidade / Híbrido | Bloqueia S2 (contratos) |
| **Entidades sem CNPJ (D-7)** | Atender / Só com CNPJ / Não atender | Bloqueia cadastro de entidades |
| **Advogado OAB** | Contratar / Usar serviço fractional | Bloqueia revisão jurídica final dos 10 docs |

### Decisões Recomendadas (do arquiteto + analista)

1. **D-1: EEA terceira** — menor custo, menor risco, timeline factível
2. **D-6: DPO centralizado fractional** — contratação de serviço de DPO como PJ (~R$ 1-3k/mês) — mais barato que cada entidade ter o seu, e mais viável que a Meia-Entrada ter funcionário dedicado
3. **D-7: Só com CNPJ** — reduz risco legal, simplifica contratos, e entidades sem CNPJ podem se regularizar (é questão de tempo)
4. **Advogado OAB fractional** — contratação por demanda para revisar os templates e aprovar notificações

---

## 5. Matriz de Artefatos (19 Documentos)

### Pesquisa & Análise (8 docs)

| Arquivo | O que é | Para que serve |
|---|---|---|
| `resume-ate-fev-2026` | Mapa do código ausente | Entender o que mudou |
| `auditoria-seguranca-lgpd` | 8 vulnerabilidades identificadas | Guia de correção S1/S2 |
| `auditoria-cie-v3-3` | 6 não-conformidades CIE | Guia de migração S3-S5 |
| `plano-acao-arquitetura` | Roadmap técnico S1-S5 | Roteiro de implementação |
| `impacto-negocio-lgpd-cie` | Análise de riscos comerciais | Decisões de negócio |
| `pesquisa-eea-icp-brasil` | EEAs, custos, timeline | Alimentar D-1 |
| `cie-v33-tecnico` | Especificação técnica CIE | Implementação S3-S4 |
| `adrs-d1-d2-d3` | 3 ADRs CIE (EEA, KMS, validador) | Decisões de arquitetura |
| `adrs-d4-d5-d6-d7` | 4 ADRs operacionais | Decisões de negócio |

### Documentos Jurídicos (10 docs)

| Pasta `legal-copy/` | Status | Falta |
|---|---|---|
| `01-politica-privacidade-final` | ✅ Pronto para revisão | Placeholders + OAB |
| `02-termos-uso-final` | ✅ Pronto para revisão | Placeholders + OAB |
| `03-contrato-operador-final` | ✅ Pronto para revisão | Placeholders + OAB |
| `04-contrato-cocontroladora-final` | ✅ Pronto para revisão | Placeholders + OAB |
| `05-ripd-final` | ✅ Pronto para revisão | Placeholders + OAB |
| `06-runbook-incidente-final` | ✅ Pronto para revisão | Placeholders + OAB |
| `07-politica-retencao-final` | ✅ Pronto para revisão | Placeholders + OAB |
| `08-rdm-final` | ✅ Pronto para revisão | Placeholders + OAB |
| `09-auditoria-copy-final` | ✅ Pronto para revisão | CI gate pendente |
| `10-governanca-pessoas-final` | ✅ Pronto para revisão | Placeholders + OAB |

---

## 6. Próximos Passos Concretos

### ⏫ Agora (esta semana)

1. **Revisar hotfix PostHog** (branch `fix/posthog-autocapture-privacy`) — aprovar e fazer deploy
2. **Rotacionar service_role** — trocar a chave no Supabase + remover do frontend
3. **Ler a consolidação** (este documento) + os ADRs + o plano do arquiteto
4. **Responder as 4 decisões bloqueantes** (D-1, D-6, D-7, advogado)

### ⏫ Depois (próxima semana)

5. **Preencher placeholders** nos 10 docs jurídicos (dados reais)
6. **Publicar Política de Privacidade** + Termos de Uso no site
7. **Aplicar NDAs** à equipe atual
8. **Implementar middleware.ts** + headers de segurança

### 🔄 Meu Papel Agora

Queres que eu:
- **Ajude a responder as decisões** — simulando cenários, custos, consequências
- **Implemente as correções S1** — middleware, CSP, consentimento, service_role refactor
- **Preencha os placeholders** — levantando dados com tu
- **Despache nova rodada de subagents** — 3 tarefas por vez
