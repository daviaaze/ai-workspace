# Política de Privacidade + Termo de Consentimento LGPD

> **Versão:** 1.0 | **Data efetiva:** {{DATA_PUBLICACAO}}
> **Controlador:** {{RAZAO_SOCIAL}}, CNPJ {{CNPJ}}
> **Subprompt:** 01 — Política de Privacidade + Consentimento
> **Alimenta findings:** L-02, L-03, L-04, L-06

---

## 1. Política de Privacidade (`/privacidade`)

### 1.1 Identificação do Controlador

| Campo | Valor |
|---|---|
| **Razão Social** | {{RAZAO_SOCIAL}} |
| **CNPJ** | {{CNPJ}} |
| **Endereço** | {{ENDERECO_CONTROLADOR}} |
| **E-mail** | {{EMAIL_CONTATO}} |

### 1.2 Encarregado (DPO)

A Meia-Entrada designou Encarregado pelo tratamento de dados pessoais, nos termos do art. 41 da LGPD:

| Campo | Valor |
|---|---|
| **Nome** | {{DPO_NOME}} |
| **E-mail** | {{DPO_EMAIL}} |
| **Canal de comunicação** | https://meiaentrada.com.br/contato-lgpd ou pelo e-mail acima |

O Encarregado atende solicitações sobre o tratamento de dados pessoais e exerce a função de ponto de contato com a Autoridade Nacional de Proteção de Dados (ANPD).

### 1.3 Definições

Para os fins desta Política:
- **Titular:** estudante que solicita a Carteira de Identificação Estudantil (CIE), ou responsável legal que consente em seu nome;
- **Controlador:** Meia-Entrada Estudantil, que decide sobre o tratamento de dados pessoais;
- **Co-controladora:** entidade emissora (DCE, UPEE, escola, IES, grêmio) que determina conjuntamente as finalidades do tratamento com o Controlador;
- **Operador:** prestador de serviços que trata dados pessoais em nome do Controlador;
- **Dado pessoal:** qualquer informação relativa a pessoa natural identificada ou identificável (art. 5º, I LGPD);
- **Dado pessoal sensível:** dado sobre origem racial ou étnica, convicção religiosa, opinião política, filiação a sindicato, dado referente à saúde ou à vida sexual, dado genético ou biométrico (art. 5º, II LGPD) — incluindo a **fotografia** coletada para emissão da carteirinha.

### 1.4 Finalidades do Tratamento

A Meia-Entrada trata dados pessoais para as seguintes finalidades:

| Finalidade | Base legal | Categoria de dados |
|---|---|---|
| Emissão da Carteira de Identificação Estudantil (CIE) para exercício do direito à meia-entrada (Lei 12.933/2013) | Art. 7º, II (obrigação legal) e art. 7º, V (execução de contrato) | Identificadores, dados cadastrais, foto |
| Validação da carteirinha por estabelecimentos (consulta ao QR/token) | Art. 7º, V (execução de contrato) | Nome, foto, status, validade, instituição |
| Gestão administrativa da campanha pela entidade emissora (co-controladora) | Art. 7º, V (execução de contrato) | Dados cadastrais, comprovantes |
| Comunicação sobre status do pedido, validade e reemissão | Art. 7º, V (execução de contrato) | E-mail, telefone |
| Cumprimento de obrigações legais e regulatórias | Art. 7º, II (obrigação legal) | Conforme exigido por lei |
| Suporte e atendimento ao titular | Art. 7º, V (execução de contrato) | Dados de contato, registro de interação |
| **Tratamento da fotografia (dado biométrico sensível)** | **Art. 11, I (consentimento específico e destacado)** | **Fotografia** |
| Analytics de produto (PostHog) — em páginas sem dados sensíveis | Art. 7º, I (consentimento) | Dados de navegação anonimizados |

### 1.5 Dados Coletados

#### 1.5.1 Do estudante (titular)

| Categoria | Dados | Obrigatório? | Fonte |
|---|---|---|---|
| Identificadores | CPF, RG, número de matrícula | Sim | Formulário web |
| Dados cadastrais | Nome completo, filiação (nome da mãe/pai), data de nascimento | Sim | Formulário web |
| Contato | E-mail, telefone | Sim | Formulário web |
| Endereço | CEP, rua, número, complemento, bairro, cidade, UF | Condicional (se entrega domiciliar) | Formulário web |
| **Dado sensível** | **Fotografia (biométrico — art. 11 LGPD)** | **Sim, com consentimento específico** | Upload no formulário |
| Comprobatórios | Documento de identificação (frente e verso), comprovante de matrícula/declaração | Sim | Upload no formulário |
| Navegação | IP, user-agent, páginas acessadas, preferências de idioma | Sim (tecnicamente) | Coleta automática |

