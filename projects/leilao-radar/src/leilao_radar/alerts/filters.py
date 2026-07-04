"""Alert filtering and scoring — decides what to alert and how urgently."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class AlertDecision:
    """Result of filtering a lot through user preferences."""

    should_alert: bool
    priority: str  # 'silver_bullet', 'high_roi', 'info', 'none'
    reason: str = ""


class AlertFilter:
    """Applies user filters and business rules to decide alerts."""

    def __init__(
        self,
        max_price: float = 8000.0,
        min_roi: float = 0.30,
        min_roi_mensal: float = 0.50,
        max_distance_km: float = 600.0,
        min_confidence: str = "estimado",
    ):
        self.max_price = max_price
        self.min_roi = min_roi
        self.min_roi_mensal = min_roi_mensal
        self.max_distance_km = max_distance_km
        self.min_confidence = min_confidence

    def evaluate(self, lot: dict[str, Any]) -> AlertDecision:
        """Evaluate whether a lot should trigger an alert."""
        preco = lot.get("preco_minimo", 0) or 0
        roi = lot.get("estimated_roi", 0) or 0
        roi_mensal = lot.get("estimated_roi_mensal", 0) or 0
        confidence = lot.get("confidence", "desconhecido")
        distancia = lot.get("distancia_km") or 0
        titulo = lot.get("titulo", "") or ""
        descricao = lot.get("descricao", "") or ""
        source = lot.get("source_label", lot.get("source_name", ""))
        edital = lot.get("edital_number", "")
        location = lot.get("location", "")

        # ── Hard filters (always block) ──────────────────────────

        # Price check
        if preco <= 0:
            return AlertDecision(False, "none", "Preço zero ou inválido")

        if preco > self.max_price:
            return AlertDecision(
                False, "none",
                f"Preço R$ {preco:,.0f} > limite R$ {self.max_price:,.0f}",
            )

        # Confidence check
        conf_levels = {"confiavel": 3, "estimado": 2, "desconhecido": 1}
        min_level = conf_levels.get(self.min_confidence, 2)
        actual_level = conf_levels.get(confidence, 1)
        if actual_level < min_level:
            return AlertDecision(
                False, "none",
                f"Confiança {confidence} < mínimo {self.min_confidence}",
            )

        # ── Filter scrap/very cheap items ────────────────────────
        titulo_upper = titulo.upper() if titulo else ""
        if "DESMONTAGEM" in titulo_upper or "SUCATA" in titulo_upper:
            return AlertDecision(False, "none", "Item para desmontagem/sucata")

        # Skip items cheaper than R$ 30 (usually scrap/parts)
        if preco < 30 and "VEÍCULO" in titulo_upper:
            return AlertDecision(False, "none", "Veículo muito barato, provável sucata")

        # ── Scoring ──────────────────────────────────────────────

        # Silver bullet: urgent, high ROI, within budget
        if (
            roi_mensal >= self.min_roi_mensal * 2  # 100%+/month
            and preco <= self.max_price * 0.7       # within 70% of budget
            and confidence in ("confiavel", "estimado")
        ):
            return AlertDecision(
                True, "silver_bullet",
                f"🥇 ROI/mês {roi_mensal:.0%} em {edital} ({location})",
            )

        # High ROI: daily digest material
        if roi_mensal >= self.min_roi_mensal and roi >= self.min_roi:
            return AlertDecision(
                True, "high_roi",
                f"🟡 ROI/mês {roi_mensal:.0%} em {edital} ({location})",
            )

        # Informative: new opportunities with some potential
        if roi >= 0.15:  # 15% minimum
            return AlertDecision(
                True, "info",
                f"⚪ ROI {roi:.0%} em {edital} ({location})",
            )

        return AlertDecision(False, "none", "ROI abaixo do mínimo")

    def format_alert_message(self, lot: dict[str, Any], decision: AlertDecision) -> str:
        """Format a lot into a human-readable alert message."""
        preco = lot.get("preco_minimo", 0) or 0
        roi = lot.get("estimated_roi", 0) or 0
        roi_mensal = lot.get("estimated_roi_mensal", 0) or 0
        confidence = lot.get("confidence", "?")
        titulo = lot.get("titulo", lot.get("descricao", "Lote sem título")) or ""
        source = lot.get("source_label", lot.get("source_name", ""))
        edital = lot.get("edital_number", "")
        location = lot.get("location", "")
        valor_mercado = lot.get("estimated_market_value", 0) or 0
        lance_max = lot.get("lance_maximo_recomendado", preco * 0.5)

        emocji = {
            "silver_bullet": "🥇",
            "high_roi": "🟡",
            "info": "⚪",
        }.get(decision.priority, "📋")

        lines = [
            f"{emocji} **{titulo[:80]}**",
            f"💰 Lance mínimo: R$ {preco:,.2f}",
            f"📈 ROI: {roi:.1%} ({roi_mensal:.0%}/mês)",
            f"✅ Confiança: {confidence}",
        ]

        if valor_mercado:
            lines.append(f"🏷️ Valor mercado: R$ {valor_mercado:,.2f}")
        if lance_max:
            lines.append(f"🎯 Lance máx sugerido: R$ {lance_max:,.2f}")
        if location:
            lines.append(f"📍 {location}")
        if source:
            lines.append(f"🔗 {source} — {edital}")

        return "\n".join(lines)
