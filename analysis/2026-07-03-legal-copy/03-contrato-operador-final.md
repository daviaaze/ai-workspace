# Contrato de Operador de Tratamento de Dados Pessoais (DPA)

> **Versão:** 1.0 | **Data:** {{DATA}}
> **Controlador:** {{RAZAO_SOCIAL}} | CNPJ {{CNPJ}}
> **Operador:** {{PROVEDOR_NOME}} | {{PROVEDOR_JURISDICAO}}
> **Subprompt:** 03 — Contrato de Operador (DPA)
> **Alimenta findings:** L-05, transferência internacional (arts. 33/36)

---

## 1. Qualificação das Partes

**Controlador:** {{RAZAO_SOCIAL}}, pessoa jurídica de direito privado, inscrita no CNPJ sob nº {{CNPJ}}, com sede na {{ENDERECO_CONTROLADOR}}, doravante **CONTROLADOR**.

**Operador:** {{PROVEDOR_NOME}}, sociedade constituída sob as leis de {{PROVEDOR_JURISDICAO}}, com sede em {{PROVEDOR_ENDERECO}}, inscrita sob nº {{PROVEDOR_REGISTRO}}, doravante **OPERADOR**.

---

## 2. Objeto

2.1. O presente Contrato de Operador (DPA — Data Processing Agreement) estabelece os termos e condições sob os quais o OPERADOR trata dados pessoais por conta e ordem do CONTROLADOR, no âmbito da prestação de serviços de {{PROVEDOR_SERVICOS}} (banco de dados gerenciado, autenticação, storage, edge functions, hospedagem).

2.2. O OPERADOR tratará exclusivamente os dados pessoais descritos no **Anexo I** e estritamente de acordo com as instruções documentadas do CONTROLADOR (art. 39, LGPD).

---

## 3. Natureza do Tratamento

3.1. O OPERADOR atua como **Operador** de tratamento de dados pessoais, nos termos do art. 5º, VII e art. 39 da LGPD, tratando dados por conta do CONTROLADOR, que é o **Controlador** (art. 5º, VI).

3.2. O OPERADOR não poderá utilizar os dados pessoais para finalidade própria ou diversa da estabelecida neste Contrato ou nas instruções do CONTROLADOR.

3.3. Região de armazenamento: {{REGIAO}}. Qualquer alteração de região depende de autorização prévia do CONTROLADOR.

---

## 4. Categorias de Dados e Titulares

| Categoria | Dados | Titulares |
|---|---|---|
| Identificadores governamentais | CPF, RG, órgão emissor, UF | Estudantes |
| Dados pessoais de identificação | Nome completo, filiação, data de nascimento | Estudantes |
| Dados acadêmicos | Matrícula, curso, período, instituição, entidade | Estudantes |
| Contato | E-mail, telefone | Estudantes, administradores de entidade |
| Endereço (condicional) | CEP, rua, número, complemento, bairro, cidade, UF | Estudantes |
| **Dado sensível — fotografia** | Arquivo de imagem (biométrico — art. 11 LGPD) | Estudantes |
| Documentos comprobatórios | Foto de documento, comprovante de matrícula | Estudantes |
| Dados cadastrais da entidade | Razão social, CNPJ, responsável | Entidades emissoras |
| Metadados operacionais | Status de carteira, tokens, UUIDs, logs de acesso | — |

---

## 5. Finalidades do Tratamento

O OPERADOR trata os dados pessoais exclusivamente para as seguintes finalidades, conforme instruções do CONTROLADOR:

- Armazenamento e processamento de dados para emissão e validação da Carteira de Identificação Estudantil (CIE);
- Autenticação de usuários (Supabase Auth);
- Armazenamento de arquivos (fotos, documentos comprobatórios);
- Processamento de funções server-side (edge functions);
- Execução de queries autorizadas no banco de dados;
- Backup e recuperação de desastres.

---

## 6. Obrigações do Operador (art. 41 LGPD)

6.1. O OPERADOR se obriga a:

a) **Segurança da informação:** Manter medidas técnicas e organizacionais adequadas à proteção dos dados, conforme Anexo II e art. 46 LGPD;

b) **Sigilo:** Manter sigilo absoluto sobre os dados pessoais, acessíveis apenas a pessoal autorizado e comprometido contratualmente com a confidencialidade;

c) **Treinamento:** Garantir que seu pessoal com acesso aos dados receba treinamento adequado em proteção de dados;

d) **Registros:** Manter registros atualizados de todas as operações de tratamento realizadas (art. 37 LGPD);

e) **Subcontratação:** Não subcontratar terceiros para tratamento de dados sem notificação prévia e autorização do CONTROLADOR (ver cláusula 7);

