# Prompt para Analista de Negócios — Viabilidade de Operação Solo em Leilões da Receita Federal

> **Contexto:** Pessoa física com CNPJ (MEI ou empresa), capital próprio de R$ 40.000,00, buscando alavancar com crédito privado para investir em lotes de mercadorias apreendidas pela Receita Federal (SLE), revendendo no Mercado Livre (ou outra plataforma). Operação solo, inicialmente do apartamento.

---

## 1. CENÁRIO BASE

### 1.1 Capital disponível
- **Próprio:** R$ 40.000,00
- **Crédito privado:** A buscar (especificar linhas disponíveis abaixo)
- **Alavancagem alvo:** A definir (ex: 1:1, 1:2, 1:3)
- **Reserva de segurança:** % do capital total para emergências

### 1.2 Perfil do investidor
- Sem experiência prévia em leilões públicos
- Sem experiência em e-commerce / marketplace
- Conhecimento técnico em eletrônicos (celulares, informática)
- Opera de casa (apto em área urbana)
- Disponibilidade: tempo parcial inicialmente

### 1.3 Estrutura jurídica
- MEI (faturamento limitado a R$ 81.000/ano) ou
- Empresa ME (qual CNAE ideal?)
- Regime tributário: Simples Nacional — qual anexo?

---

## 2. PREMISSAS DE MERCADO (levantar dados reais)

### 2.1 Fontes de aquisição (leilões)
- **Receita Federal SLE** — editais ativos mês a mês
  - Volumes típicos: 10-272 lotes por edital
  - Frequência: 2-4 editais/mês (nacional)
  - Tipos de produto: eletrônicos, celulares, informática, veículos, vestuário
  - Condições: "recondicionado, sem caixa, sem acessórios" (importante!)
  - Ágio típico nos pregões: 10-40% sobre o lance mínimo

### 2.2 Plataformas de revenda
- **Mercado Livre** (principal)
  - Comissão Clássico: 11-13% (eletrônicos/informática)
  - Comissão Premium: 16-18%
  - Custo fixo: R$ 6,00-6,75 (produtos < R$ 79)
  - Frete grátis obrigatório > R$ 79 (seller coparticipa)
  - Full: armazenagem + picking (para escala)
- **Shopee** (secundária)
  - Comissão: 14% + R$ 28 (acima de R$ 500)
  - Desconto Pix: 8% de subsídio
- **OLX / Facebook Marketplace** (direto, sem taxa)
- **Atacado** (revender lotes inteiros para lojistas)

### 2.3 Preços de referência (jul/2026)

| Produto | Preço Leilão (estimado) | Preço Revenda ML (usado/bom) |
|---------|------------------------|------------------------------|
| iPhone 13 128GB recondicionado | R$ 960 - 1.500 | R$ 2.200 - 2.800 |
| Xiaomi Redmi Note 13 256GB | R$ 300 - 500 | R$ 900 - 1.200 |
| Xiaomi Poco X6 Pro 256GB | R$ 400 - 600 | R$ 1.300 - 1.700 |
| Redmi Pad SE 128GB | R$ 200 - 350 | R$ 700 - 1.000 |
| iPhone 12 64GB recondicionado | R$ 600 - 900 | R$ 1.500 - 2.000 |
| Memória RAM PC (lote) | R$ 15-25/un | R$ 60-90/un |
| SSD 240GB (lote) | R$ 20-35/un | R$ 80-120/un |

---

## 3. ANÁLISE FINANCEIRA

### 3.1 Simulação de compra — Lote pequeno

**Exemplo: Lote 7 do Edital Itaguaí — R$ 20.000,00 — CELULAR/ACESSÓRIO**

