# Leilão Radar — Plano de Varredura v2 (Refinado)

> **Missão:** Construir um sistema automatizado que varre sites oficiais de leilão do Brasil, identificando oportunidades de revenda com ROI alto, dentro do budget do investidor.
>
> **Princípio norteador (v2):** Começa enxuto, valida o negócio, expande só quando fizer sentido.

---

## 🎯 0. MUDANÇAS DA v1 PARA v2

| # | Refinamento | Decisão |
|---|-------------|---------|
| 1 | ✅ Lean MVP antes do plano completo | Incluído |
| 2 | ✅ Classificação de fontes por nível de acesso | Aplicada |
| 3 | ✅ Parsing de PDF em camadas (MVP detecta, Fase 3 parseia) | Hibrido |
| 4 | ✅ Pricing em camadas (manual → scraping ML → API) | Aplicado |
| 5 | ✅ Scraping de agregadores no MVP ao invés de reimplementar | Aplicado |
| 6 | ✅ Checkpoints de decisão go/no-go a cada 2 semanas | Aplicado |
| 7 | ✅ Política de retenção de dados | Aplicada |

---

## 🚀 1. LEAN MVP — O QUE RODA NA SEMANA 1

**Meta do MVP:** Investidor recebe primeira notificação de oportunidade em **7 dias**, com mínimo esforço técnico.

### 1.1 Escopo do MVP

| Item | Implementação |
|------|--------------|
| **Fontes** | Somente 2: **Receita Federal SLE** (pública) + **1 agregador** (Leilão.net — scraping) |
| **Recursos** | Scraping + SQLite + CLI + daily digest por email/Telegram |
| **Pricing** | **Tabela manual** de preços-padrão (iPhone 13, Xiaomi Redmi, etc.) |
| **ROI** | Cálculo bruto (preço mercado - preço leilão) / preço leilão |
| **Tempo** | 10-15h na semana 1 |
| **Custo** | R$ 0 (rodando no próprio computador) |

### 1.2 Justificativa do MVP enxuto

```
ANTES (v1):  12 semanas → 40 fontes → 500 lotes/dia → alertas reais
             Risco: construir muito sem validar que o negócio funciona

AGORA (v2): 1 semana → 2 fontes → ~30 lotes/dia → 1ª notificação
             Validar: "O sistema detecta oportunidades que eu compraria?"
             Se SIM → Expandir (Fase 1+)
             Se NÃO → Repensar antes de investir mais tempo
```

### 1.3 Critério de sucesso do MVP

```
✅ SUCESSO se:
   → Recebeu pelo menos 1 alerta com ROI >= 50% e preço <= R$ 10K
   → Em um lote que o investidor realmente compraria

❌ FALHA se:
   → Alertas irrelevantes (> 90%)
   → Ou nenhum lote com ROI >= 50% nas 2 fontes
   → Ou sistema quebra sem recuperação em 7 dias
```

---

## 🗂 2. INVENTÁRIO DE FONTES — CLASSIFICADO POR ACESSO

### Tier A — **PÚBLICAS (sem login)** — MVP

