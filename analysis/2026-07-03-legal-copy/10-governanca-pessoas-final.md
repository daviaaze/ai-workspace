# Governança de Pessoas e Processos

> **Versão:** 1.0 | **Data:** {{DATA}}
> **Controlador:** {{RAZAO_SOCIAL}} | CNPJ {{CNPJ}}
> **DPO:** {{DPO_NOME}} — {{DPO_EMAIL}}
> **Subprompt:** 10 — Governança Pessoas e Processo
> **Equipe atual:** Davi (fundador/dev) + até 4 devs adicionais
> **Alimenta findings:** L-05, art. 50 LGPD

---

## 1. Política de Acesso à Produção (PAP)

### 1.1 Princípios

- **Menor privilégio:** Cada pessoa tem acesso apenas ao estritamente necessário para sua função.
- **Just-in-time (JIT):** Acesso elevado (produção) é concedido sob demanda, com prazo limitado.
- **MFA obrigatório:** Autenticação multifator em todos os serviços de produção.
- **Auditável:** Todo acesso a PII em produção é registrado em `access_audit_log`.
- **Separação de ambientes:** Produção isolada de staging/desenvolvimento; dados sintéticos em ambientes não-produtivos.

### 1.2 Matriz de Acesso

| Papel | Pessoa | Acesso | JIT? | MFA? | Log? | Justificativa |
|---|---|---|---|---|---|---|
| **Fundador/Dev** | Davi | Supabase Studio, DB, Vercel prod, Storage, GitHub admin, Secrets | ✅ JIT para ações específicas | ✅ | ✅ | Operações críticas; deploy |
| **Dev 1** | {{DEV_1}} | Supabase Studio (leitura only), DB (SELECT em staging), Vercel dev | ✅ JIT | ✅ | ✅ | Desenvolvimento e suporte |
| **Dev 2** | {{DEV_2}} | Git push (CI/CD), Vercel preview, Supabase dev | ✅ JIT | ✅ | ✅ | Feature development |
| **DPO** | {{DPO_NOME}} | Admin (painel LGPD), access_audit_log, `lgpd_*` tabelas (leitura) | ❌ Persistente (auditoria) | ✅ | ✅ | Supervisão de compliance |
| **DevOps (futuro)** | {{DEVOPS}} | Infra, pipelines, vault, rotação de chaves | ✅ JIT | ✅ | ✅ | Operações de produção |

### 1.3 Procedimento de Acesso JIT

1. Solicitação via {{CANAL_SOLICITACAO}} (Slack/e-mail/ticket)
2. Aprovação: DPO (para PII) ou Fundador (para infra)
3. Concessão por tempo limitado: {{TEMPO_JIT}} horas
4. Registro em `access_audit_log`: `pessoa`, `recurso`, `inicio`, `fim`, `motivo`, `aprovador`
5. Revogação automática ao expirar

### 1.4 Supabase Studio — Regras Específicas

| Ação | Permissão | Observação |
|---|---|---|
| Visualizar tabelas PII (`carteiras`, `carteira_arquivos`, `lgpd_*`) | Somente leitura | Nunca em produção sem JIT aprovado |
| Editar schema/migration | Via CI/CD (não via Studio) | Migrations versionadas e revisadas |
| Visualizar secrets do projeto | Apenas vault (1Password/Doppler) | Nunca em `.env` local |
| Executar queries SQL em produção | JIT + aprovador + log | Apenas para incidentes |

### 1.5 Separação de Ambientes

| Ambiente | Dados | Acesso |
|---|---|---|
| **Produção** | Dados reais de estudantes | Restrito (JIT) |
| **Staging** | Cópia anonimizada | Devs (acesso normal) |
| **Dev** | Dados sintéticos (fixtures) | Todos |
| **Local** | Dados sintéticos | Pessoa específica |

---

## 2. NDA e Compromisso LGPD

### 2.1 NDA Padrão — Cláusulas Essenciais

1. **Partes:** Meia-Entrada ({{RAZAO_SOCIAL}}) ↔ Pessoa física ({{NOME_PESSOA}}), doravante "Parte Receptora"
2. **Objeto:** Proteção de Informações Confidenciais, incluindo dados pessoais de titulares (estudantes) acessados durante a prestação de serviços
3. **Informações Confidenciais:** dados pessoais (art. 5º LGPD), código-fonte proprietário, chaves de API, segredos de infraestrutura, política de segurança
4. **Obrigações da Parte Receptora:**
   - Não divulgar, copiar ou utilizar para fim diverso
   - Manter medidas de segurança compatíveis com as do Controlador
   - Não armazenar dados pessoais em dispositivos pessoais
   - Notificar imediatamente qualquer violação
5. **Vigência:** Durante o vínculo + **5 (cinco) anos** após o término
6. **Compromisso LGPD (anexo):** A Parte Receptora declara ciência de que:
   - O tratamento não autorizado de dados pessoais configura violação à LGPD (art. 42)
   - A violação pode resultar em sanções administrativas (art. 52) e responsabilização civil solidária
   - O dever de guarda persiste mesmo após o término do vínculo
