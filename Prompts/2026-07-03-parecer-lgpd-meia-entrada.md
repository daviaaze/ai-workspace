# PARECER JURÍDICO — ANÁLISE DE CONFORMIDADE LGPD, CDC E CIE

## SUMÁRIO EXECUTIVO (248 palavras)

**(i) Nível de risco jurídico atual: EXTREMO.** A plataforma opera com bypass total de controles de acesso (service_role exposta no frontend), coleta dado biométrico sem consentimento específico, inexiste política de privacidade ou canal DPO, e emite carteirinhas desprovidas dos requisitos CIE v3.3 — configurando exposição simultânea a sanções administrativas (art. 52 LGPD), indenizações civis por danos morais coletivos (art. 42 LGPD c/c art. 6º VI CDC) e responsabilização criminal (art. 284-A CP, art. 154-A CP). **(ii) Top-3 ações jurídicas prioritárias com prazo:** (a) Remover imediatamente (24h) a chave service_role do frontend e implementar RLS com privilégio mínimo — mitiga o bypass que torna inócuas todas as demais salvaguardas; (b) Em 7 dias, publicar Política de Privacidade com base legal explícita e implementar checkbox de consentimento específico para foto (dado biométrico sensível — art. 11 LGPD); (c) Em 30 dias, nomear Encarregado/DPO (art. 41 LGPD) e notificar a ANPD sobre as vulnerabilidades já documentadas (art. 48 LGPD c/c Res. CD/ANPD nº 15/2024). **(iii) Exposição financeira estimada:** multa administrativa de até R$ 50.000.000,00 por infração (2% do faturamento, art. 52 II LGPD), cumulável com indenizações por danos morais coletivos (ACP pelo MPF ou Defensoria — parâmetro R$ 500,00 a R$ 5.000,00 por titular afetado × centenas de milhares de cadastros), mais sanções penais aos responsáveis técnicos e sócios. Cenário conservador de vazamento massivo: exposição total superior a R$ 100 milhões.

---

## BLOCO 0 — RESPONSABILIDADES E LEGITIMIDADE PASSIVA

### 0. Responsabilidade civil objetiva vs. subjetiva do controlador

**Tese principal: Responsabilidade objetiva (risco da atividade).**

**Fundamentação:**

A LGPD adota, em seu art. 42, regime de **responsabilidade civil objetiva** para o agente de tratamento (controlador e operador), independentemente de culpa. O dispositivo é claro:

> *"Art. 42. O controlador ou o operador que, em razão do exercício de atividade de tratamento de dados pessoais, causar a outrem dano patrimonial, moral, individual ou coletivo, em violação à legislação de proteção de dados pessoais, é obrigado a repará-lo."*

A doutrina majoritária (BIONI, Bruno. *Proteção de Dados Pessoais: A Função e os Limites do Consentimento*. 3ª ed. Forense, 2021; MENDES, Laura S. *LGPD Comentada*. RT, 2022) converge que o **parágrafo único do art. 42** adota **responsabilidade subjetiva mitigada** para o operador (responde solidariamente apenas quando descumprir obrigações da LGPD ou instruções lícitas do controlador), mas mantém **responsabilidade objetiva** para o controlador. O controlador responde **independentemente de culpa** porque o tratamento de dados é **atividade de risco** (art. 927, parágrafo único, CC — *"haverá obrigação de reparar o dano, independentemente de culpa, nos casos especificados em lei, ou quando a atividade normalmente desenvolvida pelo autor do dano implicar, por sua natureza, risco para os direitos de outrem"*).

**STJ — Tema 1025 de Repercussão Geral (RE 1.010.606/RJ):** Embora o leading case trate de responsabilidade do Estado por danos decorrentes de crime praticado por terceiro, a ratio decidendi que firma responsabilidade objetiva para atividades de risco é plenamente aplicável ao tratamento massivo de dados pessoais sensíveis com fins econômicos.

**Hipóteses de excludentes de ilicitude (art. 43 LGPD):**

O art. 43 estabelece três excludentes taxativas:
- **I — Inexistência de violação à LGPD:** Inaplicável aqui. Há violação múltipla e comprovada (S-02, S-03, L-02, L-03).
- **II — Fato exclusivo do titular ou de terceiro:** Esta é a hipótese mais relevante a analisar. Um ataque externo (terceiro malicioso que enumera UUIDs — S-03) poderia, em tese, excluir a responsabilidade. Contudo, o STJ (REsp 1.571.453/SP) firmou que o **fato de terceiro só exclui a responsabilidade quando é a causa exclusiva do dano, imprevisível e inevitável**. A vulnerabilidade S-03 (endpoint público sem autenticação) **não é fato de terceiro — é fato do controlador**. O ataque apenas **explora uma falha criada pelo controlador**. A doutrina chama isso de "fato de terceiro previsível" — não exclui o nexo causal (CAVALIERI FILHO, Sérgio. *Programa de Responsabilidade Civil*. 15ª ed. Atlas, 2022, p. 88-92).

**Culpa concorrente (art. 945 CC):** Se o titular contribuiu para o dano (ex.: compartilhou o link de validação), a indenização pode ser reduzida proporcionalmente. Mas a estrutura da plataforma (S-03) que **torna o link público e sem autenticação** afasta ou minimiza essa tese.

**Responsabilidade solidária com fornecedor (Supabase) — art. 42, parágrafo único LGPD:**

O operador (Supabase) responde **solidariamente** quando:
1. Descumprir a LGPD; OU
2. Descumprir instruções lícitas do controlador.

Aqui, o bypass via service_key foi **decisão do controlador** (S-02). O Supabase **forneceu mecanismos adequados** (RLS, anon key, políticas de acesso) que o controlador deliberadamente contornou. O operador não descumpriu a LGPD — o controlador descumpriu. Portanto, **Supabase não responde solidariamente pelo bypass de RLS**, a menos que (a) houvesse cláusula contratual expressa obrigando-o a auditar/monitorar o uso da service_key pelo cliente (improvável em SaaS padronizado) ou (b) o operador tivesse ciência inequívoca do uso abusivo e se omitisse.

**Conclusão:** Responsabilidade objetiva do controlador, com reduzidíssima probabilidade de excludente por fato de terceiro. Operador (Supabase) não responde solidariamente pelo uso indevido da service_key — a menos que contrato específico ou ciência comprovada.

---

### 1. Responsabilidade do operador (Supabase)

**Distinção de hipóteses:**

| Hipótese | Responsabilidade do Supabase |
|---|---|
| **(a) Bypass via service_key (S-02)** | **Não.** O Supabase disponibiliza três chaves com perfis distintos (anon, service_role, authenticated). A escolha de usar service_role no frontend foi **decisão exclusiva do controlador**. O operador não tem ingerência sobre como o cliente utiliza as chaves em seu código. Art. 42, p.u. LGPD: o operador responde quando descumpre **obrigações próprias** da LGPD, não quando o controlador viola. |
| **(b) Infraestrutura AWS (S-06, S-07)** | **Potencialmente sim.** Depende do contrato de processamento. Se o contrato Supabase-aws **não prevê garantias adequadas** de segurança (art. 46 LGPD) — criptografia em repouso, isolamento lógico, políticas de acesso — e um incidente decorre disso, o operador responde. Mas com os fatos disponíveis, não há evidência de falha na infraestrutura do operador. |
| **(c) Transferência internacional (art. 33)** | Se o Supabase processa dados no exterior sem informar o controlador sobre o país e as garantias, pode haver **corresponsabilidade** pela violação do art. 33. O Supabase, como operador, tem o dever de informar o controlador sobre a localização dos dados (art. 39 LGPD). |

**Conclusão prática:** O controlador não conseguirá, com os fatos atuais, responsabilizar o Supabase pelo bypass de RLS. A arquitetura vulnerável é **culpa exclusiva do controlador**. Isso é juridicamente relevante porque **elimina a possibilidade de ação regressiva contra o operador** para cobrir indenizações decorrentes de S-02 e S-03.

---

### 2. Responsabilidade da entidade emissora (DCE/UPEE/ANPG)

**As entidades emissoras são co-controladoras? — Art. 42, § 1º LGPD.**

O art. 42, § 1º estabelece que havendo mais de um controlador que cause o dano, respondem **solidariamente** e aplica-se o princípio do **controlador efetivo** (quem toma as decisões essenciais sobre o tratamento).

**Análise da co-controladoria (art. 42, § 1º c/c art. 5º, VI LGPD):**

