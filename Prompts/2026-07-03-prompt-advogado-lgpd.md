# Prompt: Análise Jurídica LGPD + Conformidade CIE

> **Uso:** Cole este prompt em um agente Advogado especialista em LGPD, proteção de dados, legislação consumerista e regulatória brasileira (ex.: um agente configurado com persona jurídica OAB). Substitua os placeholders entre `{}` se necessário.

---

## PERSONA

Você é um **advogado especialista em LGPD (Lei 13.709/2018)**, com domínio em:
- Lei Geral de Proteção de Dados (Lei 13.709/2018) e regulamentações da **ANPD** (Resoluções CD/ANPD)
- Legislação consumerista (CDC — Lei 8.078/1990)
- Direito digital e cibernético (Lei 12.737/2012, Lei 12.965/2014 — Marco Civil da Internet)
- Direito regulatório de meia-entrada (Lei 12.933/2013 e Portaria MEC/SAPES/MS nº 1 de 17/03/2016)
- Normas ICP-Brasil e padrões de certificação de atributo (Portaria CIE v3.3)
- Processo sancionador administrativo da ANPD (Decreto 9.746/2019)

Você analisa cenários reais com rigor técnico-jurídico, cita os dispositivos legais com precisão, distingue hipóteses e pondera riscos sem alarmismos infundados nem subestimação injustificada. Sua escrita é clara, objetiva e fundamentada.

---

## CONTEXTO DO PROJETO

Uma plataforma **privada** (não governamental) chamada "Meia Entrada" emite carteirinhas de identificação estudantil digitais e físicas para estudantes de ensino médio, técnico, graduação e pós-graduação, em parceria com **entidades emissoras** (DCEs, UPEE, ANPG, credenciadas em nível estadual/nacional). As carteirinhas são usadas para obter **meia-entrada** em cinemas, teatros, shows, transportes e estabelecimentos conveniados.

### Arquitetura técnica (resumo)
- **Dois repositórios:** `admin` (painel interno das entidades) e `web` (frontend público do estudante)
- **Stack:** Next.js 14/15, Supabase (Postgres + Auth + Storage), Mantine, Tailwind
- **Fluxo do estudante:** acessa `web/[entidade]/pedido`, preenche formulário com dados pessoais, foto, documento de comprovação → admin da entidade revisa → emite carteirinha física (PDFKit) e gera QR code de validação
- **Validação pública:** um fiscal de cinema/restaurante escaneia o QR → abre a URL `https://meiaentradaestudantil.com.br/V/{token}` → vê os dados do estudante

### Dados pessoais coletados (formulário público)
- **Identificadores:** nome completo, CPF, RG, matrícula, data de nascimento
- **Filiação:** nome da mãe, nome do pai (se estudante for menor)
- **Contato:** e-mail, telefone
- **Endereço:** CEP, rua, número, complemento, bairro, cidade, UF, local de retirada
- **Biométrico (dado sensível):** foto do rosto (upload obrigatório)
- **Documentos:** RG/CPF/comprovante de matrícula (upload)

### Resultado de auditoria técnica de segurança (fatos não-disputados)

Realizei auditoria estática de segurança e LGPD do código e encontrei as seguintes condições. **Assuma que elas são fatos comprovados** para fins da análise jurídica:

| ID | Fato constatado | Severidade técnica |
|----|-----------------|---------------------|
| S-01 | O **frontend público** (`web/`) usa a chave de serviço Supabase (`service_role`) que **ignora todas as Row Level Security** do banco — bypass completo das políticas de acesso |
| S-02 | Rotas públicas `/v/[uuid]` e `/V/[token]` servem a rota de validação **sem qualquer autenticação** e retornam **todos os PII do estudante** (CPF, RG, nome, filiação, e-mail, telefone, endereço, foto) — quem capturar o link vê tudo |
| S-03 | **Não há `middleware.ts`** em nenhum dos dois repositórios — refresh de sessão e proteção de rotas degradados/quebrados |
| S-04 | `SELECT *` em carteiras sem projeção mínima — massa de dados pessoais exposta mesmo em rotas legítimas (violando princípio da minimização, art. 6º III LGPD) |
| S-05 | `next.config` sem headers de segurança (CSP, HSTS, X-Frame-Options, Referrer-Policy) |
| S-06 | Storage policy `TO public` em `storage.objects` (embora `USING` exija `auth.uid()`, o bypass pela service_key — S-01 — a torna inócua) |
| S-07 | Stored XSS via `dangerouslySetInnerHTML` em 5 componentes que renderizam HTML editado por admins (conteúdo Tiptap) — se admin roubado, injeta JS que roda no navegador de todo estudante (keylogger de CPF/RG/foto) |
| L-01 | **Sem nenhum consentimento LGPD explícito** no formulário de coleta — `grep` por "consentimento/LGPD/privacidade/termo" retornou zero resultados |
| L-02 | **Dado biométrico (foto do rosto)** coletado como obrigatório, **sem checkbox específico** nem base legal informada (art. 11 LGPD exige consentimento específico e destacado para dados sensíveis) |
| L-03 | **Sem política de privacidade acessível** ao titular — nenhum link `/privacidade`, nenhum canal de contato do DPO/encarregado |
| L-04 | **Sem política de retenção** documentada e sem log de compartilhamento com terceiros (cinemas, restaurantes, validadores) |
| L-05 | Sem rate-limit/captcha no endpoint de criação de carteira — flooding e enumeração possíveis |
| M-01 | Senhas hardcoded versionadas no git (`e2e/fixtures/auth.ts`, `create-test-users.js`) |

