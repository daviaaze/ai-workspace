"""Leilão Scraper — CrewAI Tool (thin wrapper over ai_workspace.leilao_radar.engine).

The engine + all sources moved to ai_workspace.leilao_radar.engine.
This file is now just the Tool wrapper that makes them available as a CrewAI tool.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

try:
    from crewai.tools import BaseTool
except ImportError:
    BaseTool = object

from ai_workspace.leilao_radar.engine import (
    LeilaoScraperEngine,
    get_source,
)

class LeilaoScraperInput(BaseModel):
    """Input for LeilaoScraperTool."""
    action: str = Field(
        description="Action: 'scrape' (scrape one source), 'scrape_all' (all sources), "
                    "'query' (search stored), 'summary' (stats), 'export' (to JSON), "
                    "'roi' (best ROI opportunities)"
    )
    source: Optional[str] = Field(
        default=None,
        description="Source name (e.g., 'receita_federal_sle', 'caixa_imoveis')"
    )
    tipo: Optional[str] = Field(default=None, description="Filter by type (e.g., 'CELULAR', 'VEÍCULO')")
    preco_max: Optional[float] = Field(default=None, description="Maximum price filter")
    preco_min: Optional[float] = Field(default=None, description="Minimum price filter")
    limit: int = Field(default=50, description="Max results")
    export_path: Optional[str] = Field(default=None, description="Path for JSON export")


class LeilaoScraperTool(BaseTool):
    """Multi-source auction scraper for Brazilian government and bank auctions.

    Scrapes and monitors:
    - Receita Federal (SLE) - mercadorias apreendidas
    - CAIXA - imóveis retomados
    - Banco do Brasil - bens retomados
    - Polícia Federal - bens apreendidos
    Stores results in a local SQLite database with ROI analysis.

    .. note::

       Source scraping is now managed by the scheduled ``leilao_pipeline``
       DB task.  Use ``scrape_all`` or ``scrape`` here for quick ad-hoc
       checks of the remaining legacy engine sources.
    """

    name: str = "leilao_scraper"
    description: str = (
        "Leilão database query & analysis tool. Use 'query' to search stored "
        "auctions by type/price, 'roi' to find best resale opportunities, "
        "'summary' for stats on stored auctions, 'export' to save as JSON. "
        "Note: source scraping is managed by the scheduled pipeline. "
        "For ad-hoc scraping use 'scrape' with a source name or 'scrape_all'."
    )
    args_schema: Type[BaseModel] = LeilaoScraperInput

    def _run(
        self,
        action: str = "summary",
        source: Optional[str] = None,
        tipo: Optional[str] = None,
        preco_max: Optional[float] = None,
        preco_min: Optional[float] = None,
        limit: int = 50,
        export_path: Optional[str] = None,
    ) -> str:
        engine = LeilaoScraperEngine()

        if action == "scrape_all":
            results = engine.scrape_all()
            if not results:
                return "All sources migrated to BaseSource schedule. Use the pipeline to scrape."
            return self._format_scrape_results(results)

        elif action == "scrape":
            if not source:
                return "Error: 'source' required for scrape action."
            try:
                src = get_source(source)
                result = engine.scrape_source(src)
                return self._format_scrape_results([result])
            except ValueError as e:
                return f"Error: {e}"

        elif action == "query":
            lots = engine.query(
                source=source,
                tipo=tipo,
                preco_max=preco_max,
                preco_min=preco_min,
                limit=limit,
            )
            return self._format_lots(lots)

        elif action == "roi":
            lots = engine.find_best_roi(
                preco_max=preco_max or 50000,
            )
            return self._format_lots(lots, roi=True)

        elif action == "summary":
            summary = engine.get_summary()
            return self._format_summary(summary)

        elif action == "export":
            result = engine.export_json(export_path)
            return result

        return f"Unknown action: {action}. Try: scrape, scrape_all, query, roi, summary, export"

    def _format_scrape_results(self, results: list[dict[str, Any]]) -> str:
        lines = ["## 📊 Leilão Scraper Results\n"]
        for r in results:
            status = "✅" if not r["errors"] else "⚠️"
            lines.append(
                f"{status} **{r['source']}**: "
                f"{r['lots_found']} lots encontrados, "
                f"{r['lots_stored']} armazenados "
                f"({len(r['urls_scraped'])} URLs)"
            )
            if r["errors"]:
                for err in r["errors"][:3]:
                    lines.append(f"   └ ⚠️ {err}")
        return "\n".join(lines)

    def _format_lots(self, lots: list[dict[str, Any]], roi: bool = False) -> str:
        if not lots:
            return "Nenhum lote encontrado com esses filtros."

        lines = [f"## {'🏆 Melhores ROI' if roi else '📋'} Resultados ({len(lots)} lotes)\n"]

        for lot in lots[:30]:
            price = lot.get("preco_minimo", 0)
            price_str = f"R$ {price:,.2f}" if price else "N/D"
            source = lot.get("source", "")
            tipo = lot.get("tipo", "?")
            situacao = lot.get("situacao", "")
            lote = lot.get("lote", "")
            edital = lot.get("edital", "")
            permitido = lot.get("permitido_para", "")

            line = f"- **Lote {lote}** | {tipo} | {price_str}"
            if situacao:
                line += f" | {situacao}"
            if permitido:
                line += f" | {permitido}"
            if source:
                line += f" | _{source}_"
            lines.append(line)

            # Show items if available
            raw = lot.get("raw_data")
            if isinstance(raw, dict) and "itens" in raw:
                total = raw.get("total_itens", 0)
                if total:
                    lines.append(f"  └ {total} itens no lote")

        return "\n".join(lines)

    def _format_summary(self, summary: dict[str, Any]) -> str:
        lines = ["## 📈 Leilão Scraper — Summary\n"]
        lines.append(f"**Total de lotes armazenados:** {summary['total_lots']}\n")

        lines.append("### Por fonte:")
        for src, count in summary.get("by_source", {}).items():
            lines.append(f"- {src}: {count} lotes")
        lines.append("")

        lines.append("### Por tipo (top 20):")
        for tipo, count in list(summary.get("by_type", {}).items())[:20]:
            lines.append(f"- {tipo}: {count}")

        lines.append("")
        lines.append("### Fontes disponíveis:")
        for s in summary.get("sources_available", []):
            lines.append(f"- {s}")

        return "\n".join(lines)