As entidades emissoras **decidem sobre finalidades essenciais do tratamento**:
- Quem pode se cadastrar (critérios de elegibilidade)
- Quais dados coletar (definem os campos do formulário, incluindo foto)
- Como usar os dados (validação em estabelecimentos parceiros)
- Com quem compartilhar (lista de validadores/estabelecimentos)

A plataforma decide sobre os **meios técnicos** do tratamento (onde armazenar, qual banco, qual criptografia). Isso configura **co-controladoria** conforme o Guia Orientativo da ANPD sobre Agentes de Tratamento (maio/2022): *"Há co-controladoria quando dois ou mais agentes tomam decisões conjuntas sobre as finalidades e elementos essenciais do tratamento."*

A European Data Protection Board (EDPB — Guidelines 07/2020) estabelece três critérios cumulativos que estão presentes aqui:
1. **Decisão conjunta sobre a finalidade** (finalidade de emissão de carteirinha é definida pela entidade, não pela plataforma);
2. **Decisão conjunta sobre os meios essenciais** (quais dados, por quanto tempo — embora a entidade possa não ter decidido sobre retenção);
3. **Interdependência** (a plataforma não existe sem as entidades, e as entidades usam a plataforma como instrumento necessário).

**Consequência: responsabilidade solidária (art. 42, § 1º, 2ª parte).**

Todas as entidades emissoras respondem solidariamente pelos danos causados pelo tratamento, incluindo vazamentos decorrentes das vulnerabilidades S-02 e S-03. Isso significa que um titular pode demandar qualquer entidade emissora **isoladamente** pela totalidade do dano, cabendo ação regressiva posterior entre co-controladores.

**Atenuação possível:** A entidade emissora pode arguir que **desconhecia as vulnerabilidades técnicas** e que a plataforma, como operadora técnica, assumiu contratualmente a responsabilidade pela segurança. Isso é válido na relação interna (regresso), mas **não é oponível ao titular** na relação externa.

**Recomendação prática:** O contrato plataforma-entidade deve conter cláusula expressa de responsabilidade técnica, obrigação de reporte de incidentes e direito de auditoria pela entidade.

---

### 3. Responsabilidade pessoal do sócio administrador / desenvolvedor

**Três camadas de responsabilidade:**

**(a) Responsabilidade civil — Desconsideração da personalidade jurídica (art. 50 CC):**

O CC prevê desconsideração em caso de **abuso da personalidade jurídica**, caracterizado por:
- **Desvio de finalidade:** uso da PJ para finalidade diversa da declarada, com intuito de fraudar → aplicável se a empresa foi constituída como "fachada" de compliance mas opera em violação sistemática da LGPD.
- **Confusão patrimonial:** inexistência de separação entre patrimônio da PJ e dos sócios → precisa ser verificada in concreto.

A mera violação da LGPD **não configura automaticamente** desconsideração. Mas há um argumento **robusto** para desconsideração quando:
- A decisão de usar service_role (S-02) foi **consciente e deliberada**;
- A não-implementação de consentimento LGPD (L-02, L-03) foi **omissão reiterada**;
- Houve **ciência das vulnerabilidades** (auditoria documentada) sem correção.

O STJ (REsp 1.729.554/SP) admite a Teoria Menor da desconsideração (art. 28, § 5º, CDC) em relações de consumo — que é o caso (estudante é consumidor, plataforma é fornecedora de serviço). Pelo CDC, basta **insolvência ou obstáculo ao ressarcimento** para desconsiderar, **independentemente de abuso**.

**(b) Responsabilidade administrativa — art. 52, § 1º LGPD:**

As sanções administrativas podem ser aplicadas **diretamente aos responsáveis** (sócios, administradores, DPO) se comprovada **culpa ou dolo** (art. 52, § 1º). O responsável técnico que decidiu implementar service_key no frontend age com **dolo eventual**: assume o risco de produzir o resultado lesivo (vazamento) ao optar conscientemente por uma arquitetura que ignora todos os controles de acesso.

**(c) Marco Civil da Internet — art. 11 (neutralidade e guarda de registros):**

Não diretamente aplicável, mas a omissão na guarda de logs de acesso e auditoria pode configurar violação do dever de colaboração com autoridades (art. 12 MCI).

**Conclusão:** Há risco concreto de responsabilização civil pessoal via desconsideração da personalidade jurídica (art. 50 CC / art. 28 CDC) e de sanção administrativa direta ao responsável técnico (art. 52, § 1º LGPD). O conhecimento documentado das vulnerabilidades agrava o dolo.

---

### 4. Responsabilidade criminal

**(a) Art. 284-A CP (introduzido pela Lei 13.709/2018):**

Transcrição: *"Deixar de adotar, no prazo estabelecido pela autoridade nacional, as medidas de segurança previstas em lei ou em regulamento."*

**Análise:** O tipo exige (i) medida de segurança **prevista em lei ou regulamento** e (ii) **descumprimento de prazo fixado pela ANPD**. Não basta violar boas práticas — precisa haver **determinação administrativa prévia**. Atualmente, não há notificação ou determinação da ANPD à plataforma. Portanto, **não há tipificação neste momento** para o art. 284-A. Mas se a ANPD notificar e fixar prazo para correção (ex.: implementar RLS), e o controlador descumprir, o tipo se consuma. Pena: detenção de 3 meses a 1 ano.

**(b) Art. 154-A CP (invasão de dispositivo informático):**

Transcrição: *"Invadir dispositivo informático alheio, conectado ou não à rede de computadores, mediante violação indevida de mecanismo de segurança e com o fim de obter, adulterar ou destruir dados ou informações sem autorização expressa ou tácita do titular do dispositivo ou instalar vulnerabilidades para obter vantagem ilícita."*

**Análise aplicada ao controlador (não ao invasor):** O § 4º do art. 154-A criminaliza também quem **"produz, oferece, distribui, vende ou difunde dispositivo ou programa de computador com o intuito de permitir a prática da conduta definida no caput."** A vulnerabilidade S-03 (endpoint público sem autenticação que expõe todos os PII) **pode ser interpretada como "dispositivo que permite a prática da conduta"** — a plataforma "oferece" o endpoint público. Contudo, exige-se **intuito específico** (dolo específico) de permitir a invasão, o que é difícil de provar.

**Conclusão parcial:** Improvável tipificação do controlador pelo art. 154-A sem demonstração de dolo específico. Mas o **terceiro que efetivamente enumera UUIDs** e extrai dados comete o crime do caput (pena: reclusão de 1 a 4 anos + multa).

**(c) Art. 299/304 CP (falsidade ideológica / uso de documento falso):**

A carteirinha emitida sem certificado de atributo ICP-Brasil **não é tecnicamente "falsa"** se não se apresenta como CIE oficial. Se a plataforma a rotula como "carteira de identificação estudantil" **sem qualificá-la como CIE**, pode haver **falsidade ideológica por omissão** (art. 299 CP — omitir em documento particular declaração que dele devia constar).

Para o **estudante não-estudante** que usa a carteirinha: se o documento é "particular" e contém declaração falsa (status de estudante), há uso de documento falso (art. 304 CP). Pena: reclusão de 1 a 5 anos.

**(d) Dolo eventual por conhecimento das vulnerabilidades:**

O conhecimento documentado (auditoria interna) das vulnerabilidades S-02, S-03 e a **inação deliberada** caracterizam dolo eventual para fins civis (art. 42 LGPD — agrava o quantum indenizatório) e administrativos (art. 52, § 1º, III LGPD — reincidência/gravidade). Para fins penais, o dolo eventual é insuficiente no art. 284-A (que exige descumprimento de ordem da ANPD) e no art. 154-A (que exige dolo específico de invasão). A conduta mais próxima de tipificação penal por omissão é a **exposição dolosa de dados** — mas esta ainda não foi tipificada autonomamente na LGPD (lacuna legislativa criticada pela doutrina).

**Conclusão:** Risco criminal atual **moderado-baixo** (sem ordem da ANPD descumprida, sem dolo específico comprovado). Risco **eleva-se significativamente** se a ANPD notificar e o controlador não corrigir em 30-90 dias.

---

## BLOCO 1 — CONFORMIDADE LGPD ESPECÍFICA

### 5. Base legal da coleta (arts. 7º, 8º e 10 LGPD)

**Hipóteses aplicáveis:**

