# Runbook de Resposta a Incidentes + Notificação ANPD (72h Úteis)

> **Versão:** 1.0 | **Data:** {{DATA}}
> **Controlador:** {{RAZAO_SOCIAL}} | CNPJ {{CNPJ}}
> **DPO:** {{DPO_NOME}} — {{DPO_EMAIL}}
> **Subprompt:** 06 — Runbook de Incidente
> **Base legal:** Art. 48 LGPD | Res. CD/ANPD nº 15/2024 | NIST SP 800-61 R2

---

## 1. Classificação de Incidentes

| Tipo | Descrição | Gravidade | Exemplo | Notificação ANPD? | Notificação Titular? |
|---|---|---|---|---|---|
| **A** | Vazamento de PII em massa | **Crítica** | Service_role comprometido; scraping via rota pública | ✅ Sim (72h úteis) | ✅ Sim (risco/dano relevante) |
| **B** | Vazamento de dado sensível (foto) | **Crítica** | Storage público; acesso indevido a bucket | ✅ Sim (72h úteis) | ✅ Sempre (danos potenciais graves) |
| **C** | Incidente de segurança sem PII | **Média** | DDoS, indisponibilidade, ataque a servidor sem exfiltração | ❌ Não | ❌ Não |
| **D** | Fraude na emissão | **Alta** | Entidade emite para não-estudante; falsificação documental | ⚠️ Caso a caso | ⚠️ Titular afetado se houver dano |
| **E** | Perda acidental de dados | **Média** | Deletion acidental sem backup | ✅ Sim (se PII perdida) | ✅ Sim |
| **F** | Acesso não autorizado interno | **Alta** | Admin de entidade acessa dados de outra entidade fora do escopo | ✅ Sim | ✅ Sim |

---

## 2. Atribuições (RBAC da Resposta)

| Papel | Quem | Responsabilidade |
|---|---|---|
| **Incident Commander** | DPO ({{DPO_NOME}}) | Declara incidente confirmado; coordena resposta; decide notificações |
| **Primary Responder** | {{DEV_ADMIN_1}} | Executa contenção técnica (rotação de chaves, isolamento, shutdown) |
| **Secondary Responder** | {{DEV_ADMIN_2}} | Preserva evidências (logs, snapshots, storage); documenta timeline |
| **Legal Liaison** | {{ADVOGADO_OAB}} | Revisa notificações; assessora sobre obrigações legais; preserva provas penais |
| **Communications Lead** | {{DIRETORIA}} | Comunicação pública (se necessária); aprova comunicados |
| **Titular Contact** | DPO | Notifica titulares afetados; responde a perguntas |

---

## 3. Timeline de Resposta

```
T0 — DETECÇÃO
    ├── Alerta automático (Sentry/PostHog/logs) ou report externo
    └── Quem: Primary Responder avalia em ≤ 1h

T0+1h — CLASSIFICAÇÃO
    ├── Incident Commander declara tipo (A-F) e gravidade
    └── Se Tipo A/B: comunicar DPO + Diretoria imediatamente

T0+2h — CONTENÇÃO
    ├── Rotation de chaves comprometidas (service_role, API keys)
    ├── Isolamento de rota/serviço comprometido
    ├── Restringir acesso ao bucket/banco
    └── Salvar snapshot forense (preservar provas penais)

T0+4h — ERADICAÇÃO
    ├── Remover acesso do atacante (se identificado)
    ├── Aplicar patch/hotfix
    ├── Verificar backdoors
    └── Refresh de tokens de sessão de todos os usuários

T0+8h — NOTIFICAÇÃO INTERNA
    ├── DPO + Diretoria + Jurídico briefados
    └── Decisão: notificar ANPD? Notificar titulares?

T0+48h — NOTIFICAÇÃO ANPD (se aplicável)
    ├── Preencher formulário eletrônico ANPD
    ├── Prazo máximo: 72h úteis
    └── Se faltarem dados: comunicar gradativamente

T0+72h — NOTIFICAÇÃO AOS TITULARES (se aplicável)
    ├── E-mail/template para afetados
    └── Aviso público (se necessário)

T0+30d — POSTMORTEM
    ├── Documentação do incidente
    ├── Atualização de políticas/runbook
    └── Treinamento da equipe
```

---