7. **Foro:** {{COMARCA}}
8. **Penalidade:** Multa compensatória de {{VALOR_MULTA}} por violação, sem prejuízo de perdas e danos

### 2.2 Treinamento Mínimo

Antes de obter acesso à produção, cada pessoa deve concluir:

| Módulo | Duração | Conteúdo |
|---|---|---|
| LGPD Básico | 30 min | Princípios, dados sensíveis, direitos do titular, consequências |
| Segurança da Informação | 20 min | Senhas, MFA, phishing, dispositivo seguro |
| Tratamento de Dados Pessoais | 20 min | O que pode/não pode fazer com PII, como reportar incidente |
| Uso da Plataforma Supabase | 20 min | Acesso JIT, logs, proibições |

**Registro:** `lgpd_people_log.treinamento_em = data da conclusão`

---

## 3. Offboarding Rigoroso

### 3.1 Checklist de Offboarding

Quando uma pessoa (dev, operador, DPO, administrador) sai da Meia-Entrada:

- [ ] Notificar todas as plataformas: Supabase, Vercel, GitHub, {{EMAIL_PROVIDER}}, PostHog, Doppler/1Password
- [ ] Revogar chaves de API e tokens de acesso
- [ ] Remover do GitHub (organization e repositórios)
- [ ] Resetar MFA e sessões ativas
- [ ] Auditar ações nos últimos 60 dias (quais tabelas PII consultou, quais queries executou, quais chaves usou)
- [ ] Coletar device corporativo (se houver)
- [ ] Relembrar NDA + Compromisso LGPD (enviar cópia por e-mail)
- [ ] Transferir responsabilidades documentadas
- [ ] Registrar em `lgpd_people_log`

### 3.2 Registro em `lgpd_people_log`

| Campo | Exemplo |
|---|---|
| `pessoa` | Nome completo |
| `papel` | Dev |
| `acesso_producao_em` | 2026-01-15 |
| `revogado_em` | 2026-07-15 |
| `motivo` | Desligamento voluntário |
| `nda_versao` | v1.0 |
| `treinamento_em` | 2026-01-10 |
| `auditoria_pre_offboarding` | Link para relatório de auditoria |

---

## 4. Gestão de Credenciais e Senhas Hardcoded

### 4.1 Situação Atual

| Local | Problema | Gravidade | Ação |
|---|---|---|---|
| `e2e/fixtures/auth.ts` | Credenciais de teste versionadas | **Alta** | Mover para secrets de CI (GitHub Actions) |
| `create-test-users.js` | Senhas em texto claro | **Alta** | Usuários de teste com senhas geradas por CI |
| `.env.example` | Placeholders OK | **Baixo** | Manter como está |
| Histórico git | Possíveis secrets commitados no passado | **Alta** | Rotacionar chaves; git filter-repo em secrets antigos |

### 4.2 CI Gate (Secret Scanning)

Adicionar ao CI:

```yaml
- name: Secret scanning (gitleaks)
  uses: gitleaks/gitleaks-action@v2
  with:
    config-path: .github/gitleaks.toml
```

Bloqueio: pipeline falha se secret for detectado.

### 4.3 Boas Práticas

- `SUPABASE_SERVICE_KEY` somente em vault de secrets (1Password, Doppler, GitHub Secrets)
- Nenhum `.env` versionado
- Chaves de teste são geradas por CI, não versionadas
- Rotação trimestral de chaves de produção

---

## 5. Governança de Chaves Externas

| Serviço | Chave/Secret | Onde está | Dono | DPA? | Rotação |
|---|---|---|---|---|---|
| Supabase | service_role | Vault (1Password?) + GitHub Secrets ✅ | Davi | Em andamento (S2) | Trimestral |
| Supabase | anon key | `NEXT_PUBLIC_SUPABASE_ANON_KEY` (env) | Davi | — | Trimestral |
| Vercel | Deploy token | GitHub Secrets | Devs | Em andamento | Anual |
| PostHog | `NEXT_PUBLIC_POSTHOG_KEY` | env + GitHub | Davi | Em andamento | Anual |
| GitHub | PAT (Personal Access Token) | Cada dev | Individual | — | Revogar no offboarding |
| {{EMAIL_PROVIDER}} | API key | GitHub Secrets (futuro) | Devs | Futuro | Conforme política |

---

## 6. Logs de Auditoria

### 6.1 Expansão do Audit Log

Migração necessária: `carteira_deletion_audit_log` → `access_audit_log`

```sql
-- Tabela expandida (substitui a existente ou adiciona)
CREATE TABLE access_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  carteira_id UUID REFERENCES carteiras(id) ON DELETE SET NULL,
  action VARCHAR(50) NOT NULL, -- 'SELECT', 'UPDATE', 'DELETE', 'DOWNLOAD_STORAGE'
  table_name VARCHAR(100) NOT NULL,
  pessoa_id UUID NOT NULL,
  pessoa_nome VARCHAR(255) NOT NULL,
  ip_hash VARCHAR(64), -- hash do IP, não IP integral
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB -- informações adicionais (query, motivo JIT, etc.)
);

-- Índices
CREATE INDEX idx_access_audit_carteira ON access_audit_log(carteira_id);
CREATE INDEX idx_access_audit_pessoa ON access_audit_log(pessoa_id);
CREATE INDEX idx_access_audit_action ON access_audit_log(action);
```

