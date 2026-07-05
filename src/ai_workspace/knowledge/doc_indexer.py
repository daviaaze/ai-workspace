"""Documentation Indexer — crawl external docs and index via the RAG pipeline.

Hybrid approach:
  - **Code** does the heavy lifting: fetch, parse (BeautifulSoup), chunk,
    embed (Ollama), and store in the shared ``chunks`` table (pgvector).
  - **LLM** (optional, ``--review``) inspects the first page and suggests
    extraction rules / chunk strategies when standard heuristics are
    insufficient for a particular doc site.

Storage model:
  Each indexed page becomes rows in the ``chunks`` table (the same table
  used by ``DocumentIndexer``) with doc-specific metadata columns
  (``source_url``, ``source_name``, ``page_url``, ``page_title``,
  ``content_hash``).  Semantic search uses pgvector cosine similarity;
  re-indexing is incremental (unchanged pages are skipped via content hash).

Usage::

    # Index
    indexer = DocIndexer()
    await indexer.index("https://docs.crewai.com/")

    # Search (semantic)
    results = indexer.search("model context.")
    for r in results:
        print(r["content"][:200])
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin, urlparse

logger = logging.getLogger("aiw.doc_indexer")

# ── Config ──────────────────────────────────────────────────

DEFAULT_MAX_DEPTH = 2
DEFAULT_MAX_PAGES = 50
DEFAULT_TIMEOUT = 15.0


# ── Data classes ────────────────────────────────────────────


@dataclass
class DocPage:
    """A single fetched documentation page."""

    url: str
    title: str
    text: str
    depth: int = 0


@dataclass
class DocSource:
    """A documentation source (one index command)."""

    name: str
    root_url: str
    pages: list[DocPage] = field(default_factory=list)
    indexed_at: str = ""


# ── Content extraction ───────────────────────────────────────


def _extract_text(html: str, url: str) -> str:
    """Extract clean text from HTML using BeautifulSoup.

    Removes boilerplate (nav/footer/script/style), prefers ``<main>`` /
    ``<article>`` content, preserves paragraph breaks, and caps at 50k chars.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    # Strip boilerplate tags entirely
    for tag in soup(
        ["script", "style", "nav", "footer", "header", "aside", "noscript", "form", "svg"]
    ):
        tag.decompose()

    # Prefer main content containers
    target = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"class": re.compile(r"content|main|doc|markdown", re.I)})
        or soup
    )

    # Insert paragraph breaks after block elements before flattening
    for block in target.find_all(
        ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "section"]
    ):
        block.append("\n\n")

    text = target.get_text(separator=" ")
    # Collapse runs of spaces/tabs (keeps newlines intact for chunking)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()[:50_000]  # cap per page


