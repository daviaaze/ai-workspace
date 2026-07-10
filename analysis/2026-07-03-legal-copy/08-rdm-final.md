# RDM — Registro das Operações de Tratamento de Dados Pessoais

> **Versão:** 1.0 | **Data:** {{DATA_PUBLICACAO}}
> **Controlador:** {{RAZAO_SOCIAL}}, CNPJ {{CNPJ}}
> **DPO:** {{DPO_NOME}} — {{DPO_EMAIL}}
> **Subprompt:** 08 — RDM
> **Referências:** Política de Privacidade (01), Política de Retenção (07), RIPD (05), Contratos (03/04)
> **Formato:** Markdown estruturado (legível por máquina e humano)
> **Atualização:** Vivo — revisar a cada migration que altere coluna PII

---

## Operação 01: Coleta de Dados via Formulário Web

| Campo | Valor |
|---|---|
| **ID** | RDM-OP-01 |
| **Nome** | Coleta de dados do estudante via formulário web |
| **Finalidade** | Emissão de Carteira de Identificação Estudantil |
| **Titulares** | Estudantes (titulares), Responsáveis legais (menores) |
| **Dados** | C01 (CPF/RG), C02 (nome/filiação/DOB), C03 (matrícula/curso/instituição), C04 (e-mail/telefone), C05 (endereço — condicional), C06 (foto — dado sensível), C07 (documentos comprobatórios) |
| **Base legal** | Art. 7º, V (execução de contrato); art. 7º, II (obrigação legal — Lei 12.933/2013); **art. 11, I** (consentimento específico — foto) |
| **Controlador** | Meia-Entrada Estudantil ({{RAZAO_SOCIAL}}) |
| **Co-controladora** | Entidade emissora (DCE, UPEE, escola, IES) que gerencia a campanha |
| **Operadores** | Vercel Inc. (hospedagem — EUA); Supabase Inc. (banco de dados + storage — EUA) |
| **Transferência internacional** | EUA — garantias: SCC nos contratos de operador + criptografia TLS |
| **Retenção** | Prazo ativo: validade da carteirinha + 12 meses. Dado sensível (foto): +6 meses. Hard-delete conforme Política de Retenção (07). |
| **Medidas de segurança** | TLS 1.3; RLS (em implementação — S0/S1); projeção mínima de colunas (em implementação — S0/S1); rate-limit/captcha (S1) |
| **Compartilhamento** | Entidade emissora (co-controladora) — dados do estudante vinculado à campanha |
| **Risco associado** | RISCO ALTO (dado sensível — foto). Ver RIPD (05) para detalhes. |

---

## Operação 02: Upload de Foto Biométrica (Storage)

| Campo | Valor |
|---|---|
| **ID** | RDM-OP-02 |
| **Nome** | Upload e armazenamento de fotografia do estudante |
| **Finalidade** | Inclusão da foto na carteirinha + validação visual por estabelecimentos |
| **Titulares** | Estudantes |
| **Dados** | C06 — Arquivo de imagem (JPEG/PNG) — **dado biométrico sensível** |
| **Base legal** | **Art. 11, I** (consentimento específico e destacado — checkbox separado) |
| **Controlador** | Meia-Entrada Estudantil |
| **Co-controladora** | Entidade emissora |
| **Operadores** | Supabase Inc. (storage bucket privado — EUA) |
| **Transferência internacional** | EUA — SCC + criptografia em trânsito e repouso |
| **Retenção** | Até validade da carteirinha + **6 meses**. Hard-delete do storage. |
| **Medidas de segurança** | Bucket privado (não público); RLS por entidade (em implementação); criptografia em repouso (Supabase); TLS 1.3 |
| **Compartilhamento** | Apenas visualização pela entidade emissora + estabelecimento validando `/V/[token]` |
| **Risco associado** | RISCO ALTO — dado sensível. Consentimento é a única base legal. Qualquer acesso não autorizado configura violação grave. |