### 6.2 O que Logar

| Operação | Local | Action |
|---|---|---|
| SELECT em `carteiras` (admin) | `getDadosCarteira.ts` | `SELECT` |
| DOWNLOAD de foto (storage) | `getFotoEstudante.ts` | `DOWNLOAD_STORAGE` |
| UPDATE em `carteiras.status` | Server Actions admin | `UPDATE` |
| DELETE / soft-delete | Job de eliminação / titular | `DELETE` |
| Acesso JIT concedido | Sistema de JIT | `JIT_GRANT` |
| Acesso JIT expirado | Sistema de JIT | `JIT_EXPIRE` |

### 6.3 Retenção dos Logs

- Logs de auditoria: **5 anos** (art. 50 LGPD + governança)
- Acesso restrito: DPO + administradores
- Dados anonimizados (CPF → hash, nome removido)

---

## 7. Programa Anual de Governança (Art. 50)

### 7.1 Calendário

| Periodicidade | Atividade | Responsável | Registro |
|---|---|---|---|
| **Trimestral** | Revisão de acessos (matriz de acesso) | DPO + Dev lead | `lgpd_people_log` |
| **Trimestral** | Revisão de chaves/secrets | Dev lead | Access audit log |
| **Semestral** | Teste de backup/restore | Dev lead | Relatório |
| **Anual** | Treinamento LGPD (refresher) | DPO | `lgpd_people_log` |
| **Anual** | Revisão do RIPD | DPO | RIPD v2.0+ |
| **Anual** | Revisão de contratos (operador + co-controladora) | DPO + Jurídico | `lgpd_contracts` |
| **S5** | Tabletop exercise (runbook 06) | DPO + Equipe | Postmortem |
| **Pós-incidente** | Postmortem + ações corretivas | Incident Commander | Postmortem + Runbook update |

### 7.2 Tabela de Governança

```sql
CREATE TABLE IF NOT EXISTS lgpd_governance_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  activity VARCHAR(255),         -- ex.: "Revisão trimestral de acessos"
  responsible VARCHAR(100),      -- ex.: "DPO"
  due_date DATE,
  completed_at TIMESTAMPTZ,
  status VARCHAR(20),            -- 'pending' | 'completed' | 'overdue'
  evidence TEXT,                 -- link para documento/relatório
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 8. Resumo de Esforço e Custo

| Item | Esforço (dev) | Custo (financeiro) | Sprint |
|---|---|---|---|
| Política de Acesso à Produção | 2h (documento) + 4h (JIT) | Nenhum (ferramentas gratuitas) | S2 |
| NDA padrão + Compromisso LGPD | 1h (revisar modelo) | R$ 0 (template pronto) | S2 |
| Treinamento LGPD | 4h (preparar) + 1h/pessoa | R$ 0 (interno) | S2 |
| Offboarding checklist | 1h | Nenhum | S2 |
| Secret scanning (CI) | 2h (configurar gitleaks) | Nenhum (open source) | S1 |
| Expansão do audit log | 8h (migration + triggers) | Nenhum | S2 |
| Rotação trimestral de chaves | 1h/trimestre | Nenhum | Contínuo |
| Tabletop exercise | 3h (S5) | Nenhum | S5 |

---

## 9. Histórico

| Versão | Data | Autor | Alterações |
|---|---|---|---|
| 1.0 | {{DATA}} | {{DPO_NOME}} | Versão inicial |

---

## Placeholders

| Placeholder | Responsável |
|---|---|
| `{{RAZAO_SOCIAL}}` | Cliente |
| `{{CNPJ}}` | Cliente |
| `{{DPO_NOME}}` | Cliente |
| `{{DPO_EMAIL}}` | Cliente |
| `{{DEV_1}}` | Cliente |
| `{{DEV_2}}` | Cliente |
| `{{DEVOPS}}` | Cliente (quando contratado) |
| `{{CANAL_SOLICITACAO}}` | Cliente (Slack/e-mail/ticket) |
| `{{TEMPO_JIT}}` | Cliente (sugestão: 4h) |
| `{{COMARCA}}` | Cliente |
| `{{VALOR_MULTA}}` | Cliente + Jurídico |
| `{{EMAIL_PROVIDER}}` | Dev |
| `{{DATA}}` | Cliente |

---

## Disclaimer

*Documento de governança interno que materializa o dever de accountability (art. 50). A implantação depende de designação de responsável (DPO fractional ou integral) e alocação de tempo da equipe de engenharia. Proposto para startup de pequeno porte — ajustável conforme crescimento.*

**Revisão pendente:** [ ] DPO validar política de acesso; [ ] Dev configurar secret scanning; [ ] Implementar migration do access_audit_log; [ ] Aplicar NDA à equipe atual.