#### 1.5.2 Da entidade emissora (co-controladora — no painel `admin`)

| Categoria | Dados |
|---|---|
| Identificação | Razão social, CNPJ (quando houver), nome fantasia |
| Representante | Nome, CPF, e-mail, telefone do responsável legal |
| Contrato | Dados do contrato de co-controladora vigente |

### 1.6 Base Legal Detalhada

| Finalidade | Base legal | Fundamento |
|---|---|---|
| Emissão da CIE | Art. 7º, II (obrigação legal) | Lei 12.933/2013 e Portaria CIE v3.3 |
| Validação presencial | Art. 7º, V (execução de contrato) | Contrato entre titular, entidade emissora e Meia-Entrada |
| Gestão pela entidade | Art. 7º, V (execução de contrato) | Contrato de co-controladora |
| Comunicação transacional | Art. 7º, V (execução de contrato) | Contrato com o titular |
| **Fotografia (biométrico)** | **Art. 11, I (consentimento específico e destacado)** | **Consentimento separado — ver Seção 2** |
| Analytics | Art. 7º, I (consentimento) | Consentimento via banner de cookies |

### 1.7 Compartilhamento de Dados

A Meia-Entrada compartilha dados pessoais com as seguintes categorias de terceiros:

| Destinatário | Papel | Dados compartilhados | Fundamento jurídico |
|---|---|---|---|
| **Entidade emissora** (DCE, UPEE, escola, IES) | Co-controladora | Dados cadastrais do estudante vinculado à entidade, foto, comprovantes | Contrato de co-controladora + consentimento do titular |
| **Supabase Inc.** (EUA) | Operador (cloud de banco de dados + storage) | Todos os dados armazenados | Contrato de operador com cláusulas padrão de proteção (SCC) |
| **Vercel Inc.** (EUA) | Operador (hospedagem) | Dados de navegação, cache | Contrato de operador |
| **PostHog Inc.** (EUA) | Operador (analytics) | Dados de navegação anonimizados (não inclui inputs de formulário) | Consentimento + contrato de operador |
| **Provedores de e-mail** ({{EMAIL_PROVIDER}}) | Operador | E-mail, nome | Contrato de operador |
| **Órgãos públicos** (ANPD, PROCON, Ministério Público) | Autoridade | Conforme requisição legal | Obrigação legal (art. 7º, II) |

> **Transferência internacional:** Dados pessoais são armazenados e processados nos Estados Unidos (Supabase, Vercel, PostHog) e eventualmente em outros países onde os operadores mantêm servidores. A Meia-Entrada adota cláusulas-padrão de proteção (Standard Contractual Clauses — SCC) com seus operadores, nos termos dos arts. 33 e 36 da LGPD, como garantia de nível adequado de proteção.

### 1.8 Direitos do Titular (Art. 18 LGPD)

Você (titular) tem os seguintes direitos, que podem ser exercidos a qualquer momento:

| Direito | Descrição | Prazo de resposta |
|---|---|---|
| **Confirmação** | Saber se tratamos seus dados | 15 dias corridos (art. 19, §1º) |
| **Acesso** | Solicitar cópia dos dados tratados | 15 dias corridos |
| **Correção** | Corrigir dados incompletos, inexatos ou desatualizados | 15 dias corridos |
| **Anonimização/ bloqueio** | Solicitar anonimização ou bloqueio de dados desnecessários | 15 dias corridos |
| **Eliminação** | Solicitar exclusão dos dados (salvo hipóteses de guarda legal) | 15 dias corridos |
| **Portabilidade** | Solicitar portabilidade dos dados a outro fornecedor | 15 dias corridos (quando aplicável) |
| **Informação** | Saber com quem compartilhamos seus dados | 15 dias corridos |
| **Revogação do consentimento** | Retirar o consentimento a qualquer momento | Imediato (efeitos prospectivos) |