| # | Fonte | URL | Tipo | Frequência | Status MVP |
|---|-------|-----|------|-----------|------------|
| A1 | **Receita Federal SLE** | https://www25.receita.fazenda.gov.br/sle-sociedade/portal | Mercadorias | 6h | ✅ Semana 1 |
| A2 | **Leilão.net** (agregador) | https://www.leilao.net/ | Agregador | 12h | ✅ Semana 1 |
| A3 | **TriLeilões** | https://www.trileiloes.com.br/ | Agregador | 12h | Semana 4 |
| A4 | **Mega Leilões** | https://www.megaleiloes.com.br/ | Agregador | 12h | Semana 4 |
| A5 | **Parque dos Leilões** | https://www.parquedosleiloes.com.br/ | Agregador | 12h | Semana 4 |
| A6 | **Lance Judicial** | https://www.lancejudicial.com.br/ | Agregador | 12h | Semana 4 |
| A7 | **Justiça Leilão** | https://www.justica-leilao.com.br/ | Agregador | 12h | Semana 4 |
| A8 | **PF — Polícia Federal** (editais em HTML) | https://www.gov.br/pf/pt-br/assuntos/licitacoes | Bens apreendidos | 24h | Semana 4 |
| A9 | **PRF** | https://www.gov.br/prf/pt-br/leiloes | Veículos | 24h | Semana 4 |
| A10 | **Correios** (editais públicos) | https://www.correios.com.br/ | Refugo | 24h | Semana 5 |
| A11 | **SEFAZ-MT** | https://www5.sefaz.mt.gov.br/ | Mercadorias | 24h | Semana 6 |
| A12 | **PF/MJSP notícias** | https://www.gov.br/mj/pt-br/assuntos/noticias | Bens do crime | 24h | Semana 6 |
| A13 | **Ibama** | https://www.gov.br/ibama/pt-br | Bens apreendidos | 24h | Fase posterior |
| A14 | **CGU** | https://www.gov.br/cgu/pt-br | Bens inservíveis | 24h | Fase posterior |
| A15 | **CONAB** | https://www.gov.br/pt-br/servicos | Produtos agrícolas | 24h | Fase posterior |
| A16 | **Forças Armadas** (Exército/Marinha/Aer.) | Variados | Bens inservíveis | 24h | Fase posterior |
| A17 | **SEFAZ-SP** | https://portal.fazenda.sp.gov.br/ | Mercadorias | 24h | Semana 6 |
| A18 | **SEFAZ-PR** | https://www.fazenda.pr.gov.br/ | Mercadorias | 24h | Semana 6 |
| A19 | **Detran-SP** | https://www.detran.sp.gov.br/ | Veículos | 24h | Semana 7 |
| A20 | **Detran-RJ** | https://www.detran.rj.gov.br/ | Veículos | 24h | Semana 7 |

### Tier B — **CONTA SIMPLES (cadastro email)** — Fase 2

| # | Fonte | URL | Tipo | Quando |
|---|-------|-----|------|--------|
| B1 | **SEFAZ-RJ** | https://www.fazenda.rj.gov.br/ | Mercadorias | Semana 6 |
| B2 | **SEFAZ-MG** | https://www.fazenda.mg.gov.br/ | Mercadorias | Semana 6 |
| B3 | **SEFAZ-RS** | https://www.sefaz.rs.gov.br/ | Mercadorias | Semana 6 |
| B4 | **Detran-MG** | https://www.detran.mg.gov.br/ | Veículos | Semana 7 |
| B5 | **Detran-RS** | https://www.detran.rs.gov.br/ | Veículos | Semana 7 |
| B6 | **TJ-RJ** | https://www.tjrj.jus.br/leiloes | Judicial | Semana 8 |
| B7 | **TJ-MG** | https://www.tjmg.jus.br/leiloes | Judicial | Semana 8 |
| B8 | **TRFs** (1,2,3) | Variados | Judicial federal | Fase posterior |
| B9 | **Bacen — Instituições Liquidadas** | https://www.bcb.gov.br/ | Ativos | Fase posterior |
| B10 | **BRB** | https://www.brb.com.br/ | Imóveis | Fase posterior |

### Tier C — **CONTA QUALIFICADA (certificado digital/e-CAC)** — Fase 3+

| # | Fonte | URL | Tipo | Quando |
|---|-------|-----|------|--------|
| C1 | **CAIXA Imóveis** | https://venda-imoveis.caixa.gov.br/ | Imóveis (SPA) | Semana 8+ |
| C2 | **CAIXA Veículos** | https://veiculos.caixa.gov.br/ | Veículos | Semana 8+ |
| C3 | **Banco do Brasil Leilões** | https://www.bb.com.br/site/leiloes/ | Imóveis/Veículos | Semana 8+ |
| C4 | **BB — Licitações-e** | https://www.licitacoes-e.com.br/ | Portal | Semana 8+ |
| C5 | **TJ-SP (SIEJ)** | https://siej.tjsp.jus.br/ | Judicial SP | Semana 10+ |

> **Justificativa da ordenação:** MVP só roda Tier A (público). Tier B quando já tiver抗击第一次 compra validada. Tier C quando fizer sentido financeiro (imóveis = ticket alto, diferente do foco inicial).

---

## 🏗 3. ARQUITETURA v2 (com diferenças)

