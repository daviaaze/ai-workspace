# Política de Retenção e Descarte de Dados Pessoais

> **Versão:** 1.0 | **Data efetiva:** {{DATA_PUBLICACAO}}
> **Controlador:** {{RAZAO_SOCIAL}}, CNPJ {{CNPJ}}
> **DPO:** {{DPO_NOME}} — {{DPO_EMAIL}}
> **Subprompt:** 07 — Política de Retenção
> **Alimenta findings:** L-04, F-01, D-5
> **Referências cruzadas:** Política de Privacidade (01), RDM (08), RIPD (05)

---

## 1. Princípios Gerais

1.1. Esta Política estabelece os prazos de retenção e os procedimentos de eliminação dos dados pessoais tratados pela Meia-Entrada, em conformidade com:
   - **LGPD** arts. 6º (adequação, necessidade, finalidade), 15 (eliminação), 16 (exceções), 18 (direito à eliminação), 46 (segurança), 50 (governança);
   - **Resolução CD/ANPD nº 15/2024** (eliminação após incidente);
   - **Guia Orientativo de Retenção e Eliminação** (ANPD, 2025 — consulta pública);
   - **Lei 12.933/2013** (meia-entrada — validade da CIE).

1.2. **Princípios:**
   - **Minimização:** apenas os dados estritamente necessários a cada finalidade;
   - **Finalidade:** retenção apenas pelo tempo exigido pela finalidade original;
   - **Eliminação:** assim que cessada a finalidade (art. 16), exceto nas hipóteses legais de guarda;
   - **Proteção do titular:** prazos mais restritivos para dados sensíveis;
   - **Rastreabilidade:** toda eliminação é registrada em `carteira_deletion_audit_log`.

---

## 2. Inventário de Categorias de Dados

Baseado no schema das tabelas `carteiras`, `carteira_endereco`, `carteira_arquivos`, `entidades` e storage de fotos.

| # | Categoria | Dados (colunas) | Onde está | Sensível? |
|---|---|---|---|---|
| C01 | Identificadores governamentais | CPF (formatação), RG, órgão emissor, UF | `carteiras` | Não |
| C02 | Dados pessoais de identificação | nome, filiação (nome_mae, nome_pai), data de nascimento | `carteiras` | Não |
| C03 | Dados acadêmicos | matrícula, curso, período, instituição, emissor, ensino, entidade_id | `carteiras` | Não |
| C04 | Contato | e-mail, telefone | `carteiras` | Não |
| C05 | Endereço (condicional) | CEP, rua, número, complemento, bairro, cidade, UF | `carteira_endereco` | Não |
| C06 | Dado sensível — fotografia | arquivo de imagem (JPEG/PNG) | Storage Supabase (bucket privado) | **Sim** — biométrico (art. 11) |
| C07 | Documentos comprobatórios | foto do documento, comprovante de matrícula | `carteira_arquivos` + storage | **Sim** — pode conter foto |
| C08 | Metadados operacionais | status (histórico), tokens, UUIDs, datas de criação/atualização, usuário de criação | `carteiras`, `carteira_deletion_audit_log` | Não |
| C09 | Token de validação pública | token (base36), UUID | `carteiras` | Não |
| C10 | Entidade emissora | razão social, CNPJ, nome fantasia, responsável, contrato | `entidades`, contratos | Não |
| C11 | Logs de operação | registros de INSERT/UPDATE/DELETE em PII | `carteira_deletion_audit_log`, logs servidor | Não |
| C12 | Telemetria (PostHog) | eventos de navegação anonimizados | PostHog Cloud | Não — anonimizado |

---

## 3. Tabela de Retenção

### 3.1 Categorias comuns (aplicam-se a C01-C05, C08-C10)

| Categoria | Base de coleta | Período ativo | Período pós-utilidade | Destino final | Gatilho início | Gatilho fim | Justificativa |
|---|---|---|---|---|---|---|---|
| **C01-C05** (cadastro ativo) | Formulário web | Durante validade da carteirinha (até 31/03/ano+1) | **12 meses** após o fim da validade | **Hard delete** | Emissão | 12 meses após validade | Art. 7º, V (execução de contrato). Permite reemissão dentro do ano letivo + janela de reclamações. Lei 12.933/2013. |
| **C05** (endereço) | Formulário web (se entrega domiciliar) | Até a entrega ser concluída | **30 dias** após entrega confirmada | **Hard delete** | Coleta | 30 dias após entrega | Minimização (art. 6º, III). Endereço só é necessário para a entrega. |
| **C08** (metadados) | Sistema | Indefinido (dados anonimizados/pseudonimizados) | **5 anos** para logs de auditoria (DELETE/UPDATE em PII) | **Anonimização** (remoção de CPF/nome) | Criação do registro | 5 anos | Governança (art. 50) + auditoria. Dados anonimizados não são pessoais (art. 13). |
| **C09** (token) | Sistema | Durante validade da carteirinha | **90 dias** após fim da validade | **Anonimização** (hash) | Emissão | 90 dias após validade | Segurança — token de validação deve expirar. |
| **C10** (entidade) | Onboarding + contrato | Enquanto durar o contrato | **5 anos** após rescisão contratual | **Arquivo criptografado** | Contrato vigente | 5 anos após rescisão | Obrigação legal (art. 7º, II) — guarda de contratos. |

