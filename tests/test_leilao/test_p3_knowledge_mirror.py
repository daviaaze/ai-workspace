"""Tests — P3: Knowledge mirror (BC6).

Covers:
1. ``_serialize_lot`` — pure text serialization of lot dicts
2. ``mirror_closed_lots`` — idempotent mirror to pgvector (mocked)
3. ``SearchLotesTool`` — tool wrapper
"""

from __future__ import annotations

from unittest import mock

import pytest


# ──────────────────────────────────────────────────────────────────────────
# 1. _serialize_lot (pure function)
# ──────────────────────────────────────────────────────────────────────────

class TestSerializeLot:
    def test_minimal_lot(self):
        """A lot with only description produces a short block."""
        from ai_workspace.leilao_radar.knowledge_mirror import _serialize_lot

        text = _serialize_lot({"description": "Terreno 500m²"})
        assert "Leilão: Terreno 500m²" in text
        assert "Fonte:" not in text

    def test_full_lot(self):
        """A lot with all fields produces a multi-line block."""
        from ai_workspace.leilao_radar.knowledge_mirror import _serialize_lot

        lot = {
            "description": "Casa em condomínio",
            "edital_number": "2025/001",
            "location": "Campinas/SP",
            "endereco": "Rua das Flores, 123",
            "orgao": "Caixa Econômica",
            "tipo": "Imóvel Residencial",
            "preco_minimo": 250000.0,
            "preco_avaliacao": 320000.0,
            "desconto_percentual": 21.875,
            "data_leilao": "2025-06-15",
            "source": "caixa_imoveis",
            "status": "ativo",
            "url": "https://exemplo.com/lote/1",
        }
        text = _serialize_lot(lot)
        assert "Leilão: Casa em condomínio" in text
        assert "Edital: 2025/001" in text
        assert "Local: Campinas/SP" in text
        assert "Preço mínimo: R$ 250,000.00" in text
        assert "Preço avaliação: R$ 320,000.00" in text
        assert "Desconto: 21.875%" in text

    def test_prefers_description_over_title(self):
        """description takes precedence over title."""
        from ai_workspace.leilao_radar.knowledge_mirror import _serialize_lot

        text = _serialize_lot({"description": "Sala comercial", "title": "Sala na Av Paulista"})
        assert "Leilão: Sala comercial" in text

    def test_falls_back_to_title(self):
        """title is used when description is absent."""
        from ai_workspace.leilao_radar.knowledge_mirror import _serialize_lot

        text = _serialize_lot({"title": "Sala na Av Paulista"})
        assert "Leilão: Sala na Av Paulista" in text

    def test_omits_empty_fields(self):
        """Fields with None/empty values are not rendered."""
        from ai_workspace.leilao_radar.knowledge_mirror import _serialize_lot

        text = _serialize_lot({
            "description": "Terreno",
            "preco_minimo": None,
            "location": "",
        })
        assert "Leilão: Terreno" in text
        assert "Preço mínimo" not in text
        assert "Local" not in text


# ──────────────────────────────────────────────────────────────────────────
# 2. mirror_closed_lots (mocked pgvector)
# ──────────────────────────────────────────────────────────────────────────

def _fake_lot_row(**overrides) -> dict:
    """Build a dict matching the SQLite row format used by mirror_closed_lots."""
    return {
        "id": 42,
        "source_id": 1,
        "codigo_lote": "LOT-001",
        "description": "Terreno 500m² centro",
        "title": None,
        "location": "Campinas/SP",
        "endereco": "Rua ABC, 100",
        "orgao": "Caixa",
        "tipo": "Terreno",
        "preco_minimo": 150000.0,
        "preco_avaliacao": 200000.0,
        "desconto_percentual": 25.0,
        "data_leilao": "2025-06-15",
        "source": "caixa_imoveis",
        "status": "arquivado",
        "url": "https://exemplo.com/42",
        "edital_id": 5,
        "edital_number": "2025/001",
        "edital_title": "Edital Caixa 2025",
        "created_at": "2025-06-10",
        **overrides,
    }


