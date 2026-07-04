"""Configuration via environment variables with .env fallback."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Application configuration loaded from environment."""

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Location
    cep_investidor: str = "01310-100"
    raio_maximo_km: int = 600

    # Filters
    preco_maximo: float = 8000.0
    roi_minimo_percent: float = 30.0

    # Paths
    data_dir: Path = Path.home() / ".leilao_radar"
    db_path: Path = field(default_factory=lambda: Path.home() / ".leilao_radar" / "leiloes.db")

    # Scraping
    user_agent: str = "LeilaoRadar/0.1 (+contato@exemplo.com)"
    request_timeout: int = 30
    rate_limit_per_domain: float = 1.0  # seconds between requests

    def __post_init__(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "Config":
        """Load config from environment variables with .env support."""
        env_path = Path.cwd() / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())

        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            cep_investidor=os.getenv("CEP_INVESTIDOR", "01310-100"),
            raio_maximo_km=int(os.getenv("RAIO_MAXIMO_KM", "600")),
            preco_maximo=float(os.getenv("PRECO_MAXIMO", "8000")),
            roi_minimo_percent=float(os.getenv("ROI_MINIMO_PERCENT", "30")),
        )
