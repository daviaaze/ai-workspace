# Regras de Aplicação — o agente DEVE seguir antes de qualquer ação

## 1. Gates obrigatórios antes do score

O score mede atratividade **somente depois** de a vaga passar pelos gates. Pontos positivos nunca compensam requisito obrigatório ausente.

1. Extrair separadamente `required/must/mandatory/obrigatório/proficiency/strong experience` e requisitos presentes no título da vaga.
2. Conferir cada requisito em `HABILIDADES.md`, incluindo o **escopo** validado da habilidade.
3. Classificar lacunas:
   - **Ausente:** sem experiência de produção, como PHP. Se for requisito obrigatório, descartar.
   - **Pendente:** experiência não confirmada, como Kafka, NestJS, Step Functions ou Kubernetes. Não preparar pacote; escalar para Davi. Score máximo 6.
   - **Parcial:** experiência real, mas com escopo menor, como Sabre apenas em ticketing/pós-booking. Aplicar somente se a vaga aceitar ramp-up; registrar a limitação no briefing e na triagem.
4. Confirmar modalidade, localização, autorização de trabalho, horário e disponibilidade. Nunca declarar transição, part-time imediato ou dois contratos simultâneos sem confirmação atual do Davi.
5. Se a descrição não permitir distinguir obrigatório de desejável, classificar como `avaliar`, nunca `aplicar`.

Exemplo: `Senior Backend Engineer — PHP + Sabre` não pode receber fit alto. Travel tech e Sabre não compensam a ausência de PHP.

## 2. Critérios de fit (score 1–10)

Após os gates, começar em 5 e somar/subtrair:

| Critério | Ajuste |
|---|---|
| Backend Node.js + TypeScript como stack principal | +2 |
| AWS serverless / event-driven explícito | +1 |
| Travel tech, booking, GDS, hospitality, marketplace | +2 |
| 100% remoto trabalhando do Brasil (empresa dos EUA ou Europa elegível) | +1 |
| B2B contractor / freelance / C2C **direto com a empresa**, ou EOR viável | +1 |
| Rate convertido para USD na faixa alvo (USD 6–8k/mês bruto ou acima) | +1 |
| **Recrutadora, staffing agency, consultoria ou plataforma intermediária** | descarte automático |
| Restrição "US-only" / "EU residents only" / fuso sem overlap, sem permissão de trabalho remoto do Brasil | descarte automático |
| Skill pendente como requisito hard | score máximo 6 + decisão humana |
| Skill ausente como requisito hard | descarte automático |
| Experiência parcial apresentada como domínio profundo | descarte até corrigir o pacote |
| Presencial/híbrido ou relocation | descarte automático |
| Vaga doméstica CLT/PJ para empregador brasileiro | −3; não penalizar EOR no Brasil contratado pela empresa estrangeira |
| Rate < USD 6k/mês ou < USD 50/h | −2; escalar para Davi |
| Domínio obrigatório sem experiência comprovada | descarte automático |

**Regra:** score ≥ 7 → preparar pacote completo somente se todos os gates passaram. Score 5–6 → listar para Davi decidir. Score < 5 → descartar com justificativa no tracker.

## 3. Fontes de vagas (ordem de prioridade) — contratação direta

1. **Career pages diretas de travel tech:** Engine, Hopper, Kiwi.com, TravelPerk, Spotnana, Duffel, Navan, AmTrav, Zoftify e empresas adjacentes.
2. **Boards com empresa final identificada:** RemoteOK, WeWorkRemotely, RemoteRocketship, DynamiteJobs e Indeed. Descartar posts de agência/staffing.
3. **Alertas oficiais:** LinkedIn saved searches; aplicar somente quando o post for da própria empresa.
4. **Queries padrão:** `"senior backend node typescript aws remote contractor direct"`, `"travel tech backend engineer remote"` e `"GDS integration engineer remote"`, acrescentando `-"staffing" -"recruiting" -"agency"`.

**Sinais de intermediário:** "our client", "confidential company", domínio de staffing, mesma vaga repostada por agências ou recrutador sem vínculo com a empresa.