f) **Incidentes:** Notificar o CONTROLADOR imediatamente sobre qualquer incidente de segurança que envolva dados pessoais (ver cláusula 9);

g) **Devolução e eliminação:** Ao término do contrato, devolver ou eliminar os dados pessoais, conforme instrução do CONTROLADOR (ver cláusula 12).

---

## 7. Obrigações do Controlador

7.1. O CONTROLADOR se obriga a:

a) Garantir a legitimidade, licitude e necessidade do tratamento de dados pessoais instruído ao OPERADOR;

b) Fornecer ao OPERADOR instruções claras e documentadas sobre o tratamento;

c) Manter registro das operações de tratamento (RDM) e o RIPD, quando exigível;

d) Efetuar o pagamento pelos serviços contratados;

e) Notificar o OPERADOR sobre alterações relevantes nas finalidades ou bases legais.

---

## 8. Subcontratação

8.1. O OPERADOR poderá subcontratar terceiros para execução de partes dos serviços, desde que:

a) Notifique previamente o CONTROLADOR sobre a identidade e papel de cada subcontratado;

b) Exija do subcontratado o mesmo nível de proteção de dados estabelecido neste Contrato, mediante contrato escrito;

c) Permaneça solidariamente responsável pelos atos do subcontratado (art. 40 LGPD).

8.2. **Subcontratados atuais:**

| Subcontratado | Serviço | Jurisdição |
|---|---|---|
| {{SUBCONTRATADO_1}} | {{SERVICO_1}} | {{JURISDICAO_1}} |
| {{SUBCONTRATADO_2}} | {{SERVICO_2}} | {{JURISDICAO_2}} |

*Atualizar conforme Anexo III.*

---

## 9. Incidentes de Segurança

9.1. O OPERADOR deve notificar o CONTROLADOR sobre qualquer incidente de segurança envolvendo dados pessoais em até **48 horas** da ciência (art. 48 LGPD c/c Res. CD/ANPD nº 15/2024).

9.2. A notificação deve conter, no mínimo:

a) Descrição do incidente (natureza, categorias e quantidade de titulares afetados);

b) Medidas tomadas ou propostas para remediar ou mitigar o incidente;

c) Contato para comunicação (DPO do OPERADOR, se houver);

d) Medidas de segurança que estavam em vigor no momento do incidente.

9.3. O OPERADOR deve prestar toda a cooperação necessária para que o CONTROLADOR cumpra sua obrigação de notificar a ANPD e os titulares (72h úteis para a ANPD).

---

## 10. Transferência Internacional

10.1. Os dados pessoais serão armazenados e processados em {{PAIS_ARMAZENAMENTO}}.

10.2. Para garantir o nível adequado de proteção (art. 33, § único, LGPD), as Partes adotam:

☐ **Cláusulas-padrão de proteção** (Standard Contractual Clauses — Comissão Europeia, Decisão 2021/914), aplicáveis por analogia nos termos do art. 33, II;

☐ **Garantias específicas** descritas no Anexo II;

☐ **Análise de impacto** demonstrando que as medidas compensatórias são suficientes (SCCs + criptografia + controles de acesso + regime contratual).

10.3. O CONTROLADOR reconhece que a transferência internacional é indispensável para a prestação do serviço e autoriza o OPERADOR a realizar o tratamento nos locais indicados.

---

## 11. Auditoria

11.1. O CONTROLADOR tem o direito de auditar o OPERADOR para verificar o cumprimento deste Contrato, pessoalmente ou por terceiro contratado.

11.2. A auditoria será realizada:

- No máximo 1 (uma) vez por ano, salvo em caso de incidente comprovado;
- Mediante notificação com 30 dias de antecedência;
- Em horário comercial, sem interferência nas operações do OPERADOR;
- Às expensas do CONTROLADOR.

11.3. O OPERADOR deve fornecer acesso a registros, sistemas, políticas e pessoal necessários para a auditoria.

---

## 12. Vigência, Rescisão, Devolução e Eliminação

12.1. Este Contrato vigorará enquanto perdurarem os serviços contratados entre as Partes.

12.2. Ao término, o OPERADOR deve, conforme instrução do CONTROLADOR:

a) Devolver todos os dados pessoais em formato estruturado e legível (export); ou

b) Eliminar todos os dados pessoais, exceto se houver obrigação legal de retenção (art. 16);

c) Certificar por escrito que a eliminação foi concluída.

12.3. O OPERADOR pode reter dados apenas se houver obrigação legal na jurisdição aplicável, devendo informar o CONTROLADOR sobre tal retenção.

---

## 13. Penalidades e Indenização

13.1. O OPERADOR indenizará o CONTROLADOR por todos os danos, multas, sanções e custos (incluindo honorários advocatícios) decorrentes de violação deste Contrato ou da LGPD causada pelo OPERADOR ou seus subcontratados.

