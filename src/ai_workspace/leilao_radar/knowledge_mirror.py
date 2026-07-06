"""Mirror leilão lots into pgvector knowledge_entries for semantic search.

BC6 (Knowledge/Memory) — reads closed/archived lots from the leilão SQLite
operational DB and serializes them into the shared ``knowledge_entries`` table
as ``content_type = 'leilao_lot'`` entries with embeddings for vector search.

Usage
-----
    from ai_workspace.leilao_radar.knowledge_mirror import mirror_closed_lots
    result = mirror_closed_lots()
    print(f"Mirrored {result['mirrored']} lots")
"""

from __future__ import annotations

import json
from typing import Any

from ai_workspace.knowledge.rag import EMBED_MODEL

import ollama  # noqa: E402

# ─── Public API ────────────────────────────────────────────────────────────

def mirror_closed_lots(
    db_url: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Read closed/archived lots from the leilão SQLite and mirror them to
    the pgvector ``knowledge_entries`` table for RAG-based search.

    Idempotent: skips lots whose ``metadata->>'lot_uid'`` already exists.
    """

    from ai_workspace.knowledge import KnowledgeStore
    from ai_workspace.leilao_radar import Config
    from ai_workspace.leilao_radar.storage.database import Database

    # ── source: leilão SQLite ─────────────────────────────────────────
    config = Config.from_env()
    leilao_db = Database(config)

    with leilao_db.conn() as c:
        rows = c.execute("""
            SELECT l.*, e.edital_number, e.title AS edital_title
            FROM lotes l
            LEFT JOIN editais e ON l.edital_id = e.id
            WHERE l.status IN ('arquivado', 'finalizado', 'vencido')
            ORDER BY l.id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        lots = [dict(r) for r in rows]

    if not lots:
        return {"mirrored": 0, "total": 0}

    # ── target: pgvector knowledge store ──────────────────────────────
    store = KnowledgeStore(db_url=db_url)
    store.initialize()

    # Build set of already-mirrored lot_uid values
    c = store.conn.cursor()
    c.execute(
        "SELECT metadata->>'lot_uid' FROM knowledge_entries WHERE content_type = 'leilao_lot'"
    )
    existing = {row[0] for row in c.fetchall() if row[0]}
    c.close()

    new_count = 0
    for lot in lots:
        lot_id = lot.get("codigo_lote") or str(lot["id"])
        source_id = lot.get("source_id", 0)
        lot_uid = f"{source_id}_{lot_id}"

        if lot_uid in existing:
            continue

        content = _serialize_lot(lot)
        title = lot.get("description") or lot.get("title") or f"Lote {lot_id}"

        # ✦ embed via Ollama (same model as DocIndexer)
        resp = ollama.embed(model=EMBED_MODEL, input=[content])
        embedding = resp["embeddings"][0]

        entry_id = store.add_knowledge(
            content=content,
            content_type="leilao_lot",
            title=title,
            source=f"leilao_{lot.get('source_id', 'unknown')}",
            tags=["leilao", "auction", lot.get("source", "unknown")],
            metadata={
                "lot_uid": lot_uid,
                "source_id": source_id,
                "codigo_lote": lot_id,
                "edital": lot.get("edital_number", ""),
                "description": lot.get("description", ""),
                "location": lot.get("location", ""),
                "preco_minimo": lot.get("preco_minimo"),
                "preco_avaliacao": lot.get("preco_avaliacao"),
                "desconto_percentual": lot.get("desconto_percentual"),
                "tipo": lot.get("tipo"),
                "source_name": lot.get("source", ""),
                "url": lot.get("url"),
            },
            embedding=embedding,
        )
        new_count += 1

    store.close()
    return {"mirrored": new_count, "total": len(lots)}


def search_similar_lots(
    query: str,
    db_url: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Semantic search over mirrored leilão lots.

    Uses the same pgvector ``knowledge_entries`` table and embed model
    as the rest of the workspace.

    Args:
        query: Natural-language description of the lot type you're looking for.
        db_url: PostgreSQL URL for the knowledge store.
        limit: Max results (default 10).

    Returns:
        List of matching entries sorted by relevance, each with ``id``,
        ``content``, ``title``, ``similarity``, and ``metadata``.
    """
    from ai_workspace.knowledge import KnowledgeStore

    store = KnowledgeStore(db_url=db_url)
    store.initialize()

    # Embed query
    resp = ollama.embed(model=EMBED_MODEL, input=[f"search_query: {query}"])
    q_emb = resp["embeddings"][0]

    results = store.vector_search(
        query_embedding=q_emb,
        limit=limit,
        content_type="leilao_lot",
    )
    store.close()
    return results


# ─── Internal helpers ──────────────────────────────────────────────────────

def _serialize_lot(lot: dict[str, Any]) -> str:
    """Turn a leilão lot dict into a searchable natural-language description."""
    parts: list[str] = []

    desc = lot.get("description") or lot.get("title") or ""
    if desc:
        parts.append(f"Leilão: {desc}")

    if lot.get("edital_number"):
        parts.append(f"Edital: {lot['edital_number']}")
    if lot.get("location"):
        parts.append(f"Local: {lot['location']}")
    if lot.get("endereco"):
        parts.append(f"Endereço: {lot['endereco']}")
    if lot.get("orgao"):
        parts.append(f"Órgão: {lot['orgao']}")
    if lot.get("tipo"):
        parts.append(f"Tipo: {lot['tipo']}")
    if lot.get("preco_minimo"):
        parts.append(f"Preço mínimo: R$ {lot['preco_minimo']:,.2f}")
    if lot.get("preco_avaliacao"):
        parts.append(f"Preço avaliação: R$ {lot['preco_avaliacao']:,.2f}")
    if lot.get("desconto_percentual"):
        parts.append(f"Desconto: {lot['desconto_percentual']}%")
    if lot.get("data_leilao"):
        parts.append(f"Data leilão: {lot['data_leilao']}")
    if lot.get("source"):
        parts.append(f"Fonte: {lot['source']}")
    if lot.get("status"):
        parts.append(f"Status: {lot['status']}")
    if lot.get("url"):
        parts.append(f"URL: {lot['url']}")

    return "\n".join(parts)
