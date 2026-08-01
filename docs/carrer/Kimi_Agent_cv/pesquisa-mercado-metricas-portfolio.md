# Pesquisa de Mercado, Métricas de CV e Plano de Portfólio
**Davi Azevedo · Transição Contractor Europa · julho/2026**

Síntese de pesquisa em fontes de recrutamento, dados de vagas e guias de hiring managers. Tudo datado e com fonte.

---

## PARTE 1 — O que recrutadores realmente medem (evidência, não opinião)

### Fatos duros

| Fato | Implicação prática para ti | Fonte |
|---|---|---|
| Recrutador gasta **7,4 segundos** no primeiro scan do CV | Teu 1/3 superior (headline + summary + primeiros 2 bullets) decide tudo | ResumeWorded, jul/2026 [^34^] |
| Hiring managers tratam bullets sem número como **"não verificáveis"** | Cada bullet sem métrica é um bullet deletado mentalmente | GreatResumesFast, jul/2026 [^37^] |
| "Se tuas conquistas fortes estão na página 2, nós nunca as vemos" | Agent Platform e Car Hire têm que estar visíveis no primeiro scroll | ITAC Solutions, jan/2026 [^38^] |
| CV genérico é detectável: "we can tell" | Letter/CV adaptado por vaga não é opcional | ITAC Solutions [^38^] |
| **82% das contribuições de código acontecem em repositórios privados** — teu GitHub público pode ser a ÚNICA amostra visível do teu trabalho | GitHub não é enfeite; é evidência primária para contractor | Underdog.io, jun/2026 [^42^] |
| Menos de **1 em 10** candidatos inclui portfólio | Só de ter portfólio curado tu já entra no top 10% de memorabilidade | DataEngineerAcademy, jan/2026 [^43^] |
| Tempo médio para fechar uma vaga backend remota na Europa: **49 dias** | Pipeline tem que ser contínuo — uma vaga por vez não funciona | RemoteRocketship, jul/2026 [^40^] |

### A fórmula de bullet que recrutadores recomendam (Google XYZ)

**Accomplished [X] as measured by [Y] by doing [Z]** [^39^]

Aplicada aos teus cases reais (com placeholders onde falta o número):

| Teu case (CV atual) | Versão XYZ |
|---|---|
| "Led the backend integration of a major Car Hire provider, launching a new business vertical" | "Launched company's **first Car Hire vertical** (X), reaching **[€X GMV / X bookings] in the first [N] months** (Y), by designing the backend integration with [provider]'s API in Node.js/TypeScript (Z)" |
| "Architected the Agent Platform (B2B2C)... rapid market expansion" | "Grew B2B2C channel from **0 to [X] active agents / [X]% of company revenue** (Y) by architecting the Agent Platform's commissions, invoicing and reservations microservices (Z)" |
| "Scaled backend to 100,000+ IoT devices" (Porter) | "Sustained **[X]% uptime / p99 latency of [X]ms** (Y) for real-time security monitoring of **100,000+ IoT devices** (X) by building an event-based ingestion service with AWS SQS (Z)" |
| "Promoted to Tech Lead" (Havan) | "**Promoted from junior to Tech Lead in 10 months** (Y) and led squad of **[N]** in modernizing a legacy CRM/processing platform serving [X internal users] (Z)" |

**Nota:** "promoted within 12 months" é explicitamente listado como métrica forte de time-commitment [^34^] — tua promoção na Havan é um ativo que tu subestimas.

### Métricas de engenharia que o mercado aceita como prova [^36^][^37^]

Quando não tiveres número de receita, usa (nesta ordem de força):
1. **Escala:** eventos/dia, requests/seg, usuários ativos, devices, GB processados
2. **Confiabilidade:** uptime %, redução de incidentes, MTTR, p99 latency antes/depois
3. **Velocidade:** deployment frequency, lead time de feature, redução de tempo de processamento
4. **Custo:** redução de bill AWS em % ou $, horas de engenharia economizadas/semana
5. **Adoção:** agents/clientes onboarded, % de receita via canal que tu construíste

Onde puxar isso NA LUXURY ESCAPES (1–2h de trabalho): CloudWatch (invocations, p99), New Relic (throughput, error rate — já está no teu stack!), dashboards de produto (bookings, agents), bill AWS antes/depois de otimizações.

---

## PARTE 2 — Mercado europeu backend 2026: o que as vagas pedem

Análise de **437 vagas remotas backend na Europa** (RemoteRocketship, jul/2026) [^40^]:

| Skill | % das vagas | Tu tens? |
|---|---|---|
| **Docker** | 32,1% | ✅ (mas sub-usado no CV) |
| **PostgreSQL** | 27,0% | ✅ |
| **Microservices** | 26,3% | ✅ forte |
| Java | 24,0% | ❌ (não vale aprender agora) |
| **Kubernetes** | 24,0% | ⚠️ **GAP #1** |
| AWS | 23,2% | ✅ forte |
| **Python** | 23,0% | ✅ (via Atlas Logístico — invisível no CV!) |
| Git | 22,2% | ✅ |
| **CI/CD** | 21,2% | ✅ parcial |
| MySQL | 21,2% | ✅ |

