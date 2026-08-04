# Síntese: Os 3 Relatórios — Convergências, Divergências e Cenários

**Data:** 2026-07-06
**Metodologia:** 3 trilhas de pesquisa independentes → convergências e tensões identificadas → cenários possíveis
**⚠️ Este documento não recomenda um caminho. Apresenta o que os dados sustentam e as perguntas não respondidas.**

---

## 1. O QUE OS 3 RELATÓRIOS ENCONTRARAM

### Relatório 1 (Jurídico) — Principais achados

1. **Cache de torrents = reprodução** (Art. 5 VI Lei 9.610/98). Operar servidor que faz cache de conteúdo protegido → crime (Art. 184 CP).
2. **"Oferecer ao público" obra infringente = crime** (Art. 184 § 3º CP), incluindo a modalidade "deva saber" (dever de diligência).
3. **Streaming on-demand sem licença requer autorização** (Art. 29 VII Lei 9.610/98).
4. **Domínio público = 70 anos após morte do autor.** Obras em DP são livres para qualquer uso.
5. **Decreto 12.975/2026:** representante legal no Brasil obrigatório, canal de denúncias, tratamento diferenciado para pequenos provedores.
6. **ANCINE IN 174/2026:** poder administrativo de bloqueio sem ordem judicial. Escopo de "intermediário" não está definido publicamente em detalhe.
7. **Art. 16-L:** publicidade + conteúdo ilícito = presunção de responsabilidade (sem notificação prévia).
8. **Lacunas legais identificadas:** (a) "motor de busca de torrents" não tem definição legal clara; (b) "pequeno provedor" não está definido; (c) fronteira entre "revenda de serviço de terceiro" e "participação na infração" é zona cinzenta.

### Relatório 2 (Infraestrutura) — Principais achados

1. **Infra própria é barata.** R$ 31-90/mês (Hetzner CX23-CX43) serve addon/indexador para milhares de usuários.
2. **O TorBox domina o custo.** R$ 14-15/usuário/mês, >90% do custo total em escala.
3. **Margem de revenda é fina.** A R$ 19/mês, margem bruta de R$ 4/usuário com 10% de desconto no Partner Program.
4. **Custo marginal de infra é quase zero.** De 50 para 1.000 usuários, a infra sobe R$ 400 enquanto o custo TorBox sobe R$ 14.000.
5. **Eliminar TorBox reduziria custo a quase zero,** mas exige operar cache próprio (→ Relatório 1: ilegal) ou P2P mesh (→ Relatório 1: ilegal).
6. **TorBox Partner Program requer aplicação e não é garantido.** Tiers de desconto acima de 10% não são públicos.

### Relatório 3 (Distribuição/Mercado) — Principais achados

1. **Mercado massivo:** 33M lares BR com streaming pago.
2. **Dublado é maioria:** 59% preferem dublado (Datafolha 2015, corroborado Netflix).
3. **Stremio: 1M+ instalações Android mas REMOVIDO da Play Store.** Base real maior (sideload, TV, iOS).
4. **Canais de aquisição eficientes:** Reddit (r/pirataria ~230k), Discord, YouTube/TikTok, Telegram. Custo baixo (orgânico).
5. **Gap competitivo confirmado:** ninguém oferece debrid em PIX + addon dublado curado + suporte PT + biblioteca DP.
6. **Mercado endereçável estimado:** 50k-500k usuários (alta incerteza).
7. **Biblioteca DP não monetiza diretamente** — valor está em aquisição (isca grátis), diferenciação de marca, e defesa jurídica.

---

## 2. TENSÕES ENTRE OS RELATÓRIOS

### Tensão 1: Margem vs. Risco Legal

| Trilha | O que diz |
|---|---|
| **Infraestrutura** | Margem bruta de R$ 4/usuário é muito fina. Eliminar TorBox reduziria custo a ~zero/usuário. |
| **Jurídico** | Eliminar TorBox = operar cache próprio = Art. 184 CP + ANCINE. Risco criminal. |

**Pergunta não resolvida:** Existe um modelo entre "revenda TorBox com margem de R$ 4" e "cache próprio criminal"? (Ex: desconto maior no Partner Program em escala? AllDebrid como alternativa mais barata?)

### Tensão 2: Stremio fora da Play Store

| Trilha | O que diz |
|---|---|
| **Distribuição** | Stremio removido da Play Store. Instalação requer sideload. Barreira para novos usuários. |
| **Infraestrutura** | Addon no Stremio = zero custo de plataforma. App próprio = R$ 30-100k+. |

**Pergunta não resolvida:** A remoção da Play Store é uma barreira significativa ou o público-alvo já sabe fazer sideload? Um app próprio traria mais usuários ou só adicionaria custo?

### Tensão 3: Monetização via anúncios vs. Presunção de Responsabilidade