---

## Operação 03: Emissão e Produção da Carteirinha (PDF + QR)

| Campo | Valor |
|---|---|
| **ID** | RDM-OP-03 |
| **Nome** | Geração de PDF da carteirinha com QR code de validação |
| **Finalidade** | Emitir o documento físico/digital de identificação estudantil |
| **Titulares** | Estudantes |
| **Dados** | C01 (CPF), C02 (nome, foto), C03 (instituição, curso), C09 (token de validação) |
| **Base legal** | Art. 7º, V (execução de contrato) |
| **Controlador** | Meia-Entrada Estudantil |
| **Operadores** | Vercel Inc. (server-side PDF generation — EUA); Supabase (storage do PDF — EUA) |
| **Transferência internacional** | EUA — SCC |
| **Retenção** | PDF mantido enquanto a carteirinha estiver ativa + conforme retenção geral |
| **Medidas de segurança** | Geração em servidor (não exposto ao cliente); QR assinado (em implementação — S3/S4 CIE) |
| **Compartilhamento** | PDF disponível para download pelo titular; rota `/V/[token]` para validação pública |
| **Risco associado** | RISCO MÉDIO — exposição do PDF via link temporário |

---

## Operação 04: Validação Pública via Token/QR

| Campo | Valor |
|---|---|
| **ID** | RDM-OP-04 |
| **Nome** | Validação da carteirinha por estabelecimento ou fiscal |
| **Finalidade** | Permitir que estabelecimentos verifiquem a autenticidade e validade da carteirinha |
| **Titulares** | Estudantes |
| **Dados** | C02 (nome, foto), C03 (instituição, status, validade) — **apenas os mínimos necessários para validação** |
| **Base legal** | Art. 7º, V (execução de contrato) |
| **Controlador** | Meia-Entrada Estudantil |
| **Terceiro** | Qualquer pessoa com acesso ao link/token (estabelecimento, fiscal, consumidor) |
| **Retenção** | Token ativo durante validade da carteirinha; expirado após 90 dias pós-validade |
| **Medidas de segurança** | Token criptográfico (em implementação — S0/S1); rate-limit por IP (S1); cache `no-store` (em implementação); **projeção mínima** — não expor CPF/RG/endereço (S1) |
| **Compartilhamento** | Público (qualquer pessoa que acesse `/V/[token]` ou escaneie o QR) |
| **Risco associado** | RISCO ALTO — exposição de PII (foto + nome) a terceiros não autenticados. Mitigação: S-03 (token assinado + projeção mínima + rate-limit). Sem mitigação, esta operação expõe toda a PII (S-03 original). |

---

## Operação 05: Gestão Administrativa pela Entidade Emissora (Admin)

| Campo | Valor |
|---|---|
| **ID** | RDM-OP-05 |
| **Nome** | Acesso e gestão de carteirinhas pela entidade emissora no painel admin |
| **Finalidade** | Gerenciamento da campanha: autorizar, rejeitar, produzir, enviar carteirinhas |
| **Titulares** | Estudantes vinculados à entidade emissora |
| **Dados** | C01-C09 (todos os dados da carteira) — escopo restrito à(s) entidade(s) que o administrador gerencia |
| **Base legal** | Art. 7º, V (execução de contrato) + co-controladoria |
| **Controlador** | Meia-Entrada Estudantil |
| **Co-controladora** | Entidade emissora (acessa os dados dos seus estudantes) |
| **Operadores** | Vercel + Supabase |
| **Retenção** | Conforme tabela de retenção (07) |
| **Medidas de segurança** | Autenticação por session (Supabase Auth); RLS por `entidade_id` (em implementação — S0/S1); logs de acesso (S2) |
| **Compartilhamento** | A entidade emissora já é co-controladora — o compartilhamento é inerente à operação |
| **Risco associado** | RISCO MÉDIO — acesso interno. Mitigação: RLS + logs de auditoria |

---

