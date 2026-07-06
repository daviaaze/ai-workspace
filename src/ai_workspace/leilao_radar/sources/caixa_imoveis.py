"""Parser for Caixa — imóveis retomados.

The Caixa leilão site is JS-heavy and requires browser rendering.
Current implementation is a scaffold — actual parsing needs
ScrapingChain with HeadlessBrowser or Crawl4AI.
"""

from __future__ import annotations

from ai_workspace.leilao_radar.sources.base import BaseSource, SourceResult


class CaixaImoveis(BaseSource):
    """Caixa Econômica Federal — imóveis retomados (JS-heavy)."""

    name = "caixa_imoveis"
    label = "Caixa — Imóveis Retomados"
    base_url = "https://www.caixa.gov.br/leiloes/"
    check_interval_hours = 24

    def __init__(self, source_id: int | None = None):
        super().__init__(source_id)

    def scrape(self) -> SourceResult:
        result = SourceResult()
        result.source_name = self.name
        return result
