# PRD — CareerOps Pessoal (nome de trabalho: "daviaaze/career-ops")

> Produto pessoal para garantir a próxima vaga de contractor direto (USD 6–8k/mês).
> Documento vivo. Versão 0.1 — 02/ago/2026. Baseado na base de conhecimento em `/mnt/agents/output/agente-candidaturas/`.

---

## 1. Pesquisa competitiva — o que já existe (ago/2026)

| Projeto | O que faz | Licença/stack | O que aprender | O que NÃO copiar |
|---|---|---|---|---|
| **career-ops** (santifer) [^97^][^102^] | "Command center" local-first dentro de AI CLIs: escaneia 150+ portais, avalia vagas com rubrica A–F + score 1.0–5.0, gera CV ATS em PDF, research de empresa, descoberta de contato, tracker com integridade, follow-ups, análise de padrões de rejeição. 62K+ stars. Caso real: 740 vagas avaliadas → 68 aplicações → 12 entrevistas → 1 oferta | MIT; Node + skills para Claude Code/Codex etc. | **Filosofia "filtro, não spray-and-pray"** — recomenda não aplicar abaixo de 4.0/5. Human-in-the-loop total: nunca submete. Pipeline integrity (dedup, normalização de status). Módulos `deep` (research 6 eixos), `contacto` (hiring manager + msg LinkedIn ≤300 chars), `salary-gap`, `detect-reposts` (ghost jobs) | Rodar dentro de AI CLI exige setup; rubrica genérica (não é a nossa com regras de NDA/rate intermediário) |
| **ApplyPilot** (Pickle-Pixel) [^84^] | Pipeline autônomo de 6 estágios: discover (JobSpy em 5 boards + 48 portais Workday + 30 career sites) → enrich (JSON-LD → CSS → AI) → score 1–10 → tailor (nunca fabrica fatos) → cover letter → auto-apply com Claude Code + Playwright MCP. `apply --dry-run` preenche sem submeter | AGPL-3.0; Python | Cascata de extração de JD em 3 camadas; `--dry-run` como modo seguro; threshold de score configurável; preservação exata de `resume_facts` no tailoring | Submissão autônoma — viola nossa regra de aprovação humana e arrisca shadow-ban; AGPL impede reuso comercial |
| **ApplyKit** (wihlarkop) [^83^] | Self-hosted: fit score + keyword gaps + CV/cover letter por vaga + Kanban. BYOK (sua chave LLM ou Ollama offline). 1–2h por candidatura → 10–15 min | Open; SvelteKit + FastAPI + SQLite | **BYOK + dados locais** como princípio; fluxo "colar URL → fit score → CV → carta → Kanban" em 10–15 min é o benchmark de UX | Stack web completa pode ser overkill para 1 usuário |
| **jobber** (sentient-engineering) [^98^] | Agente que controla SEU browser e aplica autonomamente | Open | Conceito de "browser do próprio usuário" (sessões autenticadas legítimas) | Autonomia total = mesmo problema de risco |
| **browser-use** [^100^] | Biblioteca/CLI para agente operar browser (preencher forms etc.) | Open | Componente reutilizável para a etapa de form-fill assistida (futuro, sempre com submit humano) | — |
| Ferramentas comerciais (LazyApply, Sonara, LoopCV) | Volume automático | SaaS | Antipadrão: 47 aplicações → 0 entrevistas em vagas seniores [^81^] | Volume sem filtro |

**Síntese:** o estado da arte convergiu para **"filtro + preparação + aprovação humana"** (career-ops é a referência mais madura). Nosso diferencial não é técnico — é que o produto nasce **com a base de conhecimento do Davi embutida**: regras de score específicas (direto-only, USD 6–8k, sem intermediários), métricas validadas com fonte, sanitização NDA e o banco de bullets/STAR pronto. Nenhum projeto genérico tem isso.

**Decisão estratégica:** não construir do zero o que career-ops/ApplyPilot já fazem bem. Nosso produto = **camada própria (regras + KB + tracker + notificações + workflows) orquestrando ferramentas existentes**, com opção de adotar career-ops como engine de discovery/scoring posteriormente.

---

## 2. Visão e objetivos

**Visão:** um sistema pessoal, local-first, que transforma a busca por contrato direto de alto valor em um pipeline disciplinado e mensurável — o Davi dedica ~30 min/dia a decisões e conversas; o sistema faz todo o resto.

**Objetivos mensuráveis (OKRs pessoais):**
1. 1 contrato direto ≥ USD 6k/mês fechado até 31/out/2026
2. ≥ 3 candidaturas score ≥ 7 por semana (pipeline contínuo)
3. Taxa de resposta ≥ 15% nas candidaturas diretas (vs. ~1–3% do mercado)
4. Tempo de preparação de pacote ≤ 30 min por vaga

