# RIPD — Relatório de Impacto à Proteção de Dados Pessoais

> **Versão:** 1.0 | **Data:** {{DATA}}
> **Controlador:** {{RAZAO_SOCIAL}} | CNPJ {{CNPJ}}
> **DPO:** {{DPO_NOME}} — {{DPO_EMAIL}}
> **Subprompt:** 05 — RIPD
> **Metodologia:** Guia Orientativo RIPD (ANPD, 2024) + GDPR WP29
> **Auditoria de referência:** `analysis/2026-07-03-auditoria-seguranca-lgpd.md`
> **Plano de ação:** `analysis/2026-07-03-plano-acao-arquitetura.md`

---

## 1. Identificação do Controlador e DPO

| Campo | Valor |
|---|---|
| **Controlador** | {{RAZAO_SOCIAL}} |
| **CNPJ** | {{CNPJ}} |
| **Endereço** | {{ENDERECO_CONTROLADOR}} |
| **Encarregado (DPO)** | {{DPO_NOME}} |
| **E-mail do DPO** | {{DPO_EMAIL}} |
| **Equipe de segurança** | {{EQUIPE_SEGURANCA}} |
| **Data de elaboração** | {{DATA}} |
| **Versão** | 1.0 |

---

## 2. Descrição do Tratamento

### 2.1 Fluxo de Dados

```mermaid
graph TD
    A[Estudante] -->|preenche formulário| B[web: /[entidade]/pedido]
    B -->|POST dados| C[Server Action: createCarteira]
    C -->|insert| D[(Supabase DB)]
    C -->|upload foto| E[(Supabase Storage)]
    C -->|insert comprovantes| F[(carteira_arquivos)]
    G[Entidade Emissora] -->|acessa admin| H[admin: gestão de carteiras]
    H -->|RLS por entidade| D
    H -->|produz PDF| I[Gerador PDF]
    I -->|upload + token| D
    J[Estabelecimento] -->|escaneia QR| K[web: /V/[token]]
    K -->|SELECT limitado| D
    K -->|exibe| L[Nome, foto, status, validade]
    M[PostHog] -->|telemetria anon| N[PostHog Cloud]
```

### 2.2 Operações de Tratamento

| Operação | Local | Tecnologia |
|---|---|---|
| Coleta de dados | Formulário web | Next.js 15 + Server Actions |
| Armazenamento | Supabase (PostgreSQL + S3) | TLS 1.3, criptografia em repouso |
| Processamento (emissão) | Server-side (Vercel Edge/Functions) | Node.js + Next.js API |
| Validação pública | Rota `/V/[token]` | Next.js SSR, sem autenticação |
| Analytics | PostHog SDK | JavaScript, `autocapture: false` (pós-hotfix) |

---

## 3. Natureza dos Dados

### 3.1 Dados Pessoais

| Tipo | Categoria | Exemplos |
|---|---|---|
| Identificadores | C01 | CPF, RG |
| Cadastrais | C02 | Nome, filiação, DOB |
| Acadêmicos | C03 | Matrícula, curso, instituição |
| Contato | C04 | E-mail, telefone |
| Endereço | C05 (condicional) | CEP, rua, número, cidade, UF |
| **Sensível — biométrico** | **C06** | **Fotografia** (art. 11 LGPD) |
| Comprobatórios | C07 | Documento de identificação, comprovante de matrícula |

### 3.2 Caracterização de Alto Risco

☑️ Tratamento de **dados sensíveis** (foto — art. 11 LGPD)
☑️ Tratamento de dados de **crianças e adolescentes** (menores — art. 14 LGPD)
☑️ **Transferência internacional** de dados (EUA — arts. 33/36)
☑️ **Compartilhamento** com co-controladoras (entidades emissoras)
☑️ **Exposição pública** de PII (validação via `/V/[token]`)

**Conclusão preliminar:** O tratamento **envolve alto risco** e a realização do RIPD é obrigatória.

---

## 4. Base Legal

| Finalidade | Base legal | Art. LGPD |
|---|---|---|
| Emissão CIE (dados gerais) | Execução de contrato | Art. 7º, V |
| Emissão CIE (obrigação legal) | Cumprimento obrigação legal (Lei 12.933/2013) | Art. 7º, II |
| **Tratamento da foto (biométrico)** | **Consentimento específico e destacado** | **Art. 11, I** |
| Comunicação transacional | Execução de contrato | Art. 7º, V |
| Analytics (pós-hotfix) | Consentimento (via banner) | Art. 7º, I |
| Auditoria/Governança | Exercício regular de direitos / Obrigação legal | Art. 7º, II e V |

---

## 5. Agentes de Tratamento

