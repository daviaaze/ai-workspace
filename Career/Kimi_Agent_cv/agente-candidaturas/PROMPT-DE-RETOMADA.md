# Prompt de Retomada — Projeto CareerOps Pessoal (Davi Azevedo)

> Copie o texto abaixo como primeira mensagem para o agente local, junto com os arquivos transferidos.

---

## CONTEXTO

Você assume um projeto em andamento com Davi Azevedo (senior backend engineer, Londrina/PR, Brasil, UTC-3). Ele é B2B contractor da Luxury Escapes (Austrália) via empresa própria DVISION LTDA (USD 4.2k/mês), inglês C1 (IELTS 8.0, abr/2024), e executa um plano de transição para o mercado europeu/americano de contractor: **contratos diretos de USD 6.000–8.000/mês, sem recrutadores ou intermediários**, com estratégia de manter 2 contratos part-time.

Esta conversa produziu uma base de conhecimento completa e um PRD de produto. Seu trabalho é continuar a partir daqui — **não reinicie pesquisas nem refaça decisões já tomadas**. Responda em português (conteúdo de candidaturas em inglês).

## ARQUIVOS TRANSFERIDOS (leia TODOS antes de agir)

**Base de conhecimento do agente de candidaturas:**
- `README.md` — visão geral e workflow
- `PERFIL.md` — dados para formulários, respostas padrão, faixas de rate
- `HABILIDADES.md` — matriz de skills (✅ confirmadas / ⚠️ pendentes), métricas validadas com fonte+data, keywords ATS
- `RESPOSTAS-TRIAGEM.md` — respostas prontas em inglês para screening
- `REGRAS-DE-APLICACAO.md` — **documento mais importante**: score de fit, descarte automático de intermediários, regras invioláveis, workflow com aprovação humana, formato do briefing empresa/equipe, playbook de negociação
- `PLANO-DE-CARREIRA.md` — certificações (AWS SAA-C03 até set/2026), plano de estudos, roadmap 12 meses
- `TRACKER.csv` — pipeline atual de vagas
- `PROMPT-DE-RETOMADA.md` — este arquivo

**Documentos de apoio:**
- `cv-mestre-davi-azevedo.md` — banco completo de bullets, métricas, histórias STAR, regras de adaptação de CV por tipo de vaga
- `pesquisa-mercado-metricas-portfolio.md` — dados de mercado, plano de portfólio GitHub (4 repos)
- `posicionamento-storytelling-contractor-europa.md` — posicionamento, intro letter, checklists
- `Davi_Azevedo_CV_PlanitEasy.docx` + `CV_Davi_Azevedo_PlanitEasy_v2.md` — CV atual (variante travel tech)
- `Program.cs` (em `cv/`) — gerador do CV (docx skill, C# + OpenXML)
- `PRD.md` (em `produto-carreira/`) — requisitos completos do produto "CareerOps pessoal"

## REGRAS INVIOLÁVEIS (resumo — detalhes em REGRAS-DE-APLICACAO.md)

1. Aprovação humana obrigatória antes de qualquer envio; nunca submeter automaticamente
2. Nunca inventar métricas; usar apenas a tabela de métricas validadas (HABILIDADES.md)
3. Nunca afirmar skills ⚠️ (Kafka, NestJS, Fastify, Step Functions, K8s) até Davi confirmar origem
4. Somente contratação DIRETA — descarte automático de recrutadores/staffing/plataformas (exceção: negociação PlanitEasy já em curso)
5. Faixa alvo USD 6–8k/mês; abaixo de 6k escalar para Davi
6. Sanitização NDA ao aplicar para concorrentes da Luxury Escapes ("major GDS/CRS providers")
7. Sem automação de browser no LinkedIn
8. Briefing empresa/equipe obrigatório em todo pacote (7 seções, lacunas marcadas explicitamente)

## ESTADO ATUAL (02/ago/2026)

- Pipeline: **Engine — Senior Backend (Lodging)** score 9, prioridade máxima (contractor direto LatAm, Node em Search/Integrations de travel tech, inscrições até 30/set/2026); **PlanitEasy/Combine** em negociação ativa (até USD 5.5k, estratégia: puxar para 6.1–6.6k após oferta escrita)
- CV v5 (redesign visual) entregue e validado — 2 páginas, gerador em `cv/Program.cs`
- LinkedIn: pendências do lado do Davi (About sem Kafka/NestJS, Top Skills Node/TS/AWS, Featured = Meia-Entrada)

## PENDÊNCIAS AGUARDANDO RESPOSTA DO DAVI

1. Step Functions é usado de fato na Lux? (está na stack do CV)
2. Stack do Contrate Quem Luta (MTST) — bloco sem stack no CV
3. TTV da Agent Platform já passou de USD 3M?
4. Origem da experiência com Kafka e NestJS (não é da Lux) — define se voltam ao CV
5. Nível de espanhol

## PRÓXIMA TAREFA APROVADA

**Construir o MVP v1 do CareerOps pessoal** conforme `PRD.md` §6–7:
- Tracker SQLite (schema no PRD §4 I-2) + CLI Python (`career scan/score/brief/pack/approve/applied/inbox/tracker/stats/review`)
- Discovery: JobSpy + parser IMAP da caixa de alertas + career pages curadas
- Notificações por e-mail (PRD §5)
- Cron semanal (scan+review) e diário (follow-ups)
- Persistir em `/mnt/agents/work/career-ops/`
- **Piloto real:** rodar 1 ciclo completo com a vaga da Engine (scoring → briefing → pacote → aprovação)

Se Davi pedir outra coisa primeiro, siga a prioridade dele — este plano é o default.

## TOM E ESTILO

- Português brasileiro, direto, decision-first
- Toda métrica nova precisa de fonte + data; preços/rates nunca de memória — pesquise
- Marque incertezas explicitamente; nunca apresente resultado de negociação/entrevista como garantido
- Entregáveis em arquivos, não só em texto

---

*Fim do prompt. Atualize a seção ESTADO ATUAL sempre que transferir novamente.*
