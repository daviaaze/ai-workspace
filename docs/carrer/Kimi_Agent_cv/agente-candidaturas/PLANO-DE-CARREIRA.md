# Plano de Carreira — Contractor Backend Senior (Davi Azevedo)

> Meta: sustentar USD 6–8k/mês como contractor direto (plano ativo) e abrir caminho para USD 8–12k/mês em 12–18 meses. Revisar trimestralmente. Criado em 02/ago/2026.

## 1. Diagnóstico — onde você está vs. onde o mercado paga

**Ativos fortes (já monetizáveis):**
- Node.js + TypeScript + AWS serverless/event-driven — banda premium USD 45–70/h, mediana senior NA USD 72/h (mercado, jul/2026)
- Domínio travel tech + GDS (escasso; poucos seniores com Sabre hands-on)
- 5 anos de remoto internacional + IELTS 8.0 + LTDA própria
- Arbitragem LatAm a seu favor: mercado paga USD 30–70/h por senior LatAm, e você está no topo da faixa técnica

**Lacunas que travam vagas (confirmadas em anúncios reais, jul-ago/2026):**

| Lacuna | Evidência de demanda | Impacto em você |
|---|---|---|
| **Certificação AWS** | Clientes de consultoria/contractor "filtram por certificação" [^89^]; SAA-C03 = +30% salário médio [^87^] | Nenhuma cert — perde triagem automática sem motivo |
| **NestJS** | Requisito recorrente (Arc.dev, Lemon.io, Zoftify — 3 anúncios em 1 semana) | Pendente na matriz; você tem experiência não mapeada |
| **Docker/Kubernetes** | Docker em 32% das vagas remotas Node, K8s em 24% (análise 437 vagas RemoteRocketship) | Profundidade não confirmada |
| **Kafka** | Presente em perfis de freelancers backend top (Expert Remote) e vagas event-driven enterprise | Removido do CV por origem não mapeada |
| **LLM/RAG applied** | Demanda de AI engineer +143% YoY, gap 3.2:1 [^93^]; RAG = +10–15% salário mid [^91^] | Diferencial para rate ceiling — ainda ausente |
| **GraphQL** | Frequente em vagas fullstack/product | Não confirmado |

## 2. Certificações — ROI ordenado (fazer nesta ordem)

### ✅ Prioridade 1: AWS Certified Solutions Architect – Associate (SAA-C03)
- **Por quê:** seu stack inteiro é AWS; é a cert mais requisitada em cloud; clientes contractor filtram por ela [^89^]; +USD 15–25k/ano de premium médio [^86^][^87^]
- **Custo:** USD 150 (exame) + ~USD 15–85 (curso) | **Tempo:** 6–8 semanas a 1h/dia (você já tem 4+ anos hands-on — pule o Cloud Practitioner)
- **Materiais:**
  - Curso: **Stephane Maarek — "Ultimate AWS Certified Solutions Architect Associate" (Udemy)** — padrão-ouro da prova
  - Prática: **Tutorials Dojo practice exams** (fazer 4–6 simulados, só agendar com 80%+ consistente)
  - Labs: sua própria conta AWS free-tier + os projetos GitHub do plano de portfólio (matéria-prima perfeita: Lambda, EventBridge, Step Functions, VPC, DynamoDB)
  - Grátis complementar: AWS Skill Builder (oficial)
- **Payback:** < 2 meses no novo rate [^86^]
- **Alvo:** exame até **fim de setembro/2026**

### ✅ Prioridade 2: AWS Certified Solutions Architect – Professional (SAP-C02)
- **Por quê:** posiciona para senior/consultoria; SAA + SAP = +50% vs. não certificado [^87^]; perfil "architect contractor" é o que cobra USD 8k+/mês
- **Custo:** USD 300 | **Tempo:** 3–4 meses após a Associate
- **Materiais:** Maarek SAP-C02 (Udemy) + Tutorials Dojo + AWS whitepapers (Well-Architected Framework)
- **Alvo:** Q1/2027 — só depois de fechar o primeiro contrato 6k+

### 🔶 Prioridade 3 (condicional): CKAD ou Kafka — decidir por dados
- **CKAD (USD 445):** vale se as vagas-alvo do seu funil pedirem K8s; prepare com **KodeKloud CKAD** (labs hands-on). Não fazer CKA (admin) — você é dev, não SRE
- **Kafka:** sem cert obrigatória; provar com o projeto GitHub de referência event-driven (já planejado) usando Kafka + documentação de decisões. Confluent Developer Skills (grátis) como trilha
- **Regra:** contar quantas vagas score ≥ 7 no tracker pediram K8s vs. Kafka nos próximos 60 dias → investir na mais citada

### ❌ Não vale agora
- Cloud Practitioner (abaixo do seu nível), GCP/Azure (dispersa; AWS é 29–32% do mercado, seu stack é AWS), IELTS retake (válido para emprego; só refazer se imigração entrar no radar)