## Operação 06: Telemetria (PostHog — Analytics)

| Campo | Valor |
|---|---|
| **ID** | RDM-OP-06 |
| **Nome** | Coleta de eventos de navegação e uso da plataforma |
| **Finalidade** | Melhoria do produto, identificação de erros, análise de funil |
| **Titulares** | Visitantes (estudantes, administradores) |
| **Dados** | C12 — eventos de navegação (páginas visitadas, cliques, tempo de sessão), IP mascarado, user-agent. **NÃO inclui inputs de formulário PII.** |
| **Base legal** | Art. 7º, I (consentimento) — via banner de cookies |
| **Controlador** | Meia-Entrada Estudantil |
| **Operadores** | PostHog Inc. (EUA) |
| **Transferência internacional** | EUA — SCC (contrato de operador) |
| **Retenção** | 14 meses (padrão PostHog) |
| **Medidas de segurança** | `autocapture: false` (S-08 hotfix); `maskAllInputs: true` (quando habilitado session recording); IP truncado; sem gravação em páginas de formulário PII |
| **Compartilhamento** | PostHog Inc. (operador) |
| **Risco associado** | RISCO BAIXO (após S-08) — dados anonimizados, sem PII. **RISCO CRÍTICO** se autocapture for reabilitado sem `maskAllInputs`. |

---

## Operação 07: Comunicação Outbound (Futuro — E-mail/WhatsApp/SMS)

| Campo | Valor |
|---|---|
| **ID** | RDM-OP-07 |
| **Nome** | Comunicação com o titular sobre status do pedido, validade e reemissão |
| **Finalidade** | Notificação transacional: confirmação, alerta de expiração, reemissão, suporte |
| **Titulares** | Estudantes |
| **Dados** | C04 (e-mail, telefone), C02 (nome) |
| **Base legal** | Transacional: art. 7º, V (execução de contrato). Marketing: art. 7º, I (consentimento) — opt-in separado |
| **Controlador** | Meia-Entrada Estudantil |
| **Operadores** | {{EMAIL_PROVIDER}}, {{WHATSAPP_PROVIDER}} (futuro) |
| **Transferência internacional** | {{DEPENDE_DO_PROVIDER}} — verificar país e contrato |
| **Retenção** | Conforme política do provedor + política interna (07) |
| **Medidas de segurança** | Descadastro fácil; templates aprovados (WhatsApp ToS); opt-in registrado em `lgpd_consents` |
| **Compartilhamento** | Operador de e-mail/WhatsApp |
| **Risco associado** | RISCO MÉDIO (transacional) / RISCO ALTO (marketing sem opt-in) |

---

## Operação 08: Auditoria e Logs de Deleção

| Campo | Valor |
|---|---|
| **ID** | RDM-OP-08 |
| **Nome** | Registro de auditoria de acesso e eliminação de dados |
| **Finalidade** | Demonstrar accountability (art. 50); rastrear eliminações (art. 16, §1º); investigar incidentes |
| **Titulares** | Estudantes (anonimizados nos logs) |
| **Dados** | C11 — CPF anonimizado (hash SHA-256), carteira_id, ação, data, trigger, operador |
| **Base legal** | Art. 7º, II (obrigação legal — art. 50 LGPD); art. 7º, V (exercício regular de direitos) |
| **Controlador** | Meia-Entrada Estudantil |
| **Retenção** | 5 anos |
| **Medidas de segurança** | Dados anonimizados (CPF → hash, nome removido); acesso restrito a DPO + administradores |
| **Compartilhamento** | Nenhum (uso interno) |
| **Risco associado** | RISCO BAIXO — dados anonimizados. Falha em anonimizar corretamente = RISCO ALTO. |

---

## Operação 09: Suporte e Canal DPO