```
┌──────────────────────────────────────────────────────────────┐
│                    LEILÃO RADAR v2 — ARQUITETURA              │
└──────────────────────────────────────────────────────────────┘

   ┌────────────────────┐
   │  APScheduler       │ 灵活: MVP (manual/cron), Fase 6 (APScheduler)
   │  (ou cron simples) │  MVP: 1x/dia | Produção: 4x/dia
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐       ┌──────────────────────┐
   │  Scraper Manager   │──────▶│  Sources Registry    │
   │  (orquestrador)    │       │  (A1-A20 + B/C lazy)  │
   └─────────┬──────────┘       └──────────────────────┘
             │
             ▼
   ┌────────────────────┐
   │  Scraping Chain    │  httpx+selectolax → Playwright → Paginated
   │  (tiered tools)    │  NOVO: httpx+selectolax (10x mais rápido que
   │                    │        BeautifulSoup pra HTML estático, pra MVP)
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐
   │  Parser Registry   │  HTML parser + PDF detector (MVP só detecta)
   │  + PDF detector    │  + LLM parser (Fase 3 → Gemini Flash)
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐
   │  Storage Layer     │  SQLite → Postgres
   │  + Retention       │  NOVO: job de arquivamento semanal
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐       ┌──────────────────────┐
   │  Pricing Layer     │──────▶│  Camada 1: Manual    │ ← MVP
   │  (3 camadas)       │       │  Camada 2: ML scrape │ ← Fase 4
   │                    │       │  Camada 3: API ML    │ ← Fase 6
   └─────────┬──────────┘       └──────────────────────┘
             │
             ▼
   ┌────────────────────┐
   │  ROI Calculator     │  Bruto (MVP) → Com taxas ML/Shopee (Fase 4)
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐       ┌──────────────────────┐
   │  Alert Engine      │──────▶│  Telegram bot        │ ← Semana 2
   │                    │       │  Email digest        │ ← Semana 2
   └────────────────────┘       └──────────────────────┘
```

### Diferenças críticas vs v1
1. **httpx + selectolax** no lugar de Crawl4AI no MVP (mais simples, menos dependências)
2. **Parser de PDF** é um estágio separado, MVP só detecta o PDF e baixa
3. **Pricing em camadas** explícito (manual → scrape → API)
4. **Tier de acesso** determina ordem de implementação

---

## 📅 4. ROADMAP v2 (12 SEMANAS, COM CHECKPOINTS)

### 🟩 SEMANA 1 — LEAN MVP

| Día | Tarefa | Entrega |
|-----|--------|---------|
| 1 | Setup projeto `leilao-radar/` + pyproject.toml | Repo inicial |
| 2 | Schema SQLite + models | Banco rodando |
| 2 | Parser Receita Federal SLE (reaproveita `tools/leilao_scraper.py`) | 1ª fonte funcionando |
| 3 | Scraper Leilão.net (agregador) | 2ª fonte |
| 4 | CLI: `python -m leilao_radar scrape --all` | Orquestração |
| 5 | Tabela manual de preços (10-20 produtos chave) | Pricing v0 |
| 6 | ROI calculator bruto + categorização simples | Análise v0 |
| 7 | Bot Telegram: daily digest às 8h | 1º alerta enviado |

**Entrega semana 1:** "Bom dia! Achei 3 lotes com ROI > 50%" no Telegram.

### 🚦 CHECKPOINT #1 (Semana 2)

```
PERGUNTA: O MVP detectou oportunidades que o investidor compraria?

MÉTRICAS:
  → Quantos lotes capturados na semana 1?
  → Quantos com ROI >= 50% e preço <= R$ 10K?
  → Investidor olhou os alertas e se interessou por algum?

DECISÃO:
  🟢 SIM → Avançar pra Fase 1 (mais fontes)
  🟡 PARCIAL → Ajustar parsers/pricing, +1 semana de validação
  🔴 NÃO → Repensar: talvez fonte errada, nicho errado, ou ideia invalidada
```

### 🟩 FASE 1 — EXPANSÃO CRÍTICA (Semana 3-4)

- [ ] TriLeilões, Mega Leilões, Parque dos Leilões, Lance Judicial, Justiça Leilão (5 agregadores)
- [ ] PF (HTML), PRF (HTML)
- [ ] Pricing v1: scraping básico do ML (sem API, sem login)
- [ ] Cálculo de ROI líquido (com taxa ML 13-19%)
- [ ] Cache HTTP (não rebaixar páginas sem alteração)

**Entrega:** 8 fontes ativas, ~80 lotes/dia.

### 🚦 CHECKPOINT #2 (Semana 4)

```
PERGUNTA: Quantos lotes com ROI >= 50% foram capturados nas últimas 2 semanas?

DECISÃO:
  🟢 >= 10 lotes relevantes → Avançar pra Fase 2 (estaduais)
  🟡 3-9 lotes → Priorizar fontes que trouxeram os melhores, descartar 1-2
  🔴 < 3 lotes → Focar em melhorar ROI calculator antes de expandir
```

