# 🔐 Auditoria de Segurança e LGPD — Meia Entrada (up/)

> **Data:** 2026-07-03
> **Escopo:** `up/admin` + `up/web` (Next.js 14/15, Supabase, Mantine, Tailwind)
> **Foco:** Vulnerabilidades de configuração Next/Supabase, comprometimento de dados de estudantes, conformidade LGPD (Lei 13.709/2018)

---

## 🚨 Sumário de Gravidade

| ID | Severidade | Título |
|----|-----------|--------|
| S-01 | 🔴 **CRÍTICO** | Web usa `SUPABASE_SERVICE_KEY` em rotas públicas — bypass total de RLS |
| S-02 | 🔴 **CRÍTICO** | Rotas públicas `/v/[uuid]` e `/V/[token]` vazam todos os PII + foto do estudante |
| S-03 | 🔴 **CRÍTICO** | Ausência de `middleware.ts` nos dois repositórios — refresh de sessão e proteção de rotas quebrados |
| S-04 | 🟠 **ALTO** | `SELECT *` em carteiras expõe massa de dados pessoais sem projeção mínima |
| S-05 | 🟠 **ALTO** | `next.config` sem headers de segurança (CSP, HSTS, X-Frame-Options, Referrer-Policy) |
| S-06 | 🟠 **ALTO** | Storage policy `TO public` em storage.objects permite leitura ampla |
| S-07 | 🟠 **ALTO** | Stored XSS via `dangerouslySetInnerHTML` em campos editáveis por admins |
| **S-08** | 🔴 **CRÍTICO** | PostHog `autocapture:true` + session recording no formulário de PII/biométrico — exfiltração de dado sensível para os EUA sem consentimento (transferência internacional ilícita) |
| L-01 | 🔴 **CRÍTICO** | Sem consentimento LGPD explícito no formulário de coleta de dados sensíveis |
| L-02 | 🔴 **CRÍTICO** | Coleta de dado biométrico (foto) sem base legal específica informada |
| L-03 | 🟠 **ALTO** | Sem política de privacidade acessível ao titular |
| L-04 | 🟠 **ALTO** | Sem informação sobre retenção, compartilhamento e direitos do titular |
| L-05 | 🟡 **MÉDIO** | Sem rate-limit / captcha no `/[entidade]/pedido` — flooding e enumeração |
| M-01 | 🟡 **MÉDIO** | Senhas hardcoded em `e2e/fixtures/auth.ts` e `create-test-users.js` versionadas no git |

---

## 📜 Evidências Detalhadas

### S-01 · CRÍTICO — Service Role Key no Web Público

**Arquivo:** `up/web/src/utils/supabase/base.ts`

```ts
export const createClient = () => {
  return createSupabaseClient<Database>(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_KEY!,   // ← BYPASSA RLS
  );
};
```

**Por que é crítico:** A `SUPABASE_SERVICE_KEY` (service role) ignora **todas** as Row Level Security policies do Postgres. Todo o trabalho que você e o João Paulo tiveram com migrations `20260203024958_migrate_dkadmin...`, `20260203043701_fix_recursion...`, `20251107181230_row_level_security` é **inútil** quando o código acessa via esse client.

**Uso atual do `base.ts` (5 arquivos):**
| Arquivo | O que faz | Rota exposta |
|--------|-----------|--------------|
| `utils/getDadosCarteira.ts` | `SELECT * FROM carteiras` | `/v/[uuid]` e `/V/[token]` |
| `utils/getFotoEstudante.ts` | Signed URL da foto | `/v/[uuid]` e `/V/[token]` |
| `utils/getEntidade.ts` | SELECT explícito de `entidades` | `/[entidade]` |
| `models/carteira.ts` | INSERT carteira | `createCarteiraAction` |
| `models/arquivos.ts` | Upload + cria bucket por entidade | upload |

**Fix esperado:** O `base.ts` deve usar `createServerClient` (SSR cookies) com a **anon key**, exceto em operações específicas que realmente precisam de privilégio de serviço (ex.: bootstrapping de bucket). Mesmo nesses casos, isolar num `admin.ts` separado como o admin faz.

---

### S-02 · CRÍTICO — Rotas Públicas Vazam PII Completa

**Arquivos:** `up/web/src/app/v/[uuid]/page.tsx` e `up/web/src/app/V/[token]/page.tsx`

