"""SQLite schema for Leilão Radar."""

SCHEMA_SQL = """
-- ═══════════════════════════════════════════
-- LEILÃO RADAR v3 — MVP SCHEMA
-- ═══════════════════════════════════════════

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    label TEXT,
    url TEXT,
    tier TEXT CHECK(tier IN ('A','B','C')),
    source_type TEXT,
    check_interval_hours INTEGER,
    last_scraped_at TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS editais (
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
    pdf_downloaded BOOLEAN DEFAULT 0,
    pdf_parsed BOOLEAN DEFAULT 0,
    url TEXT,
    status TEXT DEFAULT 'ativo',
    UNIQUE(source_id, edital_number)
);

CREATE TABLE IF NOT EXISTS lotes (
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
    distancia_km REAL,
    total_itens INTEGER,
    confidence_level TEXT DEFAULT 'desconhecido',
    confidence_score REAL DEFAULT 0,
    raw_data TEXT,
    url TEXT,
    scraped_at TIMESTAMP,
    status TEXT DEFAULT 'ativo',
    UNIQUE(edital_id, lote_number)
);

CREATE TABLE IF NOT EXISTS lote_itens (
    id INTEGER PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes(id),
    quantity INTEGER,
    unit TEXT,
    description TEXT,
    brand TEXT,
    model TEXT
);

CREATE TABLE IF NOT EXISTS market_prices (
    id INTEGER PRIMARY KEY,
    product_key TEXT,
    normalized_name TEXT,
    category TEXT,
    median_price REAL,
    min_price REAL,
    max_price REAL,
    source TEXT,
    confidence REAL,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lote_analysis (
    lote_id INTEGER PRIMARY KEY REFERENCES lotes(id),
    estimated_market_value REAL,
    estimated_roi REAL,
    estimated_roi_mensal REAL,
    confidence TEXT,
    confidence_score REAL,
    meses_para_vender REAL,
    ml_fee_estimate REAL,
    shopee_fee_estimate REAL,
    frete_estimate REAL,
    analyzed_at TIMESTAMP,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS alertas (
    id INTEGER PRIMARY KEY,
    lote_id INTEGER REFERENCES lotes(id),
    alert_type TEXT,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    channel TEXT,
    delivered BOOLEAN DEFAULT 0,
    read BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS user_filters (
    id INTEGER PRIMARY KEY,
    name TEXT,
    max_price REAL,
    min_roi REAL,
    min_roi_mensal REAL,
    max_distance_km REAL,
    categories TEXT,
    locations TEXT,
    min_confidence TEXT DEFAULT 'estimado',
    is_active BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS scrape_log (
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

INSERT OR IGNORE INTO sources (name, label, url, tier, source_type, check_interval_hours, is_active)
VALUES
    ('receita_federal_sle', 'Receita Federal — SLE',
     'https://www25.receita.fazenda.gov.br/sle-sociedade/portal',
     'A', 'federal', 6, 1),
    ('leilao_net', 'Leilão.net (agregador)',
     'https://www.leilao.net/',
     'A', 'agregador', 12, 1);

INSERT OR IGNORE INTO user_filters (name, max_price, min_roi, min_roi_mensal, max_distance_km, min_confidence, is_active)
VALUES ('default', 8000, 0.30, 0.50, 600, 'estimado', 1);
"""
