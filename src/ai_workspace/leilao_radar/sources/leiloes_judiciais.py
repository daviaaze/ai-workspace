"""Parser for leilões judiciais (Tribunais de Justiça)."""

from __future__ import annotations

from ai_workspace.leilao_radar.sources.base import BaseSource, SourceResult


class LeiloesJudiciais(BaseSource):
    """Leilões judiciais — Tribunais de Justiça estaduais."""

    name = "leiloes_judiciais"
    label = "Leilões Judiciais (TJs)"
    base_url = ""
    check_interval_hours = 6

    def __init__(self, source_id: int | None = None):
        super().__init__(source_id)

    def scrape(self) -> SourceResult:
        result = SourceResult()
        result.source_name = self.name
        return result