| Trilha | O que diz |
|---|---|
| **Jurídico** | Art. 16-L Decreto 12.975: publicidade + conteúdo ilícito = presunção de responsabilidade, sem notificação prévia. |
| **Distribuição** | Anúncios (AdEx do Stremio) são uma fonte de receita complementar. |

**Pergunta não resolvida:** Anúncios em um addon que exibe conteúdo infringente acionam o Art. 16-L? Ou o addon é "ferramenta de propósito geral" e a responsabilidade é do usuário? A lei não distingue.

### Tensão 4: Escala vs. Risco de Enforcement

| Trilha | O que diz |
|---|---|
| **Distribuição** | 50k-500k usuários potenciais. Quanto maior a escala, maior a receita. |
| **Jurídico** | "Pequenos provedores" têm tratamento diferenciado (Art. 16-P). Mas "pequeno" não está definido. Escala pode atrair enforcement. |

**Pergunta não resolvida:** Em que ponto a escala deixa de ser "pequeno provedor" e passa a ser alvo prioritário da ANCINE? 1.000 usuários? 10.000? A lei não define.

---

## 3. CENÁRIOS QUE OS DADOS SUSTENTAM

### Cenário A — "Revenda Pura" (TorBox Partner + Addon + Biblioteca DP)

**O que os dados dizem:**

| Dimensão | Evidência |
|---|---|
| **Legal** | Revenda de serviço de terceiro — zona cinzenta (Art. 184 § 3º pode ou não se aplicar). Addon indexador — zona cinzenta (não definido em lei). Biblioteca DP — 100% legal. |
| **Infra** | Custo: R$ 31-90/mês (fixo) + R$ 15/usuário (TorBox). Break-even: ~100-150 usuários (com R$ 19/mês). Margem bruta: R$ 4/usuário. |
| **Mercado** | Demanda validada (dublado bloqueado no RD). Canais de aquisição existem. Gap competitivo confirmado. |

**Questão central não resolvida:** A margem de R$ 4/usuário é suficiente para cobrir CAC, suporte, churn, impostos e gerar lucro? A R$ 19/mês, provavelmente não. A R$ 29/mês, margem sobe para R$ 14/usuário — mais viável. Mas R$ 29 é 10× o preço do TorBox direto. O consumidor pagaria?

### Cenário B — "Addon Monetizado" (Só addon, sem revenda TorBox)

**O que os dados dizem:**

| Dimensão | Evidência |
|---|---|
| **Legal** | Addon indexador — zona cinzenta, mas sem o agravante de "revenda de serviço usado para pirataria". Apenas motor de busca. |
| **Infra** | Custo: R$ 31-90/mês (fixo). Zero custo variável por usuário. Receita via anúncios (AdEx) ou assinatura do addon. |
| **Mercado** | GuIndex já existe (gratuito). Diferencial seria curadoria dublado + uptime garantido + suporte. |

**Questão central não resolvida:** Anúncios em addon com conteúdo infringente acionam Art. 16-L (presunção de responsabilidade)? Se sim, o modelo de receita via anúncios é inviável. Se não, o modelo é extremamente leve e escalável.

### Cenário C — "Biblioteca DP + Comunidade" (Marca legal, monetização indireta)

**O que os dados dizem:**

| Dimensão | Evidência |
|---|---|
| **Legal** | 100% legal (domínio público, CC, OA). Nenhum risco. |
| **Infra** | Custo: R$ 31-90/mês + storage R$ 21/mês. Receita via doações, grants, ou como isca para produto pago. |
| **Mercado** | Não monetiza diretamente. Valor = aquisição (topo de funil) + legitimidade de marca + defesa jurídica. |

**Questão central não resolvida:** Uma biblioteca DP sozinha não é um negócio (não gera receita). Mas como parte de um portfólio, resolve os problemas de "marca legítima", "defesa jurídica", e "aquisição de usuários". O valor está na sinergia, não no produto isolado.

---

## 4. PERGUNTAS QUE OS DADOS NÃO RESPONDEM

Estas são questões que exigiriam pesquisa primária (survey, entrevista, teste A/B) ou consulta jurídica formal:

### 4.1 Perguntas jurídicas (exigem parecer de advogado)

1. Um addon Stremio que lista torrents de conteúdo protegido é "oferecer ao público" para fins do Art. 184 § 3º CP?
2. Revender contas TorBox para usuários brasileiros configura "participação na cadeia de infração"? Ou é análogo a revender NordVPN (ferramenta de propósito geral)?
3. Qual é o escopo exato de "intermediário" na ANCINE IN 174/2026? Inclui addons/indexadores? Inclui revendedores de debrid?
4. A partir de quantos usuários o negócio deixa de ser "pequeno provedor" (Art. 16-P Decreto 12.975) e passa a ter obrigações plenas?
5. Anúncios em addon que exibe links para conteúdo infringente acionam a presunção de responsabilidade do Art. 16-L?

### 4.2 Perguntas de mercado (exigem pesquisa com usuários)

