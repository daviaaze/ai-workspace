# Auditoria + Rewrite de Copy de Marketing (CDC Art. 37)

> **Versão:** 1.0 | **Data:** {{DATA}}
> **Subprompt:** 09 — Copy Marketing
> **Alimenta findings:** M-01/M-02
> **Ferramenta:** Auditoria semântica de claims + rewrite

---

## 1. Inventário de Alegações (Auditoria)

### 1.1 Lista de Termos-Lista-Vermelha (proibidos)

| Termo | Problema | Substituição |
|---|---|---|
| "válida em todo Brasil" / "nacional" | Alega que é CIE oficial; aplicação não é uniforme (cada estabelecimento decide) | "carteira de identificação estudantil privada" |
| "documento oficial" | Falso enquanto não houver certificação CIE v3.3 | "documento de identificação estudantil privado" |
| "reconhecida nacionalmente" | Idem | "emitida pela entidade {{ENTIDADE}}" |
| "aceita em estabelecimentos" | Sugere aceitação garantida | "pode ser apresentada em estabelecimentos" |
| "CIE" / "Carteira de Identificação Estudantil" (sem qualificação) | Sugere que é a CIE oficial | "carteira de identificação estudantil" ou "documento estudantil" |
| "garantido por lei" (sozinho, sem disclaimer) | Omite que a aceitação depende do estabelecimento | "direito garantido pela Lei 12.933/2013" + disclaimer |
| Selo ICP-Brasil, ITI, MEC | Falsa impressão de chancela governamental | Remover completamente |
| "grátis" / "sem custo" (se houver taxa) | Enganosa por omissão (art. 37, §1º CDC) | Informar custo total com destaque |

### 1.2 Locais a Vasculhar

| Local | Arquivo/Rota | Risco |
|---|---|---|
| Página inicial (web) | `web/src/app/[entidade]/page.tsx` | **Alto** — hero text, CTAs |
| Rodapé | `web/src/components/layout/footer.tsx` | **Médio** — claims recorrentes |
| Página "Sobre" | `web/src/app/sobre/page.tsx` | **Médio** — descrição do serviço |
| Textos editáveis por entidade | `intro_text`, `texto_final`, `texto_adicional_pagamento` (admin tiptap) | **Alto** — cada entidade pode escrever alegações indevidas |
| Meta tags/SEO | `layout.tsx`, `page.tsx` head | **Médio** — description pode conter claim |
| E-mail de confirmação de emissão | Templates de e-mail | **Médio** — pode prometer aceitação |
| Página de validação `/V/[token]` | Página SSR | **Baixo** — apenas dados de validação |
| Admin — dashboard entidade | `admin/src/app/dashboard/page.tsx` | **Baixo** — painel interno |

### 1.3 Tabela de Achados (Template)

| Local | Texto atual (hipótese — grepar) | Classificação | Risco CDC | Ação |
|---|---|---|---|---|
| Hero page | *"Sua carteira de estudante oficial, válida em todo o Brasil"* | **Enganosa** (art. 37) | **Alto** | Reescrever (ver §2) |
| Footer | *"Carteira de Identificação Estudantil reconhecida nacionalmente"* | **Enganosa por omissão** | **Alto** | Reescrever (ver §2) |
| CTA "Solicitar carteirinha" | *"Garanta sua meia-entrada agora"* | **Omissa** (sugere que a carteirinha por si garante o direito) | **Médio** | Reescrever (ver §2) |
| Texto entidade (tiptap) | *"Documento oficial aceito em todos os cinemas"* | **Enganosa** (não há garantia de aceitação) | **Alto** | Bloquear termo (lista vermelha) |
| Meta description | *"CIE digital oficial — a mais confiável do Brasil"* | **Enganosa** (não é CIE oficial) | **Alto** | Reescrever |

---

## 2. Rewrite Proposto

### 2.1 Modo Pré-CIE (`feature_flags.cie_oficial_emissao = false`)