## 3. Skills técnicas — plano de estudo (sem cert, prova via GitHub)

| Ordem | Skill | Por quê | Material | Esforço | Evidência pública |
|---|---|---|---|---|---|
| 1 | **NestJS** | Requisito recorrente; curva baixa p/ você (TS + decorators + DI) | Docs oficiais + curso "NestJS Zero to Hero" (Ariel Weinberger, Udemy) | 2–3 semanas | Migrar um service do projeto de referência para NestJS |
| 2 | **Docker avançado + K8s básico** | 32%/24% das vagas; entrevistas cobram | "Docker Mastery" (Bret Fisher, Udemy) + **Killercoda/KodeKloud K8s labs** (grátis) | 4–6 semanas | Repo com docker-compose multi-service + manifests K8s + deploy em kind/EKS |
| 3 | **Kafka** | Event-driven enterprise; complementa EventBridge/SQS | Confluent Developer (grátis) + "Kafka for developers" | 3–4 semanas | Projeto event-driven comparando SQS vs Kafka (blog post + repo) |
| 4 | **LLM/RAG aplicado a backend** | Maior gap de oferta do mercado (+143% YoY); sobe rate ceiling [^91^][^93^] | "LLM Engineering" (Ed Donner, Udemy) + docs Anthropic/OpenAI + **pgvector** (casa com seu PostgreSQL) | 6–8 semanas | Repo "travel-support-copilot": RAG sobre docs públicos de API de viagem, com evals + custo por conversa documentado [^91^] |
| 5 | **GraphQL** (opcional) | Aparece em vagas product/fullstack | Apollo docs + projeto pequeno | 2 semanas | Endpoint GraphQL sobre o projeto de referência |

**Sequência com o portfólio GitHub (já planejado em pesquisa-mercado-metricas-portfolio.md):** o repo 1 (event-driven reference architecture) cobre itens 2–3; o repo 2 (LLM-ops backend) cobre item 4; NestJS vira o framework do repo 1 (item 1). Um esforço, três evidências.

## 4. Otimização do perfil contractor (ações imediatas)

**LinkedIn** (pendências já identificadas — executar esta semana):
- [ ] About: remover "Kafka, NestJS" da linha de stack; restaurar quebras de linha editando direto no campo
- [ ] Top Skills: fixar **Node.js, TypeScript, AWS** (ordem)
- [ ] Featured: link do Meia-Entrada Estudantil
- [ ] Open-to-work: configurar "Contract" + títulos "Senior Backend Engineer / Backend Contractor" (visível só para recrutadores)
- [ ] Após SAA-C03: badge AWS no perfil + cert em "Licenses & certifications"

**GitHub** (a prova que substitui código privado — 82% do código de devs está em repos privados, recrutador não vê nada sem portfolio):
- [ ] Pinnar 4 repos conforme plano existente; READMEs com diagrama de arquitetura + decisões + "como rodar"
- [ ] Profile README curto: positioning sentence + stack + link CV/LinkedIn

**Posicionamento de rate** (conforme REGRAS-DE-APLICACAO.md § Negociação):
- Hoje: ancorar 6–8k com provas (500+ agências, USD 3M TTV, Sabre hands-on)
- Pós SAA-C03 + 1 contrato 6k+: subir piso para 7k
- Pós LLM/RAG portfolio + SAP-C02: mirar 8–12k (perfil "backend + AI architect")

## 5. Roadmap 12 meses

| Quando | Foco | Marco mensurável |
|---|---|---|
| **Ago/2026** | NestJS (2–3 sem) + início SAA-C03; pendências LinkedIn; 1º contrato direto 6k+ (Engine/PlanitEasy em curso) | NestJS no CV com origem definida; pipeline direto rodando |
| **Set/2026** | SAA-C03 exam; Docker/K8s labs | ✅ AWS SAA-C03; badge no LinkedIn |
| **Out–Nov/2026** | Kafka + repo event-driven publicado; decisão CKAD vs Kafka (regra §2.3) | Repo 1 pinnado com README completo |
| **Dez/2026–Jan/2027** | LLM/RAG + repo travel-support-copilot | Repo 2 pinnado; cover letters passam a citar AI |
| **Fev–Mar/2027** | Renegociar rates (piso 7k); iniciar SAP-C02 | Contrato(s) ≥ 7k/mês combinados |
| **Q2/2027** | SAP-C02; avaliar 2º contrato part-time vs. 1 full premium | Meta 8–12k/mês |

## 6. Regras de manutenção deste plano

- Revisar a cada 3 meses com dados do TRACKER.csv (quais skills as vagas score ≥ 7 realmente pediram → ajustar prioridades 2.3 e 3)
- Toda cert/skill concluída → atualizar `HABILIDADES.md` (mover de ⚠️ para ✅) + cv-mestre + LinkedIn na mesma semana
- Estudo máximo 5–7h/semana enquanto houver 2 contratos ativos — o plano assume ritmo sustentável, não sprint