### 🟩 FASE 2 — ESTADUAIS PÚBLICAS (Semana 5-7)

- [ ] Correios (editais públicos)
- [ ] SEFAZ-MT, SEFAZ-SP, SEFAZ-PR
- [ ] Detran-SP, Detran-RJ
- [ ] Rate limiting + circuit breaker (sites estaduais são instáveis)
- [ ] Parsers genéricos reutilizáveis pra sites estaduais padrão

**Entrega:** 15 fontes ativas, ~150 lotes/dia.

### 🚦 CHECKPOINT #3 (Semana 6 — MEIO DO PROJETO)

```
PERGUNTA-CHAVE: O investidor já fez a primeira compra via alerta do sistema?

ESTE É O CHECKPOINT MAIS IMPORTANTE:

  🟢 SIM → Validado! Continuar expansão + adicionar features de escala
  🟡 ALMOST (em processo) → Pausar novas fontes, focar em UX do investidor
  🔴 NÃO → Diagnóstico:
        - Alertas não chegaram? → problema de alerta
        - Chegaram mas não interessou? → problema de ROI/preço
        - Interessou mas não comprou? → problema de confiança
        → Ajustar antes de investir mais semanas
```

### 🟩 FASE 3 — CONTAS + PDF (Semana 7-9)

- [ ] Parsing de PDF (pdfplumber + Gemini Flash pra extração estruturada)
- [ ] Fontes Tier B (SEFAZ-RJ/MG/RS, Detran-MG/RS)
- [ ] TJs (TJ-RJ, TJ-MG)
- [ ] Detector de PDFs (PF, MJSP, Forças Armadas)
- [ ] Categorização via LLM (padronizar tipos)

**Entrega:** 22 fontes + capacidade de parsear editais PDF, ~300 lotes/dia.

### 🚦 CHECKPOINT #4 (Semana 8)

```
PERGUNTA: ROI calculator tem precisão útil? (comparar com compras reais)

  🟢 Erro < 30% → Avançar
  🟡 Erro 30-60% → Ajustar tabela manual, adicionar 50+ produtos
  🔴 Erro > 60% → Implementar scraping do ML de verdade (antes de API)
```

### 🟩 FASE 4 — ANÁLISE INTELIGENTE (Semana 9-10)

- [ ] Pricing v2: scraping de revenda no ML (httpx, sem API)
- [ ] Categorização automática com LLM (Gemini Flash)
- [ ] Filtro por budget, categoria, localização
- [ ] Detector de "bala de prata" (ver seção 8)
- [ ] Métricas: ROI médio, taxa de conversão de alertas

### 🚦 CHECKPOINT #5 (Semana 10)

```
PERGUNTA: Vale a pena escalar (Tier C — CAIXA/BB)?

DECISÃO:
  🟢 Já fechou 2+ compras via alertas → Adicionar Tier C (imóveis)
  🟡 Ainda em 1ª compra → Adicionar só 1-2 fontes Tier B, manter foco
  🔴 Nenhuma compra → Pausar desenvolvimento, focar só em vendas
```

### 🟩 FASE 5 — ESCALA E ALERTAS AVANÇADOS (Semana 11-12)

- [ ] Bot Telegram interativo: `/oportunidades`, `/filtrar`, `/stats`
- [ ] Alertas em tempo real (não só digest diário)
- [ ] Tier C (CAIXA Imóveis, BB, TJ-SP SIEJ) — só se checkpoint 5 liberar
- [ ] Deploy em VPS (Hetzner R$ 30/mês)
- [ ] Docker compose + monitoramento (UptimeRobot)

### 🚦 CHECKPOINT #6 (Semana 12 — FIM DO ROADMAP)

```
PERGUNTA: O sistema paga-se? (valor gerado >= custo de operação)

  🟢 SIM → Manter operação, considerar melhorias incrementais
  🟡 PRÓXIMO → Dar +4 semanas, otimizar 2 fontes que trazem mais oportunidades
  🔴 NÃO → Pausar novas features, manter só 3-5 fontes principais
  
  CRITÉRIO DEFINITIVO:
  Se gerou >= 3 compras que pagaram o tempo investido → SUCESSO
  Se não gerou nenhuma compra em 12 semanas → Sistema não é o gargalo,
  questão é de execução (investidor não está comprando) ou de tese
  (mercado não tão lucrativo quanto esperado).
```

