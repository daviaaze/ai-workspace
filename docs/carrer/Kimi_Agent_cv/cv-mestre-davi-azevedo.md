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
- Padrão: `Senior Backend Engineer — Distributed Systems & Integrations`
- Travel tech: `Senior Backend Engineer — Travel Platforms & Supplier Integrations`
- Alternativa: `Senior Integration / Solutions Engineer`

---

## 2. Registro de métricas validadas (fonte + data)

| Métrica | Valor | Fonte | Data |
|---|---|---|---|
| Agent Platform — agências | **500+ agencies** (crescendo; era 0 no início) | Davi, dado interno LE | jul/2026 |
| Agent Platform — TTV | **USD 3M** (verificar se já passou) | Davi, dado interno LE | jul/2026 |
| Porter Group — escala | **100,000+ IoT devices** no Brasil | CV anterior do Davi | confirmado jul/2026 |
| Havan — promoção | junior → **Tech Lead em 10 meses** | histórico confirmado | jul/2026 |
| Meia-Entrada | **~240 entidades, 10,000+ carteirinhas em 18 meses** | Davi (projeto próprio) | jul/2026 |
| Luxury Escapes — volume | **200+ completed Jira items, 15+ microservices** | export Jira (224 itens fechados) | jul/2026 |
| Luxury Escapes — integrações | **9 travel supplier integrations**; nomes somente quando o NDA permitir | export Jira | jul/2026 |
| Inglês | **C1 — IELTS 8.0** | certificado | — |

**Regras:** métrica nova só entra com fonte e data nesta tabela. Nunca misturar números entre projetos (500+ é do Agent Platform, NÃO da Extranet). Aproximações honestas ("hundreds of bookings/month") são aceitáveis; números inventados, nunca.

---

## 3. Experiência — bullets por emprego (banco completo)

### Luxury Escapes — Senior Backend Engineer (B2B Contractor), Austrália, remoto · mai/2023–presente
*Contexto: plataforma travel-tech. Stack confirmada: Node.js, TypeScript, AWS Lambda/SQS, PostgreSQL, Redis, New Relic e CI/CD.*

**Bullets validados:**
1. Design and evolve distributed backend services in Node.js and TypeScript for booking, supplier and post-booking workflows on AWS.
2. Deliver Sabre post-booking automation focused on e-ticket distribution, customer emails and schedule-change safeguards; do not imply ownership of the complete GDS lifecycle.
3. Completed 200+ Jira items across 15+ microservices and 9 travel supplier integrations; describe individual outcomes instead of calling every item a feature.
4. **Led the backend integration of a major Car Hire provider** — API contract mapping, availability/booking/cancellation flows, error handling and reconciliation — launching a new business vertical.
5. **Architected the Agent Platform (B2B2C)** — commission rules engine, booking flow, invoicing and regional go-lives — serving 500+ agencies with USD 3M in TTV when last validated.

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

## 6. Regras de adaptação por vaga

| A vaga pede... | Mudanças permitidas |
|---|---|
| GDS / booking / travel tech | Destacar supplier integrations e o escopo exato de Sabre pós-booking |
| Event-driven | Destacar SQS, retry, DLQ, circuit breaker, idempotência e IoT |
| Node.js / TypeScript APIs | Priorizar Luxury Escapes e o estágio Node.js; não converter Porter/Havan |
| .NET / C# | Priorizar Porter e Havan |
| Fintech / pagamentos | Destacar commission, invoicing, reconciliação, Stripe e VCC somente onde validados |
| Startup / produto 0→1 | Destacar Car Hire, Agent Platform e Meia-Entrada |

**Regras fixas:**
- Reordenar e selecionar; nunca reescrever stack histórica, datas, cargo ou formação.
- Requisito obrigatório ausente não é compensado por domínio adjacente.
- Skills pendentes não entram no título, summary, ATS ou bullets.
- Sabre deve vir acompanhado do escopo `ticketing/pós-booking`.
- `200+ completed Jira items` não vira `200+ features`.
- Para concorrentes, sanitizar fornecedores como `major GDS/CRS providers`.
- Cada bullet central deve ter uma história técnica aprofundável em entrevista.

---

## 6.5 LinkedIn

**Headline:** `Senior Backend Engineer · Distributed Systems & Integrations · Node.js, TypeScript, C#/.NET, AWS · Travel Platforms`

**Posicionamento:** backend é a especialidade; React/Next.js é capacidade complementar. Não listar Kafka, NestJS, Step Functions, Kubernetes ou outras skills pendentes.

**Ajustes de perfil:** localização Londrina · Top Skills Node.js/TypeScript/AWS · English C1/IELTS 8.0 · Open-to-work para Senior Backend, Integration e Solutions roles remotas.

---

## 7. Pendências

- [ ] Revalidar 500+ agências e USD 3M TTV antes de nova publicação
- [ ] Confirmar stack do Contrate Quem Luta
- [ ] Capturar métricas defensáveis de latência, confiabilidade e custo
- [ ] Confirmar Step Functions, DynamoDB e Datadog antes de qualquer uso
- [ ] Documentar APIs Sabre efetivamente usadas e limites do lifecycle
- [ ] Expandir quatro histórias de entrevista: e-ticket, schedule change, Car Hire e commission engine
- [ ] Conferir título oficial em cada empresa antes de gerar novo CV

---

## 8. Arquivos relacionados

- Fonte de verdade de skills e fatos: `agente-candidaturas/HABILIDADES.md`
- Regras de aplicação: `agente-candidaturas/REGRAS-DE-APLICACAO.md`
- CV principal atual: `CV_Davi_Azevedo.md`
- CV PlanitEasy: artefato histórico; não reutilizar porque contém fatos reescritos
- Pesquisa de mercado: `pesquisa-mercado-metricas-portfolio.md`