| Original | Novo texto |
|---|---|
| *"Sua carteira de estudante oficial, válida em todo o Brasil"* | ✅ *"Sua carteira de identificação estudantil — emitida por {{ENTIDADE}}. A meia-entrada é direito garantido pela Lei 12.933/2013; a aceitação em estabelecimentos é verificada no local."* |
| *"Carteira de Identificação Estudantil reconhecida nacionalmente"* | ✅ *"Carteira de identificação estudantil — emitida pela entidade {{ENTIDADE}}."* |
| *"Garanta sua meia-entrada agora"* | ✅ *"Solicite sua carteira de estudante — o direito à meia-entrada é garantido por lei (Lei 12.933/2013)."* |
| *"Documento oficial aceito em todos os cinemas"* | ✅ *"Documento de identificação estudantil. A aceitação depende da política de cada estabelecimento."* |

### 2.2 Modo CIE Oficial (`feature_flags.cie_oficial_emissao = true`)

| Original | Novo texto |
|---|---|
| *"Sua carteira de estudante oficial, válida em todo o Brasil"* | ✅ *"Sua CIE oficial — Carteira de Identificação Estudantil com certificado ICP-Brasil. Válida em todo o território nacional conforme a Portaria CIE v3.3."* |
| *"Carteira de Identificação Estudantil reconhecida nacionalmente"* | ✅ *"CIE oficial — Carteira de Identificação Estudantil com validade jurídica nacional (ICP-Brasil)."* |

---

## 3. Protocolo de Copy para Admins/Entidades

### 3.1 Regras de Negócio

Todo texto editável por entidade (na base de dados `texto_final`, `intro_text`, `texto_adicional_pagamento`) deve ser:

1. **Filtrado por lista-vermelha** — termos proibidos são bloqueados no salvamento (server-side);
2. **Aprovado por DPO/Jurídico** antes da publicação (checklist de aprovação);
3. **Versionado** — cada alteração gera nova versão rastreável.

### 3.2 Lista-Vermelha (Termos Proibidos)

```typescript
const TERMS_REDLIST = [
  'oficial', 'reconhecida nacionalmente', 'válida em todo o Brasil',
  'válida em todo brasil', 'documento oficial', 'válida nacionalmente',
  'ICP-Brasil', 'ITI', 'chancela', 'governo', 'governamental',
  'garantido por lei' (isolado), 'aceito em todos', 'todos os estabelecimentos',
  'grátis', 'sem custo', 'totalmente gratuito',
  'CIE', 'Carteira de Identificação Estudantil' (sem qualificação)
];
// Nota: 'CIE oficial' é permitido APENAS quando feature_flags.cie_oficial_emissao = true
```

### 3.3 Lista-Verde (Termos Recomendados)

```typescript
const TERMS_WHITELIST = [
  'carteira de identificação estudantil',
  'documento de estudante',
  'direito à meia-entrada',
  'Lei 12.933/2013',
  'documento privado',
  'emitido por {{ENTIDADE}}',
  'verificação no estabelecimento',
];
```

### 3.4 Checklist de Aprovação (DPO/Jurídico)

Antes de publicar qualquer texto de entidade:

- [ ] Texto não contém termos da lista-vermelha
- [ ] Não promete aceitação garantida em estabelecimentos
- [ ] Não usa "oficial"/"reconhecida" indevidamente
- [ ] Não sugere chancela governamental
- [ ] Disclaimer visível: "documento privado de identificação estudantil"
- [ ] Aprovado por: DPO [ ] Jurídico [ ] Data: {{DATA}}

---

## 4. Disclaimers Contextuais

### 4.1 Hero da página (modo pré-CIE)

> ℹ️ *Esta é uma carteira de identificação estudantil privada. O direito à meia-entrada é garantido pela Lei 12.933/2013. A aceitação em estabelecimentos depende de verificação local.*

