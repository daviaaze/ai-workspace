"""Parser for Polícia Rodoviária Federal — leilões de veículos."""

from __future__ import annotations

from ai_workspace.leilao_radar.sources.base import BaseSource, SourceResult


class PRFLeiloes(BaseSource):
    """Polícia Rodoviária Federal — leilões de veículos apreendidos."""

    name = "prf_leiloes"
    label = "PRF — Leilões de Veículos"
    base_url = "https://www.gov.br/prf/pt-br/assuntos/leiloes"
    check_interval_hours = 24

    def __init__(self, source_id: int | None = None):
        super().__init__(source_id)

    def scrape(self) -> SourceResult:
        result = SourceResult()
        result.source_name = self.name
        return result
