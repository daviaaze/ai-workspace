"""CrewAI Tool — search similar leilão lots via semantic (vector) search.

Wraps ``leilao_radar.knowledge_mirror.search_similar_lots`` so the agent
can query for past lots by natural-language description.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

try:
    from crewai.tools import BaseTool
except ImportError:
    BaseTool = object


class SearchLotesInput(BaseModel):
    query: str = Field(
        description="Natural-language description of the lot type you're looking for "
                    "(e.g. 'apartamento em leilão na zona sul', 'terreno em Campinas')",
    )
    limit: int = Field(
        default=10,
        description="Maximum number of results to return",
        ge=1,
        le=100,
    )


class SearchLotesTool(BaseTool):
    name: str = "Search Similar Lots"
    description: str = (
        "Search for leilão (auction) lots by natural-language description. "
        "Returns semantically similar lots from historical data, ranked by relevance. "
        "Useful for finding comparable properties, estimating prices, or identifying "
        "patterns in past auctions."
    )
    args_schema: type[BaseModel] = SearchLotesInput

    def _run(self, query: str, limit: int = 10) -> str:
        from ai_workspace.leilao_radar.knowledge_mirror import search_similar_lots

        results = search_similar_lots(query=query, limit=limit)

        if not results:
            return "No similar lots found."

        lines = [f"Top {len(results)} similar lots:", ""]
        for i, r in enumerate(results, 1):
            meta = r.get("metadata") or {}
            lines.append(
                f"{i}. {r['title']} "
                f"(similarity: {r.get('similarity', 0):.2f})"
            )
            lines.append(f"   {r['content'][:200]}")
            if meta.get("preco_minimo"):
                lines.append(f"   Preço mínimo: R$ {meta['preco_minimo']:,.2f}")
            if meta.get("location"):
                lines.append(f"   Local: {meta['location']}")
            lines.append("")

        return "\n".join(lines)