13.2. A indenização não se aplica quando a violação decorrer exclusivamente de instrução expressa do CONTROLADOR que viole a LGPD.

---

## 14. Foro e Legislação Aplicável

14.1. Este Contrato é regido pela Lei 13.709/2018 (LGPD) e, subsidiariamente, pela Lei 10.406/2002 (Código Civil).

14.2. Fica eleito o foro de {{COMARCA}} para dirimir controvérsias, com renúncia a qualquer outro, por mais privilegiado que seja.

---

## Anexo I — Descrição do Tratamento

| Campo | Detalhe |
|---|---|
| Finalidade do tratamento | Emissão e validação de Carteiras de Identificação Estudantil |
| Categorias de titulares | Estudantes (inclusive menores), administradores de entidades emissoras |
| Categorias de dados | Identificadores, dados cadastrais, acadêmicos, contato, endereço, **dado sensível (foto)**, documentos comprobatórios, metadados |
| Período de retenção | Conforme Política de Retenção do CONTROLADOR |
| Região de armazenamento | {{REGIAO}} |
| Frequência do tratamento | Contínuo (24x7), com picos sazonais de campanhas |
| Destinatários dos dados | CONTROLADOR, co-controladoras (entidades emissoras), estabelecimentos validadores |

---

## Anexo II — Medidas Técnicas e Organizacionais

### Medidas confirmadas (auditoria técnica)

| Medida | Status | Descrição |
|---|---|---|
| TLS 1.3 em todas as conexões | ✅ Ativo | Criptografia em trânsito |
| Criptografia em repouso | ✅ Ativo | Criptografia do banco de dados (Supabase) |
| Autenticação por sessão | ✅ Ativo | Supabase Auth com HTTP-only cookies |
| RLS (Row Level Security) | 🔧 Em implementação | S0/S1 do plano de ação |
| Rate limiting | 🔧 Em implementação | S1 |
| Headers de segurança (CSP, HSTS) | 🔧 Em implementação | S1 |
| Logs de auditoria de acesso | 🔧 Em implementação | S2 |
| Anonimização em logs de auditoria | 🔧 Em implementação | S3 |

### Medidas organizacionais

| Medida | Status |
|---|---|
| Contrato de operador (DPA) | ✅ Este documento |
| Política de Privacidade | Em elaboração (S1) |
| Política de Retenção | Em elaboração (S2) |
| RIPD | Em elaboração (S2) |
| Programa de governança (art. 50) | Em elaboração (S2) |

---

## Anexo III — Subcontratados

| Subcontratado | Serviço | Jurisdição |
|---|---|---|
| {{PROVEDOR_NOME}} | Banco de dados, storage, auth | {{PROVEDOR_JURISDICAO}} |
| {{PROVEDOR_CLOUD_NOME}} | Infraestrutura cloud (provedor subjacente) | {{PROVEDOR_CLOUD_JURISDICAO}} |

*Nota: A lista de subcontratados deve ser atualizada sempre que houver alteração. O CONTROLADOR deve ser notificado previamente.*

---

## Placeholders

| Placeholder | Descrição |
|---|---|
| `{{RAZAO_SOCIAL}}` | Nome da Meia-Entrada |
| `{{CNPJ}}` | CNPJ |
| `{{ENDERECO_CONTROLADOR}}` | Endereço do controlador |
| `{{PROVEDOR_NOME}}` | Nome do operador (ex.: Supabase Inc.) |
| `{{PROVEDOR_JURISDICAO}}` | Ex.: Delaware, EUA |
| `{{PROVEDOR_ENDERECO}}` | Endereço do operador |
| `{{PROVEDOR_REGISTRO}}` | Registro empresarial |
| `{{PROVEDOR_SERVICOS}}` | Serviços contratados |
| `{{REGIAO}}` | Região de armazenamento (ex.: us-east-1) |
| `{{PAIS_ARMAZENAMENTO}}` | País de armazenamento |
| `{{COMARCA}}` | Foro |
| `{{DATA}}` | Data de assinatura |
| `{{SUBCONTRATADO_N}}` | Subcontratados |

---

## Disclaimer

*Minuta técnico-jurídica para revisão por advogado OAB. A negociação final com o provedor pode exigir ajustes em conformidade com seus termos-padrão. Este contrato **inclui cláusulas que podem conflitar com os ToS de provedores SaaS** — indicar a tensão e negociar anexo de proteção complementar se necessário.*

**Revisão pendente:** [ ] OAB confirmar adequação das SCCs; [ ] Verificar se provedor aceita cláusula de auditoria; [ ] Confirmar região de storage com engenharia.
