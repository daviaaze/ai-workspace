# Regras de Aplicação — o agente DEVE seguir antes de qualquer ação

## 1. Critérios de fit (score 1–10)

Começar em 5 e somar/subtrair:

| Critério | Ajuste |
|---|---|
| Backend Node.js + TypeScript como stack principal | +2 |
| AWS serverless / event-driven explícito | +1 |
| Travel tech, booking, GDS, hospitality, marketplace | +2 |
| 100% remoto sem restrição geográfica (ou "LatAm welcome") | +1 |
| B2B contractor / freelance / C2C **direto com a empresa** | +1 |
| Rate na faixa alvo (USD 6–8k/mês ou equivalente/hora) | +1 |
| Part-time 20h (encaixa no plano de 2 contratos) | +1 |
| **Recrutadora, staffing agency, consultoria ou plataforma intermediária** (Combine, Lemon.io, Toptal, Arc.dev, Braintrust, "cliente confidencial" etc.) | **descarte automático** |
| Restrição "US-only" / "EU residents only" / fuso sem overlap | −4 |
| Exige skill pendente como requisito hard (Kafka, NestJS, K8s) | −2 |
| Presencial/híbrido ou relocation | descarte automático |
| CLT/PJ Brasil | −3 (fora da estratégia atual) |
| Rate < USD 6k/mês ou < USD 50/h | −2 (abaixo do alvo; 5–5.9k só com aprovação do Davi) |
| Fintech/banking domain obrigatório | −2 (sem experiência no domínio) |

**Regra:** score ≥ 7 → preparar pacote completo. Score 5–6 → listar para Davi decidir. Score < 5 → descartar com justificativa de 1 linha no tracker.

**Exceção vigente:** a negociação PlanitEasy (via Combine/Duda) já está em curso e segue até conclusão. Nenhuma NOVA oportunidade via recrutador/intermediário entra no pipeline a partir de 02/ago/2026.

## 2. Fontes de vagas (ordem de prioridade) — SOMENTE contratação direta

1. **Career pages diretas de travel tech:** Engine, Hopper, Kiwi.com, TravelPerk, Spotnana, Duffel, Navan, AmTrav, Zoftify + OTAs/membership clubs menores (modelo Luxury Escapes)
2. **Boards com filtro de empresa direta:** RemoteOK, WeWorkRemotely, RemoteRocketship, DynamiteJobs, RelocateMe, Indeed (contract) — descartar qualquer post de agência/staffing
3. **Alertas de e-mail oficiais:** LinkedIn saved searches (aplicar só quando o post for da própria empresa), Malt saved searches (projetos de cliente final)
4. **Queries padrão:** "senior backend node typescript aws remote contractor direct", "node serverless remote full-time contractor", "travel tech backend engineer remote", "GDS integration engineer remote", acrescentando `-"staffing" -"recruiting" -"agency"` quando o buscador suportar

**Sinais de que o post é de intermediário (descartar):** "our client", "confidential company", domínio de staffing no e-mail/URL, repost da mesma vaga por múltiplas agências, recrutador sem vínculo claro com a empresa no LinkedIn.

## 3. Regras de conteúdo (invioláveis)

1. **Nunca inventar métricas.** Usar apenas a tabela de métricas validadas em `HABILIDADES.md`. Se uma métrica ajudaria mas não existe, marcar "[PERGUNTAR DAVI]" no rascunho.
2. **Nunca afirmar skills ⚠️** (Kafka, NestJS, Fastify, Step Functions, K8s) até confirmação.
3. **NDA:** ao aplicar para concorrentes diretos da Luxury Escapes (OTAs/marketplaces de viagem com modelo similar), referir-se a suppliers como "major GDS/CRS providers" em vez de listar nomes; nunca usar dados internos da Lux além das métricas já validadas e públicas no CV.
4. **Separação de mundos:** nenhum dado, código ou métrica de um empregador pode ser usado em benefício de outro.
5. **CV tailoring:** reordenar e escolher bullets do banco do `cv-mestre-davi-azevedo.md` conforme a vaga — nunca criar experiências novas. Regras de adaptação por tipo de vaga estão na seção 6 do cv-mestre.
6. **Toda afirmação no CV/carta deve ser defensável em entrevista técnica.**