| Agente | Papel | Fundamento contratual |
|---|---|---|
| Meia-Entrada ({{RAZAO_SOCIAL}}) | **Controlador** | — |
| Entidade emissora (DCE, UPEE, IES, escola) | **Co-controlador** | Contrato de co-controladora (S2 — subprompt 04) |
| Supabase Inc. (EUA) | **Operador** | DPA (S2 — subprompt 03) |
| Vercel Inc. (EUA) | **Operador** | DPA (S2) |
| PostHog Inc. (EUA) | **Operador** | DPA + SCC + consentimento |
| {{EMAIL_PROVIDER}} | **Operador** (futuro) | DPA (S2) |

---

## 6. Compartilhamento e Transferência Internacional

| Destinatário | País | Garantia | Finalidade |
|---|---|---|---|
| Supabase Inc. | EUA | SCC + criptografia TLS + DPA | Banco de dados, storage, auth |
| Vercel Inc. | EUA | SCC + DPA | Hospedagem |
| PostHog Inc. | EUA | SCC + consentimento + autocapture off | Analytics |
| Entidade emissora | Brasil | Contrato de co-controladora | Gestão da campanha |
| Estabelecimentos validadores | Brasil | Público — dados mínimos via `/V/[token]` | Validação presencial |

---

## 7. Medidas de Segurança

### 7.1 Medidas Implementadas

| Medida | Status | Cobertura |
|---|---|---|
| TLS 1.3 em trânsito | ✅ Ativo (não mitigado) | Todas as conexões |
| Criptografia em repouso | ✅ Ativo | Banco de dados (Supabase) |
| Autenticação via sessão (HTTP-only cookies) | ✅ Ativo | Admin + web |
| Autocapture desabilitado (PostHog) | ✅ Ativo (S-08 hotfix) | Formulário PII |
| Session recording desabilitado | ✅ Ativo (S-08 hotfix) | Formulário PII |

### 7.2 Medidas em Implementação (Plano de Ação)

| Medida | Epic | Sprint | Status esperado |
|---|---|---|---|
| Remover service_role do frontend | S-02 | S0 | RLS efetivamente aplicado |
| Proteger rota `/V/[token]` com token assinado e projeção mínima | S-03 | S0/S1 | Não expõe CPF/RG/endereço |
| Implementar consentimento LGPD | L-01/L-02 | S1 | 2 checkboxes (geral + foto) |
| Implementar middleware (proteção de rotas) | S-04 | S1 | Sessão renovada, rotas protegidas |
| Rate-limit/captcha | L-05 | S1 | 100 req/hora/IP |
| Headers de segurança (CSP, HSTS) | S-05 | S1 | Headers presentes |
| Logs de auditoria de acesso | F-01 | S2 | Acesso PII rastreável |
| Contrato de co-controladora vigente | F-03 | S2 | Gate de emissão |
| Contrato de operador (DPA) | L-05 | S2 | Operador contratualmente vinculado |

---

## 8. Análise de Risco

### 8.1 Matriz de Risco

| # | Risco | Descrição | Prob. (hoje) | Prob. (pós-remediação) | Impacto | Risco residual | Mitigação (Epic) |
|---|---|---|---|---|---|---|---|
| R1 | **Acesso total sem autenticação** | Service_role exposta no frontend permite leitura/escrita de todos os dados por qualquer atacante | **Alta** | **Muito Baixa** | **Crítico** | **Alto** → Muito Baixo | S-02 |
| R2 | **Scraping massivo de PII** | Rotas públicas expõem CPF, RG, endereço, foto sem autenticação | **Alta** | **Baixa** | **Crítico** | **Alto** → Baixo | S-03 |
| R3 | **Vazamento de foto (biométrico)** | Acesso não autorizado ao storage; exposição na validação pública | **Média** | **Baixa** | **Alto** | **Médio** → Baixo | S-02/S-03/S-07 |
| R4 | **Falha de consentimento** | Foto tratada sem consentimento específico (art. 11) | **Alta** (hoje) | **Muito Baixa** | **Alto** | **Alto** → Muito Baixo | L-02 |
| R5 | **Transferência internacional indevida** | Dados enviados aos EUA sem garantias adequadas | **Média** | **Baixa** | **Médio** | **Médio** → Baixo | L-05 (DPA + SCC) |
| R6 | **Falha no exercício de direitos** | Titular sem canal para acessar/excluir dados | **Alta** (hoje) | **Baixa** | **Médio** | **Alto** → Baixo | F-01 |
| R7 | **Fraude acadêmica** | Entidade emissora emite para não-estudante | **Média** | **Média** | **Médio** | **Médio** | F-03 |
| R8 | **Exfiltração via telemetria** | PostHog captura inputs de PII (S-08) | **Alta** (hoje) | **Muito Baixa** | **Alto** | **Alto** → Muito Baixo | S-08 |
| R9 | **Vazamento de service_role via git** | Secret exposta em histórico do repositório | **Alta** | **Baixa** | **Alto** | **Alto** → Baixo | M-02 |
| R10 | **Ataque de XSS** | Stored XSS via dangerouslySetInnerHTML | **Média** | **Baixa** | **Médio** | **Médio** → Baixo | S-06 |