```tsx
// /v/[uuid]/page.tsx
const carteira = await getDadosCarteira(uuid);            // SELECT * — sem auth
const fotoEstudante = await getFotoEstudante(carteira.entidade_id, uuid);
return <Carteira carteira={carteira} fotoEstudante={fotoEstudante} />;
```

**`getDadosCarteira` (service key):**
```ts
.from("carteiras")
.select("*, entidades(nome,instituicao,logo_url,fundo_carteirinha_url)")
.eq("id", uuid)
.maybeSingle();
```

**Campos da tabela `carteiras` vazados:**
- PII identificadora: `nome`, `cpf`, `rg`, `matricula`, `data_nascimento`, `email`, `telefone`
- PII de filiação: `nome_mae`, `nome_pai`
- PII de endereço (via `carteira_endereco`): `cep`, `rua`, `numero`, `cidade`, `uf`
- Dado biométrico: `foto` (signed URL de 1h)
- `instituicao`, `curso`

**Vetores concretos:**
1. **Enumeração de UUID**: `/v/[uuid]` aceita UUID — se um estudante compartilhar o link, qualquer um vê tudo. UUIDs v4 têm entropia alta, mas **sem rate-limit** permiti varredura automatizada.
2. **Token de validação**: Quando o fiscal do cinema/restaurante valida a carteira, ele acessa `/V/[token]` em tempo real em local público. Quem capturar o link vê todos os dados.
3. **Logs/cache**:  A rota é server-rendered — qualquer CDN/intermediário pode cachear HTML com PII sem `Cache-Control: private, no-store`.

**Servidor não checa** se quem acessa é: o dono da carteira, um admin da entidade, ou um fiscal autorizado. Compare com a RLS que você escreveu para o admin (`dkadmin` OU `entidade_id IN usuario_entidades`) — **essa lógica não é aplicada no web** porque o client usa service key.

---

### S-03 · CRÍTICO — Ausência de Middleware de Sessão

**Arquivo:** `up/admin/src/utils/supabase/middleware.ts` existente, mas **`middleware.ts` na raiz não existe** em nenhum dos dois repositórios (verificado com `find . -name middleware.ts`).

**Evidência no código do web:**
```ts
// up/web/src/utils/supabase/server.ts, dentro do catch
try {
  cookiesToSet.forEach(({ name, value, options }) => cookieStore.set(...));
} catch (error) {
  // The `setAll` method was called from a Server Component.
  // This can be ignored if you have middleware refreshing user sessions.
  // ❌ MAS NÃO HÁ MIDDLEWARE.
}
```

**Impacto:**
- Tokens de refresh expiram e o usuário é **deslogado silenciosamente**
- Sem proteção de rota em runtime Next — só a chamada `getUser()` liberar para `/login`
- Sem renovação proativa do JWT → requisições com token expirado falham, e o refresh no Server Component falha porque cookies não podem ser setados em alguns contextos (documentado no próprio comentário)

**Fix esperado:** Criar `up/admin/middleware.ts`:
```ts
import { type NextRequest } from 'next/server'
import { updateSession } from '@/utils/supabase/middleware'
export async function middleware(request: NextRequest) {
  return await updateSession(request)
}
export const config = { matcher: '/:path*' }
```
E criar `up/web/middleware.ts` equivalente (ou restringir ao portal de validação).

---

### S-04 · ALTO — `SELECT *` em Carteiras

Mesmo após corrigir S-01, o `SELECT *` em `getDadosCarteira` (web) e em actions do admin (`fetch-carteiras.ts`, `fetch-usuarios.ts`) carrega massivamente campos que o componente mais nunca mostra.

A página pública `/v/[uuid]` precisa só de: `nome`, `curso`, `instituicao`, `validade`, `foto`, `matricula`, `uf`. Não precisa de `cpf`, `rg`, `nome_mae`, `nome_pai`, `email`, `telefone`, `endereco`.

**Princípio da minimização (LGPD art. 6º, III — "adequação"):** coletar e expor só o necessário. Hoje a carteira renderizada expõe todos os dados — enquanto uma carteira física de meia-entrada mostra nome, foto, instituição, validade e matrícula.

**Fix esperado:** Projeção explícita por contexto:
- `/v/[uuid]` pública: `nome, foto, curso, instituicao, validade, matricula, uf`
- `/V/[token]` fiscal: + `cpf` (validação off)
- Admin logado: acesso total via client com cookies (RLS cuida)

---

### S-05 · ALTO — `next.config` Sem Headers de Segurança

