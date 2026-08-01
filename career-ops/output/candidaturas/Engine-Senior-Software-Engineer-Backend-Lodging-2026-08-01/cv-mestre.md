# CV-Mestre — Davi Azevedo
**Repositório único de conteúdo para CVs futuros · atualizado em 31/jul/2026**

> Como usar: para cada vaga nova, copie este arquivo, delete o que não serve e reordene pelo guia da seção 6. Nunca edite o mestre com conteúdo específico de uma vaga — o mestre acumula tudo, os CVs derivados recortam.

---

## 1. Identidade e header

```
DAVI AZEVEDO
[Título varia por vaga — ver seção 6]
Londrina, Brazil (UTC-3) · Fully remote · English C1 (IELTS 8.0) · daviaaze@gmail.com · linkedin.com/in/daviaaze · github.com/daviaaze
```

**Títulos validados:**
- Travel tech / booking: `Senior Backend Engineer — Travel Tech | Serverless & Event-Driven Architecture`
- Contractor Europa genérico: `Senior Backend Engineer · Serverless & Event-Driven (Node.js, TypeScript, AWS) · Kafka, NestJS, Step Functions · Remote contractor para scale-ups EU/UK`

---

## 2. Registro de métricas validadas (fonte + data)

| Métrica | Valor | Fonte | Data |
|---|---|---|---|
| Agent Platform — agências | **500+ agencies** (crescendo; era 0 no início) | Davi, dado interno LE | jul/2026 |
| Agent Platform — TTV | **USD 3M** (verificar se já passou) | Davi, dado interno LE | jul/2026 |
| Porter Group — escala | **100,000+ IoT devices** no Brasil | CV anterior do Davi | confirmado jul/2026 |
| Havan — promoção | junior → **Tech Lead em 10 meses** | histórico confirmado | jul/2026 |
| Meia-Entrada | **~240 entidades, 10,000+ carteirinhas em 18 meses** | Davi (projeto próprio) | jul/2026 |
| Luxury Escapes — volume | **200+ features/tickets, 15+ microservices** | export Jira (224 tickets fechados) | jul/2026 |
| Luxury Escapes — integrações | **9 suppliers/GDS**: Sabre, DerbySoft, SynXis, SiteMinder, TravelClick, RateGain, Rentals United, TourSalesforce, TTC | export Jira | jul/2026 |
| Inglês | **C1 — IELTS 8.0** | certificado | — |

**Regras:** métrica nova só entra com fonte e data nesta tabela. Nunca misturar números entre projetos (500+ é do Agent Platform, NÃO da Extranet). Aproximações honestas ("hundreds of bookings/month") são aceitáveis; números inventados, nunca.

---

## 3. Experiência — bullets por emprego (banco completo)

### Luxury Escapes — Senior Backend Engineer (B2B Contractor), Austrália, remoto · mai/2023–presente
*Contexto: travel-tech platform (hotels & pacotes), base global de clientes. Stack: Node.js, TypeScript, AWS (Lambda, EventBridge, Step Functions, SQS/SNS, DynamoDB), PostgreSQL, Redis, New Relic, Datadog, CI/CD.*

**Bullets validados (em uso no CV PlanitEasy):**
1. Design and evolve the **serverless, event-driven backend** (Node.js, TypeScript, AWS Lambda, EventBridge, Step Functions) behind core booking and post-booking flows.
2. **Build new features on the platform's Sabre GDS integration** — currently delivering ticketing and post-booking email flows after moving to the commercial ops / integrations team, connecting GDS supplier data into the microservices ecosystem.
3. Shipped 200+ features across 15+ microservices and **9 travel supplier / GDS integrations** — Sabre, DerbySoft, SynXis, SiteMinder, TravelClick, RateGain, Rentals United and others.
4. **Led the backend integration of a major Car Hire provider** — API contract mapping, availability/booking/cancellation flows, error handling and reconciliation — **launching a new business vertical**.
5. **Architected the Agent Platform (B2B2C)** — commission rules engine, booking flow, invoicing and regional go-lives (UK, US, NZ, Cruises) — now serving **500+ agencies with USD 3M in total transaction value (TTV)**.

