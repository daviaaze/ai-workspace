# Fase 1 — Qualidade das Fontes: Source Reputation System

**Data:** 2026-06-16 | **Plano macro:** `PLANO_ARQUITETURA.md`
**Base:** CRED-1 (2.673 domínios) + CrediNet + Tracking empírico
**Decisão:** 🔴 Fontes com score < threshold são **ignoradas** (economiza tokens)

---

## 1. Arquitetura do Sistema

```
URL vinda do scraping
  ↓
1. Extrair domínio + normalizar
  ↓
2. CRED-1 lookup (score do domínio)
  ↓
3. CrediNet lookup (fallback se não estiver no CRED-1)
  ↓
4. Tracking empírico (acurácia histórica do domínio)
  ↓
5. Cross-reference (fontes que concordam entre si)
  ↓
6. Score composto (0.0 - 1.0)
  ↓
7. Decisão: score ≥ threshold? → passa pro LLM
               score < threshold? → descartada (economiza tokens)
```

---

## 2. Database Schema

### 2.1 Tabela de Domínios (reputação consolidada)

```sql
CREATE TABLE domain_reputation (
    domain TEXT PRIMARY KEY,                    -- domínio normalizado (ex: "infowars.com")
    
    -- CRED-1
    cred1_score REAL,                           -- 0.0-1.0 (do dataset)
    cred1_category TEXT,                        -- 'fake', 'unreliable', 'conspiracy', 'mixed', 'satire', 'rumor', 'reliable'
    cred1_sources INT DEFAULT 0,                -- quantas listas independentes flagaram
    cred1_scores_age REAL,                      -- score parcial (idade do domínio)
    cred1_score_cat REAL,                       -- score parcial (categoria)
    cred1_score_factcheck REAL,                 -- score parcial (fact-checking)
    cred1_score_iffy REAL,                      -- score parcial (Iffy.news)
    cred1_score_safebrowsing REAL,              -- score parcial (Safe Browsing)
    cred1_score_tranco REAL,                    -- score parcial (popularidade)
    cred1_last_updated TIMESTAMPTZ,             -- quando o CRED-1 foi atualizado
    
    -- CrediNet (fallback)
    credinet_credible BOOLEAN,                  -- TRUE/FALSE (se consultado)
    credinet_last_checked TIMESTAMPTZ,
    
    -- Nosso tracking empírico
    times_used INT DEFAULT 0,                   -- número de vezes que usamos este domínio
    times_accurate INT DEFAULT 0,               -- vezes que a info se confirmou correta
    times_inaccurate INT DEFAULT 0,             -- vezes que a info se confirmou incorreta
    accuracy_rate REAL DEFAULT NULL,            -- times_accurate / (times_accurate + times_inaccurate)
    
    -- Cross-reference
    cross_ref_score REAL DEFAULT NULL,          -- 0.0-1.0 (quanto esse domínio concorda com outros confiáveis)
    cross_ref_samples INT DEFAULT 0,            -- número de amostras de cross-ref
    
    -- User feedback
    user_rating REAL DEFAULT NULL,              -- -1.0 (ruim) a 1.0 (bom)
    user_flags INT DEFAULT 0,                   -- número de vezes que foi flagado como ruim
    user_endorsements INT DEFAULT 0,            -- número de vezes que foi endossado como bom
    
    -- Score composto final
    composite_score REAL DEFAULT 0.5,           -- 0.0-1.0 (calculado)
    composite_updated TIMESTAMPTZ DEFAULT NOW(),
    
    -- Metadados
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX idx_domain_composite_score ON domain_reputation(composite_score);
CREATE INDEX idx_domain_cred1_score ON domain_reputation(cred1_score);
CREATE INDEX idx_domain_accuracy ON domain_reputation(accuracy_rate);
```

### 2.2 Tabela de URLs (rastreamento individual)

```sql
CREATE TABLE source_tracking (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,                           -- URL completa
    domain TEXT NOT NULL REFERENCES domain_reputation(domain),
    title TEXT DEFAULT '',
    snippet TEXT DEFAULT '',
    
    -- Score na hora do uso (snapshot histórico)
    score_at_time REAL DEFAULT 0.5,
    
    -- Uso
    first_used TIMESTAMPTZ DEFAULT NOW(),
    last_used TIMESTAMPTZ DEFAULT NOW(),
    times_used INT DEFAULT 1,
    
    -- Validação posterior
    was_accurate BOOLEAN,                        -- NULL = não verificado ainda
    verified_by TEXT DEFAULT '',                  -- 'user', 'cross_ref', 'auto'
    
    -- Pesquisa associada
    research_id INT REFERENCES research_results(id),
    sub_question TEXT DEFAULT ''
);

CREATE INDEX idx_source_tracking_domain ON source_tracking(domain);
CREATE INDEX idx_source_tracking_url ON source_tracking(url);
CREATE INDEX idx_source_tracking_accurate ON source_tracking(was_accurate);
```