## 4. Notificação à ANPD (Res. CD/ANPD nº 15/2024)

### 4.1 Quando notificar

☑️ Incidente de segurança com **dados pessoais** que possa acarretar **risco ou dano relevante** aos titulares.

**Prazo:** Até **72 (setenta e duas) horas úteis** da ciência do incidente.

### 4.2 Dados necessários (formulário eletrônico ANPD)

| Campo | Responsável | Preenchimento |
|---|---|---|
| Data e hora da ciência do incidente | Incident Commander | {{DATA_CIENCIA}} |
| Data e hora do incidente (estimada) | Primary Responder | {{DATA_INCIDENTE}} |
| Natureza do incidente | Incident Commander | Vazamento / Acesso não autorizado / Modificação / Perda / Destruição |
| Categorias de dados pessoais afetados | Primary Responder | [ ] Identificadores [ ] Financeiros [ ] **Sensível (biométrico/foto)** [ ] Acadêmicos |
| Categorias de titulares | Incident Commander | Estudantes / Responsáveis legais |
| Número estimado de titulares afetados | Primary Responder | {{ESTIMATIVA_TITULARES}} |
| Circunstâncias do incidente | Incident Commander | Descrição detalhada em {{X}} palavras |
| Medidas de contenção adotadas | Primary Responder | Chaves rotacionadas / Rota isolada / Acesso revogado / Backup preservado |
| Consequências adversas (reais ou potenciais) | Legal Liaison | Uso indevido de PII / Fraude / Exposição de dado sensível / Dano à imagem |
| Medidas para reverter/minimizar danos | Incident Commander | Notificação a titulares / Troca de senhas / Monitoramento de CPF |
| Contato do Encarregado (DPO) | DPO | {{DPO_NOME}} — {{DPO_EMAIL}} |

### 4.3 Comunicação gradativa (se faltarem dados)

Se no prazo de 72h úteis nem todos os dados estiverem disponíveis, comunicar **imediatamente** os dados disponíveis e complementar tão logo seja possível. A ANPD pode solicitar informações complementares.

---

## 5. Notificação aos Titulares (Art. 48 LGPD)

### 5.1 Critério: Risco ou dano relevante

Para **dado sensível (foto — biométrico)**, a comunicação ao titular é **sempre obrigatória** (dano potencial grave — art. 11 + art. 48).

### 5.2 Template — E-mail ao Titular

**Assunto:** [Meia-Entrada] Notificação de incidente de segurança — Ação recomendada

```
Olá {{NOME}},

Identificamos um incidente de segurança envolvendo dados pessoais da plataforma Meia-Entrada (Controladora: {{RAZAO_SOCIAL}}, CNPJ {{CNPJ}}).

**O que aconteceu?**
{{DESCRICAO_INCIDENTE_CLARA}}

**Quais dados foram afetados?**
{{LISTA_DADOS_AFETADOS}} — incluindo {{DADOS_SENSIVEIS_SE_APLICAVEL}}.

**O que fizemos?**
{{MEDIDAS_CONTENCAO}}

**O que você deve fazer?**
- Monitore seu CPF e e-mail nos próximos meses (Recomendação: {{SERVICO_MONITORAMENTO}});
- Entre em contato conosco se notar uso indevido de seus dados;
- Em caso de dúvidas, nosso Encarregado (DPO) está disponível.

**Contato do DPO:**
{{DPO_NOME}} — {{DPO_EMAIL}}

**Seus direitos:**
Você tem direito de solicitar acesso, correção e eliminação de seus dados (art. 18 LGPD), além de notificar a ANPD (www.gov.br/anpd).

Atenciosamente,
{{DPO_NOME}}
Encarregado (DPO) — Meia-Entrada
```

### 5.3 Template — Aviso Público (site)

> **⚠️ Comunicado — {{DATA}}**
>
> A Meia-Entrada identificou um incidente de segurança em {{DATA_INCIDENTE}}. Os dados potencialmente afetados incluem {{CATEGORIAS}}. As medidas de contenção foram adotadas imediatamente ({{MEDIDAS}}). Titulares afetados estão sendo notificados individualmente por e-mail.
>
> DPO: {{DPO_EMAIL}}

---

## 6. Preservação de Evidências

### 6.1 Logs

