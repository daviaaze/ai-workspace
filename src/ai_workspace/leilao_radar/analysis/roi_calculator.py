"""ROI Calculator — decision engine with 3 confidence levels.

Given a lot and a market price reference, calculates:
  - Estimated market value
  - ROI total (after all costs)
  - ROI mensal (adjusted for liquidity)
  - Confidence level (confiavel / estimado / desconhecido)
  - Recommended maximum bid
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from ai_workspace.leilao_radar.analysis.manual_prices import (
    CATEGORY_FALLBACK,
    PRICE_TABLE,
    find_product_in_text,
    get_category_price,
    get_liquidity_days,
    preco_ajustado_depreciacao,
)


@dataclass
class ROIAnalysis:
    """Complete ROI analysis for a single lot."""

    lote_id: int
    titulo: str
    preco_minimo: float

    # Market value
    estimated_market_value: float = 0.0
    market_value_source: str = ""  # 'exact', 'category', 'unknown'

    # Costs
    icms_estimate: float = 0.0
    frete_estimate: float = 0.0
    platform_fee: float = 0.0       # ML/Shopee commission
    operational_cost: float = 0.0    # Embalagem + taxas

    # ROI
    estimated_roi: float = 0.0           # Total ROI
    estimated_roi_mensal: float = 0.0    # ROI/month (liquidity-adjusted)
    meses_para_vender: float = 0.0

    # Confidence
    confidence: str = "desconhecido"  # 'confiavel', 'estimado', 'desconhecido'
    confidence_score: float = 0.0

    # Recommendation
    lance_maximo_recomendado: float = 0.0
    is_silver_bullet: bool = False

    # Notes
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "lote_id": self.lote_id,
            "estimated_market_value": self.estimated_market_value,
            "estimated_roi": self.estimated_roi,
            "estimated_roi_mensal": self.estimated_roi_mensal,
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "meses_para_vender": self.meses_para_vender,
            "ml_fee_estimate": self.platform_fee,
            "shopee_fee_estimate": 0.0,
            "frete_estimate": self.frete_estimate,
            "notes": self.notes,
        }


class ROICalculator:
    """Calculates ROI for auction lots."""

    # Default cost assumptions
    ICMS_ALIQUOTA = 0.12        # 12% (SP/PR/RJ)
    ML_FEE = 0.13               # ML Clássico 13%
    SHOPEE_FEE_RATE = 0.14      # Shopee Faixa 5: 14%
    SHOPEE_FEE_FIXED = 26.0     # Shopee fixed fee for >R$200
    FRETE_MEDIO = 30.0          # Average shipping cost
    CUSTO_EMBALAGEM = 5.0       # Packaging per unit
    ACAO_PADRAO = 0.25          # Default ágio estimate (25%)

    # Risk margin
    RISCO_PRODUTO = 0.10        # 10% for damage/defects
    RISCO_DEVOLUCAO = 0.05      # 5% for returns/chargebacks

    def __init__(self, budget_max: float = 8000.0):
        self.budget_max = budget_max

    def analyze(self, lot: dict) -> ROIAnalysis:
        """Run full analysis on a lot dict.

        The lot dict must have at minimum:
          id, titulo, preco_minimo, categoria_normalizada
        """
        lote_id = lot["id"]
        titulo = lot.get("titulo", lot.get("descricao", ""))
        preco = lot.get("preco_minimo", 0)
        categoria = lot.get("categoria_normalizada") or "DIVERSOS"
        descricao = lot.get("descricao", "")
        total_itens = lot.get("total_itens", 1) or 1

        # Build combined text for product matching
        search_text = f"{titulo} {descricao} {categoria}"

        # Check for low-value indicators
        raw = lot.get("raw_data") or "{}"
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                raw = {}
        valor_avaliacao = raw.get("valor_avaliacao", 0) if isinstance(raw, dict) else 0
        is_scrap = any(kw in (titulo + descricao).upper()
                       for kw in ["DESMONTAGEM", "SUCATA", "INSERVÍVEL", "PARA PEÇAS", "PECAS"])
        is_very_cheap = preco < 100 and valor_avaliacao > 0

        # 1. Find market price
        market_value, source, confidence = self._find_market_value(
            search_text, categoria, total_itens, preco, valor_avaliacao
        )

        # Adjust for scrap/cheap items
        if is_scrap and valor_avaliacao > 0:
            market_value = max(preco * 1.2, min(valor_avaliacao * 0.15, 3000.0))
            confidence = 'estimado'
            source = 'scrap_adjusted'
        elif is_very_cheap and valor_avaliacao > preco * 20:
            market_value = max(preco * 1.5, min(valor_avaliacao * 0.3, 5000.0))
            confidence = 'estimado'
            source = 'cheap_adjusted'

        # 2. Estimate costs
        icms = preco * self.ICMS_ALIQUOTA
        frete = self.FRETE_MEDIO * min(total_itens, 20)  # Scale with items
        plataforma_fee = market_value * self.ML_FEE if market_value else 0
        operacional = self.CUSTO_EMBALAGEM * total_itens

        custo_total = preco + icms + frete + operacional
        risco = (preco * self.RISCO_PRODUTO) + (market_value * self.RISCO_DEVOLUCAO)

        receita_liquida = market_value - plataforma_fee
        lucro = receita_liquida - custo_total - risco

        roi = lucro / custo_total if custo_total > 0 else 0

        # 3. Liquidity adjustment
        meses = get_liquidity_days(categoria.lower()) / 30.0
        roi_mensal = roi / meses if meses > 0 else roi

        # 4. Apply depreciation
        roi_depreciado = (market_value * (1 - 0.03 * meses) - plataforma_fee - custo_total - risco) / custo_total if custo_total > 0 else 0
        roi_mensal_depreciado = roi_depreciado / meses if meses > 0 else roi_depreciado

        # 5. Max bid
        lance_max = self._calc_lance_maximo(market_value, categoria)

        # 6. Build analysis
        analysis = ROIAnalysis(
            lote_id=lote_id,
            titulo=titulo,
            preco_minimo=preco,
            estimated_market_value=market_value,
            market_value_source=source,
            icms_estimate=icms,
            frete_estimate=frete,
            platform_fee=plataforma_fee,
            operational_cost=operacional,
            estimated_roi=roi,
            estimated_roi_mensal=roi_mensal,
            meses_para_vender=meses,
            confidence=confidence,
            confidence_score=self._confidence_to_score(confidence),
            lance_maximo_recomendado=lance_max,
            notes=f"Market value: {source} ({confidence}). "
                  f"Items: {total_itens}. Cat: {categoria}.",
        )

        # 7. Silver bullet check
        analysis.is_silver_bullet = self._is_silver_bullet(
            analysis, preco
        )

        return analysis

    def _find_market_value(
        self, text: str, categoria: str, quantity: int,
        preco_lance: float = 0.0,
        valor_avaliacao: float = 0.0,
    ) -> tuple[float, str, str]:
        """Find market value with confidence level.

        Returns (market_value, source_description, confidence_label)
        """
        # Try exact product match
        product = find_product_in_text(text)
        if product:
            return (
                product.median * quantity,
                f"exact: {product.name}",
                "confiavel" if product.confidence >= 0.5 else "estimado",
            )

        # Try category fallback
        cat_lower = categoria.lower()
        fallback = get_category_price(cat_lower)
        if fallback:
            base = fallback.median * max(quantity, 1)
            # If we have a valuation, use it to cap
            if valor_avaliacao > 0:
                # Use the lesser of fallback and 70% of valuation
                base = min(base, valor_avaliacao * 0.7)
            return (
                max(base, preco_lance * 1.1),  # At least 10% above cost
                f"category: {cat_lower}",
                "estimado",
            )

        # Unknown — use valuation or rough estimate
        if valor_avaliacao > 0:
            return (max(valor_avaliacao * 0.5, preco_lance * 1.1), "avaliacao", "desconhecido")
        return (max(preco_lance * 2.0, 500.0), "unknown", "desconhecido")

    def _calc_lance_maximo(
        self, market_value: float, categoria: str
    ) -> float:
        """Calculate maximum bid for this lot."""
        taxa = self.ML_FEE
        frete = self.FRETE_MEDIO
        margem_risco = self.RISCO_PRODUTO + self.RISCO_DEVOLUCAO

        lance_max = market_value * (1 - taxa) - frete - (market_value * margem_risco)
        return max(lance_max, 0)

    def _confidence_to_score(self, confidence: str) -> float:
        return {"confiavel": 0.85, "estimado": 0.50, "desconhecido": 0.15}.get(
            confidence, 0.0
        )

    def _is_silver_bullet(
        self, analysis: ROIAnalysis, preco: float
    ) -> bool:
        """Check if this is an immediate-action opportunity."""
        return (
            analysis.confidence_score >= 0.5
            and analysis.estimated_roi_mensal >= 0.50
            and preco <= self.budget_max
            and preco > 0
            and analysis.estimated_market_value > 0
        )