1. Qual é o willingness-to-pay real do consumidor BR para um serviço de debrid + addon? R$ 19? R$ 29? R$ 39?
2. Quantos usuários brasileiros do Real-Debrid existiam antes do filtro? Quantos estão ativos agora?
3. O consumidor BR sabe/percebe que o problema é o RD (e não os arquivos)? Ou só acha que "parou de funcionar"?
4. A remoção do Stremio da Play Store é uma barreira real para novos usuários?
5. Qual é o CAC real nos canais Reddit/Discord/YouTube para este nicho específico?

### 4.3 Perguntas técnicas (exigem teste/protótipo)

1. TorBox cacheia efetivamente conteúdo dublado BR (BLUDV, COMANDO, WEB-DL DUAL)?
2. Qual é o cache hit rate do TorBox para conteúdo dublado brasileiro vs. conteúdo internacional?
3. O TorBox Partner Program aceitaria um revendedor brasileiro com 50-100 usuários iniciais?
4. Quais são os tiers de desconto do Partner Program acima de 10%? (não publicados — negociados)
5. AllDebrid tem cache de conteúdo dublado BR comparável ao TorBox?

---

## 5. O QUE NÃO SE SABE (E É RELEVANTE)

1. **A posição do judiciário brasileiro sobre addons Stremio.** Não há jurisprudência conhecida. Nenhum addon brasileiro (GuIndex, DF Indexer) foi processado até onde se sabe. Mas também nunca foram comercializados.

2. **A posição do judiciário brasileiro sobre revenda de debrid.** Não há precedente. Revender NordVPN é aceito. Revender Real-Debrid/TorBox — não se sabe.

3. **Se e quando o TorBox sofrerá a mesma pressão que o RD.** O RD resistiu ~10 anos antes de ceder. O TorBox é mais novo (2023+), menor, e opera com crypto. Mas o padrão da indústria é: escala → pressão → filtro.

4. **O impacto real do Decreto 12.975/2026.** A lei entrou em vigor em 20/05/2026. Os efeitos práticos (fiscalização, enforcement) ainda não são conhecidos. A ANPD é a fiscalizadora mas nunca atuou nesse setor.

5. **O enforcement da ANCINE sob IN 174/2026.** A IN foi publicada em abr/2026. Ainda não há casos públicos de bloqueio administrativo de addons/indexadores.

---

## 6. TABELA-RESUMO: O QUE CADA CENÁRIO REQUER

| Cenário | Investimento | Custo mensal (1k users) | Break-even | Risco legal | Incerteza principal |
|---|---|---|---|---|---|
| **A: Revenda + Addon + DP** | R$ 8-20k | ~R$ 15k (90% TorBox) | 100-150 users | 🟡 Zona cinzenta | Margem fina. WTP real? |
| **B: Addon monetizado** | R$ 5-10k | ~R$ 500 (infra) | 30-50 users (R$ 10/mês) | 🟡 Zona cinzenta (anúncios Art. 16-L?) | monetização viável? |
| **C: Biblioteca DP pura** | R$ 3-5k | ~R$ 120 | Não monetiza | 🟢 Zero | Sem receita. Valor = sinergia |
| **A+B+C (portfólio)** | R$ 15-30k | ~R$ 15k | 100-150 users | 🟡 Zona cinzenta | WTP, enforcement, escala |

---

## 7. PRÓXIMOS PASSOS (BASEADOS EM EVIDÊNCIA, NÃO EM OPINIÃO)

### Passos que os dados indicam como necessários (independente do cenário):

1. **Validar juridicamente:** consultar advogado especialista sobre as 5 perguntas da seção 4.1. Sem isso, qualquer cenário é especulativo.

2. **Validar TorBox tecnicamente:** criar conta free, testar conteúdo dublado (Oppenheimer DUAL, Duna 2 DUAL, BLUDV releases). Confirmar cache hit rate.

3. **Validar mercado:** pesquisa na comunidade r/pirataria (survey simples: "Você pagaria R$ 19-29/mês por um serviço que resolve o problema do Real-Debrid com conteúdo dublado?").

4. **Validar Partner Program:** contatar TorBox para confirmar viabilidade de revenda no Brasil e tiers de desconto.

### Passos que dependem do cenário escolhido:

5. Se Cenário A: desenvolver addon (fork GuIndex), site billing PIX, aplicar TorBox Partner
6. Se Cenário B: desenvolver addon premium, integrar AdEx, validar Art. 16-L
7. Se Cenário C: scraper catálogo DP, site biblioteca, comunidade

---

## Nota Final

Este documento e os 3 relatórios são análises baseadas em fontes primárias e secundárias, sem viés de confirmação. As incertezas estão explicitamente identificadas. As perguntas não respondidas estão listadas. **A decisão sobre qual caminho seguir depende de fatores que os dados disponíveis não respondem** — em especial, a interpretação jurídica dos Art. 184 § 3º CP e ANCINE IN 174/2026, e o willingness-to-pay real do consumidor brasileiro.
