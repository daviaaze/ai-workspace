"""Manual price table for known products.

Each entry has estimated market value for resale on ML/Shopee.
Updated periodically based on market research.

Format:
  product_key: {
      "name": readable name,
      "category": normalized category,
      "median": median market price,
      "min": minimum realistic price,
      "max": maximum realistic price,
      "confidence": how sure we are (0-1)
  }
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class PriceEntry:
    """A product price reference."""
    product_key: str
    name: str
    category: str
    median: float
    min_price: float
    max_price: float
    confidence: float = 0.7  # Most are manually verified


# ══════════════════════════════════════════════════════════════════════
# MANUAL PRICE TABLE v3 — Julho/2026
# ══════════════════════════════════════════════════════════════════════
#
# Fontes: ML, Shopee, OLX, Trocafone (cross-checked)
# Atualizado: Julho/2026
#
# NOTA: Preços são de revenda (usado ou lacrado conforme o caso).
# Para produtos de leilão, considerar desgaste e possíveis defeitos.
# ══════════════════════════════════════════════════════════════════════

PRICE_TABLE: dict[str, PriceEntry] = {
    # ── iPhones ─────────────────────────────────────────────────────
    "iphone_13_128gb": PriceEntry(
        product_key="iphone_13_128gb",
        name="iPhone 13 128GB",
        category="celular",
        median=2200.0,
        min_price=1800.0,
        max_price=2800.0,
        confidence=0.7,
    ),
    "iphone_13_256gb": PriceEntry(
        product_key="iphone_13_256gb",
        name="iPhone 13 256GB",
        category="celular",
        median=2500.0,
        min_price=2000.0,
        max_price=3000.0,
        confidence=0.7,
    ),
    "iphone_12_64gb": PriceEntry(
        product_key="iphone_12_64gb",
        name="iPhone 12 64GB",
        category="celular",
        median=1600.0,
        min_price=1300.0,
        max_price=2000.0,
        confidence=0.7,
    ),
    "iphone_12_128gb": PriceEntry(
        product_key="iphone_12_128gb",
        name="iPhone 12 128GB",
        category="celular",
        median=1800.0,
        min_price=1500.0,
        max_price=2200.0,
        confidence=0.7,
    ),

    # ── Xiaomi ──────────────────────────────────────────────────────
    "redmi_note_13_256gb": PriceEntry(
        product_key="redmi_note_13_256gb",
        name="Xiaomi Redmi Note 13 256GB",
        category="celular",
        median=1050.0,
        min_price=900.0,
        max_price=1200.0,
        confidence=0.8,
    ),
    "redmi_note_13_128gb": PriceEntry(
        product_key="redmi_note_13_128gb",
        name="Xiaomi Redmi Note 13 128GB",
        category="celular",
        median=850.0,
        min_price=750.0,
        max_price=950.0,
        confidence=0.8,
    ),
    "redmi_note_12_256gb": PriceEntry(
        product_key="redmi_note_12_256gb",
        name="Xiaomi Redmi Note 12 256GB",
        category="celular",
        median=800.0,
        min_price=700.0,
        max_price=1000.0,
        confidence=0.7,
    ),
    "redmi_note_14_256gb": PriceEntry(
        product_key="redmi_note_14_256gb",
        name="Xiaomi Redmi Note 14 256GB",
        category="celular",
        median=1300.0,
        min_price=1100.0,
        max_price=1500.0,
        confidence=0.6,
    ),

    # ── POCO ────────────────────────────────────────────────────────
    "poco_x6_pro_256gb": PriceEntry(
        product_key="poco_x6_pro_256gb",
        name="POCO X6 Pro 256GB",
        category="celular",
        median=1500.0,
        min_price=1300.0,
        max_price=1700.0,
        confidence=0.7,
    ),
    "poco_x7_pro_256gb": PriceEntry(
        product_key="poco_x7_pro_256gb",
        name="POCO X7 Pro 256GB",
        category="celular",
        median=1800.0,
        min_price=1500.0,
        max_price=2100.0,
        confidence=0.6,
    ),

    # ── Samsung ────────────────────────────────────────────────────
    "samsung_a55_256gb": PriceEntry(
        product_key="samsung_a55_256gb",
        name="Samsung Galaxy A55 256GB",
        category="celular",
        median=1600.0,
        min_price=1400.0,
        max_price=1900.0,
        confidence=0.7,
    ),
    "samsung_s24_256gb": PriceEntry(
        product_key="samsung_s24_256gb",
        name="Samsung Galaxy S24 256GB",
        category="celular",
        median=3000.0,
        min_price=2500.0,
        max_price=3800.0,
        confidence=0.6,
    ),

    # ── Informática ────────────────────────────────────────────────
    "ssd_nvme_512gb": PriceEntry(
        product_key="ssd_nvme_512gb",
        name="SSD NVMe 512GB",
        category="informatica",
        median=200.0,
        min_price=150.0,
        max_price=280.0,
        confidence=0.8,
    ),
    "ssd_nvme_1tb": PriceEntry(
        product_key="ssd_nvme_1tb",
        name="SSD NVMe 1TB",
        category="informatica",
        median=350.0,
        min_price=250.0,
        max_price=450.0,
        confidence=0.8,
    ),
    "memoria_ram_ddr4_8gb": PriceEntry(
        product_key="memoria_ram_ddr4_8gb",
        name="Memória RAM DDR4 8GB",
        category="informatica",
        median=80.0,
        min_price=60.0,
        max_price=120.0,
        confidence=0.8,
    ),
    "memoria_ram_ddr4_16gb": PriceEntry(
        product_key="memoria_ram_ddr4_16gb",
        name="Memória RAM DDR4 16GB",
        category="informatica",
        median=150.0,
        min_price=110.0,
        max_price=200.0,
        confidence=0.8,
    ),
    "macbook_air_m1": PriceEntry(
        product_key="macbook_air_m1",
        name="MacBook Air M1 13\"",
        category="informatica",
        median=4000.0,
        min_price=3500.0,
        max_price=5000.0,
        confidence=0.6,
    ),
    "macbook_air_m2": PriceEntry(
        product_key="macbook_air_m2",
        name="MacBook Air M2 13\"",
        category="informatica",
        median=5500.0,
        min_price=4800.0,
        max_price=6500.0,
        confidence=0.6,
    ),

    # ── Perfumes ───────────────────────────────────────────────────
    "perfume_lattafa_khamrah": PriceEntry(
        product_key="perfume_lattafa_khamrah",
        name="Perfume Lattafa Khamrah 100ml",
        category="perfume",
        median=180.0,
        min_price=140.0,
        max_price=240.0,
        confidence=0.7,
    ),
    "perfume_armaf_cdn_intense": PriceEntry(
        product_key="perfume_armaf_cdn_intense",
        name="Perfume Armaf Club de Nuit Intense 100ml",
        category="perfume",
        median=250.0,
        min_price=180.0,
        max_price=320.0,
        confidence=0.7,
    ),
    "perfume_lattafa_asad": PriceEntry(
        product_key="perfume_lattafa_asad",
        name="Perfume Lattafa Asad 100ml",
        category="perfume",
        median=150.0,
        min_price=120.0,
        max_price=200.0,
        confidence=0.7,
    ),

    # ── Veículos ───────────────────────────────────────────────────
    "hb20_2021": PriceEntry(
        product_key="hb20_2021",
        name="Hyundai HB20 2021",
        category="veiculo",
        median=55000.0,
        min_price=48000.0,
        max_price=62000.0,
        confidence=0.5,
    ),
    "cobalt_2012": PriceEntry(
        product_key="cobalt_2012",
        name="Chevrolet Cobalt 2012",
        category="veiculo",
        median=22000.0,
        min_price=15000.0,
        max_price=28000.0,
        confidence=0.4,
    ),
    "foston_x13_max": PriceEntry(
        product_key="foston_x13_max",
        name="Foston X13 Max (moto elétrica)",
        category="veiculo",
        median=3000.0,
        min_price=2500.0,
        max_price=4000.0,
        confidence=0.5,
    ),

    # ── Brinquedos ────────────────────────────────────────────────
    "brinquedo_misto": PriceEntry(
        product_key="brinquedo_misto",
        name="Brinquedo misto (lote)",
        category="brinquedo",
        median=25.0,
        min_price=10.0,
        max_price=60.0,
        confidence=0.3,  # Highly variable
    ),
}


# ─── Category-level fallback prices ──────────────────────────────────────
# When we can't identify a specific product, use category averages.

CATEGORY_FALLBACK: dict[str, PriceEntry] = {
    "celular": PriceEntry(
        product_key="__celular_generico__",
        name="Celular genérico (smartphone)",
        category="celular",
        median=500.0,
        min_price=150.0,
        max_price=2000.0,
        confidence=0.2,
    ),
    "informatica": PriceEntry(
        product_key="__informatica_generico__",
        name="Item de informática genérico",
        category="informatica",
        median=150.0,
        min_price=50.0,
        max_price=500.0,
        confidence=0.2,
    ),
    "perfume": PriceEntry(
        product_key="__perfume_generico__",
        name="Perfume importado genérico",
        category="perfume",
        median=120.0,
        min_price=60.0,
        max_price=250.0,
        confidence=0.2,
    ),
    "veiculo": PriceEntry(
        product_key="__veiculo_generico__",
        name="Veículo popular genérico",
        category="veiculo",
        median=30000.0,
        min_price=5000.0,
        max_price=60000.0,
        confidence=0.1,
    ),
    "brinquedo": PriceEntry(
        product_key="__brinquedo_generico__",
        name="Brinquedo genérico",
        category="brinquedo",
        median=20.0,
        min_price=5.0,
        max_price=80.0,
        confidence=0.1,
    ),
    "eletronico": PriceEntry(
        product_key="__eletronico_generico__",
        name="Eletrônico genérico",
        category="eletronico",
        median=200.0,
        min_price=50.0,
        max_price=1000.0,
        confidence=0.1,
    ),
    "luxo": PriceEntry(
        product_key="__luxo_generico__",
        name="Item de luxo genérico",
        category="luxo",
        median=500.0,
        min_price=100.0,
        max_price=5000.0,
        confidence=0.1,
    ),
}


# ─── Category → Liquidity mapping (days to sell) ────────────────────────

LIQUIDITY_DAYS: dict[str, float] = {
    "celular": 15,        # 15 days avg
    "informatica": 30,    # 30 days
    "perfume": 30,        # 30 days
    "veiculo": 30,        # 30 days (can be faster if priced right)
    "brinquedo": 45,      # 45 days
    "eletronico": 30,     # 30 days
    "luxo": 60,           # 60 days (niche market)
    "diversos": 60,       # 60 days (mixed, harder to sell)
}


def get_price(product_key: str) -> Optional[PriceEntry]:
    """Get price by exact product key."""
    return PRICE_TABLE.get(product_key)


def get_category_price(category: str) -> Optional[PriceEntry]:
    """Get fallback price by category."""
    return CATEGORY_FALLBACK.get(category)


def find_product_in_text(text: str) -> Optional[PriceEntry]:
    """Try to find a known product in a description text."""
    text_lower = text.lower()

    # Check each known product
    for key, entry in PRICE_TABLE.items():
        # Match on name keywords
        keywords = entry.name.lower().split()
        if all(kw in text_lower for kw in keywords[:3]):  # First 3 words
            return entry

    # Check category keywords
    category_map = {
        "celular": ["celular", "smartphone", "iphone", "xiaomi", "samsung", "motorola",
                     "poco", "redmi", "galaxy"],
        "informatica": ["ssd", "hd", "memória", "ram", "notebook", "macbook",
                        "computador", "monitor", "teclado"],
        "perfume": ["perfume", "fragrância", "colônia", "lattafa", "armaf"],
        "veiculo": ["veículo", "carro", "moto", "hb20", "cobalt", "foston", "automóvel"],
        "brinquedo": ["brinquedo", "jogo", "boneco", "carrinho"],
        "eletronico": ["tv", "som", "caixa", "fone", "tablet", "kindle"],
    }

    for category, keywords in category_map.items():
        if any(kw in text_lower for kw in keywords):
            return get_category_price(category)

    return None


def get_liquidity_days(category: str) -> float:
    """Get estimated days to sell for a category."""
    return LIQUIDITY_DAYS.get(category, 60.0)


# ─── Depreciation rates (monthly) ───────────────────────────────────────

DEPRECIACAO_MENSAL: dict[str, float] = {
    "celular": 0.03,       # 3%/month
    "informatica": 0.025,  # 2.5%/month
    "perfume": 0.01,       # 1%/month
    "veiculo": 0.015,      # 1.5%/month
    "brinquedo": 0.02,     # 2%/month
    "eletronico": 0.03,    # 3%/month
    "luxo": 0.02,          # 2%/month
    "diversos": 0.03,      # 3%/month
}


def preco_ajustado_depreciacao(
    preco_atual: float, category: str, meses: float
) -> float:
    """Estimate market price after depreciation over N months."""
    taxa = DEPRECIACAO_MENSAL.get(category, 0.03)
    return preco_atual * (1 - taxa) ** meses