---

## 🗄 5. SCHEMA v2 — COM RETENÇÃO

```sql
-- Fontes cadastradas
CREATE TABLE sources (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    label TEXT,
    url TEXT,
    tier TEXT,                -- 'A' (público), 'B' (conta), 'C' (qualificado)
    source_type TEXT,         -- 'federal', 'estadual', 'banco', 'judicial', 'agregador'
    priority TEXT,            -- 'crítica', 'média', 'baixa'
    check_interval_hours INTEGER,
    last_scraped_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    parser_class TEXT
);

-- Editais
CREATE TABLE editais (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    edital_number TEXT,
    title TEXT,
    location TEXT,
    start_propostas TIMESTAMP,
    end_propostas TIMESTAMP,
    data_pregao TIMESTAMP,
    total_lotes INTEGER,
    permitido_pf BOOLEAN,
    permitido_pj BOOLEAN,
    pdf_url TEXT,             -- NOVO: URL do edital em PDF (se houver)
    pdf_parsed BOOLEAN,       -- NOVO: se foi parseado
    raw_data TEXT,
    url TEXT,
    status TEXT DEFAULT 'ativo', -- NOVO: 'ativo', 'encerrado', 'arquivado'
    archived_at TIMESTAMP,    -- NOVO: data de arquivamento
    UNIQUE(source_id, edital_number)
);

-- Lotes
CREATE TABLE lotes (
    id INTEGER PRIMARY KEY,
    edital_id INTEGER REFERENCES editais(id),
    lote_number TEXT,
    titulo TEXT,
    descricao TEXT,
    preco_minimo REAL,
    moeda TEXT DEFAULT 'BRL',
    tipo TEXT,
    categoria_normalizada TEXT,  -- 'eletronico', 'veiculo', 'imovel', etc.
    situacao TEXT,               -- 'Aberto', 'Encerrado', 'Arrematado'
    permitido_para TEXT,
    local_retirada TEXT,
    icms_aliquota REAL,
    total_itens INTEGER,
    raw_data TEXT,
    url TEXT,
    scraped_at TIMESTAMP,
    status TEXT DEFAULT 'ativo', -- NOVO
    archived_at TIMESTAMP,       -- NOVO
    UNIQUE(edital_id, lote_number)
);

-- Itens dentro de um lote
CREATE TABLE lote_itens (
    id INTEGER PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes(id),
    quantity INTEGER,
    unit TEXT,
    description TEXT,
    brand TEXT,
    model TEXT
);

-- Pricing em camadas
CREATE TABLE market_prices (
    id INTEGER PRIMARY KEY,
    product_key TEXT UNIQUE,    -- ex: 'iphone_13_128gb', 'redmi_note_13_256gb'
    normalized_name TEXT,
    category TEXT,
    median_price REAL,
    min_price REAL,
    max_price REAL,
    source TEXT,               -- 'manual', 'ml_scrape', 'ml_api'
    confidence REAL,           -- 0-1
    updated_at TIMESTAMP,
    notes TEXT
);

-- Análise de ROI
CREATE TABLE lote_analysis (
    lote_id INTEGER PRIMARY KEY REFERENCES lotes(id),
    estimated_market_value REAL,
    estimated_roi REAL,             -- ROI bruto
    estimated_roi_after_fees REAL,  -- ROI líquido (após ML/Shopee + ICMS + frete)
    ml_fee_estimate REAL,
    shopee_fee_estimate REAL,
    confidence_score REAL,
    pricing_layer TEXT,             -- 'manual', 'ml_scrape', 'ml_api'
    analyzed_at TIMESTAMP,
    notes TEXT
);

-- Alertas
CREATE TABLE alertas (
    id INTEGER PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes(id),
    alert_type TEXT,                -- 'high_roi', 'silver_bullet', 'low_price'
    message TEXT,
    created_at TIMESTAMP,
    sent_at TIMESTAMP,
    channel TEXT,                   -- 'telegram', 'email'
    delivered BOOLEAN,
    user_clicked BOOLEAN DEFAULT 0  -- NOVO: tracking se investidor interagiu
);

-- User filters
CREATE TABLE user_filters (
    id INTEGER PRIMARY KEY,
    name TEXT,
    max_price REAL,
    min_roi REAL,
    min_roi_after_fees REAL,
    categories TEXT,                -- JSON array
    locations TEXT,                 -- JSON array
    allow_pj_only BOOLEAN,
    is_active BOOLEAN,
    created_at TIMESTAMP
);

-- Scrape log (auditoria)
CREATE TABLE scrape_log (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT,
    lots_found INTEGER,
    lots_new INTEGER,
    error TEXT,
    duration_ms INTEGER
);

-- Retention: job semanal arquiva tudo encerrado há > 90 dias
-- SQL: UPDATE lotes SET status='arquivado', archived_at=NOW()
--      WHERE situacao='Encerrado' AND archived_at IS NULL
--      AND scraped_at < NOW() - INTERVAL '90 days';
```