### 2.3 Tabela de Cross-Reference

```sql
CREATE TABLE cross_reference_log (
    id SERIAL PRIMARY KEY,
    research_id INT REFERENCES research_results(id),
    claim_hash TEXT NOT NULL,                    -- hash do fato/claim sendo verificado
    claim_summary TEXT NOT NULL,                 -- resumo do claim
    sources_agreeing INT DEFAULT 0,             -- fontes que concordam
    sources_disagreeing INT DEFAULT 0,          -- fontes que discordam
    total_sources INT DEFAULT 0,
    agreement_ratio REAL DEFAULT 0.0,           -- concordância geral
    consensus TEXT DEFAULT '',                   -- 'agrees', 'disagrees', 'inconclusive'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cross_ref_claim ON cross_reference_log(claim_hash);
CREATE INDEX idx_cross_ref_research ON cross_reference_log(research_id);
```

---

## 3. Algoritmo de Score Composto

### 3.1 Fórmula

```
composite_score = (
    w1 × cred1_weighted +
    w2 × empirical_accuracy +
    w3 × cross_ref_agreement +
    w4 × user_feedback
)

onde w1 + w2 + w3 + w4 = 1.0
```

### 3.2 Pesos Padrão

| Componente | Peso (w) | Fonte | Quando se aplica |
|-----------|----------|-------|------------------|
| CRED-1 | 0.40 | Dataset externo verificado | Sempre, se disponível |
| Acurácia empírica | 0.30 | Nosso tracking histórico | Após ≥ 5 usos do domínio |
| Cross-reference | 0.20 | Concordância entre fontes | Quando há ≥ 3 fontes sobre mesmo claim |
| User feedback | 0.10 | Usuário marcou como bom/ruim | Quando há feedback |

### 3.3 Cálculo de cada componente

**CRED-1 Weighted:**
```
Se CRED-1 tem score:          cred1_weighted = cred1_score
Se CRED-1 não tem mas CrediNet sim: cred1_weighted = 0.8 se credible, 0.2 se não
Se nenhum dos dois:           cred1_weighted = 0.5 (neutro)
```

**Acurácia Empírica:**
```
Se times_used >= 5:
    empirical_accuracy = accuracy_rate (times_accurate / total)
Se times_used < 5:
    empirical_accuracy = 0.5 + (accuracy_rate - 0.5) × (times_used / 5)
    (suavização: converge lentamente no início)
Se times_used == 0:
    empirical_accuracy = 0.5
```

**Cross-Reference:**
```
Se total_sources >= 3:
    cross_ref_agreement = agreement_ratio
Se total_sources < 3:
    cross_ref_agreement = 0.5 (neutro até ter mais dados)
```

**User Feedback:**
```
Se user_flags + user_endorsements >= 3:
    user_feedback = (0.5 + user_rating) / 2
    (normaliza de [-1, 1] para [0, 1])
Se não:
    user_feedback = 0.5
```

### 3.4 Thresholds de Decisão

| Score Composto | Ação | Impacto |
|----------------|------|---------|
| **≥ 0.60** | ✅ Usa normalmente | Fonte confiável |
| **0.40 – 0.59** | 🟡 Usa com aviso "confiança baixa" | Ainda passa pro LLM, mas marcada |
| **< 0.40** | 🔴 **Ignora** (não passa pro LLM) | Economiza tokens, evita desinformação |
| **Sem score** (neutro) | 🟢 Usa normalmente (padrão otimista) | Fonte desconhecida não é punida |

---

## 4. CRED-1 Dataset Integration

### 4.1 Formato do Dataset

O CRED-1 fornece um JSON com 2.673 domínios:

```json
{
  "infowars.com": {
    "category": "fake",
    "credibility_score": 0.14,
    "domain_age_years": 26.4,
    "sources": 2,
    "score_age": 0.2,
    "score_cat": 0.05,
    "score_factcheck": 0.0,
    "score_iffy": 0.1,
    "score_safebrowsing": 0.05,
    "score_tranco": 0.1,
    "tranco_rank": 4382
  }
}
```

