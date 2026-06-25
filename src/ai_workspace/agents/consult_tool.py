"""
consult_subagent tool — let the agent consult a Partner mid-turn.

Usage in the agent loop::

    from ai_workspace.agents.consult_tool import CONSULT_TOOL_DEF, consult_handler

    tools.append(CONSULT_TOOL_DEF)
    tool_handlers["consult_subagent"] = consult_handler
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("aiw.consult_tool")


CONSULT_TOOL_DEF: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "consult_subagent",
        "description": (
            "Consult a named Partner (AI companion with its own persona, "
            "memory, and knowledge). Use this when you need a second opinion "
            "or specialized expertise from a different perspective."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "partner_name": {
                    "type": "string",
                    "description": "Name or ID of the partner to consult",
                },
                "query": {
                    "type": "string",
                    "description": "The question or task to consult the partner about",
                },
            },
            "required": ["partner_name", "query"],
        },
    },
}


def consult_handler(partner_name: str, query: str, **kwargs: Any) -> str:
    """Handle consult_subagent tool calls from the agent loop.

    Looks up the Partner by name and calls its consult() method,
    which routes through the agent loop with the partner's SOUL.md.
    """
    try:
        from ai_workspace.agents.partner import Partner

        partners = Partner.list_all()
        partner = None
        for p in partners:
            if p.name.lower() == partner_name.lower() or p.partner_id == partner_name:
                partner = p
                break

        if partner is None:
            available = ", ".join(p.name for p in partners) if partners else "(none)"
            return (
                f"Partner '{partner_name}' not found. "
                f"Available partners: {available}"
            )

        logger.info("Consulting partner '%s' with query: %s", partner.name, query[:80])
        response = partner.consult(query)
        return response

    except Exception as exc:
        logger.warning("consult_subagent failed: %s", exc)
        return f"Consultation failed: {exc}"