### Política de retenção

| Dado | Ação | Quando |
|------|------|--------|
| Lotes encerrados sem arremate | Arquivar (manter sumário) | 90 dias após `situacao='Encerrado'` |
| Editais encerrados | Arquivar | 90 dias após `end_propostas` |
| Cache HTTP | Expirar | 7 dias |
| Logs de scrape | Manter | 90 dias |
| Alertas não entregues | Deletar | 30 dias |
| Market prices | Manter histórico | Sempre (versionado por `updated_at`) |

**Cron semanal:** domingos 03h, roda job de arquivamento.

---

## 💰 6. PRICING EM CAMADAS

### Camada 0 — Tabela Manual (MVP — Semana 1)

```python
# src/leilao_radar/analysis/manual_prices.py
MANUAL_PRICES = {
    "iphone_13_128gb":      {"median": 2500, "min": 2200, "max": 2800},
    "iphone_12_64gb":      {"median": 1700, "min": 1500, "max": 2000},
    "redmi_note_13_256gb":  {"median": 1050, "min": 900,  "max": 1200},
    "redmi_note_13_128gb": {"median": 850,  "min": 750,  "max": 950},
    "poco_x6_pro_256gb":   {"median": 1500, "min": 1300, "max": 1700},
    "redmi_pad_se_128gb":  {"median": 850,  "min": 700,  "max": 1000},
    "macbook_air_m2_13":   {"median": 6000, "min": 5500, "max": 6500},
    "ssd_240gb":           {"median": 100,  "min": 80,   "max": 120},
    "memoria_ram_pc":      {"median": 70,   "min": 50,   "max": 90},
    "hb20_2021":           {"median": 55000, "min": 48000, "max": 62000},
    "cobalt_2012":         {"median": 22000, "min": 18000, "max": 28000},
    "foston_x13_max":      {"median": 3500, "min": 2800,  "max": 4200},
    "perfume_lattafa_khamrah": {"median": 180, "min": 120, "max": 240},
    "perfume_armaf_cdn_intense": {"median": 250, "min": 180, "max": 320},
    # Atualizar 1x/mês com base em consultas manuais ao ML
}
```

### Camada 1 — Scraping do ML (Fase 4 — Semana 9-10)

- httpx请求 ao `https://lista.mercadolivre.com.br/{produto}`
- Parseia preço médio dos 10 primeiros anúncios
- Atualiza `market_prices` com `source='ml_scrape'`
- Frequency: diário para itens que alerta, semanal para demais

### Camada 2 — API Oficial ML (Fase 6 — Semana 11+)

- Cadastro como developer no ML
- API `GET /sites/MLB/search` retorna preços
- Rate limit: 10K req/dia (suficiente)
- Custo: R$ 0 (API gratuita pra pesquisa)
- Atualiza `market_prices` com `source='ml_api'`

---

## 🔍 7. PDF PARSING — ESTRATÉGIA EM CAMADAS

### MVP (Semana 1-6) — só detecta

```python
# src/leilao_radar/scrapers/pdf_detector.py
def detect_pdf_edital(html: str) -> str | None:
    """Enfera link de PDF em página HTML, baixa, mas não parseia."""
    # Retorna path local do PDF baixado, marca edital.pdf_parsed=False
    # No alerta: "Edital em PDF — análise manual necessária"
```

### Fase 3 (Semana 7-9) — parseia com LLM

```python
# src/leilao_radar/parsers/pdf_parser.py
import pdfplumber
import gemini  # Google Gemini Flash (barato)

async def parse_edital_pdf(pdf_path: str) -> list[Lot]:
    # 1. Extrair texto com pdfplumber
    text = pdfplumber.open(pdf_path).extract_text()
    
    # 2. Pedir pro Gemini estruturar
    prompt = f"""
    Extraia todos os lotes deste edital de leilão.
    Retorne como JSON: [{{"lote": "10", "descricao": "...", 
    "preco_minimo": 500000, "tipo": "CELULAR/ACESSÓRIO"}}]
    
    Edital:
    {text[:50000]}
    """
    lots = await gemini.flash(prompt, response_format="json")
    
    # 3. Salvar no banco
    return lots
```