**`up/admin/next.config.mjs`:** literalmente `{ serverRuntimeConfig: { PROJECT_ROOT } }` — vazio de segurança.

**`up/web/next.config.mjs`:** só `experimental.optimizePackageImports` + `serverActions.bodySizeLimit: 10mb`. Sem `headers()`.

**Faltando (recomendado pela OWASP e pela Next.js CSP guide):**

| Header | Por quê |
|--------|---------|
| `Content-Security-Policy` | Bloqueia XSS armazenado (ver S-07) |
| `X-Frame-Options: DENY` (ou CSP `frame-ancestors`) | Clickjacking nos formulários com CPF/RG |
| `X-Content-Type-Options: nosniff` | MIME sniffing em uploads |
| `Referrer-Policy: strict-origin-when-cross-origin` | Não vazar `?uuid=` no referer |
| `Strict-Transport-Security` | Forçar HTTPS |
| `Permissions-Policy` | `camera`, `geolocation` off por padrão |

**Fix esperado:** bloco `headers()` em `next.config.mjs` em ambos os repositórios. A punição por omitir HSTS é sessions hijacking por downgrade.

---

### S-06 · ALTO — Storage Policy `TO public`

**Arquivo:** `up/admin/supabase/migrations/20260202205256_restore_rls_policies.sql` (e `20260203024958_migrate_dkadmin...`)

```sql
CREATE POLICY "Users can read files from their entity buckets"
ON "storage"."objects"
AS PERMISSIVE
FOR SELECT
TO public                                -- ← QUALQUER UM, INCLUSIVE ANON
USING ( CAST(SPLIT_PART(bucket_id, '-', 2) AS INTEGER) IN
  ( SELECT entidade_id FROM usuario_entidades WHERE usuario_id = auth.uid() )
);
```

O `USING` exige `auth.uid()`, então o `TO public` em si não vaza para anônimos **diretamente**. Mas como o web usa **service_key** (S-01), o storage também é bypassado — e não há verificação de posse sobre `${carteiraId}/foto` no `getFotoEstudante`. Conhecer a `entidade_id` + `carteiraId` é suficiente para gerar signed URL.

**Fix esperado:**
- No web, proibir `base.ts` no acesso a storage — usar client anon e checar posse.
- `createSignedUrl` com expiração curta (atualmente 3600s) e, preferencialmente, gerar URLs só para sessões autorizadas.

---

### S-07 · ALTO — Stored XSS via `dangerouslySetInnerHTML`

**Scanner encontrado (5 ocorrências):**
- `up/web/src/app/[entidade]/page.tsx:54`
- `up/web/src/app/[entidade]/pedido/concluido/ConcluidoClient.tsx:34`
- `up/web/src/components/form/steps/step-pagamentos.tsx:69`
- `up/admin/src/components/form/steps/step-final.tsx:12`
- `up/admin/src/components/form/steps/step-introducao.tsx:45`

Admin tem `@mantine/tiptap` rich text editor (`pdfGenerator.ts`, configs de entidade). Se admin edita `texto_final`, `texto_adicional_pagamento`, `intro_text` da entidade, esse HTML é renderizado cru nos componentes de estudante. Um admin comprometido — ou uma conta admin roubada — injeta JavaScript que roda no navegador de **todo estudante** que abrir a página da entidade.

Dado que a sessão do estudante não existe (web público), não rouba cookies. Mas pode:
- Redirecionar para página de phishing com layout idêntico
- Capturar tudo que o estudante digita (CPF, RG, foto, endereço) — keylogger
- Enviar para domínio externo

**Fix esperado:**
- Sanitizar com `DOMPurify` antes de `dangerouslySetInnerHTML`
- Ou converter tiptap para React components server-side (não HTML cru)
- CSP `script-src 'self'` ainda assim reduz dano

---

### S-08 · CRÍTICO — PostHog Autocapture + Session Recording Capturam PII/Biométrico do Formulário

> ⚠️ **Adendo à auditoria original (2026-07-03, post-publicação).** A auditoria inicial registrou PostHog como "boa prática de privacidade" — **incorreto** em face da configuração efetiva. Este finding corrige aquele equívoco.

**Arquivos:** `up/web/src/providers/PostHogProvider.tsx`, `up/web/src/utils/posthog-client.ts`, `up/web/src/utils/posthog-server.ts`, além de chamadas `posthog.capture(...)` em `app/actions/createCarteira.ts`, `app/actions/initializeCarteira.ts`, `components/form/FormContext.tsx`, `components/form/FileUploadField.tsx`, `models/carteira.ts`, `utils/formPersistence.ts`.

