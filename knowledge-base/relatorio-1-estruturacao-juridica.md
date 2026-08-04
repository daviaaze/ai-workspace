# Relatório 1: Estruturação Jurídica
# Análise a partir de fontes primárias (texto da lei)

**Data:** 2026-07-06
**Metodologia:** Leitura dos textos legais vigentes (não resumos, não interpretações de terceiros)
**Escopo:** Qualquer modelo de negócio envolvendo streaming, indexação, cache, e revenda de conteúdo audiovisual e textual no Brasil

---

## SUMÁRIO

1. [Lei 9.610/98 — Direitos Autorais](#1-lei-961098--direitos-autorais)
2. [Art. 184 Código Penal — Violação de Direito Autoral](#2-art-184-código-penal)
3. [Marco Civil da Internet — Lei 12.965/2014](#3-marco-civil-da-internet)
4. [Decreto 12.975/2026](#4-decreto-129752026)
5. [ANCINE — IN 174/2026 + Lei 14.815/2024](#5-ancine--in-1742026--lei-148152024)
6. [LGPD](#6-lgpd)
7. [CDC e demais leis aplicáveis](#7-cdc-e-demais)
8. [Jurisprudência e precedentes observados](#8-jurisprudência)
9. [Conclusões jurídicas (unicamente a partir do texto)](#9-conclusões-jurídicas)

---

## 1. Lei 9.610/98 — Direitos Autorais

### 1.1 Definições críticas (Art. 5)

O Art. 5 define os termos. São relevantes para qualquer modelo de negócio:

| Termo | Definição legal (texto literal) | Implicação |
|---|---|---|
| **Reprodução** (VI) | "a cópia de um ou vários exemplares (...) **de qualquer forma tangível, incluindo qualquer armazenamento permanente ou temporário por meios eletrônicos** ou qualquer outro meio de fixação que venha a ser desenvolvido" | ✅ **Caching de torrents é reprodução.** A lei explicitamente inclui "armazenamento temporário por meios eletrônicos". Não há espaço para interpretação contrária. |
| **Distribuição** (IV) | "a colocação à disposição do público do original ou cópia de obras (...) mediante a venda, locação ou qualquer outra forma de transferência de propriedade ou posse" | Colocar à disposição = distribuição. Streaming (colocar obra ao alcance do público) pode ser enquadrado aqui ou como comunicação ao público. |
| **Comunicação ao público** (V) | "ato mediante o qual a obra é colocada ao alcance do público, por qualquer meio ou procedimento e que não consista na distribuição de exemplares" | Streaming de obra protegida sem licença = comunicação ao público não autorizada. |
| **Contrafação** (VII) | "a reprodução não autorizada" | Fazer cache de torrent sem licença = contrafação. |
| **Obra audiovisual** (VIII, i) | "a que resulta da fixação de imagens com ou sem som, que tenha a finalidade de criar, por meio de sua reprodução, a impressão de movimento, independentemente dos processos de sua captação, do suporte usado inicial ou posteriormente para fixá-lo, bem como dos meios utilizados para sua veiculação" | Filmes, séries, anime — todos são obras audiovisuais protegidas. |

### 1.2 O que requer autorização do autor (Art. 29)

O Art. 29 lista modalidades que dependem de "autorização prévia e expressa do autor":

- **I** — "a reprodução parcial ou integral"
- **VI** — "a distribuição, quando não intrínseca ao contrato firmado pelo autor com terceiros para uso ou exploração da obra"
- **VII** — "a distribuição para oferta de obras ou produções mediante cabo, fibra ótica, satélite, ondas ou qualquer outro sistema que permita ao usuário realizar a seleção da obra ou produção para percebê-la em um tempo e lugar previamente determinados por quem formula a demanda" — **este inciso descreve exatamente streaming on-demand (o usuário escolhe o que assistir, quando e onde)**
- **VIII** — diversas formas de utilização pública (exibição, radiodifusão, etc.)
- **IX** — "a inclusão em base de dados, o armazenamento em computador, a microfilmagem e as demais formas de arquivamento do gênero"
- **X** — "quaisquer outras modalidades de utilização existentes ou que venham a ser inventadas" (cláusula aberta)

### 1.3 Duração dos direitos patrimoniais (Art. 41-45)

- **Art. 41:** 70 anos contados de 1º de janeiro do ano subsequente ao falecimento do autor
- **Art. 42:** Co-autoria — conta da morte do último co-autor sobrevivente
- **Art. 43:** Obras anônimas/pseudônimas — 70 anos da primeira publicação
- **Art. 44:** Obras audiovisuais e fotográficas — 70 anos da divulgação (não da morte do autor)
- **Art. 45:** Pertencem ao domínio público: obras cujo prazo expirou, obras de autores falecidos sem sucessores, obras de autor desconhecido

### 1.4 Limitações (exceções) — Art. 46

O Art. 46 lista o que NÃO constitui ofensa aos direitos autorais:

| Inciso | Exceção | Aplicável a streaming? |
|---|---|---|
| I (a-d) | Reprodução na imprensa, discursos públicos, retratos, Braille | ❌ Não |
| **II** | "a reprodução, **em um só exemplar de pequenos trechos**, para uso privado do copista, desde que feita por este, sem intuito de lucro" | ⚠️ Limitado a "pequenos trechos" e "um só exemplar". NÃO cobre cópia integral de filme. NÃO cobre distribuição. |
| III | Citação para estudo, crítica ou polêmica | ❌ Não cobre entretenimento |
| VI | Representação teatral/execução musical no recesso familiar ou didático sem lucro | ❌ Não cobre streaming/compartilhamento |
| VIII | Reprodução de pequenos trechos em obras novas (fair use-like) | ❌ Não cobre uso integral |

**A lei brasileira NÃO tem fair use amplo como os EUA.** As exceções são taxativas. O inciso II é o mais próximo de "cópia privada" e ele é restrito a pequenos trechos.

### 1.5 O que NÃO é protegido (Art. 8)

- Ideias, métodos, sistemas, conceitos matemáticos (I)
- Esquemas, planos, regras para atos mentais/jogos (II)
- **Textos de leis, decretos, decisões judiciais e atos oficiais (IV)** — fundamental para domínio público de textos legais
- Informações de uso comum (calendários, agendas) (V)
- Nomes e títulos isolados (VI)

---

## 2. Art. 184 Código Penal

### 2.1 Texto do caput

> "Art. 184. Violar direitos de autor e os que lhe são conexos:
> Pena – detenção, de 3 (três) meses a 1 (um) ano, ou multa."

### 2.2 Agravantes (§§ 1º a 4º — Lei 10.695/2003)

| § | Conduta | Pena |
|---|---|---|
| **§ 1º** | "reproduzir, por qualquer meio, obra intelectual (...) **no todo ou em parte, para fins de comércio**" (grifo: "comércio" não é só venda — inclui qualquer objetivo de lucro, mesmo indireto) | Reclusão, 2 a 4 anos, e multa |
| **§ 2º** | "reproduzir, por qualquer meio, obra intelectual, **no todo ou em parte**, com intuito de lucro direto ou indireto" — **abrange o operador do serviço** | Mesma pena (2-4 anos) |
| **§ 3º** | "oferecer ao público (...) obra intelectual (...) que saiba ou deva saber ser produzida com violação de direito autoral" | Reclusão 1-4 anos + multa. **"Deva saber" é importante — cria dever de diligência, não só dolo direto.** |
| **§ 4º** | "oferecer ao público (...) obra intelectual (...) que saiba ou deva saber ser produzida com violação de direito autoral, **com intuito de lucro direto ou indireto**" | Reclusão 2-4 anos + multa |

### 2.3 Implicações por modelo

| Modelo de negócio | Enquadramento potencial |
|---|---|
| **Operar cache de torrents** (debrid próprio) | Art. 184 § 1º ou 2º — reprodução para fins de comércio/lucro |
| **Revender conta de debrid de terceiro** | Depende — o revendedor não reproduz. Mas pode ser enquadrado no § 3º se "oferecer ao público" obra que "deva saber" ser infringente. |
| **Indexar torrents** (addon/motor de busca) | Potencial § 3º — "oferecer ao público" é interpretável. Motor de busca não oferece diretamente, mas "coloca à disposição". |
| **Operar serviço IPTV** | § 1º ou 2º — reprodução com fins de comércio. Caso clássico. |
| **Streaming P2P mesh** (Popcorn Time-like) | § 1º, 2º e 3º — reprodução, oferta ao público, com lucro. Todos os agravantes. |

**Ponto crítico:** O § 3º usa "deva saber", não apenas "saiba". Isso impõe um dever de diligência ao intermediário — não basta alegar desconhecimento se o conteúdo é notoriamente infringente. Este trecho é o mais relevante para indexadores e revendedores: **o risco criminal existe mesmo sem dolo direto.**

---

## 3. Marco Civil da Internet — Lei 12.965/2014

### 3.1 Art. 18 (provedor de conexão)

> "O provedor de conexão à internet não será responsabilizado civilmente por danos decorrentes de conteúdo gerado por terceiros."

Aplica-se só a provedores de conexão (ISPs). **Não se aplica** a provedores de aplicação (quem roda o serviço).

### 3.2 Art. 19 (provedor de aplicação — regime original, modificado pelo STF)

Texto original:
> "Com o intuito de assegurar a liberdade de expressão e impedir a censura, o provedor de aplicações de internet somente poderá ser responsabilizado civilmente por danos decorrentes de conteúdo gerado por terceiros se, após ordem judicial específica, não tomar as providências para, no âmbito e nos limites técnicos do seu serviço e dentro do prazo assinalado, tornar indisponível o conteúdo apontado como infringente."

**STF Tema 987** (RE 1.037.396, Rel. Min. Dias Toffoli, trânsito em julgado em 17/06/2025): Declarou **parcial inconstitucionalidade** do Art. 19. O novo regime é:

- **Crimes graves e conteúdo de risco sistêmico:** o provedor pode ser notificado extrajudicialmente e deve remover (regulado pelo Decreto 12.975)
- **Crimes contra honra:** ainda precisa de ordem judicial (permanece a lógica do Art. 19 original)
- **Direitos autorais:** a ANCINE pode determinar bloqueio administrativo (sem ordem judicial) sob IN 174/2026

### 3.3 Art. 21

> "O provedor de aplicações de internet que disponibilize conteúdo gerado por terceiros será responsabilizado subsidiariamente pela violação da intimidade decorrente da divulgação, sem autorização de seus participantes, de imagens, de vídeos ou de outros materiais contendo cenas de nudez ou de atos sexuais de caráter privado quando, após o recebimento de notificação pelo ofendido ou seu representante legal, deixar de promover, de forma diligente, no âmbito e nos limites técnicos do seu serviço, a indisponibilização desse conteúdo."

Aplica-se a conteúdo íntimo não consensual. Responsabilização sem ordem judicial. **Não se aplica a direitos autorais.**

---

## 4. Decreto 12.975/2026

**Vigência:** 20 de maio de 2026 (publicação). Dispositivos com prazos de adaptação (90-180 dias).

### 4.1 Deveres gerais (Art. 16-A)

Obrigações para **todos** os provedores de aplicação:

1. **Sede e representante legal no Brasil** — pessoa jurídica, com poderes para responder judicial e administrativamente (I)
2. **Canal de denúncia permanente e de fácil acesso** para notificações de conteúdo criminoso ou ilícito (II)
3. **Medidas para impedir redes artificiais de distribuição de conteúdo ilícito** (III)
4. **Segurança e transparência** (IV)

### 4.2 Dever de cuidado — conteúdo criminoso (Art. 16-B)

**Responsabilização em caso de falha sistêmica** na indisponibilização imediata de conteúdo que caracterize:

- Terrorismo (I)
- Induzimento a suicídio (II)
- Discriminação racial, étnica, religiosa, de gênero, homofobia/transfobia (III)
- Violência contra mulher (IV)
- Crimes sexuais contra vulneráveis, CSAM (V)
- Tráfico de pessoas (VI)
- Associação criminosa, milícia (VII)

**Direitos autorais NÃO constam desta lista.** Art. 16-B é restrito a crimes contra a pessoa, dignidade, Estado Democrático.

### 4.3 Notificação de conteúdo ilícito (Art. 16-D e 16-E)

- Notificação deve conter: identificação da conduta ilícita, identificação específica do conteúdo, identificação do notificante (Art. 16-D)
- Provedor deve: confirmar recebimento, avaliar teor, comunicar decisão (Art. 16-E)
- **Prazos a serem regulamentados pela autoridade competente**

### 4.4 Indisponibilização de conteúdo criminoso (Art. 16-G)

- Provedor deve indisponibilizar conteúdo que configure crime, **exceto crimes contra a honra**
- Pode manter se houver "dúvida razoável" sobre caráter criminoso (proporcionalidade)

### 4.5 Ordem judicial — regra geral (Art. 16-J)

> "A responsabilização de provedor de aplicações de internet por conteúdo gerado por terceiro dependerá de ordem judicial específica, nos termos do Art. 19 do Marco Civil, nas hipóteses:
> I - de crimes e atos ilícitos contra a honra; e
> II - dos serviços de que trata o art. 16-O."

**Para conteúdos NÃO listados no Art. 16-B (ex: direitos autorais), o regime geral é: notificação extrajudicial → avaliação do provedor → remoção (ou não). Se não remover, o notificante pode ir ao judiciário. Mas a ANCINE tem poder administrativo próprio (IN 174).**

### 4.6 Critérios diferenciados — pequenos provedores (Art. 16-P)

> "A autoridade competente poderá definir critérios diferenciados para o cumprimento dos deveres (...) considerados o porte econômico do operador, o nível de interferência na circulação de conteúdo de terceiros, o estado da técnica e o risco envolvido no serviço, especialmente quanto aos pequenos provedores."

**Pequenos provedores têm tratamento diferenciado.** A lei reconhece que as obrigações devem ser proporcionais ao porte.

### 4.7 Exceções (Art. 16-O)

Os deveres dos Art. 16-B a 16-J **não se aplicam** a:
- Serviços de e-mail (I)
- Serviços de mensageria instantânea interpessoal (II)
- Serviços de comunicação audiovisual em grupo restrito (III)

### 4.8 Publicidade — presunção de responsabilidade (Art. 16-L)

> "Presume-se a responsabilidade do provedor quando o conteúdo ilícito for veiculado em anúncios, impulsionamentos pagos ou distribuído por meio de redes artificiais de distribuição de conteúdos, **independentemente de notificação**."

Se houver publicidade paga veiculando conteúdo ilícito, a responsabilidade é presumida. Relevante para monetização via anúncios.

### 4.9 Fiscalização (Art. 19-A)

**ANPD** (Agência Nacional de Proteção de Dados) é a autoridade fiscalizadora dos deveres dos provedores.

---

## 5. ANCINE — IN 174/2026 + Lei 14.815/2024

### 5.1 Lei 14.815/2024

A Lei 14.815/2024 alterou a Medida Provisória 2.228-1/2001 para dar à ANCINE poderes de:

> "Art. 3º (...) A ANCINE poderá determinar, administrativamente, a qualquer pessoa jurídica que desenvolva atividade considerada relevante para coibir a violação de direitos autorais sobre obras audiovisuais, a adoção de medidas para fazer cessar a infração, incluindo a indisponibilização de conteúdo."

**A ANCINE pode bloquear conteúdo sem ordem judicial.** Isso é poder administrativo direto. A IN 174/2026 regulamenta esse procedimento.

### 5.2 IN 174/2026 — Texto disponível

A IN foi publicada em 10/04/2026 (DOU nº 68, Seção 1, pág. 17). O texto está disponível no site da ANCINE como PDF. Conteúdo conhecido a partir do comunicado oficial:

- Regulamenta "apresentação, recebimento e processamento de representações em razão da oferta não autorizada de conteúdo audiovisual protegido em ambiente digital"
- Alterou a IN 170/2024
- Estabelece procedimento administrativo de notificação → avaliação → bloqueio
- **Alcança intermediários** (não apenas provedores de conteúdo direto)
- Pode determinar bloqueio sem decisão judicial

**Ponto não resolvido no texto público:** o escopo exato de "intermediários". A IN provavelmente define "intermediário" como qualquer pessoa jurídica que "desenvolva atividade considerada relevante para coibir a violação" (linguagem da Lei 14.815). Isso pode alcançar provedores de hospedagem, CDNs, e potencialmente indexadores/addons.

---

## 6. LGPD

**Lei 13.709/2018** aplica-se a qualquer tratamento de dados pessoais no Brasil.

Requisitos relevantes para o modelo:
- **DPO** (encarregado) nomeado (Art. 41)
- **Base legal** para tratamento: consentimento ou legítimo interesse (Art. 7)
- **Registro de operações** de tratamento (Art. 37)
- **Política de privacidade** acessível
- Dados de pagamento: não armazenar, usar gateway certificado (PCI-DSS)

O Decreto 12.975/2026 Art. 19-A coloca a ANPD como fiscalizadora também dos deveres do Marco Civil.

---

## 7. CDC e Demais

- **CDC (Lei 8.078/90):** aplica-se à relação B2C. Direito de arrependimento em 7 dias (Art. 49). Informação clara sobre preço, prazo, características do serviço.
- **Lei 12.485/2011 (SeAC):** Serviço de Acesso Condicionado — regula TV por assinatura. **Serviço IPTV sem licença da Anatel é ilegal por esta lei, além da violação de direitos autorais.**
- **Lei Complementar 187/2021 (Marco Legal das Startups):** pode oferecer enquadramento simplificado para empresas nascentes.

---

## 8. Jurisprudência e Precedentes Observados

### 8.1 Popcorn Time (Brasil e EUA)

- **EUA:** operadores processados criminalmente. Estúdios processaram usuários individuais (Hawaii, 2015). Juiz federal inicialmente permitiu que usuário continuasse, mas decisão não vinculante.
- **Brasil:** estúdios processaram o Popcorn Time e seus usuários (Tecnoblog reportou). Não foi encontrada decisão final publicada, mas o processo existiu.
- **Modelo P2P mesh distribuído = alvo de enforcement criminal civil em múltiplas jurisdições.**

### 8.2 Kadokawa/CODA vs. site de pirataria de anime (2026)

- **Condenação criminal:** prisão (suspensa) + multa milionária contra operador de site que extraía roteiros de anime. Caso japonês com cooperação internacional.
- O comunicado da Kadokawa explicitamente distingue "review/crítica" (uso justo) de "pirataria comercial" (criminal).
- **Demonstra que publishers japoneses buscam ativamente enforcement criminal internacional.**

### 8.3 Real-Debrid (França, 2024)

- RD sofreu pressão da Federation of Film Distributors e MPA.
- Respondeu com filtro de keywords, bloqueio de hashes, remoção de endpoints de API.
- **Nunca foi processado criminalmente (até onde se sabe), mas cedeu à pressão extrajudicial.**
- Demonstra que mesmo sem processo, a pressão da indústria força mudanças operacionais.

### 8.4 Globo vs. IPTV pirata (Brasil, 2025-2026)

- Globo obteve decisões totalizando R$ 500 milhões contra operadores de IPTV pirata.
- ANATEL e ANCINE firmaram acordo de cooperação formal.
- Bloqueio dinâmico implementado durante eventos (Copa, Brasileirão).
- **IPTV é o alvo prioritário do enforcement brasileiro em 2026.**

---

## 9. Conclusões Jurídicas (Unicamente a partir do Texto)

### 9.1 O que a lei diz (sem interpretação além do texto)

1. **Cache de torrents (debrid) = reprodução** (Art. 5, VI, Lei 9.610). Fazer cache sem licença = contrafação (Art. 5, VII). Operar um debrid com fins de lucro = Art. 184 § 1º ou 2º CP.

2. **Oferecer ao público obra infringente, mesmo que você não a tenha reproduzido = crime** (Art. 184 § 3º CP). O verbo é "oferecer". Um indexador que liste torrents pode ser enquadrado aqui, dependendo da interpretação judicial de "oferecer".

3. **"Deva saber" (Art. 184 § 3º CP) impõe dever de diligência.** Se o conteúdo é notoriamente infringente (ex: filme recém-lançado em cartaz), o intermediário não pode alegar desconhecimento.

4. **Streaming on-demand sem licença requer autorização** (Art. 29, VII, Lei 9.610). O inciso descreve exatamente o modelo Netflix/Stremio: "sistema que permita ao usuário realizar a seleção da obra para percebê-la em tempo e lugar previamente determinados".

5. **Domínio público = 70 anos após morte do autor** (Art. 41). Ou 70 anos da divulgação para obras audiovisuais (Art. 44). Obras em DP podem ser reproduzidas, distribuídas, comunicadas ao público — sem restrição.

6. **Cópia privada no Brasil é restrita** (Art. 46, II: "um só exemplar de pequenos trechos, para uso privado do copista"). Não cobre cópia integral de filme/série.

7. **O Decreto 12.975/2026 NÃO lista direitos autorais entre os crimes de dever de cuidado** (Art. 16-B). Direitos autorais seguem o regime de notificação → remoção (Art. 16-J c/c Art. 19 Marco Civil), MAS a ANCINE tem poder administrativo próprio de bloqueio (Lei 14.815/2024 + IN 174/2026).

8. **Pequenos provedores têm tratamento diferenciado** (Art. 16-P, Decreto 12.975). As obrigações são proporcionais ao porte.

9. **Publicidade paga veiculando conteúdo ilícito presume responsabilidade** (Art. 16-L). Se houver anúncios no addon/app e o conteúdo for infringente, a responsabilidade é presumida — sem necessidade de notificação prévia.

10. **Representante legal no Brasil é obrigatório** (Art. 16-A, I). Pessoa jurídica, com poderes para responder judicial e administrativamente.

### 9.2 O que a lei NÃO diz (lacunas e ambiguidades)

1. **A lei não define explicitamente se um "motor de busca de torrents" (addon Stremio) é "oferecer ao público"** para fins do Art. 184 § 3º CP. A interpretação dependerá do caso concreto e do juiz. Um motor de busca genérico (Google) não é tratado como "oferecendo" conteúdo infringente. Mas um motor de busca especializado em conteúdo pirata (addon de torrents) pode ser.

2. **A IN 174/2026 não tem texto público facilmente acessível.** O PDF existe mas o site da ANCINE fornece apenas a página de resumo. O escopo exato de "intermediário" na IN 174 precisa ser verificado no PDF.

3. **O Decreto 12.975 não define "pequeno provedor".** O Art. 16-P diz que a autoridade "poderá definir" critérios — ou seja, ainda não estão definidos. Há insegurança jurídica sobre o que constitui "pequeno".

4. **A fronteira entre "revenda de serviço de terceiro" (legal) e "participação na cadeia de infração" (ilegal) não está definida em lei.** Dependerá de interpretação judicial. Revender conta TorBox é diferente de revender lista IPTV? A lei não distingue — é o juiz que decidirá.

### 9.3 Tabela-resumo: risco jurídico por atividade

| Atividade | Lei aplicável | Tipo de responsabilidade | Gravidade |
|---|---|---|---|
| **Operar cache de torrents (debrid próprio)** | Art. 5 VI + Art. 29 I Lei 9.610 + Art. 184 § 1º CP | Criminal + Civil + Administrativa (ANCINE) | 🔴 Alta |
| **Revender conta de debrid de terceiro** | Art. 184 § 3º CP (potencial) + CDC | Civil + Criminal (controverso) | 🟡 Média |
| **Indexar/agregar torrents (addon)** | Art. 184 § 3º CP (potencial) + ANCINE IN 174 | Administrativa (ANCINE) + Criminal (controverso) | 🟡 Média |
| **Operar IPTV sem licença** | Art. 184 CP + Lei 12.485/2011 SeAC | Criminal + Civil + Anatel | 🔴 Muito alta |
| **Operar P2P mesh** | Art. 184 §§ 1-3 CP | Criminal (todos os agravantes) | 🔴 Muito alta |
| **Distribuir obras em domínio público** | Nenhuma (Art. 41 Lei 9.610) | Nenhuma | 🟢 Zero |
| **Hospedar ferramenta de terceiro (addon auto-hospedado pelo usuário)** | Marco Civil Art. 19 (regime notice and takedown) | Civil (se não remover após ordem judicial) | 🟡 Baixa |
| **Veicular publicidade em addon com conteúdo infringente** | Art. 16-L Decreto 12.975 (presunção de responsabilidade) | Civil + Administrativa (ANPD) | 🔴 Alta |

---

### Nota Metodológica

Esta análise baseia-se exclusivamente no texto da lei e em precedentes públicos documentados. Não constitui aconselhamento jurídico. Áreas de incerteza (interpretação de "oferecer", definição de "pequeno provedor", escopo da IN 174) estão identificadas como tal. A legislação brasileira de internet está em rápida evolução (Decreto 12.975/2026 com efeitos a partir de 20/07/2026). Consultar advogado especializado é indispensável antes de qualquer implementação.
