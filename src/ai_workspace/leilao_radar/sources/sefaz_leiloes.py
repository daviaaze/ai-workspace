"""Parser for SEFAZ — leilões de receitas estaduais."""

from __future__ import annotations

from ai_workspace.leilao_radar.sources.base import BaseSource, SourceResult


class SefazLeiloes(BaseSource):
    """Secretarias da Fazenda estaduais — leilões fiscais."""

    name = "sefaz_leiloes"
    label = "SEFAZ — Leilões Fiscais"
    base_url = ""
    check_interval_hours = 12

    def __init__(self, source_id: int | None = None):
        super().__init__(source_id)

    def scrape(self) -> SourceResult:
        result = SourceResult()
        result.source_name = self.name
        return result