**Configuração constatada no `PostHogProvider.tsx`:**
```ts
autocapture: true,                  // captura cliques/inputs/texto em toda a página
disable_session_recording: false,   // grava a tela enquanto o estudante preenche
capture_pageview: false,            // captura pageviews manualmente (pathname inclui slug da entidade)
capture_pageleave: true,
```

**O que isto significa na prática do fluxo `/[entidade]/pedido`:**
- **Autocapture** registra eventos de `input`/`change`/`focus` em TODOS os campos do formulário — `nome`, `nome_mae`, `nome_pai`, `rg`, `cpf`, `data_nascimento`, e-mail, telefone, CEP/endereço — com seus **valores** enviados ao PostHog Cloud (hospedagem EUA/UE).
- **Session recording** grava literalmente o estudante digitando CPF/RG e subindo a foto (dado biométrico, art. 11 LGPD). A reconstrução DOM do replay inclui texto digitado e carregamento da imagem.
- **`posthog-server.ts`** captura server-side (em `createCarteiraAction`, `initializeCarteira`) — pode incluir identificadores e estado do pedido.
- Tudo **sem consentimento de cookie/tracking** (L-01 está vazia) e **sem base para transferência internacional** de dado sensível (art. 11 + art. 33/36 LGPD).

**Severidade:** 🔴 CRÍTICO. Embasamento duplo: (a) segurança — exfiltração contínua de PII/biométrico para terceiro; (b) LGPD — transferência internacional de dado sensível sem consentimento e sem garantias adequadas (art. 33/36). Equiparável em gravidade a S-01/S-02, e **agrava** L-01/L-02/L-03 (o dado coletado sem consentimento já está indo para fora do país antes mesmo de qualquer storage).

**Fix esperado (Sprint S0 — 24h):**
- `autocapture: false` e `disable_session_recording: true` imediatamente (hotfix de 1 linha em `PostHogProvider.tsx`). Zera a exfiltração ativa.
- Isolar o `PostHogProvider` **fora** das rotas `/[entidade]/pedido` (ou condicionar à existência de um consent flag `lgpd_analytics_opt_in`).
- Se houver legítima necessidade de produto para gravação de sessão, **limitar a páginas de marketing/pós-conversão** e sempre com opt-in explícito + informação na política.
- Limpar/selecionar manualmente cada evento: **nunca** capturar `input` de PII; revisar `posthog-server.ts` e remover propriedades que carreguem `cpf`/`rg`/`nome`/`email`/`telefone`.
- Adicionar **cookie consent banner** (ou pelo menos gate de opt-in para analytics não-essenciais) — eWPD/ANPD entende analytics com identificação como tratamento.
- Contratar processamento em **região BR/UE do PostHog** se legítimo continuar, ou self-host, e formalizar no DPA do operador (subprompt 03).

**Observação sobre enumeração no Parecer:** o Parecer Jurídico do cliente enumera findings com sua própria sequência. Este S-08 foi descoberto após a emissão do parecer; o advogado precisa ser enviado para **reabrir L-01/L-03 e adicionar um item de transferência internacional** à sua cronologia. Não estávão divergindo da verdade — o parecer precede este achado.

---

### L-01 · CRÍTICO — Sem Consentimento LGPD Explícito

Grep por `consentimento|LGPD|politica|privacidade|aceito|termo` em `up/web/src`: **zero resultados**.

**Dados coletados no formulário público `/[entidade]/pedido`** (ver `step-pessoais.tsx`, `step-endereco.tsx`):
- `nome` (obrigatório)
- `nome_mae`, `nome_pai` (se secundarista)
- `rg`, `cpf`, `data_nascimento`
- Endereço completo: `cep`, `rua`, `numero`, complemento, bairro, cidade, `uf`
- `email`, `telefone`
- `foto` do rosto
- Documento de comprovação (RG/CPF/comprovante)

**LGPD art. 8º:** Tratamento de dados pessoais **somente** mediante consentimento **livre, informado e inequívoco**. Hoje o estudante não marca nenhum checkbox — basta clicar em "Enviar". Não há informação sobre:
- Finalidade específica (emitir carteira de meia-entrada — ok)
- Base legal (art. 7º, consentimento ou execução de contrato)
- Compartilhamentos (cinemas, restaurantes, ME, MS?)
- Retenção (quanto tempo fica a foto?)
- Direitos do titular (acesso, retificação, anonimização, eliminação — art. 18)