**Salário médio senior backend remoto EU: €53,7k/ano (CLT remoto)** — contractors B2B ficam bem acima disso (€50–65/h ≈ €90–110k/ano), o que confirma que contractor é o caminho certo, não emprego remoto CLT [^40^].

### Leitura estratégica

1. **Teu gap técnico #1 é Kubernetes.** Quase 1 em cada 4 vagas pede. Tu és serverless-first — ótimo para scale-ups, mas K8s aparece em vagas de empresas maiores. Não precisas virar expert: um projeto demonstrando deploy + operação básica já fecha o checkbox.
2. **Python está invisível no teu CV** e aparece em 23% das vagas. O Atlas Logístico já te dá Python + GeoPandas + PostGIS — é só expor.
3. **AI/LLM integration é o multiplicador de 2026.** "Automation & AI exposure" listado entre as skills favoritas de 2026 por recrutadores [^38^]; o Conference Board atribui o crescimento americano ao investimento em IA [^4^]. Um projeto backend que integre LLM de forma séria (não wrapper de chat) te diferencia de 95% dos backends Node.
4. **O que NÃO aprender agora:** Java/Spring (mercado grande mas é outra carreira), Go (interessante, mas dilui o posicionamento). Foco: K8s + AI integration + observabilidade.

---

## PARTE 3 — GitHub: o que hiring managers avaliam (em 30 segundos)

Síntese de guias de hiring managers (Underdog.io jun/2026 [^42^], GitHub Community [^46^], daily.dev jan/2026 [^44^]):

### A hierarquia do scan
1. **Bio do perfil** — uma linha: "Backend engineer · serverless & event-driven · Node.js/TypeScript/AWS · building logistics data tooling" (não lista de keywords)
2. **4 repos pinados** — "quatro projetos polidos vencem seis aleatórios, sempre" [^42^]
3. **README** — é a porta de entrada; se for fraco, ninguém abre o código
4. **Commits e PRs** — "add retry logic for webhook delivery failures" vence "update code"; histórico incremental vence dump único

### O README que converte (checklist) [^42^][^43^]
- Problema: o que faz e para quem (1 frase)
- Por quê: tua motivação — mostra julgamento de produto
- Setup: rodar local sem adivinhação (Docker Compose ajuda aqui)
- Arquitetura: diagrama simples (mermaid funciona no GitHub)
- Prova: screenshots/GIF ou demo live
- Testes + CI (GitHub Actions): sinal mais forte de "engenheiro de produção", não "estudante"

### Sinais que valem mais que código em 2026 [^42^]
Na era de código gerado por IA, output bruto vale pouco. O que não dá para fingir:
- decisões de arquitetura documentadas (**ADRs no repo** — tu já tem isso no teu plano!)
- notas de trade-off, disciplina de debug
- qualidade de PRs e discussões em issues

---

## PARTE 4 — Plano de portfólio: 4 pinados + 2 novos

### Os 4 pinados (máximo sinal por esforço)

| # | Repo | Status | O que prova | Ação necessária |
|---|---|---|---|---|
| 1 | **Atlas Logístico Brasil** | Existe, evoluir | Python, PostGIS, GeoPandas, data engineering, dados reais messy do governo (DNIT/IBGE/ANTT), Mapbox/Deck.gl demo visual | README completo + demo live + diagrama de pipeline + "processa [X] registros de [7] agências" |
| 2 | **job_monitor_v2** | Existe | Automação real, 6 fontes, scoring heurístico — prova que tu constróis ferramentas que resolvem teu próprio problema (product judgment) | README + sanitizar dados pessoais + métricas ("124→545 vagas, 11 matches quentes") |
| 3 | **Event-driven reference architecture (NOVO)** | Criar — 3–4 semanas | **Tua especialidade core em público:** NestJS + Kafka + AWS (LocalStack) + Step Functions pattern + testes + ADRs | Ver spec abaixo |
| 4 | **LLM-integrated backend service (NOVO)** | Criar — 2–3 semanas | AI exposure 2026: integração séria de LLM em arquitetura backend (não chat wrapper) | Ver spec abaixo |

### Spec do projeto 3 — event-driven-reference (teu "ADR executável")
- **Problema:** "Referência de arquitetura para fluxos de reserva/booking: idempotência, retries, DLQ, ordenação de eventos"
- **Stack:** NestJS + TypeScript + Kafka (ou EventBridge via LocalStack) + PostgreSQL + Docker Compose
- **Diferenciais:** suíte de testes de falha (o que acontece quando o consumidor morre no meio?), 3–5 ADRs no repo, GitHub Actions, diagrama mermaid, README com números ("processa X eventos/seg em LocalStack com p99 de Yms — medido com k6")
- **Por que funciona:** é literalmente o trabalho que tu fazes na LE, sanitizado — e vira peça de autoridade para linkar no LinkedIn e nas proposals do Malt
- **Bônus Kubernetes:** deploy opcional com Helm chart em kind/minikube → fecha o gap K8s das vagas [^40^]