### 3.2 Dados sensíveis e de alto risco (C06-C07)

| Categoria | Base de coleta | Período ativo | Período pós-utilidade | Destino final | Gatilho início | Gatilho fim | Justificativa |
|---|---|---|---|---|---|---|---|
| **C06** — **Fotografia (biométrico)** | Upload no formulário | Durante validade da carteirinha (até 31/03/ano+1) | **6 meses** após o fim da validade | **Hard delete** do storage + `carteira_arquivos` | Upload | 6 meses após validade | Minimização agressiva para dado sensível (art. 11 + art. 6º, III). Prazo mais curto de toda a tabela. |
| **C07** — Documentos comprobatórios | Upload no formulário | Durante validade da carteirinha | **6 meses** após o fim da validade | **Hard delete** | Upload | 6 meses após validade | Dados sensíveis: prazos mais restritivos. |

### 3.3 Logs e telemetria

| Categoria | Base de coleta | Período ativo | Período pós-utilidade | Destino final | Gatilho início | Gatilho fim | Justificativa |
|---|---|---|---|---|---|---|---|
| **C11** — Logs de operação | Sistema (audit trigger) | **5 anos** | — | **Arquivo criptografado** (sem delete) | Criação | 5 anos | Art. 50 (governança). Necessário para demonstrar accountability. |
| **C12** — Telemetria (PostHog) | PostHog SDK | Conforme configuração PostHog | **14 meses** (padrão PostHog) | **Delete automático** (retenção configurada) | Evento | Conforme política do produto | Consentimento (art. 7º, I) — sem PII, apenas navegação. |

---

## 4. Procedimento de Eliminação

### 4.1 Soft-delete → Hard-delete

Toda carteira passa por duas fases:

```
Status = 'Cadastrada' | 'Autorizada' | 'Em Produção' | 'Enviada' | 'Entregue'
    → solicitação de exclusão ou fim de prazo de retenção
    → Status = 'Removida' (soft-delete)
    → carimbo deleted_at = NOW()
    → aguarda janela de hard-delete (conforme tabela §3)
    → job noturno executa hard-delete
```

### 4.2 Passos do Hard-delete (job agendado)

1. **Registrar** em `carteira_deletion_audit_log`: `carteira_id`, `cpf_anonymized` (hash SHA-256 do CPF), `entity_id`, `status_anterior`, `deleted_at`, `trigger` (retenção | titular | judicial)
2. **Remover arquivos do storage** (foto + documentos comprobatórios): chamada `supabase.storage.delete(bucket, path)`
3. **Hard-delete**:
   - `DELETE FROM carteira_endereco WHERE carteira_id = ?`
   - `UPDATE carteira_arquivos SET storage_removed_at = NOW() WHERE carteira_id = ?` (mantém registro da existência do arquivo, remove o conteúdo)
   - `UPDATE carteiras SET ... removed_at = NOW(), ...` OU `DELETE FROM carteiras` — conforme definição do D-5 (Arquiteto)
4. **Token de validação**: invalidar (hash do token vira `NULL` ou marcado como expirado)
5. **Notificar titular** (se eliminação foi solicitada pelo titular): e-mail de confirmação

### 4.3 Anonimização vs Hard-delete

| Dado | Destino |
|---|---|
| CPF (em logs de auditoria) | Hash SHA-256 (anonimização) |
| Nome (em logs) | Remover completamente |
| E-mail (em logs) | Remover completamente |
| Telefone (em logs) | Remover completamente |
| Endereço | Hard-delete |
| Foto | Hard-delete do storage + remover referência |
| Metadados (status, datas) | Manter anonimizados |

### 4.4 Backups

4.4.1. Backups do banco de dados (gerenciados pelo Supabase) mantêm dados por até **N dias** (conforme política do operador). Dados em backup não são considerados "em tratamento" para fins de retenção, desde que:
   - O backup não seja acessível para consulta operacional;
   - O backup seja criptografado;
   - Haja prazo máximo de retenção do backup (configurar no operador).