---

### L-02 · CRÍTICO — Dado Biométrico Sem Base Legal Específica

**A foto do rosto `foto` é dado sensível** (LGPD art. 5º, II "íntima" → biométricos; art. 11 exige consentimento **específico** para dados sensíveis).

Hoje a coleta da foto está num dos passos do formulário exigindo upload obrigatório, mas sem checkbox separado e sem texto explicando que é dado sensível e que pode ser substituído por retirada presencial. Não há política de retenção definida.

**Risco:** ANPD pode aplicar sanções administrativas (art. 52): advertência, multa de até **2% do faturamento da pessoa jurídica, limitada a R$ 50 milhões** por infração, **bloqueio ou eliminação dos dados**.

---

### L-03 · ALTO — Sem Política de Privacidade Acessível

`grep` não encontrou link para política de privacidade. O estudante não consegue exercer direitos do art. 18 sem saber para onde mandar contato. O `README` menciona só contato com "equipe de desenvolvimento" — não serve para LGPD.

**Fix esperado:** Link `/privacidade` com política completa + canal de contato do DPO/encarregado (mesmo que fora da empresa, art. 41).

---

### L-04 · ALTO — Retenção e Compartilhamento Não Documentados

Nas migrations e configs não há:
- Política de retenção (`DELETE` automático de carteiras expiradas?)
- Log de compartilhamento (com cinemas, apps de checagem de meia entrada, etc.)
- Direito à portabilidade

Há uma boa iniciativa: `20251107183145_carteira_deletion_audit_log.sql` cria log de deleção — mostra que pensaram em auditoria. Mas auditoria de deleção não substitui política de retenção.

---

### L-05 · MÉDIO — Sem Rate-Limit / Captcha no Formulário

`CriarCarteiraButton.tsx` é só um `<Button>` que navega. `createCarteiraAction` (server action) não tem:
- Captcha (Cloudflare Turnstile / hCaptcha)
- Rate-limit por IP
- Honeypot

**Vetores:**
- Flooding: atacante cria 100k carteiras fantasmas, infla a base/pós os buckets de Supabase Storage (Storage tem limite por projeto)
- Enumeração de instituições: testar nomes/CNPJ
- Poluição de dados: injeção de CPFs falsos que poluem relatórios do admin

---

### M-01 · MÉDIO — Senhas Hardcoded Versionadas

`security-scan` marcou como ⚠️🔴 CRITICAL:
- `up/admin/e2e/fixtures/auth.ts:15,20,25,30,35` (5 instâncias "Potential Password")
- `up/admin/scripts/create-test-users.js:24,43` (2 instâncias)

São provavelmente senhas de teste (não produção), mas:
- Versionadas no git → ficam no histórico mesmo se removidas
- Se forem fracas/padrão e por descuido reutilizados em prod, é desastre
- Não há separação clara "este arquivo é só para testes"

**Fix esperado:** mover para `.env.test` (gitignored), usando faker (`@faker-js/faker` que já é dep dev) para gerar senhas ou usar `process.env.TEST_PASSWORD`.

---

## 🛠️ Plano de Remediação (priorizado)

### Sprint 1 — Bloqueio imediato (1-2 dias)
1. **S-01 + S-04**: trocar `base.ts` por `server.ts` (cookies/anon) com projeção mínima em `getDadosCarteira`/`getFotoEstudante`. Imediatamente limita vazamento.
2. **S-02**: adicionar `Cache-Control: private, no-store` nas rotas `/v/[uuid]` e `/V/[token]`. Adicionar regra de autorização server-side ( signed token curto por requisição).
3. **S-03**: criar `middleware.ts` nos dois repositórios chamando `updateSession`.
4. **S-08 (NOVO)**: hotfix de 1 linha em `PostHogProvider.tsx` — `autocapture: false`, `disable_session_recording: true` — remove a exfiltração ativa de PII/biométrico para PostHog Cloud (EUA). Em paralelo, excluir o `PostHogProvider` das rotas `/[entidade]/pedido` até existir cookie-consent. **Esto é da mesma gravidade do S-01 e compete por SPRINT 0.**

