# Contrato de Co-Controladora — Meia-Entrada ↔ Entidade Emissora

> **Versão:** 1.0 | **Data:** {{DATA}}
> **Controlador 1:** {{RAZAO_SOCIAL}} | CNPJ {{CNPJ}}
> **Controlador 2:** {{ENTIDADE_NOME}} | {{ENTIDADE_CNPJ}}
> **Subprompt:** 04 — Contrato de Co-controladora
> **Alimenta findings:** L-05, L-06, F-03

---

## 1. Qualificação das Partes

**Controlador 1 (Meia-Entrada):** {{RAZAO_SOCIAL}}, pessoa jurídica de direito privado, inscrita no CNPJ sob nº {{CNPJ}}, com sede na {{ENDERECO_CONTROLADOR}}, doravante **MEIA-ENTRADA**.

**Controlador 2 (Entidade Emissora):** {{ENTIDADE_NOME}}, {{ENTIDADE_NATUREZA}}, inscrita sob {{ENTIDADE_CNPJ_OU_REGISTRO}}, com sede em {{ENTIDADE_ENDERECO}}, doravante **ENTIDADE**.

Ambas doravante denominadas **PARTES** ou **CO-CONTROLADORAS**.

---

## 2. Papéis e Responsabilidades (RACI Matrix)

| Atividade | MEIA-ENTRADA | ENTIDADE | Detalhe |
|---|---|---|---|
| Definir plataforma e fluxo de coleta | R / A | C | MEIA-ENTRADA define o formulário, ENTIDADE pode configurar campos adicionais |
| Verificar vínculo acadêmico | I | R / A | ENTIDADE atesta a condição de estudante |
| Coletar consentimento LGPD | R | C | MEIA-ENTRADA coleta via formulário; ENTIDADE garante a base legal |
| Armazenar e proteger dados | R / A | I | MEIA-ENTRADA opera infraestrutura; ENTIDADE acessa dados dos seus estudantes |
| Emitir carteirinha | R / A | C | MEIA-ENTRADA gera PDF/QR; ENTIDADE autoriza |
| Validar carteirinha | R / A | I | MEIA-ENTRADA mantém validador público |
| Notificar incidente de segurança | R | R | Ambas se notificam mutuamente (art. 48 LGPD) |
| Responder a direitos do titular | R / A | C | MEIA-ENTRADA opera o canal; ENTIDADE confirma vínculo |
| Manter DPO | R | R | Cada parte tem seu DPO |

*Legenda: R = Responsável | A = Aprovador | C = Consultado | I = Informado*

---

## 3. Objeto

3.1. As PARTES estabelecem os termos de co-controladoria (art. 5º, VI e art. 26 LGPD) para o tratamento de dados pessoais de estudantes vinculados à ENTIDADE, para fins de emissão e validação da Carteira de Identificação Estudantil (CIE).

3.2. A co-controladoria se limita ao tratamento dos dados estritamente necessários à finalidade comum (emissão e validação da CIE), sendo cada parte responsável pelo tratamento que realiza individualmente em seus próprios sistemas ou finalidades.

---

## 4. Finalidades Comuns

4.1. As PARTES determinam conjuntamente as seguintes finalidades de tratamento:

a) Emissão de Carteira de Identificação Estudantil (CIE) para estudantes vinculados à ENTIDADE;

b) Validação da autenticidade e validade da carteirinha por estabelecimentos;

c) Gestão administrativa da campanha (autorização, produção, envio, reemissão);

d) Comunicação sobre status do pedido ao estudante;

e) Cumprimento de obrigações legais (Lei 12.933/2013, Portaria CIE v3.3).

---

## 5. Categorias de Dados Tratados

As PARTES tratam as seguintes categorias de dados, conforme detalhado no Anexo I:

- Identificadores governamentais (CPF, RG)
- Dados pessoais de identificação (nome, filiação, DOB)
- Dados acadêmicos (matrícula, curso, instituição)
- Contato (e-mail, telefone)
- Endereço (condicional — entrega domiciliar)
- **Dado sensível: fotografia (biométrico — art. 11 LGPD)**
- Documentos comprobatórios
- Metadados operacionais (status, tokens)

---

## 6. Obrigações da ENTIDADE (Co-Controladora)

6.1. A ENTIDADE se obriga a:

a) **Vínculo acadêmico:** Garantir que todos os estudantes indicados à emissão de carteirinha são estudantes regulares, sob pena de responsabilidade por falsidade ideológica (art. 299 CP);

b) **Autorização:** Autorizar apenas campanhas legítimas, com finalidade de meia-entrada (Lei 12.933/2013);

c) **Acesso:** Acessar os dados pessoais apenas na medida necessária para gestão da campanha, respeitando os níveis de privilégio (`assistente`, `supervisor`, `admin`);