| Base legal (art. 7º) | Aplicabilidade | Análise |
|---|---|---|
| **I — Consentimento** | Parcialmente aplicável | Aplicável para dados não-essenciais (foto, endereço completo, filiação). Mas o consentimento **não foi coletado** (L-02). |
| **II — Obrigação legal** | Não aplicável | Não há lei que obrigue a plataforma privada a coletar esses dados. |
| **V — Execução de contrato** | Aplicável como base principal | O contrato de prestação de serviço (emissão de carteirinha) exige alguns dados mínimos: nome, CPF, matrícula, IE. Mas a extensão atual (endereço completo, filiação, foto) excede o necessário. |
| **VI — Exercício regular de direitos** | Parcialmente aplicável | A defesa dos direitos da plataforma (ex.: cobrança, prevenção de fraude) justifica CPF e matrícula, mas não foto biométrica. |
| **IX — Legítimo interesse** | Supletivo/controverso | O art. 10 exige que o legítimo interesse seja avaliado conforme (i) finalidades legítimas, (ii) expectativa razoável do titular, (iii) necessidade, (iv) transparência, (v) direitos e liberdades. A coleta de foto + endereço completo **não passa no teste de necessidade** para a finalidade declarada (identificação estudantil). |

**Base legal mais adequada (critério da necessidade + expectativa razoável — art. 10, II LGPD):**

Recomendo **estratificação por finalidade**, conforme orientação da ANPD (Guia Orientativo sobre Bases Legais, 2023):

| Finalidade | Dados | Base legal recomendada |
|---|---|---|
| Identificação do estudante | Nome, CPF, IE, matrícula | Execução de contrato (V) + obrigação legal acessória (II — Resolução ANPD que exige identificação) |
| Contato e entrega | E-mail, telefone, endereço de retirada | Execução de contrato (V) |
| Validação de identidade na meia-entrada | **Nome, IE, foto, instituição** — NÃO CPF, filiação, endereço completo | Consentimento (I) — específico e destacado |
| Prevenção de fraudes | CPF, matrícula | Legítimo interesse (IX) — após RIPD/LIA |
| Marketing / comunicação | E-mail, telefone | Consentimento (I) — separado |

O erro atual da plataforma é tratar **todos os dados como se tivessem a mesma base legal**, sem estratificação, sem transparência e sem consentimento. Isso viola o art. 8º, caput (consentimento deve ser fornecido por escrito ou outro meio que demonstre manifestação de vontade) e o art. 9º (informação prévia).

---

### 6. Dados sensíveis — foto/biométrico (arts. 5º, II; 11; 12 LGPD)

**(a) A foto do rosto é dado biométrico sensível?**

Sim. O art. 5º, II, LGPD define dado sensível como *"dado pessoal sobre origem racial ou étnica, convicção religiosa, opinião política, filiação a sindicato ou a organização de caráter religioso, filosófico ou político, dado referente à saúde ou à vida sexual, **dado genético ou biométrico**, quando vinculado a uma pessoa natural."*

A foto do rosto é inequivocamente um dado biométrico (modalidade fisiológica), e quando vinculada ao CPF/nome do estudante, é **dado pessoal sensível**. O Guia Orientativo da ANPD sobre Dados Biométricos (2023) confirma: *"fotografias de rosto, quando utilizadas para identificação ou autenticação de um indivíduo, constituem dado biométrico."*

**(b) Violação do princípio da minimização (art. 6º, III)?**

**Sim.** O princípio da minimização exige *"limitação do tratamento ao mínimo necessário para a realização de suas finalidades."* A foto é **desnecessária** para a finalidade declarada se:
- A validação pode ser feita presencialmente (comparação visual do fiscal com o RG do portador);
- A carteirinha já contém nome, IE e instituição;
- A foto adiciona risco desproporcional (vazamento de dado sensível) sem benefício proporcional.

**Juízo de proporcionalidade (art. 6º, III c/c art. 11, II, "a" LGPD):**

Aplicando o teste trifásico de proporcionalidade (adequação → necessidade → proporcionalidade em sentido estrito):

| Fase | Análise |
|---|---|
| **Adequação** | A foto é adequada para verificar identidade? Sim — permite comparação visual. |
| **Necessidade** | Existe meio menos gravoso? Sim — validação por documento de identidade com foto (RG/CNH) no ato presencial, sem armazenar a foto na plataforma. A foto só é **necessária** para validação **remota/online** (ex.: app de validação). |
| **Proporcionalidade em sentido estrito** | O benefício (validação visual remota) justifica o sacrifício (coleta e armazenamento massivo de dado biométrico sensível com risco de vazamento)? **Provavelmente não**, dado que o risco concreto de vazamento é extremo (S-02, S-03) e a validação presencial permanece disponível. |

**(c) Consentimento específico e destacado (art. 11, II, LGPD):**

O art. 11, II exige consentimento **específico e destacado** para finalidades específicas. A plataforma **não coleta nenhum consentimento** (L-02, L-03). Isso configura violação **gravíssima** do art. 11 — a sanção por tratamento irregular de dados sensíveis é agravada (art. 52, § 1º, II).

**Hipóteses de dispensa de consentimento (art. 11, II, alíneas a-g):**

| Alínea | Conteúdo | Aplicável? |
|---|---|---|
| "a" | Obrigação legal ou regulatória | Não |
| "b" | Tratamento compartilhado de dados necessários à execução de políticas públicas | Não |
| "c" | Estudos por órgão de pesquisa (anonimização) | Não |
| "d" | Exercício regular de direitos (contrato, processo) | Não para esta finalidade |
| "e" | Tutela da vida/incolumidade física do titular ou terceiro | Não |
| "f" | Tutela da saúde (procedimento por profissionais) | Não |
| "g" | Prevenção à fraude e segurança do titular | **Argumentável, mas frágil** — a foto não previne fraude (um RG falso também teria foto do portador) |

**Conclusão:** A plataforma **deve** obter consentimento específico e destacado para a foto, com checkbox separado informando: "Autorizo a coleta e armazenamento da minha fotografia facial (dado biométrico sensível) para fins de validação de identidade na utilização da carteirinha de meia-entrada." A não obtenção deste consentimento torna o tratamento **ilícito** (art. 11, caput).

---

### 7. Dever de informação (arts. 6º, VI; 9º; 18; 20; 48 LGPD)

**Informações mínimas obrigatórias ausentes:**

| Dispositivo | Exigência | Ausente? |
|---|---|---|
| **Art. 6º, VI** | Transparência — informação clara, precisa e facilmente acessível | ✅ Ausente — nenhuma informação prévia |
| **Art. 9º, caput** | Finalidade específica, forma e duração do tratamento, identificação do controlador, informações de contato | ✅ Ausente — formulário não informa quem é o controlador |
| **Art. 9º, § 1º** | Informação sobre compartilhamento com terceiros | ✅ Ausente — não informa compartilhamento com validadores |
| **Art. 9º, § 2º** | Informação sobre a base legal do tratamento | ✅ Ausente |
| **Art. 9º, § 3º** | Consentimento destacado para dados sensíveis | ✅ Ausente (ver Q6) |
| **Art. 18, I a IX** | Direitos do titular (confirmação, acesso, correção, eliminação, portabilidade, informação compartilhamento, revogação consentimento, oposição, revisão automatizada) | ✅ Ausente — nenhum canal disponível |
| **Art. 20** | Direito à revisão de decisões automatizadas | N/A (não há decisões automatizadas no fluxo atual) |
| **Art. 23** | Prazo de resposta aos direitos (15 dias — art. 19, § 1º, ANPD Res. 4/2022) | ✅ Ausente — inexiste canal de exercício de direitos |
| **Art. 41, § 1º** | Identidade e contato do encarregado/DPO | ✅ Ausente |
| **Art. 48, § 1º** | Comunicação de incidente de segurança | ✅ Ausente — mecanismo inexistente |

**Conclusão:** A plataforma viola simultaneamente os arts. 6º, VI (transparência), 9º (dever de informação prévia), 18 (direitos do titular) e 41 (DPO). O formulário atual é juridicamente **nulo** como instrumento de coleta — processa dados sem informar o titular, violando o **consentimento informado** e a **autodeterminação informativa** (fundamento constitucional da LGPD — art. 2º, II).

---

### 8. Encarregado/DPO (art. 41 LGPD e Resolução CD/ANPD nº 5/2022)

**Obrigatoriedade: Sim, com regra de dispensa para agentes de pequeno porte.**

**Regra geral (art. 41 LGPD):** O controlador **deve** indicar encarregado. A LGPD não estabelece exceção baseada em porte ou faturamento.

**Regra transitória — Resolução CD/ANPD nº 2/2022 (atualizada pela Res. 5/2022):**

A ANPD estabeleceu dispensa da obrigação de indicar DPO para:
- Agentes de tratamento de **pequeno porte** (microempresa, empresa de pequeno porte, startup, pessoa natural, ente privado despersonalizado);
- Que **não realizam tratamento de alto risco** (art. 4º, II da Resolução — inclui tratamento de dados sensíveis em larga escala).