## 4. Workflow obrigatório (semi-autônomo)

```
Descobrir → Scoring → [≥7?] → Briefing empresa/equipe → Preparar pacote → APROVAÇÃO DAVI → Submeter → Tracker → Follow-up
```

- **Aprovação humana é obrigatória antes de qualquer submissão.** Sem exceções.
- Máximo 5 candidaturas/dia (qualidade > volume; testes de mercado mostram que volume automático gera 0% de entrevistas para vagas seniores).
- LinkedIn: nenhuma automação de browser (risco de shadow-ban — viola User Agreement 8.2). LinkedIn só via Easy Apply manual ou e-mail.
- Cada pacote = **briefing da empresa/equipe** + CV adaptado (docx) + cover letter curta (≤150 palavras) + respostas de triagem preenchidas. Salvar em `/mnt/agents/output/candidaturas/<empresa>-<data>/`.

### Briefing de empresa/equipe (obrigatório em todo pacote, quando a informação existir)

Pesquisar e apresentar em 1 página (`briefing.md` no pacote):

1. **Empresa:** o que faz, modelo de negócio, tamanho (funcionários via LinkedIn), funding/receita (Crunchbase/imprensa), sede e países de operação, fundação
2. **Produto e clientes:** produto principal, público-alvo, concorrentes diretos
3. **Equipe de engenharia:** tamanho estimado, estrutura de times, VP/Head of Engineering e tech leads identificáveis (LinkedIn), engenheiros brasileiros/latinos no time (sinal de fit cultural e histórico de contratação remota LatAm)
4. **Stack e sinais técnicos:** engineering blog, GitHub público, posts de engenheiros, vagas abertas adjacentes (revelam stack e prioridades)
5. **Saúde e riscos:** reviews de funcionários (Glassdoor/Levels.fyi), sinais de layoffs recentes, tempo médio de permanência, velocidade de contratação
6. **Angulo para o Davi:** 2–3 pontos de conexão entre o briefing e a experiência dele (usar na cover letter)
7. **Lacunas:** marcar explicitamente "informação não disponível" onde aplicável — nunca preencher com suposição

## 5. Negociação

- **Faixa alvo do plano: USD 6.000–8.000/mês** (equivalente a ~USD 50–65/h em full-time). Ancorar no topo (7–8k) quando a vaga mencionar serverless/GDS/travel explicitamente.
- **Nunca dar o primeiro número** se a pergunta for evitável ("I'd like to understand the scope first").
- Se pressionado: declarar "USD 6–8k per month, depending on scope".
- Contraproposta: +10–20% sobre a oferta inicial, SOMENTE depois de oferta escrita.
- Argumentos permitidos: ramp-up rápido (domínio + stack), escassez de perfil travel+serverless, economia de EOR no B2B direto, IELTS 8.0 + 5 anos remoto internacional.
- Abaixo de USD 6k/mês → escalar para Davi antes de responder (não recusar sozinho).
- Fallback aceitável (com aprovação): USD 6k + revisão em 6 meses por escrito.

## 6. Follow-up

- Sem resposta em 5 dias úteis → 1 follow-up curto.
- Sem resposta em +7 dias → arquivar no tracker como "sem retorno".
- Recrutador respondeu → **notificar Davi imediatamente**; conversas humanas são sempre conduzidas pelo Davi.

## 7. Registro

Toda ação (descoberta, descarte, pacote, submissão, follow-up, resposta) vai para `TRACKER.csv` com data. Métricas revisadas semanalmente: taxa de resposta, taxa de entrevista, tempo médio de resposta por fonte.