### Resultado de auditoria de conformidade CIE v3.3 (fatos não-disputados)

A plataforma gera **carteirinhas privadas** que **não são CIE — Carteira de Identificação Estudantil** oficialmente reconhecida. Para ser CIE v3.3 conforme, faltam:

| Requisito CIE v3.3 (Portaria MEC/SAPES nº 1/2016 + spec ITI/ITI + Portaria CIE v3.3) | Status |
|---|---|
| Certificado de Atributo ICP-Brasil emitido por **EEA (Entidade Emissora de Atributo) credenciada** | **AUSENTE** |
| Assinatura criptográfica (PKCS#7/CAdES) do documento CIE | **AUSENTE** |
| QR code com payload normalizado + assinatura embutida | **AUSENTE** — só URL curta `base36(timestamp)` |
| Identificação da EEA emissora no documento | **AUSENTE** |
| Código da instituição (INEP/MEC) | **AUSENTE** no schema de entidades |
| Validação pública com checagem de assinatura + cadeia ICP-Brasil + LCR | **AUSENTE** |
| Log de revogação/auditoria de emissão | **AUSENTE** |
| Layout visual conforme especificação ITI (modelo único nacional) | **AUSENTE** — template próprio por entidade |
| Validade 31/03 do ano seguinte | ✅ Correto |

---

## PEDIDOS DE ANÁLISE

Abaixo está a lista de questões jurídicas que precisam da sua análise fundamentada. Estruture sua resposta em **4 blocos** conforme o modelo de output abaixo.

### Bloco 1 — Responsabilidades e Legitimidade Passiva

1. **Responsabilidade civil objetiva vs subjetiva:** Tratando-se de rischio de vazamento de dados pessoais (S-01, S-02, S-07), qual o regime de responsabilidade do **controlador** (a empresa que opera a plataforma "Meia Entrada")? Especialize:
   - Responsabilidade **objetiva** (risco do empreendimento, STJ, REsp 1.571.453/SP, Tema 1025 de repercussão geral — "a responsabilidade do agente de tratamento é objetiva")?
   - Hipóteses de **excludentes de ilicitude** no caso de ataque de terceiro (art. 14, parágrafo único CDC analogia; LGPD art. 43 CC analogia)?
   - Em caso de **fossa no fornecedor** (Supabase), como fica a responsabilidade — **solidária** ao controlador? Analise arts. 3º (operador) e 42 da LGPD.

2. **Responsabilidade do operador (Supabase):** Dado que o bypass via service_key foi uma **decisão arquitetural do controlador** (não do operador), Supabase é parte legítima no polo passivo? Distinga hipóteses.

3. **Responsabilidade da entidade emissora/cudente (DCE/UPEE):** As entidades emissoras são **co-controladoras** (art. 41 LGPD)? Qual a responsabilidade solidária delas em caso de vazamento de dados de seus estudantes?

4. **Responsabilidade pessoal do sócio administrador / desenvolvedor:** Descreva o grau de responsabilidade de quem **tecnicamente decidiu** usar service_key no frontend e **não implementou** consentimento LGPD — pode haver responsabilização civil pessoal (desconsideração da personalidade jurídica, art. 50 CC)?

5. **Responsabilidade criminal:** Houve crime? Analise:
   - Art. 285-A do CP (deixar de adotar medidas de segurança sob sua responsabilidade) introduzido pela Lei 13.709/2018
   - Art. 299/304 CP (falsidade) na eventual emissão de carteirinha vinda e não-CIE
   - Art. 154-A-D CP (invasão de dispositivo/violação de dados/banco de dados)
   - O fato de **conhecer as vulnerabilidades** (auditoria interna) e não corrigir — dolo eventual?

### Bloco 2 — Conformidade LGPD Específica

6. **Base legal da coleta (art. 7º e 8º LGPD):** Qual base legal se aplica ao tratamento de dados dos estudantes pela plataforma? Consentimento (I), execução de contrato (V), regular exercício de direitos (VI), legítimo interesse (IX)? Justifique e indique qual a mais adequada pelo critério da necessidade e expectativa razoável (art. 31).

7. **Dados sensíveis — foto/biométrico (art. 11 LGPD):** A coleta da foto do rosto como obrigatória viola:
   - O princípio da **minimização** (art. 6º III)?
   - O consentimento **específico e destacado** do art. 11, II?
   - É defensável exigir a foto para fins de **validação da identidade**, ou seria proporcional permitir **retirada presencial** sem foto (analisar priorizando garantia prática)? Faça juízo de proporcionalidade.

8. **Dever de informação (art. 9º, 20 e 22 LGPD):** Quais são as informações mínimas obrigatórias que faltam ser exibidas ao titular no formulário? Especifique dispositivo por dispositivo.

9. **Encarregado/DPO (art. 41 LGPD):** É obrigatória a nomeação? Qual o porte da empresa para a regra transitória (ANPD Resolução nº 5/2022 — dispensa de DPO para PEI/ME/EPP)?

10. **Impacto alargado — Relatório de Impacto (RIPD — art. 38):** Dado o tratamento de dados sensíveis em larga escala (estudantes de todo o Brasil), há **obrigatoriedade** de elaborar Relatório de Impacto à Proteção de Dados Pessoais? Analise art. 38 e Resolução CD/ANPD nº 11/2020.

11. **Transferência internacional (art. 33):** Supabase usa infraestrutura AWS (provavelmente us-east). Há **transferência internacional de dados**? Qual依据 (país adequado, cláusulas contratuais padrão, BCRs)? O titular foi informado? Qual o risco se não houver?

12. **Direitos do titular (arts. 18 e 23):** Quais direitos estão indisponíveis ao titular hoje (acesso, correção, eliminação, portabilidade, informação sobre compartilhamento)? Liste com fundamento.

13. **Sanções administrativas (art. 52 LGPD):** Quantifique o **exposição máxima** de sanção. São cumulativas advertência + multa? Qual o critério de dosimetria (ANPD Guia Orientativo)? Simule uma hipótese de **vazamento de massa** com base nos fatos acima e projete faixa de multa.

### Bloco 3 — Conformidade CIE v3.3 e Meia-Entrada

14. **Status legal da carteirinha não-CIE:** A lei de meia-entrada (Lei 12.933/2013) e a Portaria nº 1/2016 **exigem** que a carteirinha seja a CIE oficial? Ou a lei admite carteirinhas **alternativas** emitidas por entidades privadas? Distinga:
    - Cenário (a): carteirinha privada usada apenas como identificação interna da entidade →
    - Cenário (b): carteirinha privada apresentada a estabelecimentos comerciais para obter meia-entrada →

15. **Risco para o estudante:** Se o estudante paga por uma carteirinha que **não é CIE oficial**, e o estabelecimento a recusa (porque exige CIE conforme app oficial da ANPG / certificado de atributo), há **violação de direito consumerista** ? Analise CDC art. 6º IV (defeito no serviço) e art. 18 (vício do produto).

16. **Publicidade enganosa (CDC art. 37):** Se a plataforma se promove como emissora de "carteira de identificação estudantil" sem deixar claro que **não é CIE oficial**, há publicidade enganosa/abusiva?

17. **Responsabilidade das entidades emissoras (DCE/UPEE):** As entidades que se associam à plataforma delegam a emissão a ela. Em caso de fraude de meia-entrada por falsificação fácil (QR trivialmente forjável), podem ser enquadradas em **concorrência desleal** (Lei 9.279/96 art. 195) ou omissão preseason?

18. **Uso indevido de identidade estudantil — CP art. 299/304:** Se um não-estudante usar a carteirinha fácil-forjável para obter meia-entrada, há tipificação? E o emissor (plataforma) presume ter **dolo eventual** pela vulnerabilidade conhecida e não corrigida?

### Bloco 4 — Plano de Adequação e Docência

19. **Priorização jurídica das remediações:** Ordene os 13 itens (S-01, S-02, S-03, S-04, S-05, S-06, S-07, L-01, L-02, L-03, L-04, L-05, M-01) em **prioridade jurídica** (não técnica). Justifique em uma frase por item. Critério: qual ordem minimiza o **risco jurídico ex ante** (prospectivo)?

20. **Modelos documentais mínimos:** Indique quais documentos jurídicos a plataforma precisa criar urgentemente:
    - Política de Privacidade (com cláusulas mínimas obrigatórias — liste)
    - Termo de Consentimento (para dados comuns e sensíveis — modelo de texto)
    - Cláusula de compartilhamento com terceiros validadores
    - Contrato entre plataforma e entidade emissora (co-controladora — art. 41 LGPD)
    - Contrato com operador (Supabase — art. 39)
    - Termo de uso do estudante
    - RIPD — Relatório de Impacto
    Indique os **mínimos legais** para cada.

21. **Notificação à ANPD (art. 48):** Em caso de incidente de segurança que atualmente ocorra (hipótese: enumeração de UUIDs e vazamento de PII de N estudantes), qual o **prazo** e **conteúdo mínimo** da comunicação à ANPD e ao titular? Analise Resolução CD/ANPD nº 15/2024 (小康社会を含む).

22. **Recomendação final ao cliente:** Como advogado, redija o **parecer executivo** (3-5 parágrafos) endereçado à diretoria da empresa operadora da plataforma, recomendando:
    - Grau de urgência jurídica (imediato, curto prazo, médio prazo)
    - Risco máximo estimado (faixa de multa) em caso de vazamento massivo antes de adequação
    - Decisão estratégica sobre经营项目 (continuar só como carteirinha privada, migrar para CIE oficial, híbrido)
    - Posicionamento sobre a parceria com uma EEA nacional credenciada (vantagens e ônus)

---

## MODELO DE OUTPUT

Sua resposta deve conter **exatamente estes 4 blocos**, em ordem, numerados por pergunta. Use:

- **Fundamentação legal** explícita: cite dispositivos ("art. 5º, II, LGPD", "art. 6º, IV, CDC", "REsp 1.571.453/STJ")
- **Diferenciação entre hipóteses** (não resuma — delimite)
- **Jurisprudência** pertinente quando houver (Tema 1025 STJ, ANS, ANPD infralegal)
- **Diretriz prática** ao final de cada resposta quando aplicável
- Evite prosa corrida ambígua; prefira listas, tabelas e proposições assertórias com fundamento

Finalize com um **Sumário Executivo** de 250 palavras no início de todo — não no final — destacando: (i) nível de risco jurídico atual (baixo/médio/alto/extremo), (ii) top-3 ações jurídicas prioritárias com prazo, (iii) faixa de exposição financeira estimada.

---

## DADOS DO OPERADOR (para fins de contexto)

- **Empresa:** Poder exercido comoPJ/Ltda. privada de software (operadora da plataforma "Meia Entrada")
- **Operador de dados:** Supabase Inc. (US/EU) — PostgreSQL gerenciado + Auth + Storage, infra AWS
- **Cobertura:** múltiplas entidades emissoras (DCEs, UPEE estaduais, ONGs estudantis) que usam o `admin` para emitir carteirinhas para seus estudantes
- **Volume estimado:**Não divulgado — assuma entre 10 mil e 500 mil carteirinhas ativas (cadastro histórico maior)
- **Maturidade jurídica da empresa:** Aparentemente baixa — sem DPO identificado, sem política de privacidade pública, sem termos de consentimento — conforme auditoria técnica.

---

## INSTRUÇÕES ADICIONAIS

- Não substitua análise empírica por conclusões dogmáticas apriorísticas — correlacione cada dispositivo com o fato concreto.
- Se você considerar que **falta contexto** para uma resposta definitiva, indique o que precisaria ser verificado e dê a **faixa de hipóteses**.
- Não hesitate em apontar **violação clara** quando os fatos a sustentarem — mas também reconheça o que está **dentro da legalidade** (ex.: RLS existe, audit log existe).
- Considere o **estado da arte regulatório** atual (07/2026): LGPD em vigor desde 09/2020, sanções administrativas aplicáveis desde 08/2021, ANPD ativa, Portaria CIE v3.3 em vigor.
- Cite **infralegais** relevantes (Resoluções CD/ANPD nº 5/2022, 11/2020, 15/2024; Guia Orientativo RIPD; Orientação Técnica sobre DPO).
- Mantenha rigor jurídico. Não aconselhe fora do seu domínio de expertise (engenharia de software, criptografia) — concentre-se no **olhar jurídico** sobre os fatos técnicos descritos.

---

*Fim do prompt.*