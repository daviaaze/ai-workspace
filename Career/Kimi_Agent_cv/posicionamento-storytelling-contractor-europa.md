# Posicionamento & Storytelling — Transição para Contractor Europeu
**Davi Azevedo · DVISION Serviços Digitais · julho/2026**

> Documento de trabalho. Seções com `[PREENCHER]` dependem de dados que só você tem (métricas, datas, empregos anteriores). Envie o CV atual para completar.

---

## 1. Diagnóstico: por que ninguém te chama hoje

O problema não é tua senioridade — é que teu material atual vende **tarefas**, e o mercado europeu de contractor compra **resultados**. Sintomas típicos do teu caso:

| Sintoma | O que o recrutador/cliente lê | Correção |
|---|---|---|
| CV lista tecnologias ("Node, TypeScript, AWS...") | "Mais um dev genérico entre 500" | Casos com problema → ação → resultado numérico |
| Projetos sem contexto | "Não sei o que ele realmente fez" | 2–3 linhas de contexto de negócio antes de cada case |
| Sem métricas | "Sem prova, sem risco vale a pena" | Toda bala de CV tem número (latência, custo AWS, throughput, time-to-market) |
| Headline do LinkedIn = cargo | Invisível nas buscas por "contractor Node AWS" | Headline com stack + tipo de engajamento + resultado |
| Posicionamento "faço tudo" | Não encaixa em nenhuma vaga específica | Nicho explícito: **backend serverless/event-driven para scale-ups** |

**Tua vantagem real que o CV atual esconde:** tu não és "dev Node" — és o cara que **opera arquitetura serverless/event-driven em produção, em escala de travel tech australiana, cobrindo 40% do preço de um contractor europeu local**. Esse é o posicionamento.

---

## 2. Posicionamento (uma frase, usada em tudo)

> **"Senior backend engineer especializado em arquiteturas serverless e event-driven (Node.js/TypeScript/AWS) — construo e opero sistemas distribuídos de alta performance para scale-ups, remotamente do Brasil, com overlap total com o horário europeu e rate 30–40% abaixo do mercado local."**

Versão curta (LinkedIn headline, 220 caracteres):

> **Senior Backend Engineer · Serverless & Event-Driven (Node.js, TypeScript, AWS) · Kafka, NestJS, Step Functions · Remote contractor para scale-ups EU/UK · Overlap total com CET**

Por que funciona:
- **"Serverless & event-driven"** — é a combinação com maior prêmio e matching mais rápido nas plataformas em 2026 ($45–70/h) [fonte: Lemon.io rate data, mai/2026];
- **Lista as tecnologias que os filtros de busca usam** (Kafka, NestJS, Step Functions) — recrutador não busca "backend", busca a stack;
- **"Remote contractor para scale-ups EU/UK"** — diz o tipo de engajamento que tu queres, filtrando vagas erradas;
- **"Overlap total com CET"** — mata a objeção #1 contra contractor latino-americano antes dela ser feita.

---

## 3. Estrutura do novo CV (1 página, inglês)

### Header
```
DAVI AZEVEDO
Senior Backend Engineer — Serverless & Event-Driven Architectures
Londrina, Brazil (GMT-3, full CET overlap) · davi@[PREENCHER] · linkedin.com/in/[PREENCHER] · github.com/[PREENCHER]
Available for B2B contracting (EU/UK) via DVISION Serviços Digitais LTDA
```

### Professional Summary (3 linhas, sem adjetivos vazios)
```
Backend engineer with [X] years building and operating distributed systems in production.
Currently running serverless, event-driven architecture (Node.js, TypeScript, AWS Lambda,
Kafka, NestJS, Step Functions) for an Australian travel-tech scale-up, [resultado principal com número].
Seeking part-time and full-time B2B contracts with EU/UK scale-ups.
```

### Experience — o modelo de cada entrada

Cada emprego segue esta estrutura (e é isso que falta no teu CV hoje):

**[Cargo] — [Empresa], [País] (remote) · [MM/AAAA – MM/AAAA]**
*Contexto em 1 linha: o que a empresa faz, escala, teu papel.*

- **Case 1:** problema de negócio → o que tu construíste → resultado numérico
- **Case 2:** idem
- **Case 3:** idem (máximo 3–4 por emprego)

#### Entrada 1 — escrita por completo (modelo a seguir):

**Senior Backend Engineer (B2B Contractor) — Luxury Escapes, Australia (remote) · [MM/AAAA – present]**
*Travel-tech scale-up; backend serverless/event-driven supporting [PREENCHER: volume — bookings/dia, usuários, GMV].*

- Designed and operate event-driven microservices on AWS (Lambda, EventBridge, Step Functions, Kafka) handling [PREENCHER: throughput — eventos/seg ou transações/dia], achieving [PREENCHER: latência p99, uptime ou redução de custo AWS em %].
- Built [PREENCHER: serviço específico — ex.: booking/pricing pipeline] with NestJS/TypeScript, reducing [PREENCHER: tempo de processamento, erros, ou time-to-market de features] by [X]%.
- [PREENCHER: case de incidente/migração/otimização — ex.: "led migration of X to event-driven pattern, cutting infrastructure cost by Y%"].

