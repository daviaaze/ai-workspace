# Leilão Radar — Plano de Varredura Completa de Leilões Oficiais do Brasil

> **Missão:** Construir um sistema automatizado que varre **TODOS** os sites oficiais de leilão do Brasil, diariamente, identificando oportunidades de revenda com ROI alto, dentro do budget do investidor.

---

## 📋 1. INVENTÁRIO COMPLETO DE SITES (36+ fontes)

### 🟢 FEDERAIS — Mercadorias Apreendidas

| # | Fonte | URL | Tecnologia | Frequência | Prioridade |
|---|-------|-----|-----------|-----------|------------|
| 1 | **Receita Federal SLE** | https://www25.receita.fazenda.gov.br/sle-sociedade/portal | SPA (JS) | 6h | 🔴 CRÍTICA |
| 2 | **Receita Federal (notícias)** | https://www.gov.br/receitafederal/pt-br/assuntos/noticias | HTML | 24h | 🟡 Média |
| 3 | **PF — Polícia Federal** | https://www.gov.br/pf/pt-br/assuntos/licitacoes | HTML + PDFs | 24h | 🟡 Média |
| 4 | **PRF — Polícia Rodoviária Federal** | https://www.gov.br/prf/pt-br/leiloes | HTML | 12h | 🟡 Média |
| 5 | **MJSP/SENAD — Bens do Crime** | https://www.gov.br/mj/pt-br/assuntos/noticias | HTML | 24h | 🟡 Média |
| 6 | **CGU — Bens Inservíveis** | https://www.gov.br/cgu/pt-br/acesso-a-informacao/licitacoes-e-contratos | HTML | 24h | 🟢 Baixa |
| 7 | **CONAB — Produtos Agrícolas** | https://www.gov.br/pt-br/servicos/participar-dos-leiloes-publicos-para-comprar-produto-da-conab-com-subvencao | HTML | 24h | 🟢 Baixa |
| 8 | **Ibama — Bens Apreendidos** | https://www.gov.br/ibama/pt-br | HTML | 24h | 🟢 Baixa |
| 9 | **Correios (ECT) — Refugo** | https://www.correios.com.br/ + Licitações-e BB | HTML + Portal BB | 24h | 🟡 Média |

### 🟢 FORÇAS ARMADAS — Bens Inservíveis (via leiloeiros credenciados)

| # | Fonte | URL | Tecnologia | Prioridade |
|---|-------|-----|-----------|------------|
| 10 | **Exército — Bens Inservíveis** | https://www.gov.br/eb/pt-br | HTML + leiloeiros | 🟢 Baixa |
| 11 | **Marinha — Bens Inservíveis** | https://www.marinha.mil.br/ | HTML + leiloeiros | 🟢 Baixa |
| 12 | **Aeronáutica — Bens Inservíveis** | https://www.fab.mil.br/ | HTML + leiloeiros | 🟢 Baixa |

### 🟢 BANCOS — Imóveis e Veículos Retomados

| # | Fonte | URL | Tecnologia | Prioridade |
|---|-------|-----|-----------|------------|
| 13 | **CAIXA — Imóveis** | https://venda-imoveis.caixa.gov.br/ | SPA pesada | 🟡 Média |
| 14 | **CAIXA — Veículos** | https://veiculos.caixa.gov.br/ | SPA | 🟡 Média |
| 15 | **Banco do Brasil — Leilões** | https://www.bb.com.br/site/leiloes/ | SPA | 🟡 Média |
| 16 | **BB — Licitações-e** | https://www.licitacoes-e.com.br/ | Portal (login) | 🟡 Média |
| 17 | **BRB — Banco de Brasília** | https://www.brb.com.br/ | HTML | 🟢 Baixa |
| 18 | **Bacen — Instituições Liquidadas** | https://www.bcb.gov.br/ | HTML | 🟢 Baixa |

### 🟢 ESTADUAIS — SEFAZ (mercadorias apreendidas)