| Fonte | O que preservar | Período |
|---|---|---|
| Supabase (db) | Logs de queries, autenticação, RLS violações | Mínimo 90 dias |
| Vercel | Logs de acesso a rotas, serverless functions | 90 dias |
| Supabase (auth) | Logins, tentativas de acesso, criação de usuários | 90 dias |
| `carteira_deletion_audit_log` | Todos os registros (logs são imutáveis) | 5 anos |
| GitHub (audit log) | Commits, deploys, acesso a secrets | 90 dias |

### 6.2 Snapshot forense

Antes de qualquer ação de contenção que altere estado:
1. Capturar snapshot do banco de dados (pg_dump);
2. Preservar logs de acesso do período suspeito;
3. Copiar arquivos de storage (bucket) em estado comprometido;
4. Documentar estado do ambiente antes da contenção.

---

## 7. Pós-Incidente — Postmortem

Estrutura obrigatória do documento postmortem:

1. **Resumo executivo** (1 parágrafo)
2. **Timeline** (deteção → contenção → erradicação → recuperação → notificação)
3. **Causa raiz** (técnica e/ou humana)
4. **Impacto** (dados expostos, titulares afetados, consequências)
5. **O que funcionou** (resposta rápida, comunicação)
6. **O que não funcionou** (lacuna de detecção, falta de acesso, atraso)
7. **Ações corretivas** (com dono e prazo)
8. **Lições aprendidas** (para treinamento, runbook, políticas)
9. **Atualizações** (Runbook atualizado? RIPD revisado? Política de Retenção alterada?)

---

## 8. Tabletop Exercise — Script (Sprint S5)

### Cenário: Vazamento de service_role em repositório público

**Participantes:** DPO, Dev Admin, Jurídico, CEO

**T0:** Um desenvolvedor comete sem querer um arquivo `.env.local` em um branch público do repositório `up/web`. A chave `SUPABASE_SERVICE_KEY` é exposta. O GitHub Advanced Security detecta o secret e envia alerta.

**Perguntas:**
1. Quem é notificado primeiro? Qual meio de comunicação?
2. Em quanto tempo o incidente é classificado?
3. Qual a primeira ação de contenção? Quem executa?
4. É necessário notificar a ANPD? Em quanto tempo?
5. É necessário notificar os titulares? Quantos?
6. Como garantir que o secret foi removido do histórico git?
7. Quem comunica o incidente aos titulares? Qual template?
8. O que muda no runbook após este incidente?

**Critério de sucesso:** Equipe conclui o tabletop em ≤ 2h. Runbook é atualizado com correções identificadas.

---

## 9. Dependências Técnicas

| Requisito | Status atual | Ação | Sprint |
|---|---|---|---|
| Monitoramento/alertas (Sentry?) | ❌ A confirmar | Implementar alerta de service_key exposta, tráfego anômalo | S2 |
| Log de acesso a PII (SELECT/READ) | ❌ Não existe | Estender `carteira_deletion_audit_log` para `access_audit_log` | S2 |
| Secret scanning (CI) | ❌ Não existe | Adicionar gitleaks/detect-secrets ao CI | S1 |
| Template de e-mail de incidente | ❌ Não existe | Armazenar como template no provedor de e-mail | S2 |
| Runbook acessível no admin | ❌ Não existe | Publicar no painel admin com acesso restrito | S2 |

---

## 10. Histórico

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
| `{{DEV_ADMIN_1}}` | Dev |
| `{{DEV_ADMIN_2}}` | Dev |
| `{{ADVOGADO_OAB}}` | Cliente |
| `{{DIRETORIA}}` | Cliente |
| `{{DATA}}` | Cliente |
| `{{SERVICO_MONITORAMENTO}}` | Cliente (ex.: Serasa, Registrato BCB) |

---

## Disclaimer

*Runbook técnico-jurídico. A condução concreta de um incidente deve ser coordenada pelo DPO e por advogado OAB. Em caso de possível ilícito penal (arts. 154-A, 299, 304 CP), preservar provas e contatar representação legal. O tempo de detecção depende de monitoramento que pode ainda não estar implementado.*

**Revisão pendente:** [ ] OAB validar templates de notificação; [ ] Dev confirmar ferramentas de monitoramento; [ ] Agendar tabletop exercise (S5).
