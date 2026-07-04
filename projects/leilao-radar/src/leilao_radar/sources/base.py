"""Base classes for auction sources."""

from __future__ import annotations

import re
import time
from datetime import datetime
from typing import Any, Optional


class SourceResult:
    """Result from scraping a source."""

    def __init__(self):
        self.source_name: str = ""
        self.editais: list[dict[str, Any]] = []
        self.lotes: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self.duration_ms: int = 0
        self.http_requests: int = 0

    @property
    def success(self) -> bool:
        return len(self.errors) == 0

    @property
    def total_lotes(self) -> int:
        return len(self.lotes)


class BaseSource:
    """Base class for all auction sources."""

    name: str = ""
    label: str = ""
    url: str = ""
    tier: str = "A"
    source_type: str = ""
    check_interval_hours: int = 24

    def __init__(self, source_id: int | None = None):
        self.source_id = source_id

    def scrape(self) -> SourceResult:
        """Main entry point. Override in subclass."""
        raise NotImplementedError

    def _extract_price(self, text: str) -> Optional[float]:
        """Extract Brazilian currency value from text."""
        patterns = [
            r"(?:R\$|R\$)\s*([\d]+(?:\.\d{3})*,\d{2})",
            r"(?:R\$|R\$)\s*([\d]+(?:\.\d{3})*,\d{2})",
            r"(?:Preço|Valor|Lance)\s*(?:Mínimo|Inicial)?\s*:?\s*R?\$?\s*([\d]+(?:[.,]\d+)+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                value = match.group(1)
                # Remove dots (thousand separators) and replace comma with dot
                value = value.replace(".", "").replace(",", ".")
                try:
                    return float(value)
                except ValueError:
                    continue
        return None

    def _clean_text(self, text: str) -> str:
        """Clean whitespace from text."""
        return re.sub(r'\s+', ' ', text).strip()

    def _parse_date(self, text: str) -> Optional[str]:
        """Try to parse a Brazilian date to ISO format."""
        patterns = [
            (r'(\d{2})/(\d{2})/(\d{4})', lambda m: f"{m.group(3)}-{m.group(2)}-{m.group(1)}"),
            (r'(\d{1,2}) de (\w+) de (\d{4})', None),  # Complex, skip for now
        ]
        for pattern, _ in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
                except (ValueError, IndexError):
                    continue
        return None

    def _normalize_tipo(self, tipo: str) -> str:
        """Normalize auction lot type."""
        tipo_upper = tipo.upper()
        if any(w in tipo_upper for w in ["CELULAR", "IPHONE", "SMARTPHONE", "XIAOMI", "SAMSUNG"]):
            return "CELULAR/ACESSÓRIO"
        if any(w in tipo_upper for w in ["INFORMÁTICA", "INFORMATICA", "NOTEBOOK", "COMPUTADOR",
                                          "SSD", "MEMÓRIA", "RAM", "HD"]):
            return "INFORMÁTICA"
        if any(w in tipo_upper for w in ["VEÍCULO", "VEICULO", "AUTOMÓVEL", "AUTOMOVEL",
                                          "CARRO", "MOTO"]):
            return "VEÍCULO"
        if any(w in tipo_upper for w in ["PERFUME", "COSMÉTICO", "COSMETICO",
                                          "FRAGRÂNCIA", "FRAGRANCIA"]):
            return "PERFUME/COSMÉTICO"
        if any(w in tipo_upper for w in ["BRINQUEDO", "JOGO"]):
            return "BRINQUEDO"
        if any(w in tipo_upper for w in ["ELETRÔNICO", "ELETRONICO", "ELETRODOMÉSTICO",
                                          "ELETRODOMESTICO", "TV", "SOM"]):
            return "ELETRÔNICO"
        if any(w in tipo_upper for w in ["RELÓGIO", "RELOGIO", "JOIA", "BOLSA"]):
            return "LUXO/ACESSÓRIO"
        return "DIVERSOS"

    def _is_permitido_pf(self, text: str) -> bool:
        """Check if lot is available to PF."""
        if not text:
            return True  # Assume PF by default
        text_upper = text.upper()
        if "PESSOA FÍSICA" in text_upper or "PF" in text_upper:
            return True
        if "SOMENTE PESSOA JURÍDICA" in text_upper or "APENAS PJ" in text_upper:
            return False
        return True  # Default: assume PF allowed