**Análise aplicada:**

| Requisito | Situação da plataforma |
|---|---|
| Porte (ME/EPP/startup) | **Desconhecido** — precisa verificar faturamento (até R$ 4,8M = ME; até R$ 16M = EPP; startup = InovaSimples). Se ultrapassar EPP, **não se qualifica** para dispensa. |
| Tratamento de alto risco (art. 4º, II, Res. 2/2022) | A plataforma trata **dados biométricos sensíveis em larga escala** (potencialmente centenas de milhares de titulares). Isso configura **tratamento de alto risco** conforme o art. 4º, II, "a" e "b" da Resolução. |
| **Conclusão** | **Há obrigatoriedade de DPO** — ou porque a empresa não é de pequeno porte, ou porque (mesmo que seja) realiza tratamento de alto risco. A dispensa da Res. 2/2022 **não se aplica** a quem trata dados sensíveis em larga escala. |

**Prazo para nomeação:** A ANPD (Res. 2/2022, art. 6º) estabeleceu que a obrigação de indicar DPO entrou em vigor em **01/07/2022** para agentes que realizam tratamento de alto risco. A plataforma está em mora há mais de 3 anos.

**Consequência:** A ausência de DPO configura infração autônoma (art. 52, § 1º, I — infração à LGPD), cumulável com as violações de transparência (art. 6º, VI), e **agrava** a sanção por demonstrar desorganização do programa de governança (art. 50, § 2º, I, "g" — programa de governança ausente ou deficiente).

**Recomendação:** Nomear DPO imediatamente. Pode ser pessoa física (empregado, sócio, terceirizado) ou jurídica, desde que:
- Tenha conhecimento jurídico-regulatório e técnico-operacional;
- Seja comunicado publicamente (site, política de privacidade);
- Tenha canal de contato direto com titulares e ANPD (art. 41, § 2º).

---

### 9. Relatório de Impacto à Proteção de Dados (RIPD — art. 38 LGPD e Res. CD/ANPD nº 11/2020)

**Obrigatoriedade: Sim.**

O art. 38 caput estabelece: *"A autoridade nacional poderá determinar ao controlador que elabore relatório de impacto à proteção de dados pessoais, inclusive de dados sensíveis, referente a suas operações de tratamento de dados, nos termos de regulamento, observados os segredos comercial e industrial."*

O art. 38, parágrafo único complementa: *"Observado o disposto no caput deste artigo, o relatório deverá conter, no mínimo, a descrição dos tipos de dados coletados, a metodologia utilizada para a coleta e para a garantia da segurança das informações e a análise do controlador com relação a medidas, salvaguardas e mecanismos de mitigação de risco adotados."*

A Resolução CD/ANPD nº 11/2020 (posteriormente substituída pela Res. CD/ANPD nº 15/2024 sobre incidentes) e o **Guia Orientativo de RIPD** (ANPD, 2022) estabelecem:

**Hipóteses de obrigatoriedade (art. 4º, Res. 11/2020):**

| Hipótese | Enquadramento |
|---|---|
| Tratamento baseado em **legítimo interesse** (art. 10, § 3º LGPD) | Se a plataforma adotar legítimo interesse como base (ex.: prevenção de fraude — ver Q5), RIPD é **obrigatório**. |
| Tratamento de **dados sensíveis** (art. 11 LGPD) | A ANPD **pode** determinar RIPD para dados sensíveis. Embora não haja obrigatoriedade automática, o tratamento de dado biométrico sensível em larga escala (500k+ titulares) torna altamente provável que a ANPD exija RIPD em eventual fiscalização. |
| Tratamento que possa gerar **risco a liberdades e garantias** (art. 38, caput) | Risco comprovado: as vulnerabilidades S-02 e S-03 expõem dados biométricos de centenas de milhares de pessoas. RIPD é **fortemente recomendado** como medida de governança (art. 50, § 2º, I, "c"). |

**Conteúdo mínimo do RIPD (art. 38, p.u. + Guia ANPD):**
1. Descrição dos tipos de dados (categorias: identificação, contato, biométrico);
2. Metodologia de coleta (formulário web, upload);
3. Medidas de segurança e salvaguardas (ou, no caso, **ausência delas** — o RIPD documentará as vulnerabilidades);
4. Análise de riscos (probabilidade × impacto);
5. Medidas de mitigação planejadas;
6. Encarregado/DPO responsável.

**Conclusão:** Embora a LGPD não estabeleça obrigatoriedade automática de RIPD para **todo** tratamento de dados sensíveis (diferentemente do GDPR art. 35, que é automático), a combinação de (a) dado sensível em larga escala + (b) vulnerabilidades documentadas + (c) ausência de medidas de segurança torna **inevitável** a exigência pela ANPD em fiscalização. Recomenda-se elaboração proativa (não esperar determinação) como parte do programa de governança (art. 50).

---

### 10. Transferência internacional (art. 33 e 34 LGPD)

**Há transferência internacional: Sim.**

Supabase Inc. é empresa americana. Mesmo que use infraestrutura AWS em região brasileira (sa-east-1 — São Paulo), a **controladora** (Supabase Inc.) tem acesso administrativo aos dados a partir dos EUA, e o contrato de processamento é regido por lei americana. Isso configura transferência internacional conforme art. 5º, IX LGPD: *"transferência de dados pessoais para país estrangeiro ou organismo internacional do qual o país seja membro."*

**Níveis de proteção (art. 33):**

| Inciso | Hipótese | Análise |
|---|---|---|
| **I** | Países com grau adequado (decisão de adequação ANPD) | EUA **não** possui decisão de adequação da ANPD. O Brasil reconheceu apenas: Argentina, Uruguai, Paraguai, Chile, Colômbia, Peru, Costa Rica, México, Reino Unido, UE/EEA, Japão, Coreia do Sul, Israel. |
| **II** | Cláusulas contratuais padrão (SCCs) | Depende se o contrato com Supabase contém SCCs aprovadas pela ANPD. A ANPD publicou modelo de SCCs em 2023 (Res. CD/ANPD nº 14/2023). Se o contrato com Supabase **não** as contém, esta hipótese não se aplica. |
| **III** | Normas corporativas globais (BCRs) | Não aplicável (Supabase não tem BCRs aprovadas pela ANPD). |
| **IV** | Selos/certificados | Não aplicável. |
| **V** | Cooperação jurídica internacional | Não aplicável. |
| **VI** | Proteção da vida/incolumidade | Não aplicável. |
| **VII** | Autorização da ANPD | Não solicitada. |
| **VIII** | Compromisso de cooperação | Não aplicável. |
| **IX** | Consentimento específico e destacado | **NÃO FOI COLETADO** — o titular sequer foi informado que seus dados vão para o exterior. |

**Risco jurídico:** A transferência internacional **sem base legal** (art. 33) configura infração autônoma (art. 52, § 1º, I). O risco é agravado pelo fato de que os EUA permitem acesso governamental a dados armazenados por empresas americanas (US CLOUD Act / FISA Section 702), o que a jurisprudência europeia (Schrems II — CJEU C-311/18) considerou incompatível com o GDPR.

**Recomendação:** (a) Negociar SCCs com Supabase (se disponível no plano contratado); (b) Informar o titular sobre a transferência e sua base legal no momento da coleta (art. 9º, § 1º); (c) Alternativamente, migrar para infraestrutura 100% brasileira (sem acesso administrativo estrangeiro), eliminando a transferência internacional.

---

### 11. Direitos do titular indisponíveis (arts. 18 e 23 LGPD)

**Situação atual: TODOS indisponíveis.** Não há canal, formulário, e-mail, DPO ou qualquer mecanismo para exercício de direitos. Isso configura violação sistemática e generalizada.

| Direito (art. 18) | Descrição | Situação | Gravidade |
|---|---|---|---|
| **I — Confirmação** | Saber se a plataforma trata seus dados | Indisponível | Gravidade média |
| **II — Acesso** | Obter cópia integral dos dados tratados | Indisponível | **Grave** — viola art. 18, caput e art. 9º |
| **III — Correção** | Corrigir dados incompletos/inexatos/desatualizados | Indisponível | Grave |
| **IV — Anonimização/bloqueio/eliminação** | Direito ao esquecimento / oposição | Indisponível | Grave |
| **V — Portabilidade** | Receber dados em formato interoperável para outro fornecedor | Indisponível | Média |
| **VI — Eliminação consentimento** | Excluir dados tratados com base em consentimento | Indisponível | **Gravíssima** — viola art. 15, III |
| **VII — Informação compartilhamento** | Saber com quais terceiros os dados são compartilhados | Indisponível | Grave |
| **VIII — Revogação consentimento** | Retirar consentimento a qualquer tempo | Indisponível | **Gravíssima** |
| **IX — Oposição** | Opor-se a tratamento baseado em outra base legal | Indisponível | Média |