d) **Confidencialidade:** Manter sigilo sobre os dados acessados, responsabilizando-se por seus administradores e usuários;

e) **Consentimento:** Colaborar com a MEIA-ENTRADA para garantir que o consentimento dos titulares seja obtido conforme a LGPD (arts. 8º e 11);

f) **Incidentes:** Notificar a MEIA-ENTRADA imediatamente sobre qualquer incidente de segurança de que tenha ciência envolvendo dados tratados em co-controladoria;

g) **DPO:** Manter um canal de comunicação com o DPO da MEIA-ENTRADA.

---

## 7. Obrigações da MEIA-ENTRADA

7.1. A MEIA-ENTRADA se obriga a:

a) **Plataforma:** Operar a plataforma com medidas de segurança adequadas (RLS, criptografia, controles de acesso);

b) **Consentimento:** Implementar e manter os mecanismos de consentimento (geral + foto) em conformidade com a LGPD;

c) **Políticas:** Publicar e manter atualizadas a Política de Privacidade, Termos de Uso e Política de Retenção;

d) **DPO:** Manter Encarregado acessível e funcional (art. 41 LGPD);

e) **Auditoria:** Registrar operações de tratamento e manter logs de acesso auditáveis;

f) **Atualização CIE:** Buscar a migração para a CIE oficial com Certificado de Atributo ICP-Brasil.

---

## 8. Partilha de Acesso — Níveis de Privilégio

8.1. A ENTIDADE acessa os dados apenas de seus próprios estudantes, por meio do painel `admin`.

8.2. Os níveis de acesso na plataforma são:

| Nível | Acesso |
|---|---|
| **Admin** | Gerenciar usuários da entidade, configurar campanha, ver todas as carteiras da entidade |
| **Supervisor** | Autorizar/rejeitar carteiras, ver dados dos estudantes da entidade |
| **Assistente** | Ver carteiras autorizadas, produzir/enviar, ver dados mínimos |

8.3. A ENTIDADE é responsável por gerenciar e auditar o acesso de seus usuários.

---

## 9. Notificação de Incidente

9.1. Cada PARTE deve notificar a outra sobre qualquer incidente de segurança envolvendo dados pessoais tratados em co-controladoria no prazo máximo de **48 horas** da ciência.

9.2. A notificação deve permitir que a outra PARTE cumpra suas obrigações legais perante ANPD e titulares (Res. CD/ANPD nº 15/2024 — 72h úteis para notificação ANPD).

9.3. Ambas as PARTES colaborarão na investigação e mitigação do incidente, compartilhando informações relevantes e preservando evidências.

9.4. Cada PARTE é responsável pela notificação aos titulares e à ANPD em relação aos dados sob sua esfera de controle.

---

## 10. DPO e Canal de Comunicação

10.1. Cada PARTE designa um Encarregado (DPO) para comunicação entre si e com titulares:

| | MEIA-ENTRADA | ENTIDADE |
|---|---|---|
| **DPO** | {{DPO_NOME}} | {{ENTIDADE_DPO_NOME}} |
| **Contato** | {{DPO_EMAIL}} | {{ENTIDADE_DPO_CONTATO}} |

10.2. As PARTES manterão canal direto de comunicação entre seus DPOs.

---

## 11. Subcontratação (Operadores)

11.1. A MEIA-ENTRADA contrata operadores para execução dos serviços, listados abaixo. A ENTIDADE anui com a contratação destes operadores.

| Operador | Serviço | Jurisdição | DPA |
|---|---|---|---|
| Supabase Inc. | Banco de dados, storage, auth | EUA | ✅ (subprompt 03) |
| Vercel Inc. | Hospedagem | EUA | Em elaboração |
| PostHog Inc. | Analytics | EUA | Em elaboração |

11.2. A MEIA-ENTRADA notificará a ENTIDADE sobre novos operadores com antecedência mínima de 30 dias.

---

## 12. Direitos dos Titulares (Interação)

12.1. O titular pode exercer seus direitos (art. 18 LGPD) perante qualquer das PARTES.

12.2. A PARTE que receber a solicitação deve:
- Responder ao titular em até 15 dias (art. 19, §1º);
- Coordenar com a outra PARTE para acessar/excluir/portar dados sob sua esfera;
- Informar a outra PARTE sobre a solicitação em até 48h.

12.3. Em caso de exclusão, a outra PARTE deve eliminar os dados sob sua esfera no menor prazo possível, respeitados os prazos da Política de Retenção.

---

## 13. Responsabilidade Civil

13.1. Em caso de violação da LGPD que cause dano a titular, as PARTES respondem solidariamente (art. 42, §1º, I), podendo a parte prejudicada exercer direito de regresso contra a PARTE que deu causa ao dano.