### 4.2 Seed Inicial

```python
# scripts/seed_cred1.py
import json
import psycopg2

# 1. Baixar dataset (sempre última versão)
#    wget https://raw.githubusercontent.com/aloth/cred-1/main/data/cred1_current.json

# 2. Carregar no banco
with open("cred1_current.json") as f:
    data = json.load(f)

conn = psycopg2.connect(AIW_DB_URL)
cur = conn.cursor()

for domain, info in data.items():
    cur.execute("""
        INSERT INTO domain_reputation (
            domain, cred1_score, cred1_category, cred1_sources,
            cred1_score_age, cred1_score_cat, cred1_score_factcheck,
            cred1_score_iffy, cred1_score_safebrowsing, cred1_score_tranco,
            composite_score, cred1_last_updated
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (domain) DO UPDATE SET
            cred1_score = EXCLUDED.cred1_score,
            cred1_category = EXCLUDED.cred1_category,
            composite_score = EXCLUDED.composite_score,
            cred1_last_updated = NOW()
    """, (
        domain,
        info.get("credibility_score"),
        info.get("category"),
        info.get("sources"),
        info.get("score_age"),
        info.get("score_cat"),
        info.get("score_factcheck"),
        info.get("score_iffy"),
        info.get("score_safebrowsing"),
        info.get("score_tranco"),
        info.get("credibility_score"),  # composite inicial = cred1_score
    ))

conn.commit()
print(f"✅ {len(data)} domínios importados do CRED-1")
```

### 4.3 Atualização Periódica

- CRED-1 é atualizado **semanalmente** (CalVer)
- `aiw source update` — baixa última versão e faz upsert
- Agendado como task Huey: toda segunda-feira às 06:00

### 4.4 Domínios CRED-1 que são "confiáveis" (score alto)

O CRED-1 tem **apenas 3 domínios marcados como "reliable"** — ele é focado em misinformation. Para fontes confiáveis, CRED-1 retorna `null` (neutro). Isso é proposital: um domínio não estar no CRED-1 **não significa que é confiável**, só significa que não foi flagado como misinformation.

---

## 5. CrediNet Integration (Fallback)

### 5.1 Instalação

```bash
pip install credigraph
```

### 5.2 Uso

```python
from credigraph import query

# Retorna True/False se o domínio é crível
result = query("apnews.com")
# {"domain": "apnews.com", "credible": True}

# Fallback: só consulta se não está no CRED-1
def get_domain_score(domain: str) -> float:
    # 1. Tenta CRED-1 primeiro
    cred1 = db.lookup(domain)
    if cred1 is not None:
        return cred1
    
    # 2. Fallback: CrediNet
    try:
        cn = query(domain)
        return 0.8 if cn["credible"] else 0.2
    except Exception:
        return 0.5  # neutro
```

### 5.3 Cache de Resultados CrediNet

- Resultados do CrediNet são cacheados na `domain_reputation` por **7 dias**
- Evita chamadas repetidas de API para o mesmo domínio

---

## 6. Cross-Reference Scoring

### 6.1 Quando ativar

- Durante a síntese do deep search, quando o LLM retorna múltiplas fontes
- Se ≥ 3 fontes independentes abordam o mesmo claim
- Fontes "independentes" = domínios diferentes, de preferência de categorias CRED-1 diferentes

### 6.2 Algoritmo

```
Para cada claim no relatório:
  1. Extrair as fontes citadas
  2. Agrupar por claim (hash do texto normalizado)
  3. Calcular agreement_ratio = fontes_que_concordam / total_fontes
  4. Se agreement_ratio >= 0.7 → "consenso"
     Se agreement_ratio <= 0.3 → "conflito"
     Senão → "inconclusivo"
  5. Atualizar cross_ref_score de cada domínio envolvido:
     - Se estava do lado do consenso: +0.05 (até máximo 1.0)
     - Se estava do lado da minoria: -0.05 (até mínimo 0.0)
```

### 6.3 Output no Relatório

```
📊 Cross-Reference Check
──────────────────────
Claim: "DeepSeek V3 é mais eficiente que GPT-4 em coding"
  3 fontes concordam: arxiv.org, paperswithcode.com, huggingface.co
  1 fonte discorda: medium.com/@randomuser
  → CONSENSO (75%) ✓

Claim: "O mercado de IA vai crescer 40% em 2026"
  2 fontes concordam, 2 discordam
  → INCONCLUSIVO ⚠️
```

---

## 7. User Feedback

### 7.1 CLI

