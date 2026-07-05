"""Smoke tests for DocCrawler and DocIndexer."""

from __future__ import annotations

from ai_workspace.knowledge.doc_indexer import (
    DocCrawler,
    DocIndexer,
    _chunk_page,
    _extract_links,
    _extract_text,
    _extract_title,
)


class TestExtractText:
    def test_strips_boilerplate_tags(self):
        html = "<html><nav>Skip this</nav><article>Keep this</article></html>"
        assert "Skip" not in _extract_text(html, "http://example.com")

    def test_strips_html_tags(self):
        html = "<p>Hello <b>world</b></p>"
        result = _extract_text(html, "http://example.com")
        assert "Hello world" in result

    def test_caps_at_50k(self):
        html = "<p>" + "x" * 60_000 + "</p>"
        result = _extract_text(html, "http://example.com")
        assert len(result) <= 50_000


class TestExtractTitle:
    def test_from_title_tag(self):
        html = "<html><title>Docs — Getting Started</title></html>"
        assert _extract_title(html, "") == "Docs — Getting Started"

    def test_fallback_to_url_path(self):
        html = "<html><body>No title</body></html>"
        title = _extract_title(html, "http://example.com/getting-started")
        assert "Getting Started" in title


class TestExtractLinks:
    def test_filters_same_domain(self):
        html = '<a href="/page1">Link</a><a href="http://other.com">Other</a>'
        links = _extract_links(html, "http://example.com")
        assert all("example.com" in l for l in links)
        assert len(links) == 1

    def test_skips_binary_files(self):
        html = '<a href="/doc.pdf">PDF</a><a href="/page">Page</a>'
        links = _extract_links(html, "http://example.com")
        assert "/page" in links[0]
        assert len(links) == 1


class TestChunkPage:
    def test_single_short_page(self):
        from ai_workspace.knowledge.doc_indexer import DocPage
        page = DocPage(url="http://example.com", title="Test", text="Hello world")
        chunks = _chunk_page(page, [])
        assert len(chunks) == 1
        assert "Hello world" in chunks[0]

    def test_long_page_split_into_chunks(self):
        from ai_workspace.knowledge.doc_indexer import DocPage
        # ~3000 chars per chunk; create text with 5 long paragraphs
        paras = []
        for i in range(5):
            paras.append(f"Paragraph {i}. " + "word " * 200)
        text = "\n\n".join(paras)
        page = DocPage(url="http://example.com", title="Test", text=text)
        chunks = _chunk_page(page, [])
        assert len(chunks) >= 2

    def test_empty_text_returns_empty(self):
        from ai_workspace.knowledge.doc_indexer import DocPage
        page = DocPage(url="http://example.com", title="Test", text="")
        chunks = _chunk_page(page, [])
        assert chunks == []


class TestDocCrawler:
    def test_crawler_default_config(self):
        crawler = DocCrawler()
        assert crawler.max_depth == 2
        assert crawler.max_pages == 50
        assert crawler.timeout == 15.0

    def test_crawl_empty_url(self):
        """Crawler handles invalid URLs gracefully."""
        import asyncio
        crawler = DocCrawler(max_depth=0, max_pages=5)
        source = asyncio.run(crawler.crawl("http://invalid.local/test"))
        assert source.name == "invalid.local"
        # Should not crash; pages may be 0 due to failed fetch
        assert isinstance(source.pages, list)


class TestDocIndexer:
    def test_indexer_instantiation(self):
        indexer = DocIndexer()
        assert indexer is not None

    def test_search_returns_empty_on_missing_db(self):
        """search returns empty if DB is unreachable (no crash)."""
        indexer = DocIndexer()
        results = indexer.search("test query")
        assert results == []


# ── Helpers for mocked DocIndexer ───────────────────────────


def _mock_indexer():
    """Build a DocIndexer with DB/ollama deps pre-mocked, schema marked ready."""
    from unittest.mock import MagicMock

    indexer = DocIndexer(db_url="postgresql:///mock")
    indexer._ollama = MagicMock()
    indexer._psycopg2 = MagicMock()
    indexer._register_vector = MagicMock()
    indexer._schema_ready = True
    return indexer


def _mock_conn():
    """A MagicMock psycopg2 connection with a default cursor."""
    from unittest.mock import MagicMock

    cur = MagicMock()
    cur.fetchone.return_value = None
    cur.fetchall.return_value = []
    cur.rowcount = 0
    conn = MagicMock()
    conn.cursor.return_value = cur
    conn.closed = False
    return conn, cur


# ── bs4 extraction (additional coverage) ────────────────────