### Spec do projeto 4 — llm-ops-backend
- **Problema real:** "Serviço que ingere documentos/logs e gera resumos estruturados via LLM, com fila, cache semântico, rate limiting e fallback entre providers"
- **Por que não é wrapper:** o valor está nas partes difíceis — fila assíncrona (Kafka/SQS), idempotência, custo por request, observabilidade, fallback. Ou seja: **é um projeto de arquitetura que usa LLM, não um projeto de LLM**
- **Stack:** Fastify ou NestJS + provider LLM via API + Redis (cache) + métricas de custo/latência no README
- **Storytelling LinkedIn:** "What it costs to run LLM features in production: queues, caching and fallbacks" — post de autoridade

### Open source (credibilidade linkável) [^44^][^45^]
- Alvo: **NestJS, Fastify, ou ferramentas AWS/Kafka que tu já usas** — começa com issues "good first issue", docs e testes
- Meta realista: **2–3 PRs mergeados em 90 dias** > 20 PRs de baixa qualidade
- Cada PR mergeado vira: item no CV ("contributor to NestJS ecosystem"), material de entrevista (STAR pronto), e possível inbound
- Regra: contribuição em projeto que o cliente-alvo usa = "risco de ramp-up menor" aos olhos dele [^45^]

---

## PARTE 5 — Estudos: onde investir as horas (alinhado ao teu plano de 12 meses)

| Prioridade | Tema | Por quê | Formato |
|---|---|---|---|
| 1 | **Kubernetes operacional** (deploy, Helm, debugging) | 24% das vagas EU [^40^]; teu único gap de checklist | Projeto 3 com deploy K8s — aprender construindo, não curso |
| 2 | **AWS cert (Solutions Architect Associate ou Developer)** | Já no teu Caminho de Certificações; valida o que tu já fazes; filtro de agências de contractor | Plano existente |
| 3 | **LLM engineering aplicado a backend** (custos, filas, avaliação, fallback) | Diferenciador 2026 [^38^]; projetos de IA estão sustentando o mercado [^4^] | Projeto 4 |
| 4 | **System design para entrevistas de contractor** (falar trade-offs em inglês) | Mock calls de vendas + comunicação adaptativa já cobrem a parte social; falta a técnica verbalizada | 1 caso/semana escrito em ADR = treino duplo (escrita + fala) |

**O que cortar:** Java, Go, Kubernetes avançado (CKS etc.), frameworks frontend novos. Cada hora fora do posicionamento "serverless/event-driven Node+AWS" é uma hora que dilui a mensagem.

---

## Sequência de execução (8 semanas)

- **Semana 1:** puxar métricas na LE (CloudWatch/New Relic/bill) + reescrever os 4 bullets principais em formato XYZ + trocar headline LinkedIn + bio GitHub
- **Semana 2:** README do Atlas Logístico + demo live + pinar; LinkedIn PDF export → eu fecho o CV final em DOCX
- **Semanas 3–5:** projeto event-driven-reference (com deploy K8s básico)
- **Semanas 5–7:** projeto llm-ops-backend (overlap proposital: os dois usam as mesmas primitivas de fila)
- **Semana 3 em diante:** 1 PR open source por quinzena (NestJS/Fastify ecosystem)
- **Semana 8:** CV final + GitHub curado + 10 aplicações/semana no Malt/Freelancermap com letter adaptada → medir taxa de resposta

**Meta mensurável:** >20% de taxa de resposta em aplicações adaptadas. Abaixo de 10% após 15 aplicações = problema de canal/mercado, iteramos juntos.

---

## Ressalvas honestas

- **Os números de % das vagas** vêm de 437 vagas remotas agregadas por um job board — bom proxy, mas amostra enviesada para remoto/startup. Vagas em plataformas fechadas (Malt, Freelancermap) podem ter mix diferente; vale validar com 10 vagas reais que tu aplicarias.
- **Projetos novos competem com o overlap de 2 empregos.** Se o contrato europeu chegar antes dos projetos 3–4, o contrato vence — portfólio serve para conseguir o primeiro cliente; depois dele, referência real > projeto.
- **Nenhum guia de "o que recrutadores querem" é ciência exata** — são padrões consistentes entre múltiplas fontes (7,4s de scan, XYZ, quantificação), mas a prova final é a tua taxa de resposta. Mede tudo.
- As métricas de engenharia devem ser **reais e defensáveis em entrevista** — um "reduzi p99 em 40%" vai ser destrinchado por qualquer CTO europeu em call técnica.