| # | Fonte | URL | Estado | Prioridade |
|---|-------|-----|--------|------------|
| 19 | **SEFAZ-SP** | https://portal.fazenda.sp.gov.br/ | SP | 🟡 Média |
| 20 | **SEFAZ-RJ** | https://www.fazenda.rj.gov.br/ | RJ | 🟡 Média |
| 21 | **SEFAZ-MG** | https://www.fazenda.mg.gov.br/ | MG | 🟡 Média |
| 22 | **SEFAZ-PR** | https://www.fazenda.pr.gov.br/ | PR | 🟡 Média |
| 23 | **SEFAZ-MT** | https://www5.sefaz.mt.gov.br/ | MT | 🟡 Média |
| 24 | **SEFAZ-RS** | https://www.sefaz.rs.gov.br/ | RS | 🟡 Média |
| 25 | **SEFAZ-BA** | https://www.sefaz.ba.gov.br/ | BA | 🟢 Baixa |

### 🟢 ESTADUAIS — DETRAN (veículos apreendidos)

| # | Fonte | URL | Estado | Prioridade |
|---|-------|-----|--------|------------|
| 26 | **Detran-SP** | https://www.detran.sp.gov.br/ | SP | 🟡 Média |
| 27 | **Detran-RJ** | https://www.detran.rj.gov.br/ | RJ | 🟡 Média |
| 28 | **Detran-MG** | https://www.detran.mg.gov.br/ | MG | 🟡 Média |
| 29 | **Detran-RS** | https://www.detran.rs.gov.br/ | RS | 🟡 Média |
| 30 | **Detran-GO** | https://www.detran.go.gov.br/ | GO | 🟢 Baixa |

### 🟢 JUDICIAIS — Tribunais

| # | Fonte | URL | Tecnologia | Prioridade |
|---|-------|-----|-----------|------------|
| 31 | **TJ-SP (SIEJ)** | https://siej.tjsp.jus.br/ | Portal próprio | 🟡 Média |
| 32 | **TJ-RJ** | https://www.tjrj.jus.br/leiloes | HTML | 🟡 Média |
| 33 | **TJ-MG** | https://www.tjmg.jus.br/leiloes | HTML | 🟡 Média |
| 34 | **TRF1, TRF2, TRF3** | Variados (justiça federal) | HTML | 🟢 Baixa |

### 🟢 AGREGADORES (centralizam editais)

| # | Fonte | URL | Tecnologia | Prioridade |
|---|-------|-----|-----------|------------|
| 35 | **Leilão.net** | https://www.leilao.net/ | Portal amplo | 🟡 Média |
| 36 | **TriLeilões** | https://www.trileiloes.com.br/ | Portal | 🟡 Média |
| 37 | **Mega Leilões** | https://www.megaleiloes.com.br/ | Portal | 🟡 Média |
| 38 | **Parque dos Leilões** | https://www.parquedosleiloes.com.br/ | Portal | 🟡 Média |
| 39 | **Lance Judicial** | https://www.lancejudicial.com.br/ | Portal | 🟡 Média |
| 40 | **Justiça Leilão** | https://www.justica-leilao.com.br/ | Portal | 🟡 Média |

---

## 🏗 2. ARQUITETURA DO SISTEMA

```
┌─────────────────────────────────────────────────────────────┐
│                    LEILÃO RADAR — ARQUITETURA                 │
└─────────────────────────────────────────────────────────────┘

   ┌────────────────────┐
   │  CRON (scheduler)  │  diariamente 06h, 12h, 18h, 00h
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐       ┌──────────────────────┐
   │  Scraper Manager   │──────▶│  Sources Registry    │
   │  (orquestrador)    │       │  (40 fontes plugin)   │
   └─────────┬──────────┘       └──────────────────────┘
             │
             ▼
   ┌────────────────────┐
   │  Scraping Chain    │  WebFetch → Crawl4AI → Headless → Paginated
   │  (hierarquia tools)│
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐       ┌──────────────────────┐
   │  Parser Registry   │──────▶│  Parsers por fonte     │
   │  (HTML→JSON)       │       │  (um por site)         │
   └─────────┬──────────┘       └──────────────────────┘
             │
             ▼
   ┌────────────────────┐
   │  Storage Layer     │  SQLite/Postgres — tabelas: leiloes, lotes,
   │  (banco de dados)  │  editais, scrape_log, alertas
   └─────────┬──────────┘
             │
             ▼
   ┌────────────────────┐       ┌──────────────────────┐
   │  Analysis Engine   │──────▶│  ROI Calculator      │
   │  (inteligência)    │       │  (preço mercado vs    │
   │                    │       │   preço leilão)       │
   └─────────┬──────────┘       └──────────────────────┘
             │
             ▼
   ┌────────────────────┐       ┌──────────────────────┐
   │  Alert Engine      │──────▶│  Notificações         │
   │  (oportunidades)   │       │  (Telegram/email)     │
   └────────────────────┘       └──────────────────────┘
```