```
Investimento:
  Lance:              R$ 20.000,00
  Ágio estimado (20%): R$ 4.000,00
  ICMS (12-18%):      R$ 3.600,00
  Frete (origem → casa): R$ 500,00
  Taxas bancárias:    R$ 100,00
  ─────────────────────────────
  CUSTO TOTAL:        R$ 28.200,00

Composição do lote (estimada):
  - 25 unidades de smartphones (R$ 800-1.200/un no ML)
  - Receita total estimada: R$ 25.000 - 30.000
  - Menos comissão ML (13%): R$ 3.250 - 3.900
  - Menos frete ML (R$ 15/un): R$ 375
  ─────────────────────────────
  RECEITA LÍQUIDA:    R$ 21.375 - 25.725
  LUCRO/PREJUÍZO:     -R$ 6.825 a -R$ 2.475 ← PROVÁVEL PREJUÍZO?
  ROI:                -24% a -8%

⚠️ Isso sugere que lotes de R$ 20K podem ser inviáveis se o ágio for alto.
   → Precisa de lotes com margem maior OU ágio baixo OU venda direta (sem ML)
```

### 3.2 Simulação de compra — Lote médio (com alavancagem)

**Exemplo: Parte do Lote 10 Brasília — iPhones 13**

```
Se conseguir comprar uma fração (rateio com outro comprador) ou
um lote menor com iPhones:

  Custo por 10 iPhones 13:
  Lance:              R$ 12.000,00 (R$ 1.200/un)
  ICMS:               R$ 2.160,00
  Frete:              R$ 300,00
  ─────────────────────────────
  CUSTO TOTAL:        R$ 14.460,00 (R$ 1.446/un)

  Venda no ML (R$ 2.500/un):
  Receita bruta:      R$ 25.000,00
  - Comissão 13%:     -R$ 3.250,00
  - Frete grátis:     -R$ 150,00
  ─────────────────────────────
  RECEITA LÍQUIDA:    R$ 21.600,00
  LUCRO:              R$ 7.140,00
  ROI:                49,4%

  Se com ágio de 30% (R$ 1.560/un):
  LUCRO:              R$ 3.540,00
  ROI:                24,5%
```

### 3.3 Fluxo de caixa projetado (12 meses)

Considerar:
- **Sazonalidade:** Black Friday (nov), Natal (dez), Dia das Mães (mai)
- **Giro de estoque:** quantos dias até vender tudo?
- **Reinvestimento:** percentual do lucro reinvestido vs. retirado
- **Custos fixos mensais:**
  - Internet/energia: R$ 200
  - Materiais de embalagem: R$ 200
  - Transporte/deslocamento: R$ 300
  - Contador (se ME): R$ 300-500
  - Plano internet/telefone: R$ 150
  - Aplicativos/ferramentas: R$ 100
  - **Total custos fixos/mês: ~R$ 1.250**

### 3.4 Ponto de equilíbrio (break-even)

- Quantas unidades/mês precisa vender para cobrir custos fixos?
- Qual o ticket médio necessário?
- Quantos meses até recuperar o capital inicial?

---

## 4. ANÁLISE DE CRÉDITO

### 4.1 Linhas de crédito disponíveis

| Linha | Taxa (mês) | Carência | Prazo | Valor máx. |
|-------|-----------|----------|-------|-----------|
| **CDC (Crédito Direto ao Consumidor)** | 1,5-3% | — | 12-48x | R$ 50K |
| **Crédito Pessoal** | 2-5% | — | 12-24x | R$ 30K |
| **Antecipação de recebíveis (cartão)** | 2-4% | — | 30d | % do fluxo |
| **Empréstimo MEI (BNDES)** | 0,8-1,5% | 6m | 36-60x | R$ 20K |
| **Cheque especial** | 7-12% | — | — | ❌ Evitar |
| **Rotativo cartão** | 12-18% | — | — | ❌ Evitar |

### 4.2 Alavancagem recomendada

| Cenário | Capital Próprio | Crédito | Total | Risco |
|---------|----------------|---------|-------|-------|
| Conservador | R$ 40K | R$ 0 | R$ 40K | Baixo |
| Moderado | R$ 40K | R$ 20K | R$ 60K | Médio |
| Agressivo | R$ 40K | R$ 60K | R$ 100K | Alto |