> **Nota:** sem os números reais, esta entrada é só promessa. Abre o CloudWatch/Datadog e pega 3 métricas de verdade — é 1 hora de trabalho que vale mais que qualquer reescrita de texto.

#### Entradas 2–4 — [PREENCHER com empregos anteriores, mesmo modelo]

#### Projeto paralelo (diferenciador — incluir!)

**Logistics Data Platform — side project · 2026**
*Plataforma de dados geoespaciais logísticos sobre dados abertos do governo brasileiro.*

- Built geospatial data pipeline (Python, GeoPandas, PostGIS) ingesting public datasets from [X] government agencies (DNIT, IBGE, ANTT, ANTAQ), visualized with Mapbox GL JS/Deck.gl.
- Demonstrates: data engineering + geospatial + product ownership end-to-end.

> Este projeto te separa de 95% dos backends Node: mostra que tu constróis coisas **tuas**, não só tickets dos outros.

### Skills (só o que tu topas ser entrevistado sobre)
```
Backend: Node.js, TypeScript, NestJS, Fastify · Event-driven: Kafka, EventBridge, SQS/SNS
AWS: Lambda, Step Functions, DynamoDB, RDS · Data: Python, PostGIS, GeoPandas
Practices: distributed systems, DDD, ADRs, serverless cost optimization
```

---

## 4. LinkedIn — as 3 seções que geram inbound

1. **Headline:** a versão curta da seção 2.
2. **About:** primeiro parágrafo = o posicionamento; segundo = 2 cases com números da Luxury Escapes; terceiro = o que tu procuras ("open to part-time B2B contracts with EU/UK scale-ups, 20h/week to start") + call to action.
3. **Featured:** fixa teu melhor ADR (Architecture Decision Record) escrito em inglês — é teu ativo de autoridade e nenhum concorrente teu tem um.

**Post semanal (já no teu plano de calibragem):** escreve sobre o que tu *operaste*, não sobre tutoriais. Ex.: "What running Step Functions at [X] events/day taught me about idempotency". Tutorial atrai junior; war story atrai cliente.

---

## 5. Introduction Letter / mensagem de aplicação (template EN)

Adaptar por vaga — nunca mandar genérica. Estrutura de 5 linhas:

```
Hi [nome],

I saw you're looking for [stack específica da vaga] for [projeto/produto mencionado].
I currently run exactly this stack in production for an Australian travel-tech scale-up:
[1 case com número — ex.: "event-driven services on AWS Lambda/Kafka processing X events/day at Y p99 latency"].

I'm a senior backend contractor based in Brazil (GMT-3) — full overlap with CET working hours,
available [20h/week / full-time] at €[rate]/h, invoicing via my own EU-ready company (DVISION LTDA).

Worth a 20-minute call this week? [link calendly ou disponibilidade]
```

**Regras:** (1) a segunda linha prova que tu leste a vaga; (2) a terceira prova que tu já fazes aquilo hoje, com número; (3) a quarta desarma as duas objeções padrão (fuso + estrutura fiscal); (4) pede algo pequeno e concreto.

---

## 6. Fit com vagas — como adaptar em 10 minutos por aplicação

| A vaga pede... | Tu reordenas o CV para abrir com... |
|---|---|
| "Kafka / event streaming" | O case Kafka/EventBridge da LE + palavra "event-driven" no summary |
| "NestJS / TypeScript APIs" | O case NestJS + Fastify nas skills no topo |
| "Serverless cost / performance" | O case de otimização de custo AWS |
| "Fintech/pagamentos" | [PREENCHER: qualquer case de integração de pagamento na LE] |
| "Geospatial/data" | O side project sobe para logo abaixo do summary |

---

## 7. Checklist de execução (esta semana)

- [ ] **Hoje (1h):** abrir CloudWatch/Datadog da LE e anotar 5 métricas reais (throughput, p99, uptime, custo, volume de bookings)
- [ ] **Hoje (30 min):** trocar headline do LinkedIn pela versão da seção 2
- [ ] **Amanhã (2h):** reescrever entrada da Luxury Escapes com o modelo da seção 3
- [ ] **Esta semana:** enviar CV atual + histórico de empregos para completar as entradas 2–4
- [ ] **Esta semana:** publicar 1 ADR em inglês no Featured do LinkedIn
- [ ] **Próxima semana:** aplicar a 5 vagas no Malt/Freelancermap com a letter da seção 5 adaptada — e medir taxa de resposta (meta: >20% de resposta; abaixo disso, iterar a letter, não o volume)

---

## Ressalvas honestas

- **A taxa de resposta é a única métrica que importa.** Se após 15 aplicações com esse material a resposta for <10%, o problema é de mercado/canal, não de texto — e aí revisamos posicionamento juntos.
- **Não inventes métricas.** Recrutadores técnicos europeus farejam números redondos demais. Métrica real imperfeita ("reduzi p99 de 800ms para ~400ms") vence número bonito falso.
- O rate de €50–65/h é sustentado pelos dados de mercado de 2026, mas tua **primeira** proposta pode fechar em €45/h para comprar a referência — e subir no 2º contrato. Isso é estratégia, não derrota.