13.2. A PARTE que der causa exclusiva ao dano arcará integralmente com a indenização, multas e custos, eximindo a outra PARTE de responsabilidade.

13.3. A PARTE que descumprir suas obrigações neste Contrato indenizará a outra PARTE por perdas e danos, incluindo multas administrativas, honorários advocatícios e custas processuais.

---

## 14. Vigência e Rescisão

14.1. Este Contrato vigorará enquanto a ENTIDADE mantiver campanha ativa na plataforma.

14.2. Qualquer PARTE pode rescindir o Contrato mediante notificação com 30 dias de antecedência.

14.3. Em caso de rescisão:

a) A ENTIDADE deve finalizar as campanhas em andamento (carteiras já emitidas permanecem válidas até o fim de sua validade);

b) A MEIA-ENTRADA deve garantir ao titular o acesso a seus dados e, se solicitado, a portabilidade (art. 18 LGPD);

c) Após o período de transição, os dados serão tratados conforme a Política de Retenção.

14.4. **Denúncia por irregularidade acadêmica:** A MEIA-ENTRADA pode suspender imediatamente a emissão de carteirinhas pela ENTIDADE se houver indício fundamentado de fraude acadêmica (vínculo falsificado, documentos falsos), sem prejuízo das demais sanções legais.

---

## 15. Foro e Legislação Aplicável

15.1. Este Contrato é regido pela Lei 13.709/2018 (LGPD), Lei 8.078/1990 (CDC), Lei 12.933/2013 e Código Civil.

15.2. Fica eleito o foro de {{COMARCA}}, com renúncia a qualquer outro.

☐ **Alternativa** (se ENTIDADE estiver em outro estado): Foro do domicílio do consumidor (art. 101, I CDC) ou foro de Brasília/DF (neutralidade).

---

## Anexo — RIPD Compartilhado (Resumo)

### Risco principal: Tratamento de dado sensível (foto) + exposição na validação pública

| Risco | Probabilidade | Impacto | Mitigação | Responsável |
|---|---|---|---|---|
| Vazamento de foto via validação pública (`/V/[token]`) | Média (pré-S-03) / Baixa (pós-S-03) | Alto (dado sensível exposto) | Token assinado + projeção mínima + rate-limit (S3) | MEIA-ENTRADA |
| Fraude acadêmica (entidade emite para não-estudante) | Média | Médio (falsidade, perda de confiança) | KYC da entidade + auditoria periódica | ENTIDADE |
| Acesso não autorizado por admin da entidade | Baixa | Médio | RLS por entidade + logs de auditoria (S2) | AMBAS |
| Vazamento via service_role | Alta (hoje) / Muito Baixa (pós-S0) | Crítico | Remover service_role do frontend (S0) | MEIA-ENTRADA |

---

## Condições Específicas por Tipo de Entidade

☐ **Entidade pública (federal, estadual, municipal):** Pode exigir procedimento licitatório simplificado. A MEIA-ENTRADA deve verificar a necessidade de contrato administrativo.

☐ **Entidade sem CNPJ (grêmio, coordenação de curso):** O responsável legal deve assinar termo de responsabilidade individual. A MEIA-ENTRADA pode exigir associação formal. **Risco elevado** — co-controladora sem personalidade jurídica.

☐ **Entidade privada (IES, colégio):** Contrato padrão, sem adaptações.

---

## Placeholders

| Placeholder | Descrição |
|---|---|
| `{{RAZAO_SOCIAL}}` | Nome da Meia-Entrada |
| `{{CNPJ}}` | CNPJ |
| `{{ENDERECO_CONTROLADOR}}` | Endereço |
| `{{ENTIDADE_NOME}}` | Nome da entidade emissora |
| `{{ENTIDADE_NATUREZA}}` | Natureza (ex.: associação, IES) |
| `{{ENTIDADE_CNPJ_OU_REGISTRO}}` | CNPJ ou outro registro |
| `{{ENTIDADE_ENDERECO}}` | Endereço da entidade |
| `{{ENTIDADE_DPO_NOME}}` | DPO da entidade |
| `{{ENTIDADE_DPO_CONTATO}}` | Contato do DPO da entidade |
| `{{COMARCA}}` | Foro |

---

## Disclaimer

*Minuta técnico-jurídica. Cada entidade pode ter regime jurídico próprio (público vs privado) que exigirá adaptação. Entidades sem CNPJ requerem atenção jurídica redobrada. A versão aqui apresentada requer revisão por advogado OAB antes da adoção.*

**Revisão pendente:** [ ] OAB validar cláusula de denúncia por irregularidade; [ ] Definir foro padrão para entidades de outros estados; [ ] Validar adaptação para entidades públicas; [ ] Decidir N-2 (atender sem CNPJ).
