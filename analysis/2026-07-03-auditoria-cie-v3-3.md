# Auditoria de Conformidade Regulatória — CIE v3.3 (Carteira de Identificação Estudantil Digital)

**Data:** 2026-07-03
**Auditor:** Davi Aazevedo (daviaaze@gmail.com)
**Escopo:** `up/admin` (Next.js 14 + Mantine + PDFKit) e `up/web` (Next.js 15 + Mantine + Supabase)
**Benchmark:** Portaria nº 1, de 17/03/2016 (modelo único nacional CIE) + Portaria CIE v3.0/3.3 (Certificado de Atributo como padrão nacional para CIE digital) + Especificação "Padronização da CIE" v1.0 (ITI)
**Status global:** **NÃO CONFORME** — implementação atual não atende nenhum dos requisitos da CIE v3.3

---

## TL;DR

A carteirinha gerada hoje é uma **carteirinha privada de meia-entrada**, não uma **CIE — Carteira de Identificação Estudantil** oficialmente reconhecida pela União. Para ser CIE v3.3 conforme, o sistema precisaria:

1. **Certificado de Atributo ICP-Brasil** emitido por uma **EEA (Entidade Emissora de Atributo)** credenciada -- a rainha das meias-entradas/UPEE/ANPG/CIE (resol. de 2016). O sistema atual **não tem nenhum certificado**.
2. **Assinatura criptográfica** (PKCS#7/CAdES) do documento de CIE, com referência auditável ao certificado de atributo. O sistema atual **assina zero**; o "QR code" só aponta para uma URL.
3. **QR code de validação normalizado** conforme especificação ITI (versão protocolo, tipo de documento, dados canônicos, assinatura embutida ou URL de validação assinada). O QR atual só codifica `https://meiaentradaestudantil.com.br/V/{token}`, com `token = base36(timestamp)` -- sem assinatura, sem payload canônico, sem versão de protocolo.
4. **Campos do emissor**: código INEP/MEC da instituição, IEEA, CNPJ, e mapeamento correto entre entidade e IEEA credenciada. O schema `entidades` hoje só tem `nome/sigla/uf/url` -- **nenhum código oficial**.
5. **Validade canônica**: 31 de março do ano seguinte ao da emissão. Este campo está **correto** (`Carteira.tsx:25`).
6. **Modelo visual padronizado** conforme especificação de layout da CIE (frente/verso, áreas de assinatura digital, etc.). O template SVG atual é um layout próprio -- não segue o modelo oficial.
7. **Validação pública** que confira a assinatura criptográfica, não apenas `SELECT *` no banco. Hoje a rota `/V/[token]` expõe dados pessoais sem conferir nada.

**Conclusão:** O projeto está a uma reimplementação arquitetural significativa de distância da conformidade CIE v3.3. Não é retrofit; é integração com infraestrutura ICP-Brasil (ACs, ARs de Atributo, EEA credenciada).

---

## 1. O que é a CIE v3.3 (resumo executivo)

A **Carteira de Identificação Estudantil (CIE)** é o documento único nacional padronizado por [Portaria conjunta MEC/MS/MTur/etc nº 1 de 2016](http://portal.mec.gov.br/...), prevista na Lei 12.933/2013 (meia-entrada). A versão **3.3** introduz a **CIE digital** assinada por **Certificado de Atributo** ICP-Brasil.

### Modelo de confiança (cadeia)

```
    AC Raiz da ICP-Brasil
        └── AC da IEEA-Raiz (Instituto Entidade Emissora de Atributo Raiz)
            └── EEA - Entidade Emissora de Atributo (credenciada, ex.: UPEE nacional)
                └── Certificado de Atributo por estudante
                    └── assina a CIE digital (PKCS#7/CAdES)
                    └── QR code embute URL de validação + dados assinados
```

### Certificado de Atributo ICP-Brasil
- **OID de extensão:** `2.16.76.1.10` (campo `cab` do Certificado de Atributo da ICP-Brasil)
- **Tipo:** X.509 v3 com extensão `Subject Directory Attributes` (atributos do portador) e OIDs próprios da ICP-Brasil
- **Formato:** `.p7b`/`.cer`,KeySpec RSA-2048/3072 ou ECC, validade curta (1-3 anos)
- **Armazenamento:** Token USB / smartcard / arquivo `.pfx` com senha, gerado pela EEA
- **Uso:** assina o PDF da CIE e/ou dados canônicos da CIE digital

### QR Code de validação (CIE v3.3)
A especificação ITI define um QR code com payload estruturado:
- **Versão do protocolo** (ex.: `01`)
- **Tipo do documento** (`CIE`)
- **ID do documento** (UUID/hash do conteúdo)
- **EEA emissora** (identificador credenciado)
- **URL de validação** (HTTPS) -- pode ser assinada
- **Assinatura** do payload pelo certificado de atributo (CAdES-BES ou CAdES-T)

O validador (app CIE da ANPG, site do ITI, órgão russo similar) baixa ou faz fetch da URL, valida o certificado de atributo no LCR/LCAR da AC da EEEA-Raiz, e renderiza o resultado da verificação.

---

## 2. Estado atual do projeto vs CIE v3.3

### 2.1 Tabela resumo de gaps

| Requisito CIE v3.3 | Status atual | Severidade |
|---|---|---|
| Certificado de Atributo ICP-Brasil emitido por EEA | **AUSENTE** | Crítica |
| Assinatura criptográfica do documento (PKCS#7/CAdES) | **AUSENTE** | Crítica |
| QR code com payload normalizado + assinatura | **AUSENTE** -- só URL curta | Crítica |
| Versão do protocolo no QR code | **AUSENTE** | Alta |
| Identificação da EEA emissora no documento | **AUSENTE** | Alta |
| Código da instituição (INEP/MEC) no schema | **AUSENTE** no `entidades` | Alta |
| Identidade da EEA-Raiz / cadeia de confiança verificável | **AUSENTE** | Alta |
| Validação pública com checagem de assinatura | **AUSENTE** -- só `SELECT *` | Alta |
| LCR/LCAR consultada na validação | **AUSENTE** | Alta |
| Vadidade até 31/03 do ano seguinte | ✅ **OK** (`Carteira.tsx:25`) | - |
| Layout visual conforme especificação ITI | **AUSENTE** -- template próprio | Média |
| Log de revogação/auditoria de emissão | **AUSENTE** | Média |
| Política de expiração sincronizada com cert. de atributo | **AUSENTE** | Média |
| Foto padronizada (3x4, fundo neutro) | **PARCIAL** -- existe foto mas sem regra de validação | Baixa |
| Campos mínimos: CPF, nome, data nasc., instituição, curso, validade | ✅ **OK** no schema `carteiras` | - |
| Campos mínimos: filiação (nome mãe/pai) | ✅ **OK** | - |
| Campos mínimos: RG e matrícula | ✅ **OK** | - |

### 2.2 QR code de validação -- o que existe hoje

`admin/src/card/utils/qrCodeUtils.ts:11-18`:
```ts
export async function makeQrCode(card: Carteira): Promise<string> {
  createTokenIfNotExists(card)
  return await QRCode.toDataURL(
    `HTTPS://MEIAENTRADAESTUDANTIL.COM.BR/V/${card.token}`,
    { errorCorrectionLevel: 'quartile', version: 3, scale: 1 },
  )
}
```

`card.token` é `base36(timestamp_ms)` (ver `encodingUtils.ts`). Ou seja, um QR que só aponta para `https://meiaentradaestudantil.com.br/V/{timestamp-base36}`.

**Problemas contra CIE v3.3:**
- ❌ Não há payload estruturado (versão, tipo doc, ID, emissor, assinatura)
- ❌ Não há assinatura criptográfica do conteúdo
- ❌ `token = base36(timestamp)` é trivialmente forjável; não é um identificador assinado
- ❌ URL do validador é `meiaentradaestudantil.com.br`, não um endpoint oficial padronizado
- ❌ A rota de validação (`web/src/app/V/[token]/page.tsx`) só confere a existência da linha no banco via `SELECT *` com **service key** que ignora RLS (ver Auditoria de Segurança, S-03) -- não há conferência criptográfica alguma
- ❌ Nenhum dado do QR é canônico (não há versão do protocolo, não há hash do PDF assinado)

### 2.3 Camadas de confiança ausentes

| Camada | CIE v3.3 exige | Projeto atual |
|---|---|---|
| AC Raiz ICP-Brasil | Implícita na validação | Não referenciada |
| AC da IEEA-Raiz | Certificar EEA | Inexistente |
| EEA credenciada | Emitir certificados de atributo por estudante | Inexistente |
| Certificado de Atributo (por emissão) | Assinar o documento CIE | Não há certificado |
| Assinatura CAdES no PDF | Garantir integridade + não-repúdio | Não há |
| LCR/LCAR online | Validação de revogação na conferência | Não consultada |
| Carimbo de tempo (TS) | CAdES-T opcional | Não há |
| Validação pública verificável | Confere assinatura + cadeia + LCR | Apenas existe registro em banco |

### 2.4 Schema `entidades` -- campos do emissor

`admin/supabase/migrations/20251107181228_storage_policies_entidade_users.sql:129-152`:

```sql
CREATE TABLE IF NOT EXISTS "public"."entidades" (
    "sigla" text NOT NULL,
    "uf" text NOT NULL,
    "url" text NOT NULL,
    "nome" text NOT NULL,
    "instituicao" text NOT NULL,
    "enabled" boolean DEFAULT true NOT NULL,
    "ensino" entidade_ensino[] NOT NULL,
    "locais_retirada" text[] NOT NULL,
    ...
);
```

**Ausências versus CIE v3.3 / especificação ITI:**
- ❌ `cnpj` (CNPJ da entidade emissora)
- ❌ `codigo_inep` ou `codigo_mec` da instituição de ensino
- ❌ `ieea_id` (identificador credenciado da EEA-secundária que a entidade representa)
- ❌ `url_validacao` oficial (hoje é hardcoded `meiaentradaestudantil.com.br`)
- ❌ Dados do responsável legal (RPAE/substabelecimento)
- ❌ Política de revogação local

### 2.5 Layout visual / modelo padronizado

- `admin/src/card/pdfGenerator.ts` usa `downloadCarteiraSvg` + `svg-to-pdfkit` + `PDFKit` para gerar um PDF com template SVG da entidade. O template SVG é baixado via `getUrlFundoEntidadeById` (não hard-coded no repo).
- A especificação ITI prevê modelo único nacional (frente/verso), com **caixa de assinatura digital**, **campo para QR code em posição fixa**, **brasão da República**, **logomarca CIE digital**.
- O layout atual é livre por entidade -- uma vez que cada entidade pode fazer upload do próprio `fundo_carteirinha_url` -- e portanto **não segue o modelo único nacional**.

### 2.6 Validade (veado OK)

`web/src/components/Carteira.tsx:25`:
```tsx
const validade = `31/03/${moment(carteira.created_at).add(1, "years").format("YYYY")}`;
```
✅ Correto: 31 de março do ano seguinte (conforme especificação CIE).

### 2.7 Geração/validação pública

`web/src/app/V/[token]/page.tsx` (rota pública):
```tsx
// getDadosCarteira.ts usa client = supabaseServiceRole()
// SELECT * FROM carteiras WHERE token = ?
// Sem auth, sem conferência de assinatura.
```

Para CIE v3.3 a validação pública deve:
1. Decodificar o QR / parsear URL de validação
2. Carregar a CIE digital assinada
3. Verificar assinatura CAdES contra a cadeia da IEEA-Raiz
4. Consultar LCR/LCAR da AC emissora do certificado de atributo
5. Conferir validade temporal (carimbo de tempo se houver)
6. Renderizar chain-of-trust verification (verde/vermelho/amarelo)

Nada disso existe hoje. O endpoint atual só confere se `token` tem linha na `carteiras` -- fácil de contornar (basta criar um QR qualquer com token que exista em produção de outra pessoa).

---

## 3. Riscos regulatórios e legais

| Risco | Detalhe |
|---|---|
| **Inidoneidade**, `meia-entrada`, `filme/cinema/teatro/eventos` | O sistema gera carteirinhas que **não são CIE oficial**; portadores podem ser **recusados** em válidos que conferem via app CIE da ANPG ou site do ITI. |
| **Fraude de meia-entrada** | Como não há assinatura criptográfica, qualquer um pode replicar a carteirinha com dados válidos de um estudante e QR apontando para o mesmo `token`. |
| **Exposição de dados pessoais (LGPD)** -- combina com Auditoria S-03 | A rota pública `/V/[token]` expõe CPF, RG, filiação, foto, etc. sem auth e sem necessidade -- agrava o risco regulatório.+implica que um QR malicioso com `token` valido libere dados de terceiros. |
| **Fiscalização pela ANPG/UPEE** | A EEA credenciada é responsável técnica pela emissão. Sem integrar-se com EEA nacional, o sistema **não é autorizado** a emitir CIE digital válida -- apenas carteirinhas privadas. |
| **Multa / ação de improbidade** | Uso inautenticado de identidade estudantil pode enquadrar art. 299/304 do CP se houver dolo. |
| **中途 financiamento do MEC** | A especificação exige que a CIE seja emitida por IEEA/entidade credenciada -- uso sem isso pode invalidar eventuais benefícios fiscais/incentivos. |

---

## 4. Plano de adequação -- roteiro em fases

> Esta é uma direção arquitetural, não uma lista detalhada de tickets. Cada item exige brainstorming com stakeholders (legal, diretoria da EEEA nacional, SECOMP ou quem for a EEA oficial) antes de codar.

### Fase 0 -- Decisão estratégica (antes de tudo)
- A **meia-entrada** é dona do sistema? Ela é uma EEEA credenciada? Ou atua como **viabilizadora técnica** para uma EEEA nacional (ANPG/UPEEE)?
- Decidir entre: (a) virar CIE oficial (alto custo), (b) continuar como carteirinha privada só para facilidade interna (baixo custo, mas sem valor legal), (c) híbrido -- apoiar EEEAs credenciadas que usarão a plataforma.
- Sem Fase 0, qualquer esforço técnico abaixo é prematuro.

### Fase 1 -- EEA / cadeia de confiança (Sprint 2-4)
1. **Mapear EEEA nacional** responsável pela CIE digital (provavelmente UPEE ou ANPG).
2. Obter credenciamento ou parceria formal.
3. Adquirir / operar **certificado de atributo de entidade emissora** (E1 da IEEA-Raiz?).
4. Provisionar infra para gerar certificados de atributo por estudante (se a plataforma for a autoridade emissora) OU só assinar com certificado de emissor (se várias EEEAs usam a plataforma).

### Fase 2 -- Schema + assinatura (Sprint 3-5)
1. Migrar `entidades` adicionando: `cnpj`, `codigo_inep`, `ieea_id`, `url_validacao_oficial`, `responsavel_legal`.
2. Migrar `carteiras` adicionando: `cie_versao` (ex.: `3.3`), `cie_documento_hash`, `cie_assinatura_pkcs7`, `cie_certificado_atributo_oid` (`2.16.76.1.10`), `cie_emissor_id`, `cie_validade` (até 31/03 ano+1 -- já computado, persistir), `cie_revogado_em`.
3. Implementar pipeline de assinatura CAdES-BES (pkcs7) na geração do PDF/PNG da CIE.
4. Subir cadeia ICP-Brasil / IEEA-Raiz no validador público.

### Fase 3 -- QR code normalizado (Sprint 4-5)
1. Substituir `qrCodeUtils.ts` por gerador que monte payload CIE v3.3:
   ```
   <id-protocolo>:<tipo-doc>:<id-doc>:<id-eea>:<url-validacao-assinada>:<hash-pdf-cie>:<timestamp-assinatura>
   ```
2. Embutir assinatura do payload pelo certificado de atributo.
3. Garantir recovery/versão (campo de versão) para futuras atualizações.

### Fase 4 -- Validação pública confiável (Sprint 5)
1. Refazer `/V/[token]` (e/ou `/v/[uuid]`) para:
   - Rejeitar requests não assinados (ex.: por assinatura protegida por canal HTTPS do validador).
   - Decodificar o payload recebido (não mais `token = base36(ts)`).
   - Validar CAdES contra cadeia da IEEA-Raiz.
   - Consultar **LCAR** online do certificado de atributo (timeout de 2s, fallback).
   - Renderizar status visual de conformidade (verde/vermelho) -- parecido com o app oficial CIE da ANPG.
2. **Nunca mais** usar service key sem auth. Para validação pública, expor SOMENTE o subconjunto de campos permitido, e idealmente exigir **PIN** ou **nonce assinado** no payload (QR rotação).

### Fase 5 -- Layout / modelo visual (Sprint 5-6)
1. Adotar template SVG **oficial** CIE digital.
2. Remover `fundo_carteirinha_url` customizado (ou mantê-lo apenas como branding secundário, com layout oficial por cima).
3. Inserir brasão da República + logo CIE digital + caixa de assinatura digital conforme spec ITI.

### Fase 6 -- Auditoria / revogação (Sprint 6)
1. Log imutável de emissão (`cie_emissao_log`: hash, ID estudante, EEA, timestamp, cert OID).
2. Endpoint de revogação (estudante cancela matrícula → revoga CIE).
3. Publicar LCR/LCAR ownhosted (URL persistente) para o validador consultar.

### Fase 7 -- Hardening (encadeia com Auditoria Segurança/LGPD)
- Resolver itens S-01 ~ S-07 do informe de segurança (cenário: serviço público abandonado, prevenção de expurgo de dados pessoais).
- Implementar `middleware.ts` em ambos os repos.
- Headers de segurança HTTP em `next.config.mjs`.
- Remover `base.ts` (service key no client).

---

## 5. Lacunas bloqueantes que precisam de decisão externa

1. **Quem é a EEEA?** É exterior ao projeto -- não é algo que se codifica. É política. Sem isso, nada abaixo faz sentido.
2. **Modelo de negócio** -- o projeto cobra por carteira emitida? Recebe repasse? Se o custo do certificado de atributo por estudante for alto, o modelo precisa revisão.
3. **Plano de incentivo fiscal / crédito tributário** -- se a EEEA for credenciada, há requisitos de auditoria (períódica).
4. **Integração com o app oficial CIE da ANPG** -- o validador móvel oficial pode já consumir URLs CIE v3.x. Precisamos nos certificar do payload exato aceito.

---

## 6. Conclusão

O projeto `up/admin` + `up/web` é uma **plataforma de gestão de carteirinhas privadas** -- não uma **CIE oficial**. Está a uma **reimplementação de camada de confiança + integração ICP-Brasil** de distância da conformidade Portaria CIE v3.3.

Os campos de dados básicos (CPF, RG, nome, filiação, DOB, curso, instituição) já estão presentes no schema `carteiras`, e a regra de validade (31/03 ano+1) está correta -- o que é um bom começo.

Os gaps críticos:

1. **Ausência total de certificado de atributo ICP-Brasil** -- núcleo da CIE v3.3.
2. **Ausência de assinatura criptográfica** (PKCS#7/CAdES) do documento.
3. **QR code trivialmente forjável** (`base36(timestamp)` só aponta URL).
4. **Validação pública sem conferência criptográfica** e com **exposição de dados pessoais** (vulnerabilidade LGPD associada a S-03).
5. **Schema sem identificadores oficiais do emissor** (CNPJ, INEP, IEEA).
6. **Layout visual próprio** por entidade -- não segue modelo único nacional.

A adequação não é mais "segurança patch" -- é uma iniciativa de produto que exige parceria institucional (EEEA credenciada) e decisão estratégica antes de codar.

Davi Aazevedo
daviaaze@gmail.com
2026-07-03