**Bullets reserva (não usados, disponíveis):**
6. Built the hotel partner self-service platform (Extranet) — multi-currency dashboards, promotion editing with anti-stacking, virtual credit card management with audit logs, and Slack alerting — reducing partner dependency on internal ops.
7. Delivered flight e-ticket distribution (automatic push + self-service download with schedule-change guardrails), reducing support contacts.

### Porter Group — Full Stack Software Engineer, remoto · ago/2021–mar/2023
*Stack: C#, .NET Core, React.js, PostgreSQL, MongoDB, Redis, AWS (SQS).*

1. Built backend services for an IoT platform operating **100,000+ connected devices across Brazil** — high-throughput ingestion, device telemetry pipelines and event processing.
2. Engineered a high-volume ingestion service for 3rd-party devices via SDKs and event-based workflows (AWS SQS), ensuring high availability for critical security and monitoring systems.

### Havan — Junior → Tech Lead · out/2020–ago/2021
*Stack: .NET Core, C#, Angular, Vue.js, SQL Server, Redis.*

1. Promoted from junior engineer to **Tech Lead in 10 months**, leading a squad modernizing a legacy retail platform — CRM, purchase processing and document emission services.

### Formação
- Information Systems — UNIFEBE, 2021–2023 · Software Engineering studies — UTFPR, 2018–2019
- English C1 (IELTS 8.0) · Portuguese native

---

## 4. Project Highlights (página 2 — banco completo)

### Luxury Escapes
| Projeto | Papel · período | Bullets-chave |
|---|---|---|
| Agent Platform (B2B2C) | Backend architect · 2023–present | commission engine + invoicing + reservations; go-lives UK/US/NZ/Cruises; 500+ agencies / $3M TTV |
| Sabre GDS — Commercial Ops | Backend engineer · 2026–present | ticketing + post-booking email flows na integração Sabre em produção |
| Extranet — Partner Self-Service | BE+FE · 2023–present | dashboards multi-moeda, anti-stacking de promoções, VCC + audit logs, alertas Slack, e-tickets |
| Car Hire Supplier Integration | Backend lead · 2023–2024 | contract mapping, availability/book/cancel, reconciliação; vertical nova |

### Porter Group
| IoT Security & Monitoring | Full stack · 2021–2023 | 100k+ devices; ingestão high-volume via SDKs + event workflows (SQS) |

### Havan
| Legacy Retail Modernization | Tech Lead · 2020–2021 | CRM, purchase processing, doc emission; promoção em 10 meses |

### Non-profit
| Meia-Entrada Estudantil | Founder/engineer | produto completo (estudante + admin), form engine dinâmico por entidade; 240 entidades / 10k+ carteirinhas · Next.js, Node.js, Supabase · meiaentradaestudantil.com.br |
| Contrate Quem Luta — MTST | Contributor | marketplace de prestadores, SP metro, expansão nacional · **[STACK PENDENTE — confirmar com Davi]** |

### Side projects (disponíveis, não usados no CV atual)
- **Atlas Logístico Brasil** — Python/GeoPandas/PostGIS sobre dados abertos (DNIT, IBGE, ANTT, ANTAQ), Mapbox GL JS/Deck.gl, Docker. Prova Python + dados + geoespacial.
- **Remote Job Monitor** — 6 fontes, scoring heurístico, 124→545 listings, 11 matches quentes.

---

## 5. Banco de histórias STAR (entrevistas — NÃO vai para CV)

**Confiabilidade / Incident response:**
1. Abandoned orders (CAR-621): investigou padrão de pedidos órfãos no fluxo de car hire → correção.
2. Commission decimal bug (LEAH-437): cálculo retornando decimais aleatórios → precisão restaurada.
3. Missing-rates audit logging (XTRNT-546): sistema de auditoria para rate plans com dados faltantes → ops detecta falhas de integração mais rápido.
4. DerbySoft flash cap bug (XTRNT-954): parceiros vendo inventário incorreto → corrigido.

**Integrações / suppliers:**
5. Rentals United promotion stacking (XTRNT-682): preveniu double-discount entre LE e RU via contract + connector + reservation.
6. DerbySoft inventory cap self-service (XTRNT-802): autonomia para suppliers gerenciarem cap.

**Go-lives / expansão:**
7. UK go-live (LEAH-607+): região, phone code, sign-up, bloqueio de regiões.
8. USA launch (LEAH-256): suporte USD no svc-pdf → checkout em dólar.
9. NZ (LEAH-221/224): Stripe NZ + invoice.