| Campo | Valor |
|---|---|
| **ID** | RDM-OP-09 |
| **Nome** | Atendimento ao titular e exercício de direitos LGPD |
| **Finalidade** | Processar solicitações de direitos (art. 18); prestar suporte |
| **Titulares** | Estudantes, Responsáveis legais |
| **Dados** | C01 (CPF), C04 (e-mail), conteúdo da solicitação (texto livre com possíveis dados PII) |
| **Base legal** | Art. 7º, V (execução de contrato — suporte); art. 7º, II (obrigação legal — responder direitos) |
| **Controlador** | Meia-Entrada Estudantil |
| **Operadores** | Provedor de e-mail; Vercel (formulário web) |
| **Retenção** | Até resolução + 90 dias (a definir conforme política de retenção) |
| **Medidas de segurança** | Prova de posse (e-mail/telefone) antes de fornecer dados; registro em `lgpd_subject_requests` |
| **Compartilhamento** | Nenhum (exceto se encaminhamento técnico ao operador) |
| **Risco associado** | RISCO MÉDIO — risco de vazamento de PII se confirmação de identidade for fraca |

---

## Resumo de Riscos por Operação

| Operação | Risco | Mitigação principal | Sprint |
|---|---|---|---|
| OP-01 — Coleta | **ALTO** (dado sensível) | Consentimento específico foto (L-02) | S1 |
| OP-02 — Storage foto | **ALTO** (biométrico) | Bucket privado + RLS (S-02, S-07) | S0/S1 |
| OP-03 — Emissão PDF | **MÉDIO** | PDF gerado server-side | — |
| OP-04 — Validação pública | **ALTO** (exposição PII) | Token assinado + projeção mínima (S-03) | S0/S1 |
| OP-05 — Admin entidade | **MÉDIO** (acesso interno) | RLS + logs (S-02, S-04) | S0/S1 |
| OP-06 — Telemetria | **BAIXO** (pós-S-08) | Autocapture off + consentimento | S0+ |
| OP-07 — Outbound (futuro) | **MÉDIO**/ALTO | Opt-in + descadastro | S2+ |
| OP-08 — Auditoria | **BAIXO** | Anonimização | S2 |
| OP-09 — Suporte/DPO | **MÉDIO** | Prova de posse | S2 |

---

## Histórico de Versões

| Versão | Data | Autor | Alterações |
|---|---|---|---|
| 1.0 | {{DATA_PUBLICACAO}} | {{DPO_NOME}} | Versão inicial |

---

## CI Gate (Proposta de ADR)

Para garantir que o RDM se mantenha atualizado, toda migration que:
- Criar nova tabela com coluna de dado pessoal;
- Adicionar coluna PII a tabela existente;
- Alterar fluxo de compartilhamento ou transferência internacional;

DEVE incluir atualização deste RDM no mesmo PR. O CI deve verificar:
```bash
# Exemplo de gate — falhar se migration PII sem atualização do RDM
if git diff --name-only HEAD~1 | grep -q "supabase/migrations/.*pii"
   && ! git diff --name-only HEAD~1 | grep -q "docs/rdm/"; then
  echo "❌ Migration PII detectada sem atualização do RDM"
  exit 1
fi
```

---

## Placeholders a Preencher

| Placeholder | Responsável |
|---|---|
| `{{RAZAO_SOCIAL}}` | Cliente |
| `{{CNPJ}}` | Cliente |
| `{{DPO_NOME}}` | Cliente |
| `{{DPO_EMAIL}}` | Cliente |
| `{{DATA_PUBLICACAO}}` | Cliente + Dev |
| `{{EMAIL_PROVIDER}}` | Dev |
| `{{WHATSAPP_PROVIDER}}` | Dev (quando implementado) |
| `{{DEPENDE_DO_PROVIDER}}` | Dev |

---

## Disclaimer

*O RDM é um instrumento interno de governança (accountability). Manter atualizado é exigência legal contínua — não algo que se faz uma única vez. DPO assina e data cada versão. A existência e atualização são prova de boa-fé e programa de governança (art. 50), mas não substitui RIPD nem auditorias.*