**Como exercer:** Acesse https://meiaentrada.com.br/direitos ou envie e-mail para {{DPO_EMAIL}} com assunto "Exercício de Direitos LGPD". Se preferir, utilize o canal presencial/telefônico do DPO. Menores de idade devem ser representados pelo responsável legal.

### 1.9 Medidas de Segurança

A Meia-Entrada adota as seguintes medidas técnicas e administrativas para proteger os dados pessoais (art. 46 LGPD):

| Medida | Descrição | Status |
|---|---|---|
| Controle de acesso | Autenticação por sessão com Supabase Auth; RLS no banco de dados | Em implementação (Sprint S0-S1) |
| Criptografia em trânsito | TLS 1.3 em todas as conexões (Vercel + Supabase) | ✅ Ativo |
| Criptografia em repouso | Criptografia do banco de dados (Supabase) | ✅ Ativo |
| Rate limiting | Controle de requisições por IP | Em implementação (Sprint S1) |
| Headers de segurança | CSP, HSTS, X-Frame-Options | Em implementação (Sprint S1) |
| Auditoria de acesso | Log de acesso a dados pessoais | Em implementação (Sprint S2) |
| Gestão de vulnerabilidades | Revisão contínua de dependências e secrets | Em implementação (Sprint S1) |

### 1.10 Retenção e Eliminação

Os prazos de retenção serão definidos na Política de Retenção de Dados (em elaboração — Sprint S2). Em linhas gerais:

| Categoria de dado | Prazo previsto (provisório) |
|---|---|
| Cadastro ativo | Enquanto durar o vínculo estudantil + período definido na política de retenção |
| Fotografia (biométrico) | Conforme política de retenção em elaboração |
| Logs de acesso | Conforme política de retenção em elaboração |
| Registros de consentimento | Pelo menos enquanto durar o tratamento ou conforme obrigação legal |

*Consulte a Política de Retenção completa em /retencao quando publicada (Sprint S2).*

### 1.11 Alterações desta Política

Esta Política pode ser atualizada periodicamente. Alterações substanciais serão comunicadas:
- Na própria página /privacidade, com destaque;
- Por e-mail aos titulares cadastrados (quando o impacto for significativo);
- No formulário de emissão, que exige reconsentimento se a base legal for alterada.

| Versão | Data | Alterações |
|---|---|---|
| 1.0 | {{DATA_PUBLICACAO}} | Versão inicial |

**Hash da versão (SHA-256):** {{HASH_POLITICA}}

### 1.12 Disposições Gerais

- **Menores de idade (art. 14 LGPD):** O tratamento de dados de crianças e adolescentes exige o consentimento específico do responsável legal. O formulário de emissão para menores de 18 anos incluirá etapa adicional de coleta de dados e consentimento do responsável.
- **Foro:** Fica eleito o foro da {{COMARCA}} para dirimir controvérsias sobre esta Política.
- **Legislação aplicável:** Lei 13.709/2018 (LGPD), Lei 12.933/2013 (meia-entrada), Lei 8.078/1990 (CDC), Portaria CIE v3.3 e regulamentações da ANPD.

---

## 2. Termo de Consentimento (Microcopy + Texto Longo)

### 2.1 Checkbox A — Consentimento Geral (Dados Pessoais)

**Texto do checkbox:**
> ☐ Autorizo o tratamento dos meus dados pessoais (nome, CPF, RG, e-mail, telefone, endereço, filiação, data de nascimento, comprovantes) para as finalidades de emissão da Carteira de Identificação Estudantil, conforme descrito na [Política de Privacidade](/privacidade). (Art. 7º, I e V da LGPD)

**Texto longo (modal "Ler mais"):**
> Ao marcar esta opção, você autoriza a Meia-Entrada Estudantil a coletar e tratar seus dados pessoais para emissão da sua Carteira de Identificação Estudantil (CIE), incluindo: identificação (CPF, RG), dados cadastrais (nome, filiação, data de nascimento), contato (e-mail, telefone), endereço (se entrega domiciliar), documentos comprobatórios (comprovante de matrícula, documento de identificação).
>
> **Base legal:** Execução de contrato (art. 7º, V) e consentimento (art. 7º, I).
> **Finalidade:** Emissão e validação da CIE, gestão pela entidade emissora, comunicação sobre o pedido, cumprimento da Lei 12.933/2013.
> **Compartilhamento:** Seus dados serão compartilhados com a entidade emissora (co-controladora) que gerencia sua campanha, e com operadores de infraestrutura (Supabase, Vercel) nos EUA, sob cláusulas contratuais padrão.
> **Prazo:** Conforme Política de Retenção (em elaboração). Seus dados serão mantidos enquanto durar o vínculo estudantil e pelo período adicional definido na política.
> **Retirada do consentimento:** Você pode retirar este consentimento a qualquer momento, entrando em contato com nosso DPO. A retirada não afeta a legalidade do tratamento anterior, mas pode inviabilizar a emissão ou manutenção da sua carteirinha.
> **Direitos:** Você tem direito de acessar, corrigir, excluir e portar seus dados (art. 18 LGPD), com resposta em até 15 dias.

