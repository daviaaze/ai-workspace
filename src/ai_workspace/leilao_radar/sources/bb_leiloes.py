"""Parser for Banco do Brasil — leilões de bens retomados."""

from __future__ import annotations

from ai_workspace.leilao_radar.sources.base import BaseSource, SourceResult


class BancoDoBrasilLeiloes(BaseSource):
    """Banco do Brasil — leilões de bens retomados."""

    name = "bb_leiloes"
    label = "Banco do Brasil — Leilões"
    base_url = "https://www.bb.com.br/site/leiloes/"
    check_interval_hours = 24

    def __init__(self, source_id: int | None = None):
        super().__init__(source_id)

    def scrape(self) -> SourceResult:
        result = SourceResult()
        result.source_name = self.name
        return result