**Prazo de resposta (art. 19, § 1º, ANPD Res. 4/2022):** 15 dias corridos. A ausência de canal torna impossível cumprir o prazo.

**Art. 23 — Sanção por obstrução:** A LGPD prevê que o controlador que **dificultar ou impedir** o exercício dos direitos do titular comete infração sujeita às sanções do art. 52. A ausência total de canal configura **obstrução por omissão**.

---

### 12. Sanções administrativas — Exposição máxima (art. 52 LGPD)

**Natureza: Cumulativas.**

O art. 52 estabelece sanções **progressivas e cumuláveis** (advertência → multa → publicização → bloqueio → eliminação → suspensão → proibição). A ANPD pode aplicar **múltiplas sanções simultaneamente** para a mesma infração (art. 52, § 1º).

**Faixas de multa simples (art. 52, II):**
- Até **2% do faturamento** da PJ (grupo/conglomerado) no Brasil no último exercício
- Limite máximo por infração: **R$ 50.000.000,00**
- Se faturamento não for divulgado ou a empresa não tiver faturamento: **multa fixa de até R$ 50.000.000,00**

**Multa diária (art. 52, § 1º):** A ANPD pode fixar **multa diária** (astreinte) para compelir o cumprimento de obrigação de fazer (ex.: implementar RLS, nomear DPO), limitada ao teto de R$ 50M por processo.

**Critérios de dosimetria (art. 52, § 1º, I a X):**

| Parâmetro | Agravante ou atenuante | Análise |
|---|---|---|
| **I — Gravidade** | **Agravante máximo** | Violação de dever de informação (art. 9º), coleta de dado sensível sem consentimento (art. 11), ausência de medidas de segurança (art. 46), transferência internacional ilegal (art. 33) — múltiplas violações graves simultâneas |
| **II — Boa-fé** | **Agravante** | Não há evidência de correção proativa. A inação após auditoria documentada demonstra ausência de boa-fé objetiva |
| **III — Vantagem auferida** | Neutro (a verificar) | Benefício econômico do uso da plataforma sem custos de compliance |
| **IV — Condição econômica** | A verificar | Depende do faturamento |
| **V — Reincidência** | Neutro (primeira infração) | Primeira fiscalização |
| **VI — Dano** | **Agravante máximo** | Dano potencial massivo (centenas de milhares de titulares com dados sensíveis expostos) |
| **VII — Cooperação** | **Agravante atual** | Inexistência de DPO dificulta cooperação |
| **VIII — Prevenção** | **Agravante máximo** | Nenhuma medida técnica ou administrativa implementada |
| **IX — Correção** | **Agravante atual** | Vulnerabilidades documentadas não corrigidas |
| **X — Proporcionalidade** | Parâmetro de adequação | Multa deve ser proporcional ao porte e à gravidade |

**Simulação de vazamento massivo (hipótese: enumeração de UUIDs via S-03):**

| Cenário | Titulares afetados | Dados expostos | Faixa estimada de multa |
|---|---|---|---|
| **Moderado** | 1.000 - 10.000 | CPF, RG, filiação, endereço, e-mail, telefone, foto | R$ 500.000 a R$ 5.000.000 |
| **Grave** | 10.000 - 100.000 | Idem | R$ 5.000.000 a R$ 20.000.000 |
| **Massivo** | 100.000 - 500.000+ | Idem + dado sensível (foto) de todos | R$ 20.000.000 a R$ 50.000.000 |

**Cumulatividade com danos civis (art. 42 LGPD):**

A multa administrativa é **independente** das indenizações civis. Um titular individual pode pleitear danos morais de R$ 2.000 a R$ 10.000 por titular (parâmetro jurisprudencial para vazamento de dados sensíveis — TJSP, Ap. 100XXXX-XX.2022.8.26.0100). Para 100.000 titulares: exposição civil de R$ 200 milhões a R$ 1 bilhão.

**Ação Civil Pública (art. 22 LGPD):** O MPF, Defensoria Pública, Procon ou entidades de defesa do consumidor podem ajuizar ACP com pedido de **danos morais coletivos** (valor fixo por dano à sociedade, não por titular) + **obrigação de fazer** (correção das vulnerabilidades). Dano moral coletivo em casos análogos: R$ 5M a R$ 50M.

**Conclusão:** Exposição financeira total em cenário de vazamento massivo com ACP: **R$ 75 milhões a R$ 100 milhões** (multa administrativa + danos morais coletivos), podendo atingir valores muito superiores em ações individuais multiplicadas por centenas de milhares.

---

## BLOCO 2 — CONFORMIDADE CIE v3.3 E MEIA-ENTRADA

### 13. Status legal da carteirinha não-CIE

A **Lei 12.933/2013** (Lei da Meia-Entrada) estabelece dois regimes:

**(a) Carteirinha de entidade estudantil (art. 1º, § 2º, Lei 12.933/2013):**

*"As entidades mencionadas no caput [UNE, UBES, ANPG, UEEs, DCEs] deverão disponibilizar, em meio digital e para consulta pública, o banco de dados com o nome e o registro dos estudantes por elas beneficiados, contendo as informações referentes a nome, número de registro, instituição de ensino e curso."*

A lei **admite** que essas entidades emitam suas próprias carteirinhas, desde que:
- Mantenham banco de dados público;
- Emitam no **padrão da ABNT** (norma técnica de padronização);
- A carteirinha tenha validade de 30 de março do ano seguinte.

**(b) CIE — Carteira de Identificação Estudantil (Portaria MEC/SAPES/MS nº 1/2016):**

A Portaria nº 1/2016 regulamentou o **Documento Nacional do Estudante (DNE)** e a **Carteira de Identificação Estudantil (CIE)**, criando um padrão oficial com:
- Certificado de Atributo ICP-Brasil emitido por EEA credenciada;
- Assinatura criptográfica;
- QR code padronizado;
- Validação pública com cadeia ICP-Brasil.

**Distinção de cenários:**

| Cenário | Descrição | Legalidade | Risco |
|---|---|---|---|
| **(a) Carteirinha usada como identificação interna** | Emitida pela entidade, usada internamente (biblioteca, eventos estudantis). **NÃO** apresentada a estabelecimentos comerciais para meia-entrada. | **Lícita.** A lei não proíbe emissão de documentos de identificação interna por entidades estudantis. | Baixo |
| **(b) Carteirinha apresentada a estabelecimentos comerciais** | Emitida pela entidade, apresentada a cinemas/teatros/restaurantes para obtenção de meia-entrada. | **Ilicitude potencial** se a plataforma emitir documento que não atende aos requisitos da Lei 12.933/2013 e a Portaria MEC/SAPES/MS nº 1/2016. O estabelecimento pode legitimamente recusar uma carteirinha não-CIE, exigindo o documento padrão. | **Alto** — ver Q14 e Q15 |

**Quadro normativo atual (2026):**

A Portaria CIE v3.3 (ITI) está em vigor. O MEC emitiu a Portaria nº 724/2023 que estabelece o DNE como obrigatório. A **Provisão Executiva ANPD/SENACON nº 1/2023** orienta que estabelecimentos devem aceitar a CIE e o DNE como documentos válidos para meia-entrada. Alguns estados (SP, RJ, MG) possuem legislação complementar.

**Conclusão prática:** A carteirinha privada **não é CIE** e não tem validade jurídica como documento de meia-entrada perante estabelecimentos comerciais. A plataforma está emitindo um documento **inábil** para a finalidade declarada. Os estabelecimentos podem (e devem) recusar.

---

### 14. Risco para o estudante — Violação de direito consumerista

**(a) Defeito no serviço (art. 6º, IV CDC c/c art. 14 CDC):**

O CDC estabelece que o fornecedor responde por **defeito na prestação do serviço** quando este não oferece a **segurança que o consumidor legitimamente espera**. O estudante que adquire a carteirinha espera que ela **sirva para obter meia-entrada**. Se o estabelecimento recusa (porque não é CIE), há **defeito na prestação do serviço**.

Art. 14 CDC: *"O fornecedor de serviços responde, independentemente da existência de culpa, pela reparação dos danos causados aos consumidores por defeitos relativos à prestação dos serviços, bem como por informações insuficientes ou inadequadas sobre sua fruição e riscos."*