**Flight domain (relevante para PlanitEasy!):**
10. E-ticket push automático para My Escapes (XTRNT-720) → clientes veem e-tickets sem suporte.
11. Self-service download de e-ticket (XTRNT-721) → redução de chamados.
12. Schedule-change guardrail (XTRNT-723) → prevenção de reenvio incorreto.

**Frase de bolso para calls:** *"500+ agencies now, and it was zero when I started."*

---

## 6. Regras de adaptação por vaga (10 min por aplicação)

| A vaga pede... | Mudanças |
|---|---|
| GDS / booking / travel tech | Título travel-tech; Sabre bullet em 2º; e-ticket STARs prontos (é o CV PlanitEasy atual) |
| Kafka / event streaming | Bullet 1 primeiro; "event-driven" no título; Extranet alertas/eventos nos highlights |
| NestJS / TypeScript APIs | NestJS no título; bullet commission engine (regras de negócio complexas em NestJS) |
| Serverless cost / performance | Redis caching do Car Hire + bill AWS [MÉTRICA PENDENTE: % redução custo AWS] |
| Fintech / pagamentos | VCC, commissions, invoicing, Stripe (NZ), GST invoices |
| Dados / geoespacial | Atlas Logístico sobe para logo após o summary |
| Startup seed/Series A | Meia-Entrada e side projects sobem — prova de ownership 0→1 |

**Regras fixas:**
- Página 1 = cronológico enxuto (scan de 7,4s); página 2 = Project Highlights. Máximo 2 páginas.
- 1 página só se <5 projetos relevantes para a vaga.
- Toda aplicação: reordenar, não reescrever. Se um bullet novo for escrito, volta para este mestre.
- Nunca listar suppliers sob NDA por nome se a vaga for de concorrente direto — generalizar ("major GDS/CRS providers").
- Taxa de resposta é a métrica do processo: <10% após 15 aplicações → problema de canal/posicionamento, não de texto.

---

## 6.5 LinkedIn (reescrito em 31/jul/2026, alinhado com este mestre)

**Diagnóstico do perfil antigo:** headline de empregado, localização desatualizada (Florianópolis), About com autodepreciação e stack antiga, Porter em português, FATEC inflado como "Software Engineer", Top Skills erradas (ERPNext), Featured vazio.

**Headline:** `Senior Backend Engineer · Serverless & Event-Driven (Node.js, TypeScript, AWS) · Travel Tech: booking, GDS/Sabre, supplier integrations · B2B contractor`

**About + descrições por experiência:** texto completo aprovado na conversa de 31/jul/2026 (mesmos bullets do CV — Summary espelha a seção 2/3 deste mestre). Regra: qualquer atualização de métrica no mestre reflete no LinkedIn na mesma semana.

**Ajustes de perfil:** localização Londrina · Top Skills Node.js/TypeScript/AWS · English C1/IELTS 8.0 em certifications · Featured = Meia-Entrada + primeiro ADR · Open-to-work só para recrutadores (EU/UK/US remote).

---

## 7. Pendências

- [ ] Stack do Contrate Quem Luta (MTST)
- [ ] TTV atualizado do Agent Platform (se > $3M)
- [ ] Métrica de custo AWS (otimização serverless) — puxar bill antes/depois
- [ ] p99 latência antes/depois de alguma otimização (New Relic)
- [x] ~~Kafka/NestJS na LE~~ — CORRIGIDO 31/jul: removidos de CV/mestre/LinkedIn (não fazem parte da stack da LE)
- [x] Fastify — CORRIGIDO 31/jul: não usado na LE, removido de CV/mestre
- [ ] Confirmar se Step Functions é usado na LE (mantido por ora)
- [ ] Export do LinkedIn (Save to PDF) para alinhar About/headline com este mestre

---

## 8. Arquivos relacionados

- CV derivado atual (PlanitEasy): `Davi_Azevedo_CV_PlanitEasy.docx` + `.md`
- Gerador do layout (rebuild de variantes): `/mnt/agents/work/cv/Program.cs`
- Análise Jira completa (fonte): upload `# Análise de 3 anos.txt` (jul/2026)
- Pesquisa de mercado/métricas/portfólio: `pesquisa-mercado-metricas-portfolio.md`
- Posicionamento & storytelling: `posicionamento-storytelling-contractor-europa.md`
