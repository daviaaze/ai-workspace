"""
RAG (Retrieval Augmented Generation) tool for AgentLoop integration.

Provides retrieve_knowledge as a callable tool that agents can use
to search the workspace knowledge base before answering questions.

Refs: SPEC_RAG.md
"""

from __future__ import annotations

from typing import Any

from ai_workspace.tools.base import Tool

_RAG_TOOL_DEFINITION: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "retrieve_knowledge",
        "description": (
            "Search the AI Workspace knowledge base for relevant code, "
            "documentation, and context. Use this BEFORE answering "
            "technical questions about the codebase. Returns the most "
            "relevant chunks with source file references."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query. Use specific technical terms, "
                        "function names, or module paths for best results."
                    ),
                },
                "k": {
                    "type": "integer",
                    "description": "Number of results (default 5, max 10)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}


def handle_retrieve_knowledge(query: str, k: int = 5) -> str:
    """Retrieve relevant context from the workspace knowledge base.

    Uses hybrid search (dense vector + BM25 + RRF merge) against
    the pgvector-indexed codebase.

    Args:
        query: Search query.
        k: Number of results (default 5).

    Returns:
        Formatted context string with source references, or
        a message indicating no results or that the index is empty.
    """
    try:
        from ai_workspace.knowledge import retrieve_context
        context = retrieve_context(query, k=min(k, 10))
        if context:
            return context
        return (
            "No matching documents found for query: "
            f"'{query}'. The workspace may not be indexed. "
            "Run 'aiw kb index' to index the codebase."
        )
    except Exception as exc:
        return (
            f"Knowledge retrieval failed: {exc}. "
            "The RAG database may not be available. "
            "Answer using your training knowledge instead."
        )


def get_rag_tool() -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (tool_definition, tool_handler) for AgentLoop integration.

    Usage::

        tool_def, handler = get_rag_tool()
        params = LoopParams(
            task="Explain how the agent loop works",
            tools=[tool_def],
            tool_handlers={"retrieve_knowledge": handler},
        )
    """
    return _RAG_TOOL_DEFINITION, {"retrieve_knowledge": handle_retrieve_knowledge}


class RetrieveKnowledgeCrewTool(Tool):
    """crewAI-compatible RAG tool.

    Registered in get_all_tools() so every agent has workspace
    knowledge access by default.
    """

    name: str = "retrieve_knowledge"
    description: str = (
        "Search the AI Workspace knowledge base for relevant code, "
        "documentation, and context. Use this BEFORE answering "
        "technical questions about the codebase. Returns the most "
        "relevant chunks with source file references."
    )

    def _run(self, query: str, k: int = 5) -> str:
        return handle_retrieve_knowledge(query=query, k=k)