### 2.2 Checkbox B — Consentimento Específico para Fotografia (Dado Sensível)

**Texto do checkbox (destacado, separado):**
> ☐ **Consinto especificamente** com o tratamento da minha fotografia (dado biométrico sensível — art. 11, I da LGPD) para inclusão na Carteira de Identificação Estudantil e validação presencial por estabelecimentos.

**Texto longo (modal "Ler mais") — deve ser visualmente conectado ao checkbox:**
> Sua fotografia é considerada **dado pessoal sensível** pela LGPD (art. 5º, II — dado biométrico). Por isso, exigimos seu consentimento **específico e destacado** para tratá-la.
>
> **Finalidade específica:** Impressão na carteirinha e validação visual por estabelecimentos (cinemas, teatros, eventos) que exigem identificação do beneficiário da meia-entrada.
> **Base legal exclusiva:** Art. 11, I da LGPD (consentimento específico). Não é possível tratar sua foto com base em outra hipótese legal.
> **Armazenamento:** Sua foto fica armazenada em servidores nos EUA (Supabase) com criptografia em trânsito e repouso.
> **Prazo estimado de guarda:** Conforme Política de Retenção (em elaboração). Previsão provisória: retenção durante a validade da carteirinha + período definido na política.
> **Consequência da recusa:** Se você não consentir com o tratamento da foto, **não será possível emitir sua carteirinha**, pois a fotografia é elemento essencial do documento de identificação estudantil (art. 8º, §2º LGPD c/c CDC art. 39 — não configura venda casada, pois é intrínseca ao serviço contratado).
> **Retirada a qualquer momento:** Você pode retirar este consentimento a qualquer momento. A retirada não afeta a legalidade do tratamento anterior, mas a foto será removida e a carteirinha perderá validade (será necessário solicitar reemissão sem foto, se aplicável, ou a carteirinha será cancelada).
> **Consequências da retirada:** Cancelamento da carteirinha vigente, sem direito a reembolso do período restante (a CIE sem foto não atende à finalidade contratada).

### 2.3 Regra de UI para Implementação

```
// Os dois checkboxes DEVEM estar separados (não combinados em um):
// ❌ ERRADO: "Aceito os termos de uso e política de privacidade"
// ✅ CERTO:
//   [ ] Autorizo o tratamento dos meus dados pessoais (consentimento geral)
//   [ ] Consinto especificamente com o tratamento da minha foto (dado sensível)

// O consentimento da foto DEVE ser visualmente destacado:
// - Borda ou fundo diferente
// - Texto explicativo visível (não oculto atrás de "Ler mais")
// - Conexão visual com o texto longo

// Validação:
// - Formulário não submete sem AMBOS checkboxes aceitos
// - Se consentimento da foto for retirado posteriormente:
//   - Foto removida do storage
//   - Carteirinha marcada como cancelada (status: 'removida' ou similar)
//   - Titular notificado por e-mail
```

---

## 3. Canal de Comunicação do DPO (Instruction Copy)

### 3.1 Página `/privacidade` (seção DPO)

> **Encarregado (DPO):** {{DPO_NOME}}
>
> Para exercer seus direitos como titular de dados (art. 18 LGPD), esclarecer dúvidas sobre o tratamento de seus dados pessoais ou reportar incidentes:
>
> **Canal principal:** https://meiaentrada.com.br/contato-lgpd
> **E-mail:** {{DPO_EMAIL}}
> **Prazo de resposta:** até **15 dias corridos** (art. 19, §1º, Resolução ANPD 4/2022)
>
> Ao entrar em contato, informe:
> - Seu nome completo e CPF
> - O direito que deseja exercer (acesso, correção, exclusão, portabilidade, etc.)
> - A entidade emissora responsável pela sua campanha (se souber)