def _extract_title(html: str, url: str) -> str:
    """Extract <title> (or <h1>) or fall back to URL path."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    if soup.title and soup.title.string:
        return soup.title.string.strip()[:200]
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)[:200]
    path = urlparse(url).path.strip("/")
    return path.replace("/", " — ").replace("-", " ").title() or url


def _extract_links(html: str, base_url: str) -> list[str]:
    """Extract all same-domain links from HTML via BeautifulSoup."""
    from bs4 import BeautifulSoup

    domain = urlparse(base_url).netloc
    soup = BeautifulSoup(html, "lxml")
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full = urljoin(base_url, href)
        # Only same domain, no anchors, no binary files
        if urlparse(full).netloc == domain and not href.startswith("#"):
            if not re.search(r"\.(pdf|zip|tar|gz|png|jpg|jpeg|gif|svg|ico)$", href, re.IGNORECASE):
                links.append(full)
    return links


# ── Crawler ──────────────────────────────────────────────────


class DocCrawler:
    """Crawl documentation sites, fetching and extracting pages.

    BFS traversal within the same domain up to ``max_depth`` from root.
    """

    def __init__(
        self,
        max_depth: int = DEFAULT_MAX_DEPTH,
        max_pages: int = DEFAULT_MAX_PAGES,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.timeout = timeout

    async def crawl(self, root_url: str, name: str = "") -> DocSource:
        """Crawl a documentation site and return structured pages."""

        import httpx

        source = DocSource(name=name or urlparse(root_url).netloc, root_url=root_url)
        visited: set[str] = set()
        queue: list[tuple[str, int]] = [(root_url, 0)]

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            while queue and len(visited) < self.max_pages:
                url, depth = queue.pop(0)
                if url in visited or depth > self.max_depth:
                    continue
                visited.add(url)

                try:
                    resp = await client.get(url, headers={"User-Agent": "aiw-doc-indexer/1.0"})
                    resp.raise_for_status()
                    html = resp.text
                except Exception as exc:
                    logger.debug("Failed to fetch %s: %s", url, exc)
                    continue

                title = _extract_title(html, url)
                text = _extract_text(html, url)
                if text:
                    source.pages.append(DocPage(url=url, title=title, text=text, depth=depth))

                # Queue sub-links (only at depth < max_depth)
                if depth < self.max_depth:
                    for link in _extract_links(html, url):
                        if link not in visited:
                            queue.append((link, depth + 1))

        source.indexed_at = datetime.now(UTC).isoformat()
        logger.info(
            "Crawled %s: %d pages from %s",
            source.name, len(source.pages), root_url,
        )
        return source


# ── LLM review (optional) ───────────────────────────────────


def _review_extraction(source: DocSource) -> list[dict[str, Any]]:
    """Use LLM to review the first page and suggest extraction tweaks.

    Returns a list of suggestions::

        [
            {"type": "css_selector", "selector": ".main-content", "reason": "...)"},
            {"type": "exclude_pattern", "pattern": "tutorial/", "reason": "..."},
        ]

    This is optional (``--review`` flag).  If the LLM is unavailable,
    we return an empty list and default heuristics are used.
    """
    if not source.pages:
        return []

    sample = source.pages[0]
    text_snippet = sample.text[:3000]

    try:
        from ai_workspace.providers import chat_sync

        system = (
            "You are a documentation indexing specialist. Review the first page "
            "of a documentation site and suggest improvements for the extraction:\n"
            "- CSS selectors to target the main content\n"
            "- URL patterns to exclude (e.g. versioned docs, changelogs)\n"
            "- Chunk size adjustments if the content is unusually dense/sparse\n"
            "Return a JSON list of suggestions, or [] if defaults work well."
        )
        user = (
            f"Root URL: {source.root_url}\n"
            f"Page title: {sample.title}\n"
            f"Page URL: {sample.url}\n\n"
            f"Extracted content (first 3k chars):\n{text_snippet}\n\n"
            "What extraction adjustments do you recommend?"
        )
        result = chat_sync(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            provider="ollama",
            model="qwen3:14b",
        )
        import json

        suggestions = json.loads(str(result))
        if isinstance(suggestions, list):
            return suggestions
    except Exception as exc:
        logger.debug("LLM review skipped: %s", exc)

    return []


# ── Indexer — orchestrator ──────────────────────────────────


class DocIndexer:
    """Orchestrates crawl → chunk → embed → store for documentation sources.

    Storage reuses the shared ``chunks`` table (pgvector) from ``rag.py``.
    Doc-specific metadata lives in nullable columns (``source_name``,
    ``page_url``, ``page_title``, ``content_hash``) added by ``_ensure_schema``.
    Re-indexing is incremental: pages whose content hash is unchanged are
    skipped, avoiding redundant embeddings.
    """

    def __init__(self, db_url: str | None = None):
        from ai_workspace.knowledge.rag import DEFAULT_DB_URL

        self.db_url = db_url or DEFAULT_DB_URL
        self.crawler = DocCrawler()
        self._ollama = None
        self._psycopg2 = None
        self._register_vector = None
        self._schema_ready = False

    # ── lazy imports & schema ────────────────────────────────

    def _ensure_imports(self) -> None:
        if self._ollama is None:
            import ollama

            self._ollama = ollama
        if self._psycopg2 is None:
            import psycopg2

            self._psycopg2 = psycopg2
        if self._register_vector is None:
            from pgvector.psycopg2 import register_vector

            self._register_vector = register_vector

    def _ensure_schema(self) -> None:
        """Create the ``chunks`` table (via ``rag.setup_schema``) + doc columns."""
        if self._schema_ready:
            return
        self._ensure_imports()
        from ai_workspace.knowledge.rag import setup_schema

        setup_schema(self.db_url)
        conn = self._psycopg2.connect(self.db_url)
        try:
            self._register_vector(conn)
            cur = conn.cursor()
            for col_def in (
                "source_url TEXT",
                "source_name TEXT",
                "page_url TEXT",
                "page_title TEXT",
                "content_hash TEXT",
            ):
                cur.execute(f"ALTER TABLE chunks ADD COLUMN IF NOT EXISTS {col_def}")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS chunks_source_name_idx "
                "ON chunks (source_name)"
            )
            conn.commit()
        finally:
            conn.close()
        self._schema_ready = True

    def _connect(self):
        """Open a connection with pgvector registered."""
        self._ensure_imports()
        conn = self._psycopg2.connect(self.db_url)
        self._register_vector(conn)
        return conn

    # ── embedding (mirrors rag.DocumentIndexer) ──────────────

    def _embed_chunks(self, texts: list[str]) -> list[list[float]]:
        from ai_workspace.knowledge.rag import EMBED_MODEL

        prepared = [f"search_document: {t}" for t in texts]
        embeddings: list[list[float]] = []
        batch = 20
        for i in range(0, len(prepared), batch):
            batch_texts = prepared[i : i + batch]
            resp = self._ollama.embed(model=EMBED_MODEL, input=batch_texts)
            embeddings.extend(resp.get("embeddings", []))
        return embeddings

    def _embed_query(self, query: str) -> list[float] | None:
        from ai_workspace.knowledge.rag import EMBED_MODEL

        resp = self._ollama.embed(model=EMBED_MODEL, input=[f"search_query: {query}"])
        embs = resp.get("embeddings", [])
        return embs[0] if embs else None

    # ── index ─────────────────────────────────────────────────

    async def index(
        self,
        url: str,
        name: str = "",
        *,
        review: bool = False,
        max_depth: int = DEFAULT_MAX_DEPTH,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> dict[str, Any]:
        """Index a documentation URL.

        Returns a summary dict: name, pages, chunks, skipped, errors, suggestions.
        """
        self._ensure_imports()
        self._ensure_schema()
        self.crawler.max_depth = max_depth
        self.crawler.max_pages = max_pages

        # 1. Crawl
        source = await self.crawler.crawl(url, name=name)

        # 2. Optional LLM review
        suggestions: list[dict[str, Any]] = []
        if review:
            suggestions = _review_extraction(source)

        # 3. Chunk + embed + store (incremental via content hash)
        total_chunks = 0
        errors = 0
        skipped = 0

        conn = None
        try:
            conn = self._connect()
            cur = conn.cursor()

            for page in source.pages:
                try:
                    page_hash = hashlib.sha256(page.text.encode()).hexdigest()[:16]

                    # Incremental: skip pages whose content is unchanged
                    cur.execute(
                        "SELECT content_hash FROM chunks "
                        "WHERE source_name = %s AND page_url = %s LIMIT 1",
                        (source.name, page.url),
                    )
                    row = cur.fetchone()
                    if row and row[0] == page_hash:
                        skipped += 1
                        continue

                    chunks = _chunk_page(page, suggestions)
                    if not chunks:
                        continue

                    embeddings = self._embed_chunks(chunks)
                    if len(embeddings) != len(chunks):
                        raise RuntimeError(
                            f"embedding count mismatch: {len(embeddings)} != {len(chunks)}"
                        )

                    url_hash = hashlib.sha256(page.url.encode()).hexdigest()[:12]
                    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                        chunk_id = f"doc:{source.name}:{url_hash}:{idx}"
                        cur.execute(
                            """
                            INSERT INTO chunks
                                (id, content, source_file, chunk_type,
                                 embedding, ts_vector,
                                 source_url, source_name, page_url,
                                 page_title, content_hash, updated_at)
                            VALUES (%s, %s, %s, %s, %s,
                                    to_tsvector('english', %s),
                                    %s, %s, %s, %s, %s, NOW())
                            ON CONFLICT (id) DO UPDATE SET
                                content = EXCLUDED.content,
                                embedding = EXCLUDED.embedding,
                                ts_vector = EXCLUDED.ts_vector,
                                page_title = EXCLUDED.page_title,
                                content_hash = EXCLUDED.content_hash,
                                updated_at = NOW()
                            """,
                            (
                                chunk_id,
                                chunk,
                                page.url,
                                "paragraph",
                                emb,
                                chunk,
                                source.root_url,
                                source.name,
                                page.url,
                                page.title,
                                page_hash,
                            ),
                        )
                    total_chunks += len(chunks)
                except Exception as exc:
                    logger.warning("Failed to index %s: %s", page.url, exc)
                    errors += 1

            conn.commit()
        except Exception as exc:
            logger.error("Indexing failed: %s", exc)
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

        logger.info(
            "Indexed %s: %d chunks from %d pages (%d skipped, %d errors)",
            source.name, total_chunks, len(source.pages), skipped, errors,
        )

        return {
            "name": source.name,
            "root_url": url,
            "pages": len(source.pages),
            "chunks": total_chunks,
            "skipped": skipped,
            "errors": errors,
            "suggestions": suggestions,
        }

    # ── search (dense pgvector) ─────────────────────────────

    def search(
        self,
        query: str,
        k: int = 5,
        doc_name: str = "",
    ) -> list[dict[str, Any]]:
        """Semantic search over indexed docs via pgvector cosine similarity.

        Filters by ``source_name`` when ``doc_name`` is given.  Returns []
        gracefully if the DB or Ollama is unavailable.
        """
        try:
            self._ensure_imports()
            self._ensure_schema()
            q_emb = self._embed_query(query)
            if q_emb is None:
                return []
        except Exception as exc:
            logger.warning("Doc search embed failed: %s", exc)
            return []

        conn = None
        try:
            conn = self._connect()
            cur = conn.cursor()
            if doc_name:
                cur.execute(
                    """
                    SELECT id, content, page_title, source_name, page_url,
                           1 - (embedding <=> %s) AS score
                    FROM chunks
                    WHERE source_name = %s AND embedding IS NOT NULL
                    ORDER BY embedding <=> %s
                    LIMIT %s
                    """,
                    (q_emb, doc_name, q_emb, k),
                )
            else:
                cur.execute(
                    """
                    SELECT id, content, page_title, source_name, page_url,
                           1 - (embedding <=> %s) AS score
                    FROM chunks
                    WHERE embedding IS NOT NULL AND source_name IS NOT NULL
                    ORDER BY embedding <=> %s
                    LIMIT %s
                    """,
                    (q_emb, q_emb, k),
                )
            return [
                {
                    "id": row[0],
                    "content": row[1][:2000],
                    "page_title": row[2] or "",
                    "doc_name": row[3] or "",
                    "source_url": row[4] or "",
                    "score": float(row[5]) if row[5] is not None else 0.0,
                }
                for row in cur.fetchall()
            ]
        except Exception as exc:
            logger.warning("Doc search failed: %s", exc)
            return []
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    # ── list / remove (operates on the chunks table) ─────────

    def list_sources(self) -> list[dict[str, Any]]:
        """List all indexed documentation sources."""
        try:
            self._ensure_imports()
            self._ensure_schema()
        except Exception as exc:
            logger.warning("Failed to list sources: %s", exc)
            return []

        conn = None
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT source_name, MIN(created_at), COUNT(*)
                FROM chunks
                WHERE source_name IS NOT NULL
                GROUP BY source_name
                ORDER BY source_name
                """
            )
            return [
                {
                    "name": row[0],
                    "first_indexed": row[1].isoformat() if row[1] else "",
                    "chunk_count": row[2],
                }
                for row in cur.fetchall()
                if row[0]
            ]
        except Exception as exc:
            logger.warning("Failed to list sources: %s", exc)
            return []
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def remove_source(self, name: str) -> int:
        """Remove all chunks for a documentation source. Returns count removed."""
        try:
            self._ensure_imports()
            self._ensure_schema()
        except Exception as exc:
            logger.warning("Failed to remove source %s: %s", name, exc)
            return 0

        conn = None
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM chunks WHERE source_name = %s",
                (name,),
            )
            conn.commit()
            return cur.rowcount
        except Exception as exc:
            logger.warning("Failed to remove source %s: %s", name, exc)
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return 0
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