---

## 📅 3. FASES DE IMPLEMENTAÇÃO

### FASE 0 — FOUNDATION (Semana 1)

**Objetivo:** Infraestrutura base funcionando
- [ ]_setup do projeto `leilao-radar/`
- [ ] Banco SQLite com schema unificado
- [ ] Scraper engine assíncrono (já iniciado em `tools/leilao_scraper.py`)
- [ ] ScrapingChain integrado (Crawl4AI → Headless → Paginated)
- [ ] Logger + métricas

**Entrega:** `python -m leilao_radar scrape receita_federal_sle` funciona

### FASE 1 — FONTES PRINCIPAIS (Semana 2-3)

**Objetivo:** Cobrir 80% das oportunidades com 20% dos sites
- [ ] Receita Federal SLE (refinar parser já existente)
- [ ] CAIXA Imóveis (SPA pesada)
- [ ] Banco do Brasil Leilões
- [ ] PF — Polícia Federal
- [ ] PRF — PRF
- [ ] Correios (via Licitações-e BB)

**Entrega:** 6 fontes funcionando, ~50 lotes/dia capturados

### FASE 2 — FONTES ESTADUAIS (Semana 4-5)

**Objetivo:** Cobrir SEFAZ + Detran dos principais estados
- [ ] SEFAZ-SP, RJ, MG, PR, MT, RS
- [ ] Detran-SP, RJ, MG, RS
- [ ] Parsers genéricos para sites estaduais padrão

**Entrega:** 14 fontes adicionais, ~150 lotes/dia

### FASE 3 — JUDICIAIS E AGREGADORES (Semana 6-7)

**Objetivo:** Leilões de Tribunais + agregadores
- [ ] TJ-SP (SIEJ), TJ-RJ, TJ-MG
- [ ] Leilão.net, TriLeilões, Mega Leilões, Parque dos Leilões
- [ ] Lance Judicial, Justiça Leilão

**Entrega:** 40 fontes no total, ~500 lotes/dia

### FASE 4 — ANÁLISE INTELIGENTE (Semana 8-9)

**Objetivo:** Não apenas coletar, mas ANALISAR
- [ ] Integrar API do Mercado Livre (preço de revenda)
- [ ] Calcular ROI automático por lote
- [ ] Categorização por tipo (celular, informática, veículo, etc.)
- [ ] Filtragem por budget (ex: "lotes até R$ 10K com ROI > 50%")
- [ ] Detecção de itens "bala de prata" (preço absurdamente baixo)

**Entrega:** Database com ROI, recomendações automáticas

### FASE 5 — ALERTAS EM TEMPO REAL (Semana 10)

**Objetivo:** Notificar quando surgir oportunidade
- [ ] Bot Telegram (alerta em tempo real)
- [ ] Daily digest (email/WhatsApp)
- [ ] Filtros personalizáveis por categoria, valor, ROI
- [ ] Dashboard web (opcional, Textual TUI)

**Entrega:** "Novo lote iPhone 13 por R$ 961/un — Edital Brasília" no Telegram

### FASE 6 — OTIMIZAÇÃO E ESCALA (Semana 11-12)

**Objetivo:** Operação em produção
- [ ] Docker compose
- [ ] Proxies rotativos (pra não ser bloqueado)
- [ ] Cache inteligente (não baixar páginas sem alteração)
- [ ] Monitoramento (UptimeRobot, Prometheus)
- [ ] CI/CD com GitHub Actions

**Entrega:** Sistema rodando 24/7 sem intervenção

---

## 🗄 4. SCHEMA DO BANCO DE DADOS