**Escopo (v1):** discovery, scoring, briefing, preparação de pacote, tracker, follow-ups, notificações, estatísticas.
**Fora de escopo (v1):** submissão automatizada de formulários (risco + regra), entrevistas por IA, multi-usuário/SaaS, mobile app.

**Princípios invioláveis (herdados da KB):**
1. Aprovação humana antes de qualquer envio
2. Nunca inventar métricas; só skills ✅
3. Sanitização NDA em concorrentes da Lux
4. Sem automação de browser no LinkedIn
5. Direto com a empresa; nada de intermediários
6. Dados locais (single-user, sem nuvem obrigatória)

---

## 3. Workflows

### WF-1 Discovery semanal (e contínuo por alertas)
```
Fontes (REGRAS §2) → coleta → dedup (URL + título+empresa) → filtro duro
(remoto? direto? geografia?) → fila "novas" → notificação digest
```
- Entrada: career pages travel tech (lista curada), boards com filtro, e-mails de alerta (caixa dedicada, parse via IMAP)
- Saída: registros no tracker com status `nova`

### WF-2 Scoring
```
Vaga → score 1–10 (regras REGRAS §1) →
  ≥7 → fila "preparar" + notificação imediata
  5–6 → fila "avaliar" (digest semanal)
  <5 → descarte com justificativa
```

### WF-3 Briefing (obrigatório para score ≥ 7)
```
Empresa → research (7 seções: empresa, produto, engenharia, stack, saúde, ângulo, lacunas)
→ briefing.md no pacote → flag "lacuna" quando info indisponível
```

### WF-4 Preparação de pacote
```
Vaga + briefing → seleção de bullets (cv-mestre §6, regras por tipo de vaga)
→ CV adaptado (docx via pipeline docx existente) → cover letter ≤150 palavras
→ respostas de triagem pré-preenchidas → pacote em candidaturas/<empresa>-<data>/
→ status "aguardando aprovação" → notificação com checklist de revisão
```

### WF-5 Aprovação e submissão (humano)
```
Davi revisa pacote → aprova (status "aprovado") → Davi submete manualmente
→ marca "submetido" + data → agenda follow-up automático (+5 dias úteis)
```
- O sistema nunca clica "submit". (Futuro: form-fill assistido via browser-use, com submit manual — avaliar na v2.)

### WF-6 Follow-up e respostas
```
+5 dias úteis sem resposta → notificação "enviar follow-up" (com texto pronto)
+12 dias → "sem retorno"
Resposta chegou (caixa dedicada) → classificar (triagem/entrevista/rejeição/outro)
→ notificação imediata se positiva → atualiza tracker → conversa passa a ser 100% humana
```

### WF-7 Estatísticas e revisão (semanal)
```
Tracker → funil (descobertas→preparadas→submetidas→respostas→entrevistas→ofertas)
→ taxa por fonte → skills pedidas nas vagas ≥7 (alimenta PLANO-DE-CARREIRA §6)
→ detecção de ghost jobs (repost da mesma vaga >3x) → digest semanal
```

### Máquina de estados da vaga
`nova → scored → (descartada | avaliar | preparar) → preparando → aguardando_aprovacao → aprovada → submetida → (sem_retorno | em_conversa | rejeitada | oferta → aceita/recusada)`

---

## 4. Interfaces

### I-1 CLI (primária — v1)
Comandos (estilo career-ops/ApplyPilot):
```
career scan              # WF-1: descobre e deduplica
career score [--all]     # WF-2
career brief <id>        # WF-3
career pack <id>         # WF-4 (gera pacote completo)
career approve <id>      # marca aprovado (ação humana)
career applied <id>      # marca submetido + agenda follow-up
career inbox             # WF-6: processa respostas da caixa dedicada
career tracker           # tabela de status
career stats             # WF-7
career review            # digest semanal consolidado
```

### I-2 Tracker (arquivo único de verdade)
- Evoluir `TRACKER.csv` → **SQLite local** (`tracker.db`) com export CSV/MD sob demanda
- Tabela `vagas`: id, empresa, título, url, fonte, data_descoberta, score, justificativa, status, rate, contato, datas (submissão, follow-up, resposta), notas, pacote_path
- Tabela `eventos`: log imutável de toda transição (auditoria + stats)
- Tabela `alertas`: cadastros de alerta por fonte e status de verificação

### I-3 Dashboard HTML estático (v1.5)
- Gerado por `career stats --html`: funil, Kanban read-only, taxa por fonte, skills demandadas
- Sem servidor — arquivo único aberto no browser (mesmo padrão do dashboard ApplyPilot)

### I-4 Pacote de candidatura (filesystem)
```
candidaturas/<empresa>-<AAAA-MM-DD>/
  briefing.md        # WF-3
  cv.docx            # adaptado
  cover-letter.md
  triagem.md         # respostas pré-preenchidas
  checklist.md       # o que Davi revisa antes de aprovar
```