class TestExtractTextBs4:
    def test_prefers_main_content(self):
        """Content inside <main> is extracted; outside content is dropped."""
        html = (
            "<html><body>"
            "<div>Sidebar noise</div>"
            "<main><p>Important docs</p></main>"
            "</body></html>"
        )
        result = _extract_text(html, "http://example.com")
        assert "Important docs" in result

    def test_strips_script_content(self):
        """Script text is not present in the extracted output."""
        html = "<html><script>alert('xss')</script><p>Real text</p></html>"
        result = _extract_text(html, "http://example.com")
        assert "alert" not in result
        assert "Real text" in result

    def test_preserves_paragraph_breaks(self):
        """Block elements produce double-newline separators."""
        html = "<p>Para one</p><p>Para two</p>"
        result = _extract_text(html, "http://example.com")
        assert "\n\n" in result


class TestExtractTitleBs4:
    def test_h1_fallback(self):
        """When no <title>, fall back to <h1>."""
        html = "<html><body><h1>Page Heading</h1></body></html>"
        assert _extract_title(html, "http://example.com") == "Page Heading"


class TestExtractLinksBs4:
    def test_resolves_relative_links(self):
        """Relative hrefs are resolved against the base URL."""
        html = '<a href="docs/intro">Intro</a>'
        links = _extract_links(html, "http://example.com/guide")
        assert "http://example.com/docs/intro" in links


# ── Chunking with LLM suggestions ───────────────────────────


class TestChunkPageSuggestions:
    def test_chunk_size_suggestion(self):
        """Suggestions with chunk_size produce smaller chunks."""
        from ai_workspace.knowledge.doc_indexer import DocPage

        text = "\n\n".join([f"Paragraph {i} " + "x" * 200 for i in range(10)])
        page = DocPage(url="http://example.com", title="T", text=text)

        default_chunks = _chunk_page(page, [])
        small_chunks = _chunk_page(page, [{"chunk_size": 300}])

        assert len(small_chunks) > len(default_chunks)
        for c in small_chunks:
            assert len(c) <= 600  # rough upper bound (one big para + buffer)

    def test_exclude_pattern_suggestion(self):
        """Paragraphs matching exclude_pattern are dropped."""
        from ai_workspace.knowledge.doc_indexer import DocPage

        text = "Keep this.\n\nADVERTISEMENT buy now\n\nAlso keep this."
        page = DocPage(url="http://example.com", title="T", text=text)
        chunks = _chunk_page(page, [{"exclude_pattern": r"ADVERTISEMENT"}])
        joined = " \n\n".join(chunks)
        assert "buy now" not in joined
        assert "Keep this" in joined

    def test_invalid_chunk_size_ignored(self):
        """Non-int chunk_size falls back to default (no crash)."""
        from ai_workspace.knowledge.doc_indexer import DocPage

        page = DocPage(url="http://example.com", title="T", text="Short text.")
        chunks = _chunk_page(page, [{"chunk_size": "huge"}])
        assert len(chunks) == 1
        assert "Short text" in chunks[0]

    def test_exclude_all_returns_empty(self):
        """If all paragraphs match exclude_pattern, return []."""
        from ai_workspace.knowledge.doc_indexer import DocPage

        page = DocPage(url="http://example.com", title="T", text="spam\n\nmore spam")
        chunks = _chunk_page(page, [{"exclude_pattern": r"spam"}])
        assert chunks == []

    def test_non_dict_suggestions_ignored(self):
        """Non-dict suggestion entries are skipped gracefully."""
        from ai_workspace.knowledge.doc_indexer import DocPage

        page = DocPage(url="http://example.com", title="T", text="Hello world.")
        chunks = _chunk_page(page, ["not a dict", 42, None, {"chunk_size": 1000}])
        assert len(chunks) == 1


# ── Embedding (mocked ollama) ───────────────────────────────


class TestEmbedding:
    def test_embed_chunks_calls_ollama(self):
        """_embed_chunks calls ollama.embed with search_document prefix."""
        indexer = _mock_indexer()
        indexer._ollama.embed.return_value = {
            "embeddings": [[0.1] * 4, [0.2] * 4]
        }
        result = indexer._embed_chunks(["hello", "world"])
        assert len(result) == 2
        indexer._ollama.embed.assert_called_once()
        call_args = indexer._ollama.embed.call_args
        prepared = call_args.kwargs.get("input") or call_args.args[1]
        assert all(s.startswith("search_document: ") for s in prepared)

    def test_embed_chunks_batches_at_20(self):
        """25 texts produce 2 batches (20 + 5)."""
        indexer = _mock_indexer()
        indexer._ollama.embed.side_effect = [
            {"embeddings": [[0.1] * 4] * 20},
            {"embeddings": [[0.1] * 4] * 5},
        ]
        result = indexer._embed_chunks([f"t{i}" for i in range(25)])
        assert len(result) == 25
        assert indexer._ollama.embed.call_count == 2

    def test_embed_query_returns_vector(self):
        """_embed_query returns the first embedding with search_query prefix."""
        indexer = _mock_indexer()
        indexer._ollama.embed.return_value = {"embeddings": [[0.5] * 8]}
        vec = indexer._embed_query("how to configure")
        assert vec == [0.5] * 8
        call_args = indexer._ollama.embed.call_args
        prepared = call_args.kwargs.get("input") or call_args.args[1]
        assert prepared[0].startswith("search_query: ")

    def test_embed_query_returns_none_on_empty(self):
        """No embeddings in response → None."""
        indexer = _mock_indexer()
        indexer._ollama.embed.return_value = {"embeddings": []}
        assert indexer._embed_query("test") is None