```sql
-- Fontes cadastradas
CREATE TABLE sources (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    label TEXT,
    url TEXT,
    source_type TEXT,        -- 'federal', 'estadual', 'banco', 'judicial', 'agregador'
    priority TEXT,           -- 'crítica', 'média', 'baixa'
    check_interval_hours INTEGER,
    last_scraped_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    parser_class TEXT        -- qual parser usar
);

-- Editais (leilões completos)
CREATE TABLE editais (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    edital_number TEXT,      -- ex: "0100100/000003/2026"
    title TEXT,
    location TEXT,           -- ex: "Brasília/MS"
    start_propostas TIMESTAMP,
    end_propostas TIMESTAMP,
    data_pregao TIMESTAMP,
    total_lotes INTEGER,
    permitido_pf BOOLEAN,
    permitido_pj BOOLEAN,
    raw_data TEXT,
    url TEXT,
    UNIQUE(source_id, edital_number)
);

-- Lotes individuais
CREATE TABLE lotes (
    id INTEGER PRIMARY KEY,
    edital_id INTEGER REFERENCES editais(id),
    lote_number TEXT,        -- ex: "Lote 10"
    titulo TEXT,
    descricao TEXT,
    preco_minimo REAL,
    moeda TEXT DEFAULT 'BRL',
    tipo TEXT,               -- ex: 'CELULAR/ACESSÓRIO', 'VEÍCULO'
    categoria_normalizada TEXT,  -- ex: 'eletrônico', 'veículo', 'imóvel'
    situacao TEXT,
    permitido_para TEXT,    -- 'PF', 'PJ', 'PF/PJ'
    local_retirada TEXT,
    icms_aliquota REAL,
    total_itens INTEGER,
    raw_data TEXT,           -- JSON completo
    url TEXT,
    scraped_at TIMESTAMP,
    UNIQUE(edital_id, lote_number)
);

-- Itens individuais dentro de um lote
CREATE TABLE lote_itens (
    id INTEGER PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes(id),
    quantity INTEGER,
    unit TEXT,
    description TEXT,
    brand TEXT,
    model TEXT
);

-- Histórico de scraping (auditoria)
CREATE TABLE scrape_log (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT,            -- 'success', 'error', 'partial'
    lots_found INTEGER,
    lots_new INTEGER,
    error TEXT,
    duration_ms INTEGER
);

-- Análise de ROI
CREATE TABLE lote_analysis (
    lote_id INTEGER PRIMARY KEY REFERENCES lotes(id),
    estimated_market_value REAL,
    estimated_roi REAL,             -- %
    estimated_roi_after_fees REAL,  -- após ML/Shopee fees
    confidence_score REAL,          -- 0-1
    market_data_source TEXT,        -- 'ML API', 'manual', 'estimate'
    analysis_at TIMESTAMP,
    notes TEXT
);

-- Alertas gerados
CREATE TABLE alertas (
    id INTEGER PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes(id),
    alert_type TEXT,        -- 'high_roi', 'low_price', 'rare_item'
    message TEXT,
    sent_at TIMESTAMP,
    channel TEXT,           -- 'telegram', 'email'
    delivered BOOLEAN
);

-- Filtros do usuário
CREATE TABLE user_filters (
    id INTEGER PRIMARY KEY,
    name TEXT,
    max_price REAL,
    min_roi REAL,
    categories TEXT,        -- JSON array
    locations TEXT,          -- JSON array
    is_active BOOLEAN
);
```

---

## 🧩 5. PADRÃO DE PARSER (PLUGIN)

Cada fonte é um plugin Python com interface uniforme:

```python
from leilao_radar.sources.base import BaseSource, Lot

class SefazSPSource(BaseSource):
    name = "sefaz_sp"
    label = "SEFAZ-SP — Mercadorias Apreendidas"
    url = "https://portal.fazenda.sp.gov.br/"
    source_type = "estadual"
    priority = "média"
    check_interval_hours = 24

    def get_urls(self) -> list[str]:
        """Lista de URLs para scrape."""
        return [self.url + "leiloes"]

    async def parse_editais(self, html: str) -> list[Edital]:
        """Parser específico do HTML da SEFAZ-SP."""
        # Retorna lista de editais
        ...

    async def parse_lotes(self, edital: Edital) -> list[Lot]:
        """Parser específico dos lotes de um edital."""
        # Pode paginar se necessário
        ...

    def get_lance_maximo(self, lote: Lot) -> float | None:
        """Dica: preço máximo recomendado (ROI >= 30%)."""
        # Usa categoria + preço de mercado
        ...
```

---

## 🔔 6. CRITÉRIOS DE ALERTA (OPORTUNIDADES)