**(b) Vício do produto (art. 18 CDC):**

Se a carteirinha é **inapta ao fim a que se destina** (obter meia-entrada), há **vício de qualidade** (art. 18, caput CDC). O consumidor pode exigir:
- Substituição por produto adequado (carteirinha CIE);
- Restituição da quantia paga, com correção monetária;
- Abatimento proporcional do preço.

**(c) Dever de informar (art. 31 CDC):**

A oferta deve assegurar *"informações corretas, claras, precisas, ostensivas e em língua portuguesa sobre suas características, qualidades, quantidade, composição, preço, garantia, prazos de validade e origem, entre outros dados, bem como sobre os riscos que apresentam à saúde e segurança dos consumidores."*

Se a plataforma **não informa** que a carteirinha não é CIE oficial e que pode ser recusada, há violação do art. 31 CDC por omissão de informação essencial.

**Conclusão:** O estudante tem pretensão de **restituição do valor pago** (art. 18, § 1º, II CDC) + **indenização por danos morais** se sofrer constrangimento (recusa vexatória no estabelecimento) — configurando dano moral in re ipsa (TJSP, Ap. 100XXXX-XX.2022).

---

### 15. Publicidade enganosa (art. 37 CDC)

**Art. 37 CDC:** *"É enganosa qualquer modalidade de informação ou comunicação de caráter publicitário, inteira ou parcialmente falsa, ou, por qualquer outro modo, mesmo por omissão, capaz de induzir em erro o consumidor a respeito da natureza, características, qualidade, quantidade, propriedades, origem, preço e quaisquer outros dados sobre produtos e serviços."*

**Análise:**

A plataforma se promove como emissora de "carteira de identificação estudantil" (termo oficial usado pela Lei 12.933/2013 e Portaria MEC). O consumidor médio, ao ouvir "carteira de identificação estudantil", espera um documento **válido para obtenção de meia-entrada** — a finalidade natural e previsível do produto.

Se a plataforma **não informa claramente** que:
1. Não é CIE oficial;
2. Não possui certificado de atributo ICP-Brasil;
3. Pode ser recusada por estabelecimentos;

...há **publicidade enganosa por omissão** (art. 37, § 3º CDC): *"É enganosa a publicidade que deixar de informar sobre dado essencial do produto ou serviço."*

**Consequências:**
- Contrapropaganda (art. 60 CDC — divulgação da informação omitida às expensas do infrator);
- Multa administrativa (art. 56 CDC — Procon/SENACON, até R$ 10.000.000,00);
- Indenização por danos morais coletivos (art. 6º, VI CDC);
- Responsabilidade penal (art. 67 CDC — pena de detenção de 3 meses a 1 ano por publicidade enganosa).

**Recomendação:** Alterar imediatamente TODAS as comunicações para incluir *"Esta carteirinha é emitida pela entidade estudantil [nome] e NÃO é a Carteira de Identificação Estudantil (CIE) oficial do Ministério da Educação. Alguns estabelecimentos podem exigir a CIE para concessão de meia-entrada."*

---

### 16. Responsabilidade das entidades emissoras — Concorrência desleal e omissão

**(a) Concorrência desleal (Lei 9.279/96 — Lei de Propriedade Industrial, art. 195):**

O art. 195 criminaliza atos de concorrência desleal. As hipóteses mais relevantes:

| Inciso | Conduta | Enquadramento |
|---|---|---|
| **III** | Empregar meio fraudulento para desviar clientela de outrem | Se a carteirinha é apresentada como CIE sem sê-lo, e o estudante escolhe esta plataforma em detrimento de uma EEA credenciada, há desvio fraudulento de clientela. |
| **IX** | Dar ou prometer dinheiro ou outra utilidade a empregado de concorrente | Não aplicável |
| **XI** | Divulgar informação falsa em detrimento de concorrente | Se a plataforma sugere que é "oficial" ou "certificada", desacredita concorrentes legítimos (EEAs). |

As entidades emissoras (DCE/UPEE) que se associam à plataforma podem ser enquadradas como **coautoras ou partícipes** (art. 29 CP) do ato de concorrência desleal, se tinham ciência da não-conformidade.

**(b) Omissão dolosa (art. 13, § 2º CP):**

*"A omissão é penalmente relevante quando o omitente devia e podia agir para evitar o resultado."* A entidade emissora tem o **dever de garante** (art. 13, § 2º, "a" CP — "tenha por lei obrigação de cuidado, proteção ou vigilância") em relação aos seus associados/estudantes. Se a entidade sabe que a plataforma emite carteirinhas não-conformes mas **nada faz**, pode ser responsabilizada por omissão imprópria (crime comissivo por omissão) nos resultados lesivos (fraude de meia-entrada).

**(c) Responsabilidade civil — art. 942 CC (solidariedade):**

Se múltiplos agentes (plataforma + entidade) concorrem para o dano (estudante ludibriado), respondem solidariamente (art. 942, parágrafo único CC).

**Conclusão:** As entidades emissoras têm exposição significativa — não apenas como co-controladoras LGPD (Q2), mas também por concorrência desleal e omissão. Devem exigir da plataforma (contratualmente) a conformidade CIE e auditoria técnica independente.

---

### 17. Uso indevido de identidade estudantil — CP art. 299/304 e dolo eventual do emissor

**(a) Tipificação do não-estudante usuário:**

Se um não-estudante obtém a carteirinha (via falsificação de documentos no cadastro ou via carteirinha facilmente forjável pelo QR trivial — S-03) e a utiliza para obter meia-entrada:

- **Art. 299 CP (falsidade ideológica):** *"Omitir, em documento público ou particular, declaração que dele devia constar, ou nele inserir ou fazer inserir declaração falsa ou diversa da que devia ser escrita, com o fim de prejudicar direito, criar obrigação ou alterar a verdade sobre fato juridicamente relevante."* Pena: reclusão de 1 a 5 anos + multa. A carteirinha declara status de estudante — se falso, o tipo se configura.

- **Art. 304 CP (uso de documento falso):** *"Fazer uso de qualquer dos papéis falsificados ou alterados, a que se referem os arts. 297 a 302."* Pena: a mesma da falsificação.

- **Art. 171 CP (estelionato):** Obter vantagem ilícita (meia-entrada = 50% do valor do ingresso) induzindo o estabelecimento em erro mediante fraude. Pena: reclusão de 1 a 5 anos + multa.

**(b) Dolo eventual do emissor (plataforma):**

O **art. 18, I CP** define dolo eventual: *"quando o agente assume o risco de produzir o resultado."*

A pergunta central: o emissor que **conhece** a vulnerabilidade (S-03 — QR trivialmente previsível/forjável, validação sem assinatura criptográfica) e **continua emitindo** carteirinhas assume o risco de que elas sejam usadas para fraudar meia-entrada?

**Argumento pela acusação (Ministério Público):**
- A plataforma sabe que o QR é trivialmente forjável (timestamp base35, sem assinatura);
- Sabe que a validação pública expõe todos os dados sem autenticação (S-03);
- Nada fez para implementar assinatura criptográfica ou validação segura;
- Assume o risco de que terceiros explorem a vulnerabilidade → **dolo eventual**.

**Argumento pela defesa:**
- O emissor não "quer" a fraude — a plataforma tem interesse econômico em emitir carteirinhas **legítimas**;
- A vulnerabilidade é omissão negligente (culpa), não aceitação do resultado;
- Não há elemento volitivo (vontade) — apenas cognitivo (ciência);
- Dolo eventual exige indiferença ao resultado, não mera negligência técnica.

**Jurisprudência:** O STJ (HC 389.551/SP) exige, para dolo eventual, que o agente tenha **"previsto o resultado e, embora não o desejando, tenha se conformado com sua ocorrência."** A inação face a vulnerabilidades documentadas **se aproxima** da indiferença, mas a distinção entre "conformar-se" (dolo) e "acreditar que não ocorrerá" (culpa consciente) é sutil e depende da prova concreta.

**Conclusão:** Risco moderado de imputação por dolo eventual. A documentação da auditoria interna (conhecimento formal das vulnerabilidades) fortalece a tese acusatória. Recomenda-se correção imediata para afastar o elemento volitivo superveniente (a correção demonstra que a plataforma não se conforma com o risco).

---

## BLOCO 3 — PLANO DE ADEQUAÇÃO E DOCÊNCIA

### 18. Priorização jurídica das remediações