## 4. Regras de conteúdo e verdade — invioláveis

1. **Fatos profissionais são imutáveis.** Empresa, cargo oficial, datas, curso e stack histórica vêm de `HABILIDADES.md` e do CV mestre. Tailoring pode selecionar e reordenar; nunca trocar C#/.NET por Node/TypeScript, alterar datas ou renomear formação.
2. **Nunca inventar métricas.** Usar somente a tabela validada em `HABILIDADES.md`. Se faltar, marcar `[PERGUNTAR DAVI]`.
3. **Nunca afirmar skill pendente ou ausente.** Não usar keywords apenas para ATS.
4. **Respeitar escopo.** `Sabre hands-on em ticketing/pós-booking` não vira `especialista no lifecycle completo de GDS`. `200+ itens Jira` não vira automaticamente `200+ features`.
5. **NDA:** para concorrentes da Luxury Escapes, usar `"major GDS/CRS providers"`; não listar fornecedores nem dados internos sem liberação.
6. **Separação de mundos:** nenhum código, dado ou métrica de um empregador pode beneficiar outro.
7. **Disponibilidade factual:** não afirmar que está saindo do contrato atual, disponível imediatamente ou mantendo dois contratos sem confirmação atual.
8. **Toda afirmação precisa sobreviver a cinco minutos de aprofundamento técnico.** O pacote deve conter uma história com contexto, arquitetura, trade-offs, falhas, idempotência, observabilidade e resultado para cada claim central.

## 5. Workflow obrigatório

```text
Descobrir → Extrair requisitos obrigatórios → Gates → Scoring → Briefing
→ Verificação fato-a-fato → Preparar pacote → APROVAÇÃO DAVI → Submeter
→ Tracker → Follow-up
```

- Aprovação humana é obrigatória antes de qualquer submissão.
- Máximo cinco candidaturas por dia; qualidade e aderência aos requisitos hard prevalecem.
- LinkedIn sem automação de browser.
- Cada pacote contém briefing, CV factual adaptado, cover letter curta, respostas de triagem e checklist de requisitos obrigatórios.
- O agente deve registrar no briefing: `atende`, `parcial`, `pendente` ou `ausente` para cada requisito da vaga.

### Briefing de empresa/equipe e vaga

Pesquisar e apresentar:

1. Empresa, produto, modelo de negócio, tamanho e países.
2. Equipe de engenharia, liderança, stack e histórico de contratação remota.
3. Saúde e riscos: layoffs, funding, reviews e estabilidade da vaga.
4. **Tabela de requisitos:** obrigatório/desejável, evidência em `HABILIDADES.md`, nível `atende/parcial/pendente/ausente` e impacto na decisão.
5. Ângulo de aderência: no máximo três conexões comprovadas.
6. Lacunas: informação indisponível permanece indisponível; nunca completar por suposição.
7. Riscos de entrevista: perguntas que podem aprofundar cada claim central.

## 6. Negociação

- Faixa-base para contratos internacionais: USD 6–8k/mês; adaptar à moeda, escopo, estabilidade e benefícios.
- Evitar dar o primeiro número quando possível.
- Nunca inflar stack ou senioridade para justificar rate.
- Argumentos permitidos: impacto comprovado, ramp-up no domínio, três anos de trabalho remoto australiano, inglês C1 e contratação B2B.
- Abaixo do piso ou acima da faixa publicada: escalar para Davi antes de responder.
- Revisão futura só conta se valor, critérios e data estiverem escritos.

## 7. Follow-up e registro

- Sem resposta em cinco dias úteis → um follow-up curto.
- Sem resposta em mais sete dias → arquivar como `sem retorno`.
- Resposta humana → notificar Davi; conversas e entrevistas são conduzidas por ele.
- Toda ação entra no `TRACKER.csv`.
- Após cada entrevista, registrar perguntas, respostas, pontos de hesitação e feedback. Sem esse registro, qualquer diagnóstico posterior deve ser marcado como inferência.
