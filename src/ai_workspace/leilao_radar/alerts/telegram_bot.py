"""Telegram bot for daily digest and alerts.

Uses python-telegram-bot v20+.
If token is not configured, alerts are saved to DB but not sent.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ai_workspace.leilao_radar.config import Config

logger = logging.getLogger("leilao_radar.alerts.telegram")


class TelegramBot:
    """Minimal Telegram bot for sending alerts."""

    def __init__(self, config: Config):
        self.token = config.telegram_bot_token
        self.chat_id = config.telegram_chat_id
        self._bot: Any = None  # Lazy import to avoid dependency if not needed

    @property
    def available(self) -> bool:
        return bool(self.token and self.chat_id)

    def _get_bot(self):
        """Lazy import python-telegram-bot."""
        if self._bot is not None:
            return self._bot
        if not self.available:
            return None

        try:
            from telegram import Bot
            from telegram.request import HTTPXRequest

            request = HTTPXRequest(connect_timeout=10, read_timeout=10)
            self._bot = Bot(token=self.token, request=request)
            return self._bot
        except ImportError:
            logger.warning("python-telegram-bot not installed. Install with: pip install python-telegram-bot")
            return None

    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Send a message via Telegram."""
        bot = self._get_bot()
        if not bot:
            logger.info("Telegram not configured. Message not sent:\n%s", text[:200])
            return False

        try:
            import asyncio
            # python-telegram-bot v20+ uses async
            async def _send():
                await bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    disable_web_page_preview=True,
                )

            asyncio.run(_send())
            return True
        except Exception as e:
            logger.error("Failed to send Telegram message: %s", e)
            return False

    def send_digest(self, alerts: list[dict[str, Any]]) -> bool:
        """Send a daily digest of multiple alerts."""
        if not alerts:
            return self.send_message(
                "📋 *Leilão Radar — Resumo do Dia*\n\n"
                "Nenhuma oportunidade encontrada hoje."
            )

        # Build digest message
        lines = ["📋 *Leilão Radar — Digest Diário*\n"]

        # Group by priority
        silver = [a for a in alerts if a.get("priority") == "silver_bullet"]
        high = [a for a in alerts if a.get("priority") == "high_roi"]
        info = [a for a in alerts if a.get("priority") == "info"]

        if silver:
            lines.append(f"*🥇 {len(silver)} Oportunidades Críticas*\n")
            for a in silver:
                lines.append(self._format_alert_short(a))
            lines.append("")

        if high:
            lines.append(f"*🟡 {len(high)} Oportunidades Promissoras*\n")
            for a in high:
                lines.append(self._format_alert_short(a))
            lines.append("")

        if info:
            lines.append(f"*⚪ {len(info)} Informativo*\n")
            for a in info[:5]:  # Cap info alerts
                lines.append(self._format_alert_short(a))

        lines.append("")
        lines.append("— Leilão Radar v0.1")

        message = "\n".join(lines)

        # Telegram has 4096 char limit — truncate if needed
        if len(message) > 4000:
            message = message[:4000] + "\n\n... (truncado)"

        return self.send_message(message)

    def _format_alert_short(self, alert: dict[str, Any]) -> str:
        """Format short alert line for digest."""
        preco = alert.get("preco_minimo", 0) or 0
        roi = alert.get("estimated_roi", 0) or 0
        roi_m = alert.get("estimated_roi_mensal", 0) or 0
        titulo = (alert.get("titulo") or "Lote")[:60]
        edital = alert.get("edital_number", "")
        location = alert.get("location", "")

        loc_str = f" ({location})" if location else ""
        return (
            f"• *{titulo}* — R$ {preco:,.0f} | "
            f"ROI {roi:.0%} ({roi_m:.0%}/mês){loc_str}"
        )