# ── Schema setup (mocked psycopg2) ─────────────────────────


class TestEnsureSchema:
    def test_ensure_schema_idempotent(self):
        """Second call to _ensure_schema is a no-op (schema_ready flag)."""
        indexer = _mock_indexer()
        # _schema_ready already True → should do nothing
        indexer._ensure_schema()
        indexer._psycopg2.connect.assert_not_called()

    def test_ensure_schema_runs_alters(self):
        """When schema not ready, ALTER TABLE statements are executed."""
        from unittest.mock import patch

        indexer = _mock_indexer()
        indexer._schema_ready = False
        conn, cur = _mock_conn()
        indexer._psycopg2.connect.return_value = conn

        with patch("ai_workspace.knowledge.rag.setup_schema") as mock_setup:
            indexer._ensure_schema()

        mock_setup.assert_called_once_with("postgresql:///mock")
        # ALTER TABLE should have been executed for each column + index
        assert cur.execute.call_count >= 5
        conn.close.assert_called_once()
        assert indexer._schema_ready is True


# ── Index (incremental + storage) ───────────────────────────


class TestDocIndexerIndex:
    def _make_source(self, pages):
        from ai_workspace.knowledge.doc_indexer import DocSource

        return DocSource(name="test-docs", root_url="http://test.local", pages=pages)

    def test_index_skips_unchanged_page(self):
        """Pages whose content_hash matches are skipped (incremental)."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from ai_workspace.knowledge.doc_indexer import DocPage

        indexer = _mock_indexer()
        conn, cur = _mock_conn()
        indexer._psycopg2.connect.return_value = conn
        indexer._ollama.embed.return_value = {"embeddings": [[0.1] * 4]}

        page = DocPage(url="http://test.local/p1", title="P1", text="Some content here")
        page_hash = __import__("hashlib").sha256(page.text.encode()).hexdigest()[:16]

        # Simulate existing page with same hash → should be skipped
        cur.fetchone.return_value = (page_hash,)

        with patch.object(indexer.crawler, "crawl", new=AsyncMock(return_value=self._make_source([page]))):
            result = asyncio.run(indexer.index("http://test.local"))

        assert result["skipped"] == 1
        assert result["chunks"] == 0

    def test_index_stores_new_chunks(self):
        """New pages are chunked, embedded, and stored via INSERT."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from ai_workspace.knowledge.doc_indexer import DocPage

        indexer = _mock_indexer()
        conn, cur = _mock_conn()
        indexer._psycopg2.connect.return_value = conn
        # Dynamic mock: return exactly as many embeddings as texts passed in
        indexer._ollama.embed.side_effect = lambda model, input, **kw: {
            "embeddings": [[0.1] * 4] * len(input)
        }

        page = DocPage(
            url="http://test.local/p1",
            title="P1",
            text="Para one.\n\nPara two.",
        )

        with patch.object(indexer.crawler, "crawl", new=AsyncMock(return_value=self._make_source([page]))):
            result = asyncio.run(indexer.index("http://test.local"))

        assert result["chunks"] >= 1
        assert result["errors"] == 0
        # At least one INSERT should have been executed
        insert_calls = [
            c for c in cur.execute.call_args_list if "INSERT INTO chunks" in str(c)
        ]
        assert len(insert_calls) >= 1
        conn.commit.assert_called_once()

    def test_index_handles_embed_mismatch(self):
        """Embedding count mismatch → page counted as error, not crash."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from ai_workspace.knowledge.doc_indexer import DocPage

        indexer = _mock_indexer()
        conn, cur = _mock_conn()
        indexer._psycopg2.connect.return_value = conn
        # Return fewer embeddings than chunks (fixed 1 regardless of input)
        indexer._ollama.embed.return_value = {"embeddings": [[0.1] * 4]}

        # Large paragraphs force 2+ chunks (each > 2500 chars)
        page = DocPage(
            url="http://test.local/p1",
            title="P1",
            text="A" + "x" * 2500 + "\n\nB" + "x" * 2500,
        )

        with patch.object(indexer.crawler, "crawl", new=AsyncMock(return_value=self._make_source([page]))):
            result = asyncio.run(indexer.index("http://test.local"))

        assert result["errors"] >= 1
        assert result["chunks"] == 0

    def test_index_returns_suggestions_when_review(self):
        """review=True populates suggestions in the result."""
        import asyncio
        from unittest.mock import AsyncMock, patch

        from ai_workspace.knowledge.doc_indexer import DocPage

        indexer = _mock_indexer()
        conn, cur = _mock_conn()
        indexer._psycopg2.connect.return_value = conn
        indexer._ollama.embed.return_value = {"embeddings": [[0.1] * 4]}

        page = DocPage(url="http://test.local/p1", title="P1", text="Hello.")

        with patch.object(indexer.crawler, "crawl", new=AsyncMock(return_value=self._make_source([page]))):
            with patch("ai_workspace.knowledge.doc_indexer._review_extraction", return_value=[{"chunk_size": 500}]):
                result = asyncio.run(indexer.index("http://test.local", review=True))

        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["chunk_size"] == 500


# ── Vector search (mocked embed + DB) ───────────────────────


class TestDocIndexerSearch:
    def test_search_returns_formatted_results(self):
        """search returns dicts with id, content, score, metadata."""
        indexer = _mock_indexer()
        conn, cur = _mock_conn()
        indexer._psycopg2.connect.return_value = conn
        indexer._ollama.embed.return_value = {"embeddings": [[0.1] * 4]}

        cur.fetchall.return_value = [
            ("doc:test:abc:0", "Chunk content here", "Page Title", "test-docs", "http://test.local/p1", 0.92),
        ]

        results = indexer.search("how to configure")
        assert len(results) == 1
        assert results[0]["id"] == "doc:test:abc:0"
        assert results[0]["content"] == "Chunk content here"
        assert results[0]["page_title"] == "Page Title"
        assert results[0]["doc_name"] == "test-docs"
        assert results[0]["score"] == 0.92

    def test_search_filters_by_doc_name(self):
        """doc_name adds a WHERE source_name = %s filter."""
        indexer = _mock_indexer()
        conn, cur = _mock_conn()
        indexer._psycopg2.connect.return_value = conn
        indexer._ollama.embed.return_value = {"embeddings": [[0.1] * 4]}

        indexer.search("query", doc_name="specific-doc")

        sql = str(cur.execute.call_args)
        assert "source_name = %s" in sql
        assert "specific-doc" in str(cur.execute.call_args.args)

    def test_search_returns_empty_on_embed_failure(self):
        """If embedding fails, search returns [] gracefully."""
        indexer = _mock_indexer()
        indexer._ollama.embed.return_value = {"embeddings": []}

        results = indexer.search("query")
        assert results == []

    def test_search_returns_empty_on_db_error(self):
        """If DB query fails, search returns [] gracefully."""
        indexer = _mock_indexer()
        indexer._ollama.embed.return_value = {"embeddings": [[0.1] * 4]}
        indexer._psycopg2.connect.side_effect = RuntimeError("DB down")

        results = indexer.search("query")
        assert results == []


# ── List / remove sources ───────────────────────────────────


class TestDocIndexerListRemove:
    def test_list_sources_returns_grouped(self):
        """list_sources returns sources grouped by source_name."""
        from datetime import datetime

        indexer = _mock_indexer()
        conn, cur = _mock_conn()
        indexer._psycopg2.connect.return_value = conn

        cur.fetchall.return_value = [
            ("crewai-docs", datetime(2026, 1, 1), 42),
            ("fastapi-docs", datetime(2026, 2, 1), 18),
        ]

        sources = indexer.list_sources()
        assert len(sources) == 2
        assert sources[0]["name"] == "crewai-docs"
        assert sources[0]["chunk_count"] == 42
        assert sources[1]["name"] == "fastapi-docs"

    def test_list_sources_empty_on_error(self):
        """DB error → list_sources returns []."""
        indexer = _mock_indexer()
        indexer._psycopg2.connect.side_effect = RuntimeError("DB down")

        assert indexer.list_sources() == []

    def test_remove_source_returns_count(self):
        """remove_source returns the rowcount of deleted chunks."""
        indexer = _mock_indexer()
        conn, cur = _mock_conn()
        indexer._psycopg2.connect.return_value = conn
        cur.rowcount = 7

        count = indexer.remove_source("old-docs")
        assert count == 7

        sql = str(cur.execute.call_args)
        assert "DELETE FROM chunks" in sql
        assert "source_name = %s" in sql
        conn.commit.assert_called_once()

    def test_remove_source_handles_error(self):
        """DB error during removal → returns 0, rollback called."""
        indexer = _mock_indexer()
        conn, cur = _mock_conn()
        indexer._psycopg2.connect.return_value = conn
        cur.execute.side_effect = RuntimeError("DB error")

        count = indexer.remove_source("bad-docs")
        assert count == 0
        conn.rollback.assert_called_once()