### I-5 Config (YAML)
`config.yml`: faixas de rate, threshold de score, fontes ativas, credenciais (referências a env vars, nunca em plain), calendário de follow-up, remetente de notificações. Regras de conteúdo NÃO vivem em config — vivem na KB (versionada).

---

## 5. Notificações

| Evento | Canal | Urgência | Conteúdo |
|---|---|---|---|
| Vaga score ≥ 7 encontrada | E-mail (caixa dedicada) | Imediato | Empresa, título, score, rate, link, deadline |
| Pacote pronto p/ aprovação | E-mail | Imediato | Link do pacote + checklist de revisão |
| Follow-up devido | E-mail | Diário (batch 8h) | Vaga, dias desde submissão, texto pronto |
| Resposta de empresa na caixa dedicada | E-mail | Imediato | Classificação + remetente + trecho |
| Digest semanal | E-mail | Seg 8h | Funil, novas vagas 5–6, stats, skills pedidas, ações da semana |
| Alerta de fonte quebrada | E-mail | Ao ocorrer | Fonte X não responde há N ciclos (integridade do pipeline) |

Implementação v1: e-mail SMTP via caixa dedicada Gmail (mesma que já recebe alertas de vagas — um só ponto de entrada). Sem Slack/Telegram no v1 (ruído; e-mail basta para 1 usuário).

---

## 6. Arquitetura técnica (v1)

- **Linguagem:** Python 3.12 (scripting) — consistente com o ecossistema dos projetos de referência
- **Persistência:** SQLite + filesystem (pacotes, KB) — tudo em `/mnt/agents/work/career-ops/` com espelho de entregáveis em `output/`
- **Discovery:** JobSpy (boards) + RSS/APIs oficiais + parser IMAP da caixa de alertas; career pages via lista curada com extração em cascata (JSON-LD → seletores → IA)
- **IA (scoring, briefing, tailoring, classificação de respostas):** chamadas LLM via a própria sessão Kimi/CLI no v1; BYOK posterior
- **CV docx:** pipeline docx existente (Program.cs versionado em `/mnt/agents/work/cv/`)
- **Agendamento:** cron semanal (scan+review) + diário (follow-ups, inbox)
- **Sem:** servidor web, containers, nuvem — complexidade adiada até doer

## 7. Roadmap

| Versão | Conteúdo | Critério de pronto |
|---|---|---|
| **v0 (já existe)** | KB completa + tracker CSV + workflow manual assistido | Em uso desde 02/ago |
| **v1 — MVP** (2–3 sessões) | SQLite tracker + CLI (score/brief/pack/tracker/stats) + notificações e-mail + cron scan semanal | 1 ciclo real completo rodado com vaga verdadeira (Engine) |
| **v1.5** | Dashboard HTML + digest semanal + análise de skills → plano de carreira | Digest enviado 2 semanas seguidas |
| **v2** (avaliar) | Form-fill assistido (browser-use, submit manual), detector de ghost jobs, `contacto` (hiring manager + msg ≤300 chars), integração career-ops como engine | Decisão por dados do funil |

## 8. Métricas do produto (o que o sistema mede sobre si mesmo)

- Funil: descobertas → ≥7 → pacotes → aprovadas → submetidas → respostas → entrevistas → ofertas
- Taxa de resposta por fonte e por tipo de CV/bullet
- Tempo médio: descoberta→pacote, submissão→resposta
- % de pacotes aprovados sem edição (qualidade do tailoring)
- Skills mais pedidas nas vagas ≥7 (feedback ao PLANO-DE-CARREIRA)

## 9. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Fontes quebram/bloqueiam scraping | Alertas oficiais de e-mail como canal primário; sonda de integridade + notificação |
| Tailoring inventar fato | Regra KB + `resume_facts` congelados + revisão humana obrigatória |
| Volume baixo por filtro direto-only | Esperado e aceito; compensar com briefing + `contacto` (v2) |
| Manutenção virar fardo | Escopo v1 mínimo por design; 30 min/dia é o teto de uso |
| Dados sensíveis (NDA Lux) vazarem em pacote | Sanitização automática em concorrentes + checklist de aprovação |

---

### Referências de pesquisa
[^81^]: Teste 30 dias LazyApply/Sonara/LoopCV (0 entrevistas em 47 aplicações seniores)
[^83^]: ApplyKit — medium.com/@wihlarkop (abr/2026)
[^84^]: ApplyPilot — github.com/Pickle-Pixel/ApplyPilot (fev/2026)
[^97^][^102^]: career-ops — github.com/santifer/career-ops / career-ops.org (ago/2026)
[^98^]: jobber — github.com/sentient-engineering/jobber
[^100^]: browser-use — github.com/browser-use/browser-use