4.4.2. **Recomendação técnica:** Ajustar a política de backup do Supabase para **retenção máxima de 30 dias** de backups diários + 1 backup semanal (para dados sensíveis). Após hard-delete, o dado será eliminado dos backups no ciclo natural de rotação.

### 4.5 Exceções do Art. 16

O direito à eliminação (art. 18, VI) não se aplica quando a retenção for necessária para:

| Hipótese legal | Aplicação |
|---|---|
| **Obrigação legal ou regulatória** | Guarda de contratos de co-controladora por 5 anos; registros contábeis. |
| **Exercício regular de direitos** | Dados necessários para defesa em processo judicial ou administrativo. |
| **Pesquisa por órgão de pesquisa** | Não aplicável atualmente. |
| **Transferência a terceiro** | Não aplicável (dados são eliminados, não transferidos). |
| **Uso exclusivo do controlador com anonimização** | Logs de auditoria anonimizados (sem possibilidade de reidentificação). |

---

## 5. Direito à Eliminação pelo Titular

5.1. O titular pode solicitar a eliminação de seus dados a qualquer momento (art. 18, VI LGPD).

5.2. **Procedimento:**
   - Solicitação via `/direitos` → protocolo gerado
   - Verificação de identidade (prova de posse de e-mail/telefone)
   - Confirmação se aplica exceção do art. 16
   - Se não aplicável:
     - Status da carteira → 'Removida'
     - Início da janela de eliminação → hard-delete conforme §3
   - Se aplicável (ex.: carteira com ação judicial):
     - Informar titular sobre a impossibilidade + motivo + prazo

5.3. **Prazo:** até 15 dias corridos para iniciar o procedimento (art. 19, §1º).

5.4. **Registro:** cada eliminação fica registrada em `carteira_deletion_audit_log` com: `cpf_anonymized` (hash), `carteira_id`, `trigger = 'titular'`, `deleted_at`, `protocolo_id`.

---

## 6. Revisão Periódica

6.1. Esta Política será revisada:
   - **Anualmente** (ou a cada mudança relevante de tratamento);
   - **A cada nova categoria de dado** (nova migration em tabela PII);
   - **Após incidente de segurança** com vazamento de dados.

6.2. Cada revisão gera nova versão com data e autor.

| Versão | Data | Autor | Alterações |
|---|---|---|---|
| 1.0 | {{DATA_PUBLICACAO}} | {{DPO_NOME}} | Versão inicial |

---

## 7. Execução pelo Job de Eliminação

7.1. O job agendado (Vercel Cron / Supabase `pg_cron` / Edge Function) deve executar **diariamente** a verificação de prazos expirados.

### 7.2 Lógica do Job

```
PARA CADA carteira WHERE status = 'Removida':
    SE deleted_at + janela_hard_delete <= NOW():
        EXECUTAR hard_delete(carteira_id)

PARA CADA carteira WHERE validade < NOW() - periodo_pos_utilidade:
    EXECUTAR soft_delete(carteira_id, trigger = 'retencao')
```

### 7.3 Critério de Aceite Técnico

- Job testado com dados sintéticos em múltiplos estados (carteira ativa, removida, expirada, com endereço, sem endereço, com foto, sem foto, vinculada a ação judicial)
- Vitest ou similar validando a lógica de seleção e eliminação
- Log de execução: `job_retention_execution_log(id, run_at, carteiras_deleted, errors, duration_ms)`
- **Rollback:** em caso de erro, job falha e não confirma transação

---

## Placeholders a Preencher

| Placeholder | Responsável |
|---|---|
| `{{RAZAO_SOCIAL}}` | Cliente |
| `{{CNPJ}}` | Cliente |
| `{{DPO_NOME}}` | Cliente |
| `{{DPO_EMAIL}}` | Cliente |
| `{{DATA_PUBLICACAO}}` | Cliente + Dev |
| `{{N_DIAS_BACKUP}}` | Dev (configurar política de backup Supabase) |

---

## Disclaimer

*Política técnico-jurídica. Definições de prazo só valem após validação pelo DPO e (recomendado) advogado OAB. A entrada em vigor exige publicação e criação do job de eliminação correspondente. Prazos marcados com * são estimativas provisórias.*

**Revisão pendente:** [ ] OAB validar prazos; [ ] DPO confirmar janela de hard-delete; [ ] Dev confirmar viabilidade técnica do job de eliminação; [ ] Configurar política de backup do Supabase.