### 4.2 Rodapé (todas as páginas)

> *Meia-Entrada — Emissão de carteiras de identificação estudantil. Consulte nossos [Termos de Uso](/termos) e [Política de Privacidade](/privacidade).*

### 4.3 Recibo de emissão

> *Carteira emitida em {{DATA}}. Documento de identificação estudantil privado. A CIE oficial com certificação ICP-Brasil está em processo de implementação.*

---

## 5. Implementação Técnica

### 5.1 CI Gate

```yaml
# .github/workflows/ci.yml — adicionar step após lint
- name: Check for prohibited marketing terms
  run: |
    TERMS_PROHIBIDOS=("oficial" "reconhecida nacionalmente" "válida em todo brasil" "documento oficial")
    for term in "${TERMS_PROHIBIDOS[@]}"; do
      if grep -r -i -l "$term" web/src/app/admin --include="*.{tsx,ts,jsx,js}" 2>/dev/null; then
        echo "❌ Termo proibido encontrado: '$term'"
        exit 1
      fi
    done
    echo "✅ Nenhum termo proibido encontrado"
```

### 5.2 Feature Flag

```typescript
// Quando true, troca automaticamente o disclaimer e o texto hero
// Definir em: feature_flags.cie_oficial_emissao
const MODE = process.env.NEXT_PUBLIC_CIE_OFICIAL === 'true' ? 'cie' : 'pre_cie';
```

### 5.3 Versionamento

Textos de UI renderizados a partir de variantes versionadas (não hardcoded). Usar arquivo YAML/JSON de tradução:

```yaml
# public/locales/pt-BR/disclaimers.yaml
pre_cie:
  hero: "carteira de identificação estudantil privada..."
  footer: "documento privado - CIE oficial em implementação"
  receipt: "documento privado"
cie_oficial:
  hero: "CIE oficial com certificação ICP-Brasil..."
  footer: "CIE oficial - Portaria CIE v3.3"
  receipt: "CIE oficial - {{CODIGO_VALIDACAO}}"
```

---

## 6. Risco CDC por Alegação (Resumo)

| Alegação | Art. CDC | Risco | Multa ANPD/CDC | Ação |
|---|---|---|---|---|
| "Documento oficial" (sem CIE) | Art. 37 (enganosa) | **Alto** | Multa CDC até R$ 11MM (art. 56) | Remover |
| "Válida em todo Brasil" | Art. 37 (enganosa) | **Alto** | Multa CDC + indenização coletiva | Reescrever + disclaimer |
| "Grátis" (se com taxa) | Art. 37, §1º (enganosa por omissão) | **Médio** | Multa CDC + obrigação de informar | Corrigir transparência |
| Selo governamental sem autorização | Art. 67 (falsa indicação) | **Alto** | Crime (art. 67 Lei 8.078) + multa | Remover imediatamente |
| "Meia-entrada garantida" (sem disclaimer) | Art. 30 (vinculação) | **Médio** | Obrigação de cumprir o prometido | Reescrever |

---

## 7. Histórico

| Versão | Data | Autor | Alterações |
|---|---|---|---|
| 1.0 | {{DATA}} | {{DPO_NOME}} | Versão inicial |

---

## Placeholders

| Placeholder | Responsável |
|---|---|
| `{{ENTIDADE}}` | Dinâmico (nome da entidade emissora) |
| `{{DPO_NOME}}` | Cliente |
| `{{DATA}}` | Cliente |

---

## Disclaimer

*Auditoria técnico-jurídica de copy. A aprovação final dos textos de marca é do marketing com o jurídico (OAB). A lista-vermelha é sugestão inicial — cada entidade pode ter peculiaridades. O CI gate é implementação técnica que deve ser validada antes de ativar.*

**Revisão pendente:** [ ] OAB validar rewrites propostos; [ ] Dev implementar CI gate; [ ] DPO revisar textos de entidades ativas; [ ] Produto configurar feature flag.