**Justificativa:** Gemini Flash é barato (~$0.07/million input tokens). Editais típicos ~20K tokens = ~$0.001 por PDF. 100 PDFs/mês = $0.10. Viável.

---

## 🆚 8. DIFERENCIAL vs AGREGADORES EXISTENTES

| Critério | Leilão.net, TriLeilões | Leilão Radar (nós) |
|----------|------------------------|---------------------|
| **Foco** | Lista editais | ROI pra revenda |
| **Filtro** | Por tipo/categoria | Por budget + ROI |
| **Alertas** | Diários/Email | Tempo real + Telegram |
| **Pricing** | Só preço do lance | Preço de mercado + ROI |
| **Personalização** | Genérico | Configurado pro investidor |
| **Custo** | Grátis (mas upgrade pago) | Grátis (self-hosted) |

**Estratégia:** O MVP usará Leilão.net como uma das fontes (scraping dele), em vez de reimplementar a catalogação dele. Nosso diferencial é a camada de análise por cima.

---

## 🔔 9. CRITÉRIOS DE ALERTA v2

### Silver Bullet (🥇 Crítico — notificação imediata)

```python
def is_silver_bullet(lote: Lot, analysis: LoteAnalysis) -> bool:
    return (
        lote.preco_minimo <= 5_000
        and analysis.estimated_roi_after_fees >= 1.0  # 100% líquido
        and lote.categoria_normalizada in ['eletronico', 'veiculo', 'informatica']
        and lote.permitido_para != 'PJ'  # PF pode comprar
        and lote.end_propostas <= NOW() + timedelta(days=7)
    )
```

### High ROI (🟡 Daily digest)

```python
def is_high_roi(lote, analysis) -> bool:
    return (
        lote.preco_minimo <= 10_000
        and analysis.estimated_roi_after_fees >= 0.5  # 50% líquido
        and lote.end_propostas <= NOW() + timedelta(days=14)
    )
```

### Informativo (⚪ Semana)

- Novo edital aberto em fontes prioritárias
- Lote com preço 30%+ abaixo da média histórica da categoria

---

## 📦 10. ESTRUTURA DE ARQUIVOS v2

```
leilao-radar/
├── README.md
├── pyproject.toml
├── docker-compose.yml
├── .env.example
│
├── src/leilao_radar/
│   ├── cli.py                              # `python -m leilao_radar scrape`
│   ├── config.py
│   │
│   ├── sources/
│   │   ├── base.py                         # BaseSource, Lot, Edital
│   │   ├── tier_a/                         # Públicas
│   │   │   ├── receita_federal_sle.py      # ⭐ MVP
│   │   │   ├── leilao_net.py               # ⭐ MVP (agregador)
│   │   │   ├── trileiloes.py
│   │   │   ├── mega_leiloes.py
│   │   │   ├── parque_dos_leiloes.py
│   │   │   ├── lance_judicial.py
│   │   │   ├── justica_leilao.py
│   │   │   ├── pf_leiloes.py
│   │   │   ├── prf_leiloes.py
│   │   │   ├── correios.py
│   │   │   ├── sefaz_mt.py
│   │   │   ├── sefaz_sp.py
│   │   │   ├── sefaz_pr.py
│   │   │   ├── detran_sp.py
│   │   │   └── detran_rj.py
│   │   ├── tier_b/                         # Conta simples
│   │   │   ├── sefaz_rj.py
│   │   │   ├── sefaz_mg.py
│   │   │   ├── ...
│   │   │   └── tj_rj.py
│   │   └── tier_c/                         # Conta qualificada
│   │       ├── caixa_imoveis.py
│   │       ├── bb_leiloes.py
│   │       └── tj_sp_siej.py
│   │
│   ├── scrapers/
│   │   ├── scraping_chain.py               # httpx+selectolax → Playwright
│   │   ├── pdf_detector.py                 # MVP
│   │   ├── pdf_parser.py                   # Fase 3 (Gemini)
│   │   └── rate_limiter.py
│   │
│   ├── analysis/
│   │   ├── manual_prices.py                # Tabela hardcoded (MVP)
│   │   ├── market_pricer.py                # Scraping ML (Fase 4)
│   │   ├── ml_api_pricer.py                # API ML (Fase 6)
│   │   ├── roi_calculator.py
│   │   ├── categorizer.py                  # LLM (Fase 3)
│   │   └── silver_bullet.py
│   │
│   ├── alerts/
│   │   ├── telegram_bot.py
│   │   ├── email_digest.py
│   │   └── filters.py
│   │
│   ├── storage/
│   │   ├── database.py
│   │   ├── models.py
│   │   └── retention.py                    # Job de arquivamento
│   │
│   └── scheduler/
│       ├── cron.py
│       └── checkpoint.py                   # Avalia go/no-go a cada 2 semanas
│
├── tests/
│   ├── fixtures/
│   │   ├── receita_federal_edital.html
│   │   ├── leilao_net_home.html
│   │   └── ...
│   ├── test_sources/
│   └── test_analysis/
│
└── data/
    ├── leiloes.db
    ├── pdf_cache/                           # PDFs baixados
    └── html_cache/                          # HTTP cache (7 dias)
```