### Sprint 2 — Endurecimento (3-5 dias)
4. **S-05**: implementar `headers()` em ambos `next.config.mjs`. CSP restritiva, HSTS, X-Frame-Options.
5. **S-07**: sanitizar HTML do tiptap com `DOMPurify` (ou migrar para React elements server-side).
6. **S-06**: revisar policies de storage; checagem de posse explícita em `getFotoEstudante`.
7. **L-05**: adicionar rate-limit no `createCarteiraAction` (Upstash/Redis ou Supabase function) + Turnstile.

### Sprint 3 — LGPD (1-2 semanas)
8. **L-01**: checkbox de consentimento específico e inequívoco no formulário com link para política.
9. **L-02**: checkbox **separado** para dado biométrico (foto), com alternativa de retirada presencial.
10. **L-03**: criar `/privacidade` com política em PDF assinado; informar encarregado.
11. **L-04**: definir política de retenção (ex.: carteira expira 1 ano após `validade` → `delete` automático com log no `carteira_deletion_audit_log`).
12. Formulário de exercício de direitos (acesso, retificação, exclusão).

### Sprint 4 — Boas práticas
13. **M-01**: mover senhas de teste para `.env.test` gitignored.
14. Rotacionar histórico git com `git filter-repo` se segredo real.
15. Adicionar `SECRET_SCANNING` no CI (`gitleaks` action).

---

## 📋 Matriz de Riscos LGPD

| Art. LGPD | Item | Status |
|-----------|------|--------|
| 6º, III (adequação) | S-04 minimização no SELECT | ❌ |
| 6º, II (finalidade) | L-03 propósito claro | ❌ |
| 7º, I (consentimento) | L-01 checkbox de consentimento | ❌ |
| 8º (consentimento inequívoco) | L-01 + L-02 separação de base | ❌ |
| 9º (informação) | L-03 política acessível | ❌ |
| 11 (dados sensíveis) | L-02 base específica para foto | ❌ |
| 16 (segurança) | S-01,02,03,05,07 | ❌ |
| 18 (direitos do titular) | L-04 canal para direitos | ❌ |
| 33/36 (transferência internacional) | **S-08** PostHog Cloud (EUA) com dado sensível sem garantias | ❌ |
| 52 (sanções) | Exposição até 2% faturamento, R$50M | ⚠️ |
| 41 (encarregado/DPO) | Não identificado no README | ❌ |

---

## ✅ Boas Práticas Já Existentes

Para balancear — coisas que vocês fizeram certas:

- ✅ RLS habilitada nas tabelas sensíveis (re-enable pela `20260202205256`)
- ✅ `carteira_deletion_audit_log` para auditoria de deleção
- ✅ system de permissões granulares via `usuarios_permissoes`
- ✅ Signed URLs (expiração) em vez de URLs públicas para fotos — bo decisão
- ✅ Migrations versionadas no git
- ✅ Bucket privado por entidade com `allowedMimeTypes` e `fileSizeLimit`
- ✅ `posthog` em vez de Sentry — escolha boa para BR (privacidade) — **⚠️ CORREÇÃO (ver S-08):** a *escolha* é defensável, mas a *configuração* atual (`autocapture:true` + session recording no formulário de PII) é uma exfiltração ativa. A boa prática existe apenas depois do hotfix S-08.
- ✅ `serverActions.bodySizeLimit: 10mb` — limita payload do formulário
- ✅ `getEntidade` usa projeção explícita com comentário SECURITY
- ✅ Vitest + Playwright — cobertura de testes existe

---

## 🎯 Conclusão

O sistema está **funcional** mas tem uma postura de segurança **relaxada em pontos críticos**. Os três maiores riscos — **service key no web**, **ausência de middleware** e **ausência de consentimento LGPD** — combinados expõem a empresa a:

1. **Vazamento de massa de PII de estudantes** se alguém descobrir/enumerar UUIDs
2. **Sanções administrativas da ANPD** (multa + bloqueio de dados)
3. **Perda de confiança pública** (projeto de estudantes, instituições de ensino)

A boa notícia: você já desenhou as RLS certas — só precisa **aplicá-las no código** (cortar o bypass pelo service key) e **completar a camada de LGPD** que faltou. A base técnica é sólida; falta a camada de governança.

Recomendo priorizar o Sprint 1 como bloqueio de sangramento; o Sprint 3 (LGPD) tem deadline regulatório.

---

*Auditoria realizada em 2026-07-03 por pi com base em análise estática do estado atual dos repositórios `up/admin` e `up/web`. Não substitui pentest nem consulta jurídica formal com profissional habilitado (OAB) para LGPD.*