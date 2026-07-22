# 🏆 Leilão Radar v3 — Plano de Negócio + Sistema de Varredura

> **Missão:** Operação solo de compra e revenda de lotes de leilão público, com suporte de sistema automatizado de varredura, análise de ROI, e alertas.
>
> **Investidor:** Pessoa CLT (40h/semana), MEI, R$ 40K reserva intocável, crédito PRONAMPE de R$ 5-8K
> **Disponibilidade:** 10-11h/semana (noites + fds)
> **Meta:** Validar tese em 60 dias com paper trading, primeira compra real em 90 dias.

---

## SUMÁRIO

- [PARTE I — A TESE DE NEGÓCIO](#parte-i--a-tese-de-negócio)
- [PARTE II — O MODELO FINANCEIRO](#parte-ii--o-modelo-financeiro)
- [PARTE III — DECISION ENGINE](#parte-iii--decision-engine)
- [PARTE IV — AS FONTES (priorizadas por valor de negócio)](#parte-iv--as-fontes-priorizadas-por-valor-de-negócio)
- [PARTE V — LEAN MVP — O SISTEMA MÍNIMO](#parte-v--lean-mvp--o-sistema-mínimo)
- [PARTE VI — ARQUITETURA E DATA](#parte-vi--arquitetura-e-data)
- [PARTE VII — ALERTAS E NOTIFICAÇÕES](#parte-vii--alertas-e-notificações)
- [PARTE VIII — OPERAÇÃO DO INVESTIDOR](#parte-viii--operação-do-investidor)
- [PARTE IX — RISCOS](#parte-ix--riscos)
- [PARTE X — ROADMAP 12 SEMANAS](#parte-x--roadmap-12-semanas)

---

# PARTE I — A TESE DE NEGÓCIO

## 1.1 O Problema

O governo brasileiro leiloa milhares de lotes de mercadorias apreendidas todos os meses. Os preços de abertura são **30-80% abaixo do valor de mercado**. Mas:

- Os lotes estão espalhados por **40+ sites diferentes** (Receita, CAIXA, BB, PF, PRF, SEFAZ, TJs, etc.)
- Cada site tem formato, regras e prazos diferentes
- A maioria dos lotes tem descrição genérica ("CELULAR/ACESSÓRIO")
- É impossível uma pessoa monitorar tudo manualmente em tempo parcial

**Oportunidade:** Um sistema que varre todas as fontes, calcula ROI automaticamente e alerta o investidor só quando aparece algo que vale a pena.

## 1.2 A Tese

```
COMPRAR:   Lotes em leilão público com preço ≤ 30% do valor de mercado
VENDER:    No Mercado Livre (13% taxa), Shopee (14%+), ou OLX (0%)
MARGEM:    ROI líquido ≥ 25% em ≤ 60 dias
CAPITAL:   R$ 5-8K de crédito PRONAMPE (reserva de R$ 40K INTOCÁVEL)
DIFERENCIAL: Sistema de varredura + ROI automático + alertas em tempo real
```

## 1.3 Restrições Absolutas (não negociáveis)

```
🔴 REGRA #1: RESERVA DE R$ 40K NÃO EXISTE PRA ISSO
   Ela é emergência. Ponto final. Se o crédito não vier, a operação não começa.

🔴 REGRA #2: SÓ COMPRE COM CRÉDITO SE TAXA ≤ 2%/MÊS
   PRONAMPE (1,6%) sim. Cartão de crédito (12-18%) não.

🔴 REGRA #3: CADA LOTE PRECISA CABER NO TEMPO DISPONÍVEL
   10h/semana. Se um lote exige 20h pra testar/embalar/postar, não serve.

🔴 REGRA #4: NENHUM LOTE PODE TRAVAR O CAPITAL > 60 DIAS
   Se não vender em 60 dias, vende no prejuízo pra girar.
```

## 1.4 Métricas de Sucesso do Negócio

| Indicador | Meta | Quando medir |
|-----------|------|-------------|
| **Primeiro lote comprado via alerta do sistema** | ✅ SIM | Até 3 meses |
| **Primeiro lote vendido (ciclo completo)** | ✅ SIM | Até +30 dias |
| **ROI realizado ≥ 25% líquido** | ✅ SIM | Na primeira venda |
| **Sistema se paga** (lucro ≥ custo operacional) | ✅ SIM | Até 6 meses |
| **ROI previsto vs ROI realizado** | erro < 20% | Após cada venda |
| **Reserva de R$ 40K intacta** | ✅ SIM | Sempre |

---

# PARTE II — O MODELO FINANCEIRO

## 2.1 Capital e Crédito

| Item | Valor |
|------|-------|
| **Reserva de emergência** | R$ 40.000 (🔴 INTOCÁVEL) |
| **Crédito PRONAMPE** | R$ 5.000 - R$ 8.000 |
| **Taxa PRONAMPE** | ~1,6% ao mês (Selic+6% a.a.) |
| **Parcela mensal** | ~R$ 165 (R$ 5K em 48x) |
| **Caixa operacional inicial** | R$ 5.000 - R$ 8.000 |
| **Margem de segurança** | ~R$ 700 de caixa restante pós-compra |

## 2.2 Estrutura de Custos por Lote

```
CUSTO TOTAL = Lance + Ágio + ICMS + Frete + Taxas

Onde:
  Lance          → Preço mínimo do edital
  Ágio           → 10-50% sobre o lance mínimo (histórico SLE: 20-40%)
  ICMS           → 12-18% (depende do estado de retirada × estado de venda)
  Frete          → R$ 200-800 (depende da distância e peso)
  Taxas          → R$ 50-150 (DARF, transferência, etc.)

RECEITA LÍQUIDA = Preço de venda - Taxa da plataforma - Frete ao comprador

Onde:
  ML Clássico    → 11-13% para eletrônicos/informática
  Shopee         → 14% + R$ 28 fixo (acima de R$ 200)
  OLX            → 0%
  Frete          → R$ 10-40/un (via Correios PAC)

ROI = (Receita Líquida - Custo Total) / Custo Total
```

## 2.3 Projeção Financeira — 12 Meses

### Cenário Conservador (brinquedos, diversos — margem menor, risco menor)

```
Mês 0:   Toma R$ 5K PRONAMPE                      Caixa: R$ 5.000
Mês 1:   Compra lote 2 (brinquedos - R$ 3.507)     Caixa: R$ 1.193
Mês 2:   Vende brinquedos R$ 5.500 (ML 13%)        Caixa: R$ 5.978
Mês 3:   Compra lote 9 (R$ 2.952 + custos)         Caixa: R$ 2.726
Mês 4:   Vende lote 9 R$ 5.000                     Caixa: R$ 7.276
Mês 5:   Compra lote 6 (R$ 6.918)                  Caixa: R$ 358
Mês 6:   Vende lote 6 R$ 9.500                     Caixa: R$ 8.858
Mês 7:   Compra lote maior (R$ 8.000)              Caixa: R$ 858
Mês 8:   Vende lote R$ 11.000                      Caixa: R$ 10.858
Mês 9:   Compra lote R$ 8.000                      Caixa: R$ 2.858
Mês 10:  Vende lote R$ 11.000                      Caixa: R$ 12.858
Mês 11:  Compra lote R$ 8.000                      Caixa: R$ 4.858
Mês 12:  Vende lote R$ 11.000 + QUITA PRONAMPE     Caixa: ~R$ 15.000

📊 RESULTADO:
  Capital girado:     R$ 5.000 → R$ 15.000
  Crédito usado:      R$ 5.000
  Juros pagos:        ~R$ 600
  Lucro líquido:      ~R$ 10.000
  Dívida:             0
  Reserva R$ 40K:     ✅ INTACTA
```

### Cenário Otimista (veículos — margem maior, risco maior)

```
Mês 0:   Toma R$ 8K PRONAMPE                      Caixa: R$ 8.000
Mês 1:   Compra lote 11 (carro - R$ 3.000)         Caixa: R$ 5.000
Mês 2:   Vende carro R$ 12.000 - 13%               Caixa: R$ 15.440
Mês 3:   Compra lote 20 (4 motos R$ 2.500)         Caixa: R$ 12.940
Mês 4:   Vende motos R$ 12.000 - 13%               Caixa: R$ 23.380
Mês 5-6: Escala com capital próprio (R$ 8-10K/lote)
Mês 7-11: Ciclos mensais de compra→venda
Mês 12:  QUITA PRONAMPE + lucro                    Caixa: ~R$ 35.000

📊 RESULTADO:
  Capital girado:     R$ 8.000 → R$ 35.000
  Crédito usado:      R$ 8.000
  Juros pagos:        ~R$ 800
  Lucro líquido:      ~R$ 27.000
  Dívida:             0
  Reserva R$ 40K:     ✅ INTACTA
```

### Pior Cenário (realista — R$ 3-5K de perda)

```
Situação: crédito tomado, lote comprado, mas:
  - Produto veio com defeitos não esperados
  - Mercado desabou OU demorou > 60 dias pra vender
  - Teve que vender no prejuízo pra girar

Perda máxima realista: R$ 3.000 - R$ 5.000
  → Parcela de R$ 165/mês × 24 meses = R$ 3.960 total
  → Coberto pelo salário CLT (não afeta reserva)
  → Risco conhecido e aceitável
```

## 2.4 Break-Even do Sistema

```
CUSTO DO SISTEMA (tempo do investidor):
  Construção MVP:    ~15h (semana 1)
  Manutenção/mês:    ~2h (depois de pronto)
  VPS (se deploy):   R$ 30/mês

BENEFÍCIO MÍNIMO:
  1 lote extra de R$ 3K com ROI 30% = R$ 900 de lucro
  → 1 lote a mais por trimestre paga o sistema
  → Se o sistema gerar 1 alerta bom/mês, já viabiliza
```

---

# PARTE III — DECISION ENGINE

O coração do sistema não é o scraper. É a **regra de decisão**: dado um lote, compro ou não?

## 3.1 ROI com 3 Níveis de Confiança (A1)

Nem todo lote tem descrição detalhada. O sistema classifica cada análise em:

### 🟢 ROI Confiável (confiança alta = 0.7-1.0)
- Lote com descrição detalhada (modelos, quantidades, marcas)
- Produtos presentes na tabela manual de preços OU scraping do ML
- **Ação:** Alerta automático, recomendação de compra

### 🟡 ROI Estimado (confiança média = 0.3-0.7)
- Lote com tipo + quantidade, mas produtos genéricos (ex: "25 unidades de smartphone")
- Produtos com preço estimado (categoria similar ou marca genérica)
- **Ação:** Alerta informativo, precisa olhada manual

### 🔴 ROI Desconhecido (confiança baixa = 0-0.3)
- Descrição vaga ("DIVERSOS"), sem detalhamento
- Categoria sem preço de referência
- **Ação:** Não alerta. Só menciona no digest semanal como "lotes pra investigação manual"

```python
# Lógica de confiança do ROI
def confidence_level(lote: Lot) -> tuple[float, str]:
    """Retorna (confiança 0-1, label)"""
    if lote.tem_descricao_detalhada and lote.produtos_na_tabela:
        return (0.85, 'confiavel')
    elif lote.tem_quantidade_e_tipo:
        return (0.50, 'estimado')
    else:
        return (0.15, 'desconhecido')
```

## 3.2 ROI por Mês (Liquidez Ajustada) (A2)

ROI total não basta. Um lote que rende 80% em 6 meses é pior que um que rende 30% em 30 dias.

```
ROI líquido / mês = ROI_total / meses_estimados_para_vender

Exemplo iPhone 13:
  ROI total: 49%
  Tempo de venda: 15 dias (0.5 mês)
  ROI/mês: 49% / 0.5 = 98%/mês ← EXCELENTE

Exemplo brinquedos diversos:
  ROI total: 35%
  Tempo de venda: 45 dias (1.5 mês)
  ROI/mês: 35% / 1.5 = 23%/mês ← BOM
  
Exemplo lote opaco:
  ROI total: 80% (estimado)
  Tempo de venda: 120 dias (4 meses)
  ROI/mês: 80% / 4 = 20%/mês ← Questionável
```

### Tabela de liquidez estimada por categoria

| Categoria | Tempo médio de venda (ML) | Fonte |
|-----------|--------------------------|-------|
| iPhone/Samsung top | 7-15 dias | Histórico |
| Xiaomi intermediário | 15-30 dias | Histórico |
| Perfume importado | 15-30 dias | Estimado |
| Brinquedo (lote) | 15-45 dias | Estimado |
| Informática (SSD, RAM) | 30-60 dias | Estimado |
| Veículo popular | 7-30 dias | Estimado |
| Moto popular | 15-45 dias | Estimado |
| Eletrodoméstico | 15-45 dias | Estimado |
| Vestuário/Roupas | 30-90 dias | Estimado |

## 3.3 Regra de Ouro — Lance Máximo

```python
def lance_maximo(preco_mercado: float, categoria: str, risco: float = 0.10) -> float:
    """
    Calcula o valor máximo que você deve dar de lance.
    
    Fórmula:
      Lance máx = Preço mercado × (1 - taxa_plataforma) - frete - margem_risco
      
      Onde taxa_plataforma = 13% (ML Clássico)
            frete = R$ 15-40/un (Correios PAC)
            margem_risco = 10-15% (produto com defeito, devolução, etc.)
    """
    taxa = 0.13                     # ML Clássico
    frete_medio = 30.0              # R$ por unidade
    margem_risco = risco            # 10%
    
    return preco_mercado * (1 - taxa) - frete_medio - (preco_mercado * margem_risco)

# Exemplo iPhone 13 (R$ 2.500 de mercado):
# Lance máx = 2500 * 0.87 - 30 - 250 = R$ 1.895
# Se lance mínimo é R$ 960 → ágio máximo suportado: 97% 👍
```

## 3.4 Critério de "Bala de Prata" v3

```python
def is_silver_bullet(lote: Lot, analysis: LoteAnalysis) -> bool:
    """Bala de prata = alerta imediato no Telegram"""
    return (
        analysis.confidence >= 0.5                          # ROI pelo menos estimado
        and analysis.roi_mensal >= 0.5                       # ROI/mês >= 50%
        and lote.preco_minimo <= 5_000                       # cabe no budget
        and lote.permitido_para in ['PF', 'PF/PJ']           # pode comprar
        and lote.dias_ate_o_pregao <= 7                      # urgente
    )
```

## 3.5 Depreciação Projetada (A3)

Preços de mercado não são estáticos. O sistema ajusta:

```python
# Taxa de depreciação mensal por categoria
DEPRECIACAO_MENSAL = {
    'iphone':      0.03,    # 3%/mês
    'xiaomi':      0.04,    # 4%/mês
    'samsung':     0.035,   # 3.5%/mês
    'informatica': 0.025,   # 2.5%/mês (SSD, RAM são estáveis)
    'veiculo':     0.015,   # 1.5%/mês
    'perfume':     0.01,    # 1%/mês
    'brinquedo':   0.02,    # 2%/mês
}

def preco_mercado_ajustado(produto: str, preco_atual: float, meses: int) -> float:
    """Estima o preço de revenda no momento da venda."""
    taxa = DEPRECIACAO_MENSAL.get(produto, 0.03)
    return preco_atual * (1 - taxa) ** meses
```

---

# PARTE IV — AS FONTES (priorizadas por valor de negócio)

## 4.1 Classificação por ROI Potencial

Nem toda fonte tem o mesmo potencial de lucro. Ordenadas por **retorno estimado por hora de implementação**:

| Rank | Fonte | Tipo | ROI potencial | Facilidade scraping | Prioridade |
|------|-------|------|--------------|---------------------|------------|
| 🥇 | **Receita Federal SLE** | Mercadorias | Alto (eletrônicos 30-80% abaixo mercado) | ✅ Já temos estrutura | **MVP** |
| 🥇 | **Leilão.net** (agregador) | Todas | Médio (já filtra, mas não calcula ROI) | ✅ Simples (HTML) | **MVP** |
| 🥈 | **Agregadores** (Tri, Mega, Parque, Lance, Justiça) | Todas | Médio | ✅ Simples | **Fase 1** |
| 🥈 | **PF** | Bens apreendidos | Alto (celulares, carros) | ✅ HTML | **Fase 1** |
| 🥈 | **PRF** | Veículos | Alto (carros populares) | ✅ HTML | **Fase 1** |
| 🥉 | **SEFAZ-MT/SP/PR** | Mercadorias | Médio (eletrônicos) | ⚠️ SPA ou HTML | **Fase 2** |
| 🥉 | **Detran-SP/RJ** | Veículos | Médio (carros apreendidos) | ⚠️ SPA | **Fase 2** |
| 4️⃣ | **Correios** | Refugo | Baixo (misturado) | ⚠️ Login | **Fase 2** |
| 5️⃣ | **CAIXA Imóveis** | Imóveis | Alto mas ticket alto | ❌ SPA + login | **Fase 3+** |
| 5️⃣ | **BB Leilões** | Imóveis/Veículos | Alto mas ticket alto | ❌ SPA + login | **Fase 3+** |
| 6️⃣ | **TJs (SP, RJ, MG)** | Judiciais | Variável | ⚠️ Login ou certificado | **Fase 3+** |
| 7️⃣ | **Forças Armadas, Ibama, CGU, etc.** | Diversos | Baixo (poucos lotes) | ⚠️ PDFs | **Se sobrar tempo** |

**Critério de corte:** Se uma fonte não entregou ≥ 2 alertas relevantes em 30 dias rodando, desativar e reavaliar.

## 4.2 Tiers de Acesso

```
TIER A — Público (20 fontes) → MVP + Fase 1-2
TIER B — Conta simples (8 fontes) → Fase 3
TIER C — Certificado digital (5 fontes) → Fase 5+
```

(vide tabela completa em PLANO_V2.md seção 2)

---

# PARTE V — LEAN MVP — O SISTEMA MÍNIMO

## 5.1 O que o MVP entrega na Semana 1

| Funcionalidade | Entrega | Como |
|---------------|---------|------|
| **2 fontes** | Receita SLE + Leilão.net | Scraping via httpx + selectolax |
| **SQLite** | Lotes salvos localmente | Schema com todas as tabelas futuras |
| **ROI básico** | Cálculo com tabela manual (~20 produtos) | Preço mercado - custo estimado |
| **Alerta diário** | Telegram bot às 8h | ```python-telegram-bot``` |
| **3 níveis de confiança** | 🔴🟡🟢 no alerta | Confidence >= 0.5 dispara alerta |
| **Dedup automático** | Mesmo lote = 1 alerta | Hash por (fonte + edital + lote) |

## 5.2 O que o MVP NÃO faz (de propósito)

| Não faz | Motivo | Quando fazer |
|---------|--------|-------------|
| Scraping de PDF | Muito complexo pra semana 1 | Fase 3 (LLM) |
| Pricing via ML | Tabela manual é suficiente no início | Fase 4 |
| Portfolio tracking | Só faz sentido pós-compra | Fase 5 |
| Login em sites | Precisa de certificado/regulamentação | Fase 5+ |
| VPS/24h | Roda no seu PC por enquanto | Fase 6 |

## 5.3 Tecnologia do MVP

```python
# MVP usa o que já temos + mínimo de dependências novas
Stack MVP:
  - Python 3.11+
  - httpx           → chamadas HTTP (já temos)
  - selectolax      → parser HTML (10x mais rápido que BS4)
  - sqlite3          → banco local (built-in)
  - python-telegram-bot → alerts
  - APScheduler     → agendamento simples (ou cron)

Não inclui (ainda):
  - Crawl4AI (muito pesado pra MVP)
  - Playwright (só se site exigir JS)
  - PostgreSQL (SQLite é suficiente pra 500 lotes/dia)
```

## 5.4 Comportamento do MVP ante PDFs (C7)

O MVP **não parseia** PDFs, mas deve:

1. Detectar links para PDF nas páginas
2. Baixar o PDF para `data/pdf_cache/`
3. Marcar `edital.pdf_parsed = False`
4. No alerta diário: "📄 Edital em PDF — baixado, precisa análise manual"

Isso garante que nenhum PDF seja perdido, mesmo que não seja parseado automaticamente.

---

# PARTE VI — ARQUITETURA E DATA

## 6.1 Schema Completo v3 (com todos os refinamentos)

```sql
-- ═══════════════════════════════════════════
-- LEILÃO RADAR v3 — SCHEMA COMPLETO
-- ═══════════════════════════════════════════

-- Fontes
CREATE TABLE sources (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    label TEXT,
    url TEXT,
    tier TEXT CHECK(tier IN ('A','B','C')),
    source_type TEXT,
    priority TEXT,
    check_interval_hours INTEGER,
    last_scraped_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    parser_class TEXT,
    business_priority INTEGER        -- NOVO: ordem de valor de negócio
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
    pdf_url TEXT,
    pdf_downloaded BOOLEAN DEFAULT 0,    -- NOVO
    pdf_parsed BOOLEAN DEFAULT 0,        -- NOVO
    raw_data TEXT,
    url TEXT,
    status TEXT DEFAULT 'ativo',
    UNIQUE(source_id, edital_number)
);

-- Lotes com imagens
CREATE TABLE lotes (
    id INTEGER PRIMARY KEY,
    edital_id INTEGER REFERENCES editais(id),
    lote_number TEXT,
    titulo TEXT,
    descricao TEXT,
    preco_minimo REAL,
    moeda TEXT DEFAULT 'BRL',
    tipo TEXT,
    categoria_normalizada TEXT,
    situacao TEXT,
    permitido_para TEXT,
    local_retirada TEXT,
    distancia_km REAL,                    -- NOVO: distância do CEP do investidor
    icms_aliquota REAL,
    total_itens INTEGER,
    confidence_level TEXT DEFAULT 'desconhecido', -- NOVO: 'confiavel', 'estimado', 'desconhecido'
    confidence_score REAL DEFAULT 0,              -- NOVO
    raw_data TEXT,
    url TEXT,
    scraped_at TIMESTAMP,
    status TEXT DEFAULT 'ativo',
    UNIQUE(edital_id, lote_number)
);

-- Imagens dos lotes (C7)
CREATE TABLE lote_imagens (
    id INTEGER PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes(id),
    url TEXT,
    local_path TEXT,                       -- caminho no cache local
    downloaded BOOLEAN DEFAULT 0,
    downloaded_at TIMESTAMP
);

-- Itens individuais
CREATE TABLE lote_itens (
    id INTEGER PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes(id),
    quantity INTEGER,
    unit TEXT,
    description TEXT,
    brand TEXT,
    model TEXT
);

-- Preços de mercado (com histórico)
CREATE TABLE market_prices (
    id INTEGER PRIMARY KEY,
    product_key TEXT,                      -- ex: 'iphone_13_128gb'
    normalized_name TEXT,
    category TEXT,
    median_price REAL,
    min_price REAL,
    max_price REAL,
    source TEXT,                           -- 'manual', 'ml_scrape', 'ml_api'
    confidence REAL,
    recorded_at TIMESTAMP DEFAULT NOW(),   -- NOVO: versão do preço
    UNIQUE(product_key, source, recorded_at)
);

-- Análise de ROI completa
CREATE TABLE lote_analysis (
    lote_id INTEGER PRIMARY KEY REFERENCES lotes(id),
    estimated_market_value REAL,
    estimated_roi REAL,                    -- ROI total
    estimated_roi_mensal REAL,             -- NOVO: ROI ajustado por liquidez
    estimated_roi_after_fees REAL,         -- ROI líquido
    confidence TEXT,                       -- 'confiavel', 'estimado', 'desconhecido'
    confidence_score REAL,
    pricing_layer TEXT,
    meses_para_vender REAL,                -- NOVO: estimativa de liquidez
    ml_fee_estimate REAL,
    shopee_fee_estimate REAL,
    frete_estimate REAL,
    deprec_at_venda REAL,                  -- NOVO: depreciação projetada
    analyzed_at TIMESTAMP,
    notes TEXT
);

-- Portfolio (B4) — ciclo completo de compra→venda
CREATE TABLE portfolio (
    id INTEGER PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes(id),
    data_arremate TIMESTAMP,
    valor_pago REAL,                       -- lance + ágio + taxas
    custo_total REAL,                      -- valor_pago + frete + ICMS + outros
    data_quitacao TIMESTAMP,
    data_retirada TIMESTAMP,
    
    -- Vendas (pode ter múltiplas vendas para um lote)
    data_venda TIMESTAMP,
    platform TEXT,                         -- 'ML', 'Shopee', 'OLX', 'atacado'
    receita_bruta REAL,
    taxa_plataforma REAL,
    frete_pago REAL,
    receita_liquida REAL,
    
    -- Métricas realizadas
    roi_realizado REAL,                    -- (receita_líquida - custo_total) / custo_total
    roi_realizado_mensal REAL,             -- ROI / meses_ate_venda
    dias_ate_venda INTEGER,
    
    -- Calibração do sistema
    roi_previsto REAL,                     -- o que o sistema estimou
    erro_roi REAL,                         -- (realizado - previsto) / previsto
    
    status TEXT DEFAULT 'comprado',        -- 'comprado', 'vendendo', 'vendido'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Alertas (com dedup — D9)
CREATE TABLE alertas (
    id INTEGER PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes(id),
    source_id INTEGER REFERENCES sources(id),     -- NOVO: pra dedup
    alert_type TEXT,
    message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    sent_at TIMESTAMP,
    channel TEXT,
    delivered BOOLEAN DEFAULT 0,
    read BOOLEAN DEFAULT 0,
    user_action TEXT,                              -- NOVO: 'viu', 'clicou', 'comprou'
    UNIQUE(lote_id, alert_type, DATE(created_at)) -- NOVO: 1 alerta/lote/dia
);

-- Tracking de ágio por categoria (C8)
CREATE TABLE agio_history (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    category TEXT,
    lote_number TEXT,
    lance_minimo REAL,
    valor_arremate REAL,
    agio_percent REAL,
    data_pregao TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Paper trading (B5)
CREATE TABLE paper_trades (
    id INTEGER PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes(id),
    decision TEXT,                         -- 'compraria', 'passaria'
    lance_maximo_definido REAL,
    investimento_estimado REAL,
    roi_esperado REAL,
    resultado_real TEXT,                   -- 'arrematado_por_X', 'nao_arrematado'
    acertou BOOLEAN,                       -- decisão correta?
    created_at TIMESTAMP DEFAULT NOW()
);

-- Manutenção de parsers (D10)
CREATE TABLE parser_health (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    last_success TIMESTAMP,
    last_failure TIMESTAMP,
    consecutive_failures INTEGER DEFAULT 0,
    test_result TEXT,                      -- JSON com hash da fixture vs real
    is_broken BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Filtros do usuário
CREATE TABLE user_filters (
    id INTEGER PRIMARY KEY,
    name TEXT,
    max_price REAL,
    min_roi REAL,
    min_roi_mensal REAL,                   -- NOVO
    max_distance_km REAL,                  -- NOVO: filtro geográfico
    categories TEXT,
    locations TEXT,
    min_confidence TEXT DEFAULT 'estimado', -- NOVO: 'confiavel', 'estimado', 'desconhecido'
    allow_pj_only BOOLEAN DEFAULT 0,
    is_active BOOLEAN DEFAULT 1
);

-- Scrape log
CREATE TABLE scrape_log (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id),
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    status TEXT,
    lots_found INTEGER,
    lots_new INTEGER,
    error TEXT,
    duration_ms INTEGER,
    parser_version TEXT                     -- NOVO: hash do parser pra detectar mudança
);
```

## 6.2 Política de Retenção (v2 mantida)

| Dado | Ação | Quando |
|------|------|--------|
| Lotes encerrados | Arquivar | 90 dias após `situacao='Encerrado'` |
| Editais encerrados | Arquivar | 90 dias após `end_propostas` |
| Cache HTTP | Expirar | 7 dias |
| Imagens de lote | Manter | Enquanto lote ativo + 30 dias |
| Alertas não entregues | Deletar | 30 dias |
| Market prices (histórico) | Manter | Sempre (útil pra calibração) |
| Agio history | Manter | Sempre (útil pra modelos) |

---

# PARTE VII — ALERTAS E NOTIFICAÇÕES

## 7.1 Canais

| Canal | Prioridade | Conteúdo |
|-------|-----------|----------|
| **🥇 Telegram** | Imediato | 🥇 Balas de prata + 🟡 ROI alto |
| **🥈 Email digest** | Diário 8h | Todos os lotes com ROI >= 25% |
| **🥉 Arquivo local** | Semanal | Relatório completo de oportunidades |

## 7.2 Formato do Alerta Telegram

```
🥇 BALA DE PRATA — Edital Curitiba

📱 Lote 20 — Honda CG 125 2018
💰 Lance mínimo: R$ 2.500
📈 ROI estimado: 156% (R$ 6.400/mês)
✅ Confiança: Alta (veículo completo, FIPE R$ 8.200)
📍 Retirada: Curitiba/PR (380km — ✅ dentro do filtro)
⏰ Pregão: 28/Jul 10h (4 dias)

🟢 Recomendação: COMPRAR
Lance máximo sugerido: R$ 5.700

Próximo passo: Abrir edital → Definir lance → Dar proposta
```

## 7.3 Dedup de Alertas (D9)

```python
def cria_alerta(lote, source):
    """Cria alerta com dedup: mesmo lote = 1 alerta/dia, mesmo em fontes diferentes."""
    hoje = date.today()
    
    # Verifica se já existe alerta pra este lote hoje
    existente = db.execute("""
        SELECT id FROM alertas 
        WHERE lote_id = ? AND DATE(created_at) = ?
    """, (lote.id, hoje))
    
    if existente:
        return None  # Já alertado hoje — não duplicar
    
    # Se veio de fonte diferente (ex: Receita SLE + Leilão.net), 
    # dedup por hash do conteúdo
    hash_lote = hash(f"{lote.edital_id}-{lote.lote_number}")
    existente_hash = db.execute("""
        SELECT id FROM alertas WHERE lote_id IN (
            SELECT id FROM lotes WHERE 
            hash(edital_id || '-' || lote_number) = ?
        ) AND DATE(created_at) = ?
    """, (hash_lote, hoje))
    
    if existente_hash:
        # Atualiza source mas não cria novo alerta
        return None
    
    return novo_alerta(lote, source)
```

## 7.4 Filtro Geográfico (B6)

```python
# Configuração
CEP_INVESTIDOR = "01310-100"   # São Paulo/SP
RAIO_MAXIMO_KM = 600            # 600km de SP = Curitiba, RJ, BH, interior SP

# Cálculo
def distancia_ate_lote(lote_location: str) -> float:
    """Retorna distância em km do lote até o investidor."""
    # Usa API do Google Maps ou tabela de distâncias fixas
    pass

# Lote é automaticamente excluído do alerta se:
def filtrar_por_geografia(lote: Lot) -> bool:
    return lote.distancia_km <= RAIO_MAXIMO_KM or lote.categoria == 'veiculo'
    # Veículos têm exceção: vale a pena viajar pra buscar
```

---

# PARTE VIII — OPERAÇÃO DO INVESTIDOR

## 8.1 Rotina Semanal (10-11h — confirmado do plano anterior)

| Dia | Horário | Atividade | Horas |
|-----|---------|-----------|-------|
| **Seg** | 20h-21h | Revisar alertas do dia, analisar lotes novos | 1h |
| **Ter** | 20h-21h | Responder clientes ML, preparar envios | 1h |
| **Qua** | 20h-21h | Pesquisar preços de referência, atualizar tabela | 1h |
| **Qui** | 20h-21h | Organizar estoque, tirar fotos | 1h |
| **Sex** | — | Off | — |
| **Sáb** | 10h-13h | **Operação pesada**: retirada, teste, triagem | 3h |
| **Sáb** | 14h-16h | Preparar lotes pra postar segunda | 2h |
| **Dom** | 10h-12h | Planejamento da semana + paper trading | 2h |

## 8.2 Fluxo Completo: Alerta → Compra → Venda

```
🟢 ALERTA CHEGA (Telegram)
  ↓
1. INVESTIGAR (30 min)
   ├── Ler descrição completa do lote
   ├── Ver fotos (se disponíveis)
   ├── Pesquisar preço de revenda no ML
   └── Calcular lance máximo manualmente (conferir ROI do sistema)
  ↓
2. DECIDIR (15 min)
   ├── 🟢 COMPRAR → Definir lance máximo
   └── 🔴 PASSAR → Marcar motivo (preço, distância, risco)
  ↓
3. PREPARAR (1h — antes do pregão)
   ├── Separar documentos (CNPJ, cert. digital)
   ├── Ler edital completo (regras, taxas, retirada)
   └── Configurar alerta pro dia do pregão
  ↓
4. PREGÃO (2-3h — no dia)
   ├── Se puder estar online → dar lances ao vivo
   ├── Se não → usar proposta fechada (modalidade SLE)
   └── Definir incremento máximo
  ↓
5. PÓS-ARREMATE (até 30 dias)
   ├── Se ganhou → Pagar DARF em 30 dias
   ├── Agendar retirada (fds)
   ├── Retirar, transportar
   └── Se perdeu → Registrar ágio final (calibrar sistema)
  ↓
6. VENDA (7-60 dias)
   ├── Testar/triar cada unidade
   ├── Fotografar
   ├── Anunciar no ML/Shopee/OLX
   ├── Atender, negociar, vender
   └── Registrar no PORTFOLIO (pra calibrar ROI)
  ↓
🔁 REINVESTIR
```

## 8.3 Paper Trading (B5) — Como validar a tese sem gastar dinheiro

**O que é:** Registrar alertas como "compraria" ou "passaria", e depois checar se decisão estava certa.

**Como funciona:** Cada alerta 🥇 ou 🟡 gera uma entrada em `paper_trades`:
- Decisão: compraria / passaria
- Lance máximo definido
- Investimento estimado

**Após o pregão (30 dias depois):**
- Resultado real: arrematado por X / não arrematado
- Sua decisão estava certa? (se compraria e preço ≤ lance máx → acertou)

**Meta do paper trading (60 dias):**
- 10+ decisões registradas
- Taxa de acerto ≥ 60%
- ROI médio das oportunidades perdidas ≥ 40%

**Se validar → PRIMEIRA COMPRA REAL**

## 8.4 Portfolio Tracking Pós-Compra (B4)

Após a primeira compra, cada lote vira um registro em `portfolio`.

| Campo | Por que importa |
|-------|----------------|
| Custo total real | Comparar com estimativa do sistema |
| Dias até vender | Validar / calibrar tabela de liquidez |
| ROI realizado | **Essencial**: calibra o decision engine |
| Erro de ROI | Se sistema erra > 30%, ajustar pricing |

**Quando o `erro_roi` acumulado cruza 30% para mais de 3 lotes consecutivos:**
→ Sistema está descalibrado → revisar tabela de preços ou regra de lance

## 8.5 Checklist de Preparação (pré-operacional)

```
📋 ANTES DE COMEÇAR:
   [ ] CNPJ MEI ativo (CNAE 4771701)
   [ ] Conta GOV.BR nível Ouro
   [ ] Certificado digital (R$ 100-150)
   [ ] Acesso e-CAC funcionando
   [ ] Conta Mercado Livre (CNPJ)
   [ ] Conta Shopee (CNPJ)
   [ ] Conta OLX
   [ ] PRONAMPE aprovado (R$ 5K)
   [ ] Scraper MVP rodando
   [ ] Telegram bot configurado
   [ ] Espaço em casa pra estoque (1-2m²)
   [ ] Balança Correios (R$ 40-80)
   [ ] Caixas/papelão para envio
   [ ] Impressora (etiquetas)
```

---

# PARTE IX — RISCOS

## 9.1 Risco de Negócio

| Risco | Prob. | Impacto | Mitigação |
|-------|-------|---------|-----------|
| Lote com defeito/condição pior que esperada | 🟡 Média | 🟠 Médio | Visitar lote antes se possível; margem de risco 10% |
| Crédito não aprovado | 🟢 Baixa | 🔴 Alto | Ter 2ª opção (Procred 360); economia de 8 meses |
| Produto não vender em 60 dias | 🟡 Média | 🟠 Médio | Precificar 5% abaixo do menor ML; diversificar OLX |
| Pregão no horário de trabalho | 🔴 Alta | 🟡 Leve | Usar proposta fechada; não depende de estar online |
| Concorrência (outros revendedores) | 🟡 Média | 🟡 Leve | Nicho específico; ágio controlado |
| ICMS/DIFAL inviabilizar margem | 🟡 Média | 🟡 Leve | Fatorar ICMS no cálculo de lance máximo |
| Receita Federal mudar regras do SLE | 🟢 Baixa | 🔴 Alto | Diversificar fontes (CAIXA, PF, PRF como backup) |
| ML/Shoppee aumentarem taxas | 🟢 Baixa | 🟡 Leve | Repassar ao preço ou migrar para OLX |

## 9.2 Risco Técnico (Manutenção do Sistema — D10)

| Risco | Prob. | Impacto | Mitigação |
|-------|-------|---------|-----------|
| Site muda layout (parser quebra) | 🔴 Alta | 🔴 Alto | Teste automático c/ HTML fixture; alerta de parser quebrado |
| Site bloqueia scraping | 🟡 Média | 🟠 Médio | Rate limiting; User-Agent; proxying (só se necessário) |
| Dependência externa (Telegram API) | 🟢 Baixa | 🟡 Leve | Fallback pra email |
| Bug no ROI calculator | 🟡 Média | 🟠 Médio | Validação manual das primeiras análises; testes unitários |
| Banco de dados corrompido | 🟢 Baixa | 🔴 Alto | Backup diário automático |

### Estratégia de Manutenção de Parsers (D10)

```python
# Todo scrape compara o HTML atual com a fixture salva
# Se o hash mudou E o output está vazio → PARSER QUEBRADO

def check_parser_health(source: Source) -> bool:
    """Verifica se o parser ainda funciona."""
    fixture_path = f"tests/fixtures/{source.name}_edital.html"
    atual_html = fetch_page(source.url)
    
    # Parseia com o parser atual
    resultado = source.parser(atual_html)
    
    # Se não encontrou nada mas antes encontrava → quebrou
    if len(resultado) == 0:
        with open(fixture_path) as f:
            fixture_result = source.parser(f.read())
        if len(fixture_result) > 0:
            alerta_parser_quebrado(source)
            return False
    return True
```

---

# PARTE X — ROADMAP 12 SEMANAS (com checkpoints)

## 🟩 SEMANA 1 — LEAN MVP (15-20h)

| Dia | Tarefa | Entrega |
|-----|--------|---------|
| 1 | Setup projeto `leilao-radar/`, pyproject, SQLite | Repo + DB |
| 2 | Parser Receita Federal SLE (reaproveitar `tools/leilao_scraper.py`) | 1ª fonte |
| 3 | Parser Leilão.net (agregador — HTML simples) | 2ª fonte |
| 4 | Tabela manual de preços (~20 produtos) + ROI calculator | ROI v0 |
| 5 | 3 níveis de confiança + filtro geográfico | Decision engine |
| 6 | Telegram bot + dedup de alertas | Alertas |
| 7 | Paper trading setup | Modo teste |

**Entrega:** "Bom dia! 3 oportunidades hoje" no Telegram 🚀

### 🚦 CHECKPOINT #1 (final Semana 1)

```
PERGUNTA: O sistema detecta oportunidades que você compraria?

MÉTRICAS:
  → Lotes capturados: ?
  → ROI >= 50% e preço <= R$ 10K: ?
  → Você olhou os alertas e se interessou?

DECISÃO:
  🟢 SIM → Avançar
  🟡 PARCIAL → Ajustar parsers/pricing, +1 sem
  🔴 NÃO → Repensar tese
```

## 🟩 SEMANA 2-3 — FASE 1: EXPANSÃO (10-12h)

- [ ] +5 agregadores (Tri, Mega, Parque, Lance, Justiça)
- [ ] PF (HTML), PRF (HTML)
- [ ] Captura de imagens dos lotes (C7)
- [ ] Cache HTTP + rate limiter
- [ ] Primeiro paper trade registrado
- [ ] Checkpoint #2 avalia: "tem >= 10 lotes relevantes/semana?"

**Entrega:** 8 fontes, ~80 lotes/dia, imagens sendo baixadas

## 🟩 SEMANA 4-6 — FASE 2: ESTADUAIS + PDF (10-15h)

- [ ] Correios (Lucitações-e), SEFAZ-MT, -SP, -PR
- [ ] Detran-SP, -RJ
- [ ] Detector de PDF (baixa + marca para revisão)
- [ ] Circuit breaker + parser health checks (D10)
- [ ] **Paper trading: 10+ decisões registradas**
- [ ] Checkpoint #3 (semana 6 — MEIO): **Já fez primeira compra?**

### 🚦 CHECKPOINT #3 (Semana 6 — DECISÃO CRÍTICA)

```
PERGUNTA: Já realizou primeira compra real?

  🟢 SIM → Parabéns! Continuar expansão: 
         Portfolio tracking, escalar fontes
  🟡 NÃO, MAS paper trading validou → Falta confiança ou capital:
         Investigar o que trava. Ajustar e tentar na semana 7.
  🔴 NÃO, E paper trading não validou → Tese fraca:
         Repensar categorias, fontes, ou estratégia
  🔴🔴 NÃO, E crédito não aprovado → Sem capital:
         Pausar. Retomar quando crédito sair.
```

## 🟩 SEMANA 7-9 — FASE 3: ANÁLISE INTELIGENTE (12-15h)

- [ ] Parsing de PDF com pdfplumber + Gemini Flash
- [ ] Pricing v1: scraping do ML (httpx, sem login)
- [ ] Histórico de preços + depreciação (A3)
- [ ] Tracking de ágio por categoria (C8) — alimentar dos pregões
- [ ] Portfolio tracking pós-compra (B4)
- [ ] ROI realizado vs previsto — calibragem
- [ ] Categorização via LLM (Gemini Flash)

**Entrega:** Sistema analisa PDFs, pricing automático, ROI se calibra com dados reais

## 🟩 SEMANA 10-12 — FASE 4+5: ESCALA E ALERTAS AVANÇADOS (10-15h)

- [ ] Alertas em tempo real (não só digest)
- [ ] Dashboard TUI simples (Textual)
- [ ] Bot Telegram interativo: `/oportunidades`, `/stats`, `/filtrar`
- [ ] Deploy em VPS (Hetzner R$ 30/mês)
- [ ] Docker compose + monitoramento
- [ ] Fontes Tier C (CAIXA Imóveis, BB) — só se checkpoint 3 foi 🟢
- [ ] Checkpoint final (semana 12)

### 🚦 CHECKPOINT FINAL (Semana 12)

```
PERGUNTA: O sistema gera valor real?

CRITÉRIO:
  ✅ Pelo menos 1 compra real realizada
  ✅ ROI realizado >= 25%
  ✅ Reserva de R$ 40K intacta
  ✅ Paper trading taxa de acerto >= 60%
  ✅ Previsão de ROI com erro < 30%

Se SIM → Manter e operar. Melhorias incrementais.
Se NÃO → Pausar. O gargalo não é o sistema, é execução ou tese.
```

---

## 📊 RESUMO EXECUTIVO — v3

```
O QUE MUDOU DA V2 PARA V3:

v2 era:     "Plano técnico de scraping com menção ao negócio"
v3 é:       "Plano de negócio que usa scraping como ferramenta"

MUDANÇAS ESTRUTURAIS:
  ✅ PARTE I-III: Tese de negócio + modelo financeiro + decision engine
  ✅ PARTE IV: Fontes ordenadas por valor de negócio, não por facilidade técnica
  ✅ PARTE V: MVP pequeno mas focado em gerar o primeiro alerta útil
  ✅ PARTE VII: Alertas com regras de negócio, não só scraping
  ✅ PARTE VIII: Rotina do investidor integrada ao sistema
  ✅ PARTE IX: Risco de negócio + risco técnico lado a lado

10 REFINAMENTOS APLICADOS:
  A1 — 3 níveis de confiança de ROI         🟢
  A2 — ROI mensal (liquidez ajustada)       🟢
  A3 — Histórico de preços + depreciação    🟢
  B4 — Portfolio tracking pós-compra        🟢
  B5 — Paper trading (modo teste)           🟢
  B6 — Filtro geográfico                    🟢
  C7 — Captura de imagens dos lotes         🟢
  C8 — Tracking de ágio dos concorrentes    🟢
  D9 — Dedup de alertas                     🟢
  D10 — Manutenção de parsers               🟢

MÉTRICA NORTE:
  "Primeiro lote comprado via alerta do sistema em até 90 dias"
```

---

## 🔮 PRÓXIMO PASSO

O plano de negócio + sistema está completo (v3). Agora a decisão é:

1. **🟢 IMPLEMENTAR MVP (Semana 1)** — Rodar `leilao_radar` com Receita SLE + Leilão.net no seu computador, configurar Telegram, começar paper trading
2. **🔵 REVISAR V3** — Ajustar alguma parte antes de começar a construir
3. **🟡 PROTOTIPAR** — Testar só o pipeline Receita SLE (já temos estrutura em `tools/leilao_scraper.py`) pra ver se o retorno justifica construir o resto

Qual?