class TestMirrorClosedLots:
    @mock.patch("ai_workspace.leilao_radar.knowledge_mirror.ollama")
    def test_mirrors_new_lots(self, mock_ollama):
        """Lots not yet in pgvector get mirrored with an embedding."""
        from ai_workspace.leilao_radar.knowledge_mirror import mirror_closed_lots

        # Mock ollama.embed
        mock_ollama.embed.return_value = {"embeddings": [[0.1] * 1792]}

        # Mock leilão Database
        fake_lots = [_fake_lot_row()]
        with (
            mock.patch("ai_workspace.leilao_radar.storage.database.Database") as m_db,
            mock.patch("ai_workspace.knowledge.KnowledgeStore") as m_store,
        ):
            # DB connect returns rows
            m_db.return_value.conn.return_value.__enter__.return_value\
                .execute.return_value.fetchall.return_value = fake_lots

            # Store: no existing entries
            c = mock.MagicMock()
            c.fetchall.return_value = []
            m_store.return_value.conn.cursor.return_value = c
            m_store.return_value.add_knowledge.return_value = 1

            result = mirror_closed_lots()

            assert result["mirrored"] == 1
            assert result["total"] == 1
            m_store.return_value.add_knowledge.assert_called_once()
            call_kwargs = m_store.return_value.add_knowledge.call_args[1]
            assert call_kwargs["content_type"] == "leilao_lot"
            # embedding passed
            assert call_kwargs["embedding"] == [0.1] * 1792

    @mock.patch("ai_workspace.leilao_radar.knowledge_mirror.ollama")
    def test_skips_existing_lots(self, mock_ollama):
        """Lots already in pgvector (by lot_uid) are skipped."""
        from ai_workspace.leilao_radar.knowledge_mirror import mirror_closed_lots

        fake_lots = [_fake_lot_row()]
        with (
            mock.patch("ai_workspace.leilao_radar.storage.database.Database") as m_db,
            mock.patch("ai_workspace.knowledge.KnowledgeStore") as m_store,
        ):
            m_db.return_value.conn.return_value.__enter__.return_value\
                .execute.return_value.fetchall.return_value = fake_lots

            # Already mirrored
            c = mock.MagicMock()
            c.fetchall.return_value = [("1_LOT-001",)]
            m_store.return_value.conn.cursor.return_value = c

            result = mirror_closed_lots()

            assert result["mirrored"] == 0
            assert result["total"] == 1
            m_store.return_value.add_knowledge.assert_not_called()


# ──────────────────────────────────────────────────────────────────────────
# 3. SearchLotesTool
# ──────────────────────────────────────────────────────────────────────────

class TestSearchLotesTool:
    @mock.patch("ai_workspace.leilao_radar.knowledge_mirror.search_similar_lots")
    def test_run_returns_formatted_results(self, mock_search):
        """The tool wraps search_similar_lots and formats results."""
        from ai_workspace.leilao_radar.search_lotes_tool import SearchLotesTool

        mock_search.return_value = [
            {
                "id": 1,
                "title": "Terreno 500m²",
                "content": "Leilão: Terreno 500m² centro\nPreço mínimo: R$ 150,000.00",
                "metadata": {"preco_minimo": 150000.0, "location": "Campinas/SP"},
                "similarity": 0.85,
            },
        ]

        tool = SearchLotesTool()
        result = tool._run(query="terreno campinas")

        assert "Terreno 500m²" in result
        assert "similarity: 0.85" in result
        assert "R$ 150,000.00" in result
        assert "Campinas/SP" in result
        mock_search.assert_called_once_with(query="terreno campinas", limit=10)

    def test_run_no_results(self):
        """When no results found, returns a clear message."""
        from ai_workspace.leilao_radar.search_lotes_tool import SearchLotesTool

        with mock.patch(
            "ai_workspace.leilao_radar.knowledge_mirror.search_similar_lots",
            return_value=[],
        ):
            tool = SearchLotesTool()
            result = tool._run(query="não existe")
            assert "No similar lots found" in result