---

## 📊 11. MÉTRICAS DE SUCESSO v2

| Métrica | Meta MVP (Sem 1) | Meta Fase 4 (Sem 10) | Meta Fase 6 (Sem 12) |
|---------|------------------|-----------------------|-----------------------|
| Fontes ativas | 2 | 15 | 25+ |
| Lotes/dia capturados | 30 | 300 | 500 |
| Lotes com ROI >= 50%/semana | 3 | 15 | 30 |
| Latência descoberta → alerta | < 12h | < 4h | < 1h |
| Falsos positivos (alertas) | < 50% | < 20% | < 10% |
| ROI médio dos alertas | não medido | >= 50% | >= 60% |
| Uptime | 80% (local) | 95% | 99% (VPS) |
| **Primeira compra via alerta** | — | **OBRIGATÓRIO** | — |
| Custo mensal | R$ 0 | R$ 0 | R$ 30 (VPS) |

---

## 🛡 12. CONSIDERAÇÕES LEGAIS E TÉCNICAS (mantido da v1 + ajustes)

### Legal
- ✅ Respeitar `robots.txt` de cada site
- ✅ Rate limiting: 1 req/s por domínio, 10 reqs/min pra agregadores
- ✅ User-agent identificável `LeilaoRadar/0.1 (+contato@exemplo.com)`
- ✅ Não armazenar dados pessoais de terceiros
- ❌ NÃO adicionar scraping de sites que pedem login sem ter conta

### Técnico
- ✅ Cache HTTP (não rebaixar páginas sem alteração) — 7 dias
- ✅ Detecção de mudanças (hash de HTML)
- ✅ Retry com backoff exponencial (max 3 retries)
- ✅ Circuit breaker (se uma fonte falha 3x, pausa 24h)
- ✅ Backup diário do banco

### Governança
- ✅ Logs de auditoria
- ✅ Versionamento de parsers (sites mudam)
- ✅ Testes por parser com HTML salvo (fixtures)
- ✅ Alertas de parser quebrado (sem dados há X horas)

---

## 🎯 13. RESUMO EXECUTIVO v2

```
🚀 SEMANA 1: Lean MVP
   2 fontes (Receita SLE + Leilão.net), SQLite, tabela manual,
   bot Telegram com daily digest.
   → Valida: "Sistema detecta oportunidades que eu compraria?"

🔄 SEMANAS 3-6: Expansão conservadora
   +6 agregadores + PF/PRF + estaduais públicas.
   → Valida: "Tem >= 10 lotes relevantes por semana?"

📊 SEMANAS 7-10: Análise inteligente + PDF
   Parsing de PDF (Gemini), scraping do ML pra pricing, 
   categorização LLM, filtros, "bala de prata".
   → Valida: "Já realizei primeira compra?"

🚀 SEMANAS 11-12: Escala
   Tier C (CAIXA/BB), deploy VPS, alertas em tempo real.
   → Valida: "Sistema paga o custo de operação?"

🛑 CHECKPOINTS a cada 2 semanas com critério claro de
   go/no-go. Se não validar → ajustar antes de investir mais.
```

> Diferencial chave vs v1: **sistema evolui conforme o negócio se valida**,
> não de forma cega por 12 semanas. Começa com 2 fontes. Se gerar valor,
> escala pra 25. Se não, ajusta ou desiste sem ter investido tudo.