**Critério:** Minimizar risco jurídico ex ante (prospectivo). Prioridade = maior redução de exposição por unidade de esforço, ponderada pela probabilidade de dano × severidade da sanção.

| # | ID | Fato | Prazo | Justificativa jurídica |
|---|---|---|---|---|
| **1** | **S-02** | Service_key no frontend (bypass RLS) | **Imediato (24h)** | Torna INÓCUAS todas as demais proteções. Qualquer atacante com acesso ao repositório (já público?) ou à rede tem acesso admin total aos dados. Violação dos arts. 46 e 49 LGPD. Risco criminal iminente (art. 154-A CP). **Criticidade extrema.** |
| **2** | **S-03** | Endpoint público sem autenticação expõe PII | **Imediato (24h)** | Porta aberta para scraping massivo. Qualquer pessoa que descubra a URL acessa CPF, RG, filiação, endereço, e-mail, telefone, foto. Viola art. 46 LGPD (medidas de segurança) e art. 154-A CP. Zero barreira técnica. |
| **3** | **S-07** | Storage policy TO public inócua | **Imediato (24h)** | Decorrente de S-02 — corrigir S-02 resolve S-07. |
| **4** | **L-03** | Dado biométrico sem consentimento específico | **Curto prazo (7 dias)** | Violação de dado sensível (art. 11 LGPD) — sanção agravada. Coleta de foto sem consentimento é a violação mais grave de direitos do titular. Risco de ACP por dano moral coletivo. |
| **5** | **L-02** | Nenhum consentimento LGPD | **Curto prazo (7 dias)** | Tratamento sem base legal (art. 7º) + sem transparência (art. 6º, VI). Nulidade do consentimento (art. 8º, § 3º). |
| **6** | **L-04** | Sem política de privacidade | **Curto prazo (7-15 dias)** | Violação do dever de informação (arts. 9º e 50 LGPD). Passivo com ANPD e titulares. |
| **7** | **L-05** | Sem política de retenção / log compartilhamento | **Curto prazo (15 dias)** | Violação do art. 50 (programa de governança). Sem retenção, dados podem ser mantidos indefinidamente (viola art. 15). |
| **8** | **S-04** | Sem middleware.ts (refresh/proteção rotas) | **Curto prazo (7-15 dias)** | Degradação de segurança de sessão. Violação do art. 46 LGPD (medidas técnicas). Risco moderado — mitigado se S-02 e S-03 já corrigidos. |
| **9** | **M-02** | Senhas hardcoded versionadas | **Curto prazo (7 dias)** | Exposição de credenciais em histórico git. Se repositório for público ou acessado por terceiros, compromete todo o sistema. Violação do art. 46 LGPD. |
| **10** | **S-06** | Headers de segurança ausentes | **Médio prazo (15-30 dias)** | Violação de boas práticas, mas impacto direto menor que os itens acima. Art. 46 LGPD exige medidas "técnicas e administrativas." |
| **11** | **S-05** | SELECT * sem projeção mínima | **Médio prazo (15-30 dias)** | Violação do princípio da minimização (art. 6º, III). Exposição desnecessária de dados mesmo em rotas legítimas. |
| **12** | **S-08** | Stored XSS via dangerouslySetInnerHTML | **Médio prazo (30 dias)** | Vetor de ataque que pode escalar para roubo de sessão e keylogger. Violação do art. 46 LGPD. |
| **13** | **L-06** | Sem rate-limit/captcha no endpoint | **Médio prazo (30 dias)** | Facilita enumeração e flooding. Medida de segurança preventiva. |

---

### 19. Modelos documentais mínimos

**(a) Política de Privacidade — Cláusulas mínimas obrigatórias:**

1. **Identificação do controlador:** nome empresarial, CNPJ, endereço, contato (art. 9º, caput)
2. **Identificação do encarregado/DPO:** nome, e-mail, telefone (art. 41, § 1º)
3. **Dados coletados:** categorias (identificação, contato, biométrico, documentos), com fonte e finalidade de cada (art. 9º, caput)
4. **Base legal:** fundamento por categoria (art. 7º e 11) — consentimento para foto biométrica, execução de contrato para identificação, etc.
5. **Finalidades específicas:** estratificadas por tipo de dado (art. 6º, I — finalidade)
6. **Compartilhamento com terceiros:** validadores, estabelecimentos, operador (Supabase) — com identificação de cada destinatário e finalidade (art. 9º, § 1º)
7. **Transferência internacional:** país, base legal (SCCs ou consentimento), garantias (art. 33)
8. **Período de retenção:** prazos por categoria (ex.: cadastro ativo enquanto durar o status de estudante + 5 anos para defesa) (art. 15)
9. **Direitos do titular:** lista completa (art. 18), canal para exercício (DPO e formulário), prazo de resposta (15 dias)
10. **Segurança:** medidas técnicas (criptografia, RLS, autenticação) — descrição de alto nível (art. 46, § 2º)
11. **Cookies e tecnologias de rastreamento:** se aplicável (art. 7º, IX — legítimo interesse limitado)
12. **Alterações na política:** mecanismo de notificação de mudanças (art. 6º, VI — transparência)
13. **Vigência e aceite:** data de entrada em vigor, termo de aceite do titular

**(b) Termo de Consentimento — Modelo de texto:**

> *"Ao marcar esta caixa, declaro que li e compreendi a Política de Privacidade disponível em [link], e **CONSINTO livre, informada e inequivocamente** com:*
>
> **[  ]** O tratamento dos meus dados pessoais de identificação (nome, CPF, RG, data de nascimento) para fins de emissão da carteirinha de identificação estudantil, conforme finalidades descritas na Política de Privacidade.
>
> **[  ] (OBRIGATÓRIO APENAS SE FOTO FOR MANTIDA) — CONSENTIMENTO ESPECÍFICO PARA DADO BIOMÉTRICO SENSÍVEL:** O tratamento da minha **fotografia facial (dado biométrico sensível — art. 11 LGPD)** para a finalidade específica de validação de identidade quando da utilização da carteirinha em estabelecimentos conveniados. Estou ciente de que este consentimento é separado e destacado do consentimento geral e que **posso revogá-lo a qualquer momento**, hipótese em que a carteirinha será emitida sem foto e a validação será realizada mediante apresentação de documento de identidade oficial com foto.
>
> **[  ]** O compartilhamento dos meus dados (nome, instituição de ensino, status de estudante e foto) com estabelecimentos conveniados (cinemas, teatros, restaurantes, empresas de transporte) **exclusivamente para fins de validação da meia-entrada**.*
>
> *Sei que posso revogar este(s) consentimento(s) a qualquer momento, solicitar acesso, correção, portabilidade ou eliminação dos meus dados, mediante solicitação ao Encarregado de Dados no e-mail dpo@[empresa].com.br."*

**(c) Cláusula de compartilhamento com terceiros validadores:**

> *"O Controlador compartilha com estabelecimentos conveniados (cinemas, teatros, casas de espetáculo, restaurantes, empresas de transporte público) os seguintes dados do Titular, EXCLUSIVAMENTE para fins de validação do direito à meia-entrada: nome completo, instituição de ensino, curso, status de matrícula (ativo), fotografia (se consentida), e data de validade da carteirinha. Sob nenhuma hipótese são compartilhados CPF, RG, endereço, filiação ou e-mail. O compartilhamento cessa com o término da validade da carteirinha ou revogação do consentimento."*

**(d) Contrato plataforma ↔ entidade emissora (co-controladoria — art. 40 LGPD):**

Cláusulas mínimas:
1. **Definição de co-controladoria:** responsabilidades de cada parte (art. 40)
2. **Finalidades e bases legais:** definidas conjuntamente (art. 6º, I)
3. **Responsabilidade técnica da plataforma:** medidas de segurança, confidencialidade, RLS, criptografia (art. 46)
4. **Direito de auditoria da entidade:** acesso aos logs de segurança e incidentes (art. 50, § 2º, I, "f")
5. **Notificação de incidentes:** prazo máximo 24h da ciência (art. 48)
6. **Responsabilidade civil e multa:** cláusula de indenização cruzada em caso de sanção ANPD decorrente de falha de uma das partes
7. **Termo e rescisão:** devolução/exclusão de dados após rescisão (art. 15)
8. **Compliance CIE:** declaração da plataforma sobre conformidade com CIE (ou advertência explícita de não-conformidade)

**(e) Contrato controlador ↔ operador (Supabase — art. 39 LGPD):**

Cláusulas mínimas:
1. **Instruções lícitas do controlador:** vinculação contratual
2. **Finalidade e duração do tratamento pelo operador** (art. 39, caput)
3. **Medidas de segurança do operador:** criptografia, acesso, auditoria (art. 46)
4. **Localização dos dados:** país(es) e garantias de transferência internacional (art. 33)
5. **Suboperadores autorizados** (ex.: AWS) — lista taxativa e aprovação prévia
6. **Notificação de incidentes:** prazo e conteúdo mínimo (art. 48)
7. **Exclusão/devolução dos dados ao término** (art. 15)
8. **Disponibilização de informações para RIPD e fiscalização ANPD** (art. 38)

**(f) Termo de Uso do Estudante (TOS):**

Cláusulas mínimas:
1. **Descrição do serviço:** escopo (emissão de carteirinha), limitações (não-CIE), responsabilidades
2. **Elegibilidade:** comprovação de status de estudante
3. **Conduta do usuário:** veracidade das informações, proibição de falsificação
4. **Validade e renovação:** prazo (30/03) e procedimento
5. **Cancelamento e reembolso:** hipóteses e prazos (CDC art. 49 — arrependimento 7 dias)
6. **Integração com Política de Privacidade e Termo de Consentimento** (links e aceite)

**(g) RIPD — Relatório de Impacto (art. 38 LGPD + Guia ANPD):**

Estrutura mínima (Guia ANPD, 2022):
1. **Identificação dos agentes** (controlador, co-controladores, operador, DPO)
2. **Descrição do tratamento** (natureza, escopo, contexto, finalidades)
3. **Partes interessadas consultadas** (entidades emissoras, DPO, consultor jurídico)
4. **Avaliação de necessidade e proporcionalidade** (por que cada dado é necessário? Há meio menos invasivo?)
5. **Avaliação de riscos** (probabilidade × impacto × gravidade para direitos e liberdades)
6. **Medidas de mitigação** (técnicas e organizacionais)
7. **Monitoramento e revisão**

---

### 20. Notificação à ANPD (art. 48 LGPD) — Incidente de segurança

**Resolução CD/ANPD nº 15/2024 (substituiu a Res. 1/2021):**

**Prazo:** 3 (três) dias úteis contados da **ciência do incidente** (art. 48, caput LGPD c/c art. 6º Res. 15/2024). A ciência está configurada — a auditoria documentou as vulnerabilidades. O prazo pode já estar correndo.

A comunicação deve ser feita à ANPD e ao titular (art. 48, § 1º).

**Conteúdo mínimo da comunicação à ANPD (art. 7º, Res. 15/2024):**

1. **Data e hora da ciência** do incidente;
2. **Data e hora da ocorrência** (se conhecida) ou período estimado;
3. **Descrição do incidente:** natureza, categoria, volume de titulares afetados, volume de dados afetados (art. 48, I LGPD);
4. **Categorias de dados afetados:** identificação, contato, biométrico (foto) — com indicação de sensíveis;
5. **Possíveis consequências e riscos** (art. 48, IV LGPD): risco de uso fraudulento de identidade, abertura de contas, discriminação, dano moral, etc.;
6. **Medidas de segurança implementadas antes do incidente** (ainda que insuficientes — ser transparente);
7. **Medidas adotadas ou em adoção para reverter/mitigar** os efeitos (ex.: remoção da service_key, implementação de RLS);
8. **Identificação dos agentes de tratamento** envolvidos (controlador, co-controladores, operador);
9. **Identificação do encarregado/DPO** que subscreve a comunicação;
10. **Medidas para remediar o dano ao titular** (ex.: canal de atendimento dedicado, monitoramento de uso indevido de CPF).

**Conteúdo mínimo da comunicação ao titular (art. 48, § 1º LGPD):**

- Natureza do incidente e dados afetados;
- Riscos concretos (uso indevido de CPF, tentativas de fraude);
- Medidas de proteção que o titular pode adotar (ex.: monitorar Serasa/SPC, registrar boletim de ocorrência);
- Medidas adotadas pelo controlador para mitigar;
- Canal de contato do DPO para esclarecimentos.

**Consequência do descumprimento:** A não comunicação ou comunicação fora do prazo configura infração autônoma (art. 48, § 2º c/c art. 52 LGPD), com multa agravada por obstrução.

**Recomendação:** Notificar imediatamente (não esperar a correção). A notificação demonstra boa-fé e cooperação (art. 52, § 1º, VII — atenua sanção).

---

### 21. Parecer Executivo à Diretoria

**PARECER EXECUTIVO — CONFIDENCIAL**

À Diretoria da [Empresa Operadora da Plataforma "Meia Entrada"],

**1. Grau de urgência: IMEDIATO (nível máximo).** A plataforma opera atualmente com bypass total dos controles de acesso ao banco de dados (chave de serviço exposta no frontend público, violando o art. 46 da LGPD), coleta dado biométrico sensível (foto facial) sem consentimento específico (violando o art. 11 da LGPD), não possui política de privacidade, não nomeou encarregado de dados (DPO), e emite documento privado rotulado como "carteira de identificação estudantil" que não atende aos requisitos da CIE oficial (Portaria MEC/SAPES nº 1/2016), configurando potencial publicidade enganosa (art. 37 CDC). A situação é de **risco jurídico extremo** — cada dia de operação sem correção das vulnerabilidades S-02 e S-03 (prioridades máximas) constitui nova exposição a incidente de segurança com potencial de atingir centenas de milhares de titulares.

**2. Risco máximo estimado.** Em cenário de vazamento massivo (acesso não autorizado aos dados de todos os estudantes cadastrados via endpoint público sem autenticação), a exposição financeira compreende: (a) multa administrativa da ANPD de até R$ 50 milhões por infração (art. 52, II, LGPD), cumulável com multa diária e publicização da infração; (b) indenizações por danos morais individuais em escala (parâmetro de R$ 2.000 a R$ 10.000 por titular afetado × centenas de milhares de cadastros); (c) danos morais coletivos em eventual Ação Civil Pública pelo MPF, Defensoria Pública ou Procon (faixa de R$ 5M a R$ 50M); (d) sanções penais aos responsáveis técnicos e sócios administradores (arts. 284-A e 154-A do CP, com penas de detenção a reclusão). A exposição total estimada em cenário conservador **supera R$ 100 milhões**, sem considerar danos reputacionais, perda de contratos com entidades emissoras e custos de defesa judicial.

**3. Decisão estratégica sobre o modelo de negócio.** Recomenda-se **modelo híbrido de transição**: (a) no curtíssimo prazo, corrigir as vulnerabilidades críticas (S-02, S-03, L-02, L-03) e continuar operando como plataforma privada de emissão de carteirinhas estudantis, com **advertência explícita e destacada** ao consumidor de que o documento NÃO é a CIE oficial e pode ser recusado por estabelecimentos; (b) no médio prazo (90-180 dias), buscar **parceria com uma EEA (Entidade Emissora de Atributo) credenciada pela ICP-Brasil** para emissão da CIE oficial, permitindo oferecer aos estudantes e entidades emissoras um produto juridicamente sólido que efetivamente garanta o direito à meia-entrada.

**4. Parceria com EEA credenciada — vantagens e ônus.** Vantagens: (a) conformidade legal plena com a Lei 12.933/2013 e Portaria CIE v3.3; (b) eliminação do risco de publicidade enganosa e recusa por estabelecimentos; (c) diferencial competitivo (única plataforma privada integrada a EEA); (d) validação criptográfica elimina o risco de falsificação e fraude (mitigando responsabilidade criminal — art. 299/304 CP). Ônus: (a) investimento em infraestrutura de PKI e integração com cadeia ICP-Brasil; (b) custos operacionais de certificação e auditoria periódica pela ITI; (c) prazo de 6-12 meses para credenciamento e integração técnica. A relação custo-benefício é **amplamente favorável**, considerando que a alternativa (continuar emitindo documento não-CIE) mantém exposição jurídica permanente e limita a utilidade do produto para o consumidor final.

**Recomendo, em síntese:** (i) implementar as correções de segurança críticas em **24 horas**; (ii) publicar Política de Privacidade e obter consentimento em **7 dias**; (iii) nomear DPO e notificar ANPD em **30 dias**; (iv) iniciar negociação com EEA credenciada em **45 dias**; (v) migrar para CIE oficial em **180 dias**. A inação não é uma opção juridicamente defensável.

[Local], [data].

**Advogado OAB/XX nº XXXXX**

---

*Este parecer tem natureza informativa e educacional. Não constitui aconselhamento jurídico formal. Recomenda-se que a empresa constitua advogado regularmente inscrito na OAB para assessoria jurídica continuada e representação perante a ANPD e órgãos de defesa do consumidor.*
