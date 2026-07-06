"""Parser for Polícia Federal — leilões de bens apreendidos."""

from __future__ import annotations

from ai_workspace.leilao_radar.sources.base import BaseSource, SourceResult


class PoliciaFederalLeiloes(BaseSource):
    """Polícia Federal — leilões de bens apreendidos."""

    name = "pf_leiloes"
    label = "Polícia Federal — Leilões"
    base_url = "https://www.gov.br/pf/pt-br/assuntos/leiloes"
    check_interval_hours = 12

    def __init__(self, source_id: int | None = None):
        super().__init__(source_id)

    def scrape(self) -> SourceResult:
        result = SourceResult()
        result.source_name = self.name
        return result
