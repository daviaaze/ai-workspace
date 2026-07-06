import asyncio
from typing import Any

from pydantic import BaseModel, Field

try:
    from crewai.tools import BaseTool
except ImportError:
    BaseTool = object


class DocIndexerInput(BaseModel):
    url: str = Field(
        description="URL of the documentation page (or root) to index",
    )
    name: str = Field(
        default="",
        description="Optional label for the documentation source",
    )
    max_pages: int = Field(
        default=10,
        description="Maximum number of pages to index (default 10, max 50)",
        ge=1,
        le=50,
    )
    max_depth: int = Field(
        default=3,
        description="Maximum crawl depth",
        ge=1,
        le=5,
    )


class DocIndexerTool(BaseTool):
    name: str = "Index Documentation"
    description: str = (
        "Crawl and index a documentation website into the knowledge base "
        "(pgvector) for semantic search. Once indexed, the agent can retrieve "
        "relevant docs automatically when answering questions. "
        "Safe to run multiple times on the same URL (incremental — skips "
        "unchanged pages via content hash)."
    )
    args_schema: type[BaseModel] = DocIndexerInput

    def _run(self, url: str, name: str = "",
             max_pages: int = 10, max_depth: int = 3) -> str:
        from ai_workspace.knowledge.doc_indexer import DocIndexer

        async def _do_index():
            indexer = DocIndexer()
            result = await indexer.index(
                url=url,
                name=name or url,
                max_pages=max_pages,
                max_depth=max_depth,
            )
            return result

        result = asyncio.run(_do_index())

        return (
            f"Indexed [bold]{result.get('chunks', 0)}[/] chunks "
            f"from {result.get('pages', 0)} pages "
            f"(name: {result.get('name', url)})."
        )