### 8.2 Risco de Tratamento vs Risco de Incidente

| Tipo | Exemplos |
|---|---|
| **Risco de tratamento** (inerente à finalidade) | Coleta de foto biométrica (R4), compartilhamento com co-controladora (R7) |
| **Risco de incidente** (falha técnica) | Service_role exposta (R1), scraping (R2), XSS (R10) |

### 8.3 Risco Residual (após conclusão S0-S2)

Após a implementação das remediações dos Sprints S0, S1 e S2, todos os riscos de **probabilidade alta** são reduzidos para **baixa ou muito baixa**. O risco residual mais significativo é **fraude acadêmica** (R7), que não é mitigável tecnicamente — exige KYC e auditoria periódica (F-03).

---

## 9. Direitos dos Titulares — Procedimentos

| Direito (art. 18) | Procedimento | Prazo | Responsável |
|---|---|---|---|
| Confirmação e acesso | Formulário `/direitos` → consulta em `carteiras` | 15 dias | MEIA-ENTRADA |
| Correção | Formulário `/direitos` → update em `carteiras` | 15 dias | MEIA-ENTRADA + ENTIDADE |
| Eliminação | Formulário `/direitos` → soft-delete → hard-delete | 15 dias (início) | MEIA-ENTRADA |
| Portabilidade | Formulário `/direitos` → export JSON | 15 dias | MEIA-ENTRADA |
| Revogação de consentimento | Checkbox no perfil → atualizar `lgpd_consents` | Imediato (prospectivo) | MEIA-ENTRADA |
| Informação sobre compartilhamento | Política de Privacidade + RDM | — | MEIA-ENTRADA |

---

## 10. Conformidade com CIE v3.3 (Contexto de Risco)

| Requisito CIE | Status atual | Risco | Impacto na LGPD |
|---|---|---|---|
| Certificado de Atributo ICP-Brasil | ❌ Não implementado | Médio (carteira não é CIE oficial) | Não viola LGPD diretamente, mas expõe a alegações de publicidade enganosa (CDC art. 37) |
| Assinatura criptográfica do QR | ❌ Não implementado | Médio (QR atual sem validade jurídica) | Documento sem garantia de integridade |
| Layout oficial (QR + foto + dados) | Parcial | Baixo | Apenas apresentação |
| Validador offline | ❌ Não implementado | Baixo (validação depende de internet) | Sem impacto direto |

---

## 11. Plano de Mitigação (Link ao Plano de Ação)

| Risco | Epic | Sprint | Critério de aceite |
|---|---|---|---|
| R1, R2, R3 | S-02, S-03, S-07 | S0 | Service_role removida do web; token assinado; storage privado |
| R4, R8 | S-08, L-01, L-02 | S0/S1 | PostHog off; 2 checkboxes; política publicada |
| R5 | L-05 (contratos) | S2 | DPA assinado; SCC anexado |
| R6 | F-01 | S2 | Canal de direitos funcional; SLA 15 dias |
| R7 | F-03 | S2 | Gate de contrato antes de emissão |
| R9 | M-02 | S1 | Secret scanning no CI; chave rotacionada |
| R10 | S-06 | S1 | Sem dangerouslySetInnerHTML |

---

## 12. Revisão e Versionamento

| Versão | Data | Autor | Alterações |
|---|---|---|---|
| 1.0 | {{DATA}} | {{DPO_NOME}} | Versão inicial |

12.1. O RIPD será revisado:
   - Anualmente;
   - Após qualquer mudança relevante no tratamento (nova categoria de dado, novo operador, alteração de base legal);
   - Após incidente de segurança com dados pessoais.

---

## Placeholders

| Placeholder | Responsável |
|---|---|
| `{{RAZAO_SOCIAL}}` | Cliente |
| `{{CNPJ}}` | Cliente |
| `{{ENDERECO_CONTROLADOR}}` | Cliente |
| `{{DPO_NOME}}` | Cliente |
| `{{DPO_EMAIL}}` | Cliente |
| `{{EQUIPE_SEGURANCA}}` | Cliente |
| `{{DATA}}` | Cliente |
| `{{EMAIL_PROVIDER}}` | Dev |

---

## Disclaimer

*O RIPD é instrumento técnico-jurídico interno. Recomenda-se envolvimento do DPO e advogado OAB na assinatura; a mera existência demonstra boa-fé e programa de governança (art. 50), mas não confunde com blindagem jurídica. As avaliações de probabilidade/impacto baseiam-se nas auditorias técnicas e no Parecer Jurídico — não substituem avaliação independente.*

**Revisão pendente:** [ ] OAB validar matriz de risco; [ ] Atualizar após contratos de operador (S2); [ ] Atualizar após implementação técnica (S0-S1).