# ── Chunking ─────────────────────────────────────────────────


def _chunk_page(page: DocPage, suggestions: list[dict[str, Any]]) -> list[str]:
    """Chunk a page's text into segments for indexing.

    Honours LLM review suggestions:
      - ``chunk_size`` (int): target characters per chunk (default 3000)
      - ``exclude_pattern`` (regex str): drop paragraphs matching this pattern
    """
    text = page.text
    if not text.strip():
        return []

    # Parse suggestions
    chunk_size = 3000
    exclude_patterns: list[str] = []
    for sug in suggestions or []:
        if not isinstance(sug, dict):
            continue
        if "chunk_size" in sug:
            try:
                chunk_size = max(500, int(sug["chunk_size"]))
            except (TypeError, ValueError):
                pass
        if "exclude_pattern" in sug and sug["exclude_pattern"]:
            exclude_patterns.append(str(sug["exclude_pattern"]))

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]

    # Apply exclude patterns (drop matching paragraphs)
    if exclude_patterns:
        combined = re.compile("|".join(exclude_patterns))
        paragraphs = [p for p in paragraphs if not combined.search(p)]
        if not paragraphs:
            return []

    chunks: list[str] = []
    buffer: list[str] = []
    buf_size = 0

    for para in paragraphs:
        para_size = len(para)
        if buf_size + para_size > chunk_size:
            if buffer:
                chunks.append("\n\n".join(buffer))
            buffer = [para]
            buf_size = para_size
        else:
            buffer.append(para)
            buf_size += para_size

    if buffer:
        chunks.append("\n\n".join(buffer))

    return chunks or [text[:chunk_size]]