```bash
# Marcar fonte como boa
aiw source endorse https://arxiv.org/abs/2506.12345

# Marcar fonte como ruim
aiw source flag https://medium.com/clickbait-article

# Ver score de uma fonte
aiw source check https://example.com/article

# Ver estatísticas do sistema
aiw source stats
# 📊 Source Reputation System
#   Domínios trackeados: 2,789
#   Fontes usadas: 1,234
#   CRED-1 coverage: 2,673 / 2,789 (95.8%)
#   Cross-ref amostras: 456
#   Score médio: 0.63
```

### 7.2 TUI

- Botão ✅ / ❌ em cada fonte citada no relatório
- Cor verde/amarelo/vermelho por nível de confiança
- Tooltip com explicacão do score

### 7.3 Feedback Implícito

- Usuário **reusa** uma fonte = endosso implícito
- Usuário **edita/remove** parte do relatório que citava a fonte = possível desconfiança

---

## 8. Integração com o Deep Search Existente

### 8.1 Onde mexer

```python
# src/ai_workspace/sources/
# ├── __init__.py          → exports (já existe)
# ├── models.py            → SourceRecord, DomainReputation (já existe)
# ├── reputation.py        → SourceReputationManager (principal lógica)
# ├── scoring.py           → Algoritmo de score composto
# ├── cred1.py             → CRED-1 dataset loader
# └── credinet.py          → CrediNet API wrapper

# Arquivos existentes que precisam de adaptação:
# search/deep_search.py   → Filtrar fontes antes de passar pro LLM
# cli.py                  → Comandos aiw source {check,flag,endorse,stats,update}
```

### 8.2 Fluxo no deep_search

```python
# Antes de passar fontes pro LLM sintetizador:
from ai_workspace.sources import SourceReputationManager

reputation = SourceReputationManager()

async def filter_sources(sources: list[str]) -> list[str]:
    """Filtra fontes com score abaixo do threshold."""
    trusted = []
    for url in sources:
        score = await reputation.get_composite_score(url)
        if score >= 0.4:  # threshold de ignorar
            trusted.append((url, score))
        else:
            logger.info(f"Ignored source {url} (score: {score:.2f})")
    return trusted
```

---

## 9. Métricas de Sucesso da Fase 1

| Métrica | Atual | Meta | Como Medir |
|---------|-------|------|------------|
| Domínios com score | 0 | **≥ 2.700** (CRED-1 seed) | `SELECT COUNT(*) FROM domain_reputation` |
| Fontes filtradas por pesquisa | — | **10-30%** descartadas | Proporção de fontes ignoradas / total |
| Cross-ref ativo | 0% | **≥ 50%** das pesquisas | `cross_reference_log` por research_id |
| User feedback registrado | 0 | **≥ 10/semana** | `user_flags` + `user_endorsements` |
| Precisão das fontes | — | **≥ 80%** acurácia | `accuracy_rate` médio |

---

## 10. Riscos e Mitigações

| Risco | Probabilidade | Mitigação |
|-------|--------------|-----------|
| CRED-1 cobre só fontes ruins (não certifica as boas) | Certo | Neutro = 0.5 (não punir desconhecido). Precisamos de lista complementar |
| Cross-reference falso (mesma informação copiada entre sites) | Média | Detectar duplicatas por diff de conteúdo |
| Threshold 0.4 muito agressivo (perde info boa) | Média | Começar com 0.3 e ajustar conforme feedback |
| CrediNet API ficar indisponível | Baixa | Cache local de 7 dias, fallback pra neutro |
| Usuário não dá feedback | Alta | Feedback implícito (reuso de fontes) compensa |

---

## Anexo: Lista Complementar de Fontes Confiáveis (Seed Manual)

Além do CRED-1 (que foca em misinformation), podemos adicionar manualmente fontes conhecidamente confiáveis:

```python
RELIABLE_DOMAINS = {
    "arxiv.org": 0.95,
    "github.com": 0.90,
    "wikipedia.org": 0.85,
    "reuters.com": 0.95,
    "apnews.com": 0.95,
    "nature.com": 0.95,
    "sci-hub.se": 0.80,
    "paperswithcode.com": 0.90,
    "huggingface.co": 0.85,
    "python.org": 0.90,
    "docs.python.org": 0.95,
    "nixos.org": 0.85,
    "kernel.org": 0.90,
    "stackoverflow.com": 0.75,  # útil mas verificar
}
```

Ideal: evoluir para um sistema onde **qualquer usuário pode contribuir** com ratings de domínio (moderados).