### 3.2 Página `/direitos` (Portal de Exercício de Direitos)

> **Seus Direitos**
>
> Você pode, a qualquer momento:
>
> | Direito | Descrição | Como solicitar |
> |---|---|---|
> | Saber se tratamos seus dados | Solicitar confirmação e visão geral | Selecione "Acesso" |
> | Ver meus dados | Receber cópia de todos os dados que temos sobre você | Selecione "Acesso" |
> | Corrigir dados errados | Solicitar atualização de dados incorretos ou desatualizados | Selecione "Correção" |
> | Excluir meus dados | Solicitar remoção dos seus dados (salvo guarda legal) | Selecione "Eliminação" |
> | Retirar consentimento | Revogar autorizações dadas anteriormente | Selecione "Revogar consentimento" |
> | Portar meus dados | Receber seus dados em formato estruturado para levar a outro serviço | Selecione "Portabilidade" |
>
> **Prazo de resposta:** até 15 dias corridos.
> **Menores de idade:** O responsável legal deve fazer a solicitação em nome do menor.

### 3.3 E-mail automático de confirmação (após solicitação)

> **Assunto:** Recebemos sua solicitação LGPD — {{NUMERO_PROTOCOLO}}
>
> Olá {{NOME_TITULAR}},
>
> Recebemos sua solicitação de exercício de direitos LGPD (protocolo {{NUMERO_PROTOCOLO}}).
>
> **O que você solicitou:** {{TIPO_SOLICITACAO}}
> **Prazo para resposta:** até {{DATA_LIMITE}} (15 dias corridos)
>
> Acompanhe o status: https://meiaentrada.com.br/direitos/{{NUMERO_PROTOCOLO}}
>
> Se você não fez esta solicitação, entre em contato imediatamente com {{DPO_EMAIL}}.
>
> Atenciosamente,
> {{DPO_NOME}} — Encarregado (DPO)
> Meia-Entrada Estudantil

---

## Anexo: Mapeamento para Implementação Técnica

| Componente UI | Tabela DB | Campo-chave | Responsável |
|---|---|---|---|
| Checkbox A (consentimento geral) | `lgpd_consents` | `scope = 'geral'` | Dev frontend |
| Checkbox B (consentimento foto) | `lgpd_consents` | `scope = 'fotografia'` | Dev frontend |
| Política /privacidade | `lgpd_policy_versions` | `version, hash, content` | Dev + Jurídico |
| Canal DPO /contato-lgpd | `lgpd_subject_requests` | `tipo, status, created_at` | Dev fullstack |
| Modal "Ler mais" | — | Conteúdo estático inline | Dev frontend |
| Hash da versão da política | `lgpd_policy_versions.hash` | SHA-256 do markdown | CI pipeline |

---

## Placeholders a Preencher

| Placeholder | Responsável |
|---|---|
| `{{RAZAO_SOCIAL}}` | Cliente (fundador) |
| `{{CNPJ}}` | Cliente |
| `{{ENDERECO_CONTROLADOR}}` | Cliente |
| `{{EMAIL_CONTATO}}` | Cliente |
| `{{DPO_NOME}}` | Cliente (nomear) |
| `{{DPO_EMAIL}}` | Cliente |
| `{{EMAIL_PROVIDER}}` | Dev (definir provedor) |
| `{{COMARCA}}` | Jurídico |
| `{{DATA_PUBLICACAO}}` | Cliente + Dev (definir data de go-live) |
| `{{HASH_POLITICA}}` | CI pipeline (SHA-256 do markdown) |
| `{{NUMERO_PROTOCOLO}}` | Gerado pelo sistema (UUID) |
| `{{TIPO_SOLICITACAO}}` | Dinâmico (do formulário de direitos) |
| `{{DATA_LIMITE}}` | Calculado: created_at + 15 dias |

---

## Disclaimer

*Este texto é rascunho técnico-jurídico para integração em produto digital. Não substitui revisão por advogado regularmente inscrito na OAB. A Meia-Entrada deve constituir assessoria jurídica continuada antes de publicar.*

**Revisão pendente:** [ ] OAB confirmar cláusulas de compartilhamento (especialmente co-controladoria com entidades sem CNPJ); [ ] Confirmar texto de consequência da recusa da foto (art. 8º, §2º); [ ] Validar foro.