- **Custo da dívida por mês:** qual parcela compromete o fluxo?
- **ROI necessário para superar o juro:** se o crédito custa 2%/mês, o lote precisa render >2%/mês

### 4.3 Risco de alavancagem

- E se o lote não for arrematado? (o dinheiro fica preso no caução?)
- E se a venda demorar mais que o prazo do crédito?
- E se o produto vier em condição pior que a esperada?

---

## 5. LOGÍSTICA E OPERAÇÃO

### 5.1 Fluxo operacional (passo a passo)

1. **Pré-leilão** (5-15 dias antes do pregão):
   - Analisar editais e lotes disponíveis
   - Calcular preço máximo de lance (com margem de segurança)
   - Visitar lotes presencialmente (quando possível)
   - Preparar documentação (GOV.BR Prata/Ouro, certificado digital)

2. **Pregão** (dia do leilão):
   - Dar lances online via e-CAC
   - Acompanhar disputa em tempo real
   - Tempo estimado: 2-4 horas

3. **Pós-arremate** (30 dias):
   - Emitir DARF e pagar em até 30 dias
   - Retirar mercadorias no depósito da Receita
   - Transportar para casa/estoque

4. **Triagem e preparação** (1-7 dias):
   - Testar cada unidade (funcionalidade, tela, bateria)
   - Limpar, higienizar
   - Categorizar: "bom", "com defeito", "para peças"
   - Fotografar
   - Precificar

5. **Anúncio e venda** (7-90 dias):
   - Criar anúncios no ML/Shopee/OLX
   - Atender cliente, negociar
   - Embalar e postar
   - Gerenciar devoluções

### 5.2 Capacidade operacional (solo)

| Atividade | Tempo/unidade | 10 unidades | 50 unidades |
|-----------|-------------|-------------|-------------|
| Testar/triar | 10 min | 1,7h | 8,3h |
| Limpar/fotografar | 15 min | 2,5h | 12,5h |
| Anunciar (ML) | 20 min | 3,3h | 16,7h |
| Atendimento (por venda) | 15 min | 2,5h | 12,5h |
| Embalar/postar | 10 min | 1,7h | 8,3h |
| **Total por lote** | | **~11,7h** | **~58,3h** |

### 5.3 Gargalos identificados
- **Espaço:** apartamento comporta quantas unidades?
- **Tempo:** conciliação com trabalho atual?
- **Conhecimento técnico:** sabe testar iPhone/Xiaomi?
- **Devoluções:** como lidar com logística reversa?

---

## 6. RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Impacto | Mitigação |
|-------|-------------|---------|-----------|
| Lote vir com produtos defeituosos | Média | Alto | Visitar lote antes, testar na retirada |
| Edital ser cancelado/suspenso | Baixa | Médio | Diversificar editais |
| Ágio muito alto no pregão | Alta | Médio | Definir lance máximo antes |
| Mercadoria roubada/extraviada | Baixa | Alto | Seguro, transporte seguro |
| Produto não vender (estoque parado) | Média | Alto | Precificar abaixo do mercado |
| Devolução/compliance ML | Média | Médio | Fotos detalhadas, descrição honesta |
| Mudança nas taxas da plataforma | Média | Baixo | Diversificar canais |
| Problema fiscal (nota, ICMS) | Média | Médio | Contador especializado |
| Concorrência de outros revendedores | Alta | Baixo | Nicho específico, diferencial |

---

## 7. VIABILIDADE — CRITÉRIOS DE DECISÃO

### 7.1 Indicadores-chave

| Indicador | Meta | Fórmula |
|-----------|------|---------|
| **ROI mínimo por lote** | ≥ 25% | (Receita - Custo total) / Custo total |
| **ROI líquido/mês** | ≥ 5% | ROI / meses para vender tudo |
| **Payback** | ≤ 6 meses | Investimento / Lucro mensal |
| **Margem líquida** | ≥ 20% | Lucro líquido / Receita bruta |
| **Giro de estoque** | ≤ 60 dias | Dias entre compra e última venda |
| **Taxa de ocupação do capital** | ≥ 2x/ano | (Lucro anual / Capital total) |

### 7.2 Regra de ouro para lances

```
Valor máximo do lance = (Preço de revenda × 0,75) - custos fixos - frete - margem de segurança

Onde 0,75 = 1 - 0,25 (margem mínima desejada + taxa ML aproximada)

Exemplo iPhone 13:
Lance máx = (R$ 2.500 × 0,75) - R$ 50 (frete) - R$ 100 (margem segurança)
Lance máx = R$ 1.725,00

Se o lance mínimo for R$ 960 e o ágio máximo suportado é R$ 765 (80% de ágio).
```

---

## 8. RECOMENDAÇÃO E PRÓXIMOS PASSOS

Com base nos dados acima, o analista deve produzir:

### 8.1 Entregáveis esperados
1. **Planilha financeira** com fluxo de caixa projetado para 12 meses (3 cenários: conservador, moderado, agressivo)
2. **Matriz de viabilidade** por tipo de lote (celular, informática, veículo, etc.)
3. **Análise de break-even** — quantas unidades/mês para ser sustentável
4. **Recomendação de alavancagem** — quanto crédito tomar e de qual linha
5. **Cronograma de implantação** — primeiros 90 dias passo a passo
6. **Análise de risco** — cenário pessimista, realista, otimista
7. **Decisão final:** SIM/NÃO viável, com justificativa numérica

### 8.2 Perguntas específicas a responder

1. **Com R$ 40K, qual o maior lote que posso comprar sem crédito?**
2. **Vale a pena pegar crédito de R$ 20K a 2,5%/mês para aumentar o capital para R$ 60K?** O ROI extra cobre o juro?
3. **Qual a margem mínima por lote para compensar o risco de alavancagem?**
4. **Quantas horas/semana são necessárias para operar solo?**
5. **Qual o melhor edital para começar (menor risco, maior previsibilidade)?**
6. **É melhor comprar um lote grande e revender no atacado (menor margem, menor trabalho) ou lotes pequenos e vender no varejo (maior margem, mais trabalho)?**
7. **Qual o CNAE ideal para a operação?** Comércio varejista de equipamentos de informática? Comércio atacadista de equipamentos eletrônicos?
8. **ICMS: como fica na compra interestadual?** DIFAL? Qual alíquota efetiva?

---

## 9. ANEXOS

### A. Editais-alvo para primeira operação

Prioridade para começar (menor risco):

| Ordem | Edital | Local | Lotes Interessantes | Investimento Mín. |
|-------|--------|-------|---------------------|-------------------|
| 1 | **900100/8/2026** | Curitiba/PR | Diversos (cosméticos, brinquedos, veículos, videogames) | R$ 2.500 |
| 2 | **100100/4/2026** | Brasília/MS | Lote 14: R$ 59 (informática), 9: R$ 78K (memórias/SSD) | R$ 59 |
| 3 | **717800/2/2026** | Itaguaí/RJ | Lote 7: R$ 20K (celular), 13: R$ 28K (celular) | R$ 20K |
| 4 | **100100/3/2026** | Brasília/MS | Lotes 6-11: celulares (R$ 150-500K) | R$ 150K |

### B. Documentação necessária
- [ ] CPF regular
- [ ] CNPJ (MEI ou ME)
- [ ] Conta GOV.BR nível Prata ou Ouro
- [ ] Certificado Digital (A1 ou A3)
- [ ] Acesso ao e-CAC
- [ ] Inscrição Estadual (para venda com NF)
- [ ] Contador

---

> ⚠️ **Instrução ao analista:** Produza um relatório de no máximo 3 páginas (resumo executivo) respondendo à pergunta principal: **"É viável uma operação solo de compra e revenda de lotes da Receita Federal começando com R$ 40K, eventualmente alavancado com crédito?"** Inclua números, riscos e recomendação clara (SIM/NÃO/em quais condições). Considere todos os custos ocultos: ICMS, frete, taxas ML/Shopee, embalagem, contador, devoluções, e seu próprio tempo.