```
ALERTA CRÍTICO (notificação imediata):
  → ROI estimado >= 100% E preço <= R$ 10K
  → Item de alta demanda (iPhone, Xiaomi, MacBook)
  → Edital fecha em < 48h

ALERTA MÉDIO (digest diário):
  → ROI estimado >= 50% E preço <= R$ 5K
  → Lote pequeno (< 50 itens) fácil de revender

ALERTA INFORMATIVO:
  → Novo edital aberto em qualquer fonte
  → Lote com preço abaixo da média histórica
```

---

## 🛠 7. STACK TÉCNICO RECOMENDADO

| Camada | Tecnologia | Justificativa |
|--------|-----------|---------------|
| **Linguagem** | Python 3.11+ | Stack existente, async, bibliotecas |
| **Scraping SPA** | Playwright | Mais robusto que Selenium pra SPAs |
| **Scraping estático** | httpx + selectolax | 10x mais rápido que BeautifulSoup |
| **Banco de dados** | SQLite (dev) → PostgreSQL (prod) | Começa simples, escala depois |
| **Queue/Scheduler** | APScheduler → Celery (escala) | Início simples, evolução clara |
| **Alertas** | python-telegram-bot | Bot Telegram é gratuito e prático |
| **Dashboard** | Textual (TUI) → FastAPI+React | TUI primeiro, web depois |
| **Deploy** | Docker + docker-compose | Container único no início |
| **Monitoramento** | Loguru + Sentry | Logs estruturados + erros em produção |

---

## 📊 8. MÉTRICAS DE SUCESSO

| Métrica | Meta Fase 1 | Meta Fase 6 |
|---------|-------------|-------------|
| Fontes ativas | 6 | 40 |
| Lotes capturados/dia | 50 | 500+ |
| Latência (descoberta → alerta) | < 12h | < 1h |
| Falsos positivos (alertas ruins) | < 30% | < 10% |
| ROI médio dos alertas | não medido | >= 60% |
| Uptime do scraper | 80% | 99% |
| Custo mensal (infra) | R$ 0 (local) | R$ 50 (VPS) |

---

## 🚦 9. PRIORIDADES DE EXECUÇÃO (PRÓXIMAS 4 SEMANAS)

### Semana 1 — Mínimo Viável (MVP)
1. Estruturar projeto `leilao-radar/`
2. Refazer `leilao_scraper.py` como módulo do projeto
3. Implementar **Receita Federal SLE** (fonte principal)
4. **CAIXA Imóveis** (fonte secundária)
5. Banco SQLite + script de plotagem básica
6. Rodar 1x ao dia via cron

### Semana 2 — Cobertura Crítica
7. **Banco do Brasil** Leilões
8. **PF** Polícia Federal
9. **PRF** PRF
10. **Correios** (via Licitações-e)
11. Scheduler automático (APScheduler)

### Semana 3 — Análise Inteligente
12. Integrar **API Mercado Livre** (preços de revenda)
13. Cálculo automático de ROI
14. Categorização com LLM (claude/gemini) pra padronizar tipos
15. Primeiros filtros de budget

### Semana 4 — Alertas e UX
16. Bot Telegram com comandos `/oportunidades`, `/filtra`
17. Daily digest matinal
18. Dashboard TUI simples (Textual)
19. Documentação + README
20. Deploy em VPS (Hetzner R$ 30/mês)

---

## ⚙ 10. CONSIDERAÇÕES LEGAIS E TÉCNICAS

### Legal
- ✅ Respeitar `robots.txt` de cada site
- ✅ Rate limiting (máx 1 req/s por domínio)
- ✅ User-agent identificável
- ✅ Não armazenar dados pessoais
- ✅ Não tuitar resultados sem contexto

### Técnico
- ✅ Cache HTTP (não rebaixar páginas sem alteração)
- ✅ Detecção de mudanças (hash de HTML)
- ✅ Retry com backoff exponencial
- ✅ Circuit breaker (se um site cai, não derruba o sistema)
- ✅ Backup diário do banco

### Governança
- ✅ Logs de auditoria (quem/varreu/quando)
- ✅ Versionamento de parsers (sites mudam layout)
- ✅ Testes automatizados por parser (mock HTML)
- ✅ Alertas de parser quebrado (sem dados há X horas)

---

## 🎯 11. CRITÉRIO DE "OPORTUNIDADE BALA DE PRATA"

O sistema deve marcar um lote como **🥇 Bala de Prata** quando:

```python
def is_silver_bullet(lote: Lot) -> bool:
    return (
        lote.preco_minimo <= 5_000 and
        lote.estimated_roi >= 1.5 and            # 150%
        lote.categoria_normalizada in ['eletronico', 'veiculo', 'informatica']
        and lote.permitido_para != 'PJ'           # PF pode comprar
        and lote.end_propostas within 7 days
    )
```

Itens que já vimos que se encaixam:
- ✅ Edital Curitiba Lote 20 (R$ 2.500, 4 motos elétricas — ROI 220-460%)
- ✅ Edital Curitiba Lote 11 (R$ 3.000, HB20 2021 + Cobalt — ROI 733%+)
- ✅ Edital Brasília 004 Lote 14 (R$ 59, informática — ROI aparentemente altíssimo)

---

## 📦 12. ESTRUTURA DE ARQUIVOS DO PROJETO

```
leilao-radar/
├── README.md
├── pyproject.toml
├── docker-compose.yml
├── .env.example
│
├── src/leilao_radar/
│   ├── __init__.py
│   ├── cli.py                          # CLI: python -m leilao_radar scrape --all
│   ├── config.py                       # Config via env vars
│   │
│   ├── sources/                        # Um arquivo por fonte
│   │   ├── __init__.py
│   │   ├── base.py                     # BaseSource, Lot, Edital dataclasses
│   │   ├── receita_federal_sle.py      # ⭐ Principal
│   │   ├── caixa_imoveis.py
│   │   ├── bb_leiloes.py
│   │   ├── pf_leiloes.py
│   │   ├── prf_leiloes.py
│   │   ├── correios_licitacoes_e.py
│   │   ├── sefaz_sp.py
│   │   ├── sefaz_rj.py
│   │   ├── detran_sp.py
│   │   ├── tj_sp_siej.py
│   │   ├── leilao_net.py
│   │   └── ...                         # Demais fontes
│   │
│   ├── scrapers/                       # Engines de scraping
│   │   ├── __init__.py
│   │   ├── scraping_chain.py           # WebFetch → Crawl4AI → Playwright
│   │   ├── paginated_scraper.py
│   │   └── rate_limiter.py
│   │
│   ├── parsers/                       # Helpers de parsing
│   │   ├── __init__.py
│   │   ├── html_utils.py
│   │   └── normalizers.py              # Padroniza categorias
│   │
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── database.py                 # SQLite/Postgres
│   │   ├── models.py                   # SQLAlchemy models
│   │   └── migrations/
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── roi_calculator.py           # Calcula ROI por lote
│   │   ├── market_pricer.py           # Busca preço de revenda no ML
│   │   ├── categorizer.py              # LLM para categorizar
│   │   └── silver_bullet.py           # Detector de oportunidades
│   │
│   ├── alerts/
│   │   ├── __init__.py
│   │   ├── telegram_bot.py
│   │   ├── email_digest.py
│   │   └── filters.py                  # user filters
│   │
│   └── scheduler/
│       ├── __init__.py
│       ├── cron.py                     # Agendador principal
│       └── managers.py                 # Gestão de fontes
│
├── tests/
│   ├── fixtures/                       # HTML salvo por fonte
│   │   ├── receita_federal_edital.html
│   │   └── ...
│   ├── test_sources/
│   └── test_parsers/
│
└── data/
    ├── leiloes.db                      # SQLite
    └── cache/                          # HTTP cache
```

---

## 🚀 13. PRÓXIMO PASSO IMEDIATO

**Decisão:** Qual caminho seguir?

1. **🟢 IMPLEMENTAR AGORA** — Começar a construir o `leilao-radar` nesta sessão, começando pela Fase 0 + Fase 1 (Receita Federal + CAIXA)

2. **🟡 REFINAR PLANO** — Ajustar prioridades, adicionar fontes específicas, refinar schema

3. **🔵 PROTOTIPAR UMA FONTE** — Escolher 1 fonte (ex: Receita Federal SLE) e fazer produção-ready, depois replicar padrão

4. **🟣 MOCK PRIMEIRO** — Criar só os testes + fixtures HTML, sem scraper, pra validar arquitetura

> **Recomendação:** Opção 1 ou 3 — começar a construir. A Receita Federal SLE já tem estrutura parcial em `tools/leilao_scraper.py` — podemos refatorar num projeto próprio `leilao-radar/` e expandir.

Que caminho escolhe?