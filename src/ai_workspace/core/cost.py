"""Semantic cache, budget enforcement, and cost logging for LLM calls."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("aiw.cost")


class SemanticCache:
    """Cache semântico usando pgvector + HNSW.

    Embedding backends (tentados em ordem):
    1. Ollama nomic-embed-text (local, 768-dim, já rodando)
    2. sentence-transformers all-MiniLM-L6-v2 (384-dim, fallback)

    Antes de chamar qualquer LLM, verifica se uma pergunta similar
    já foi respondida (cosine similarity >= threshold).

    Thresholds:
        >= 0.95 → hit exato (retorna sem questionar)
        0.85-0.94 → hit similar (retorna com aviso)
        < 0.85 → miss (chama LLM)
    """

    # Embedding dimensions: auto-detected from first successful embedding
    DEFAULT_EMBEDDING_DIM = 768  # nomic-embed-text default
    DEFAULT_SIMILARITY_THRESHOLD = 0.85

    def __init__(
        self,
        db_url: str | None = None,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        embedding_backend: str = "auto",  # "auto", "ollama", "sentence-transformers"
        ollama_host: str = "http://localhost:11434",
        ollama_embed_model: str = "nomic-embed-text",
    ):
        self.db_url = db_url or os.getenv(
            "AIW_DB_URL", "postgresql:///ai_workspace"
        )
        self.similarity_threshold = similarity_threshold
        self.embedding_backend = embedding_backend
        self.ollama_host = ollama_host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.ollama_embed_model = ollama_embed_model
        self._conn = None
        self._model = None  # lazy load
        self._embedding_dim = None  # auto-detected


    @property
    def conn(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.db_url)
            self._conn.autocommit = True
        return self._conn


    @property
    def embedding_dim(self) -> int:
        """Get embedding dimensions, auto-detecting on first use."""
        if self._embedding_dim is None:
            # Try a quick embedding to detect dimensions
            test_emb = self._embed("test")
            if test_emb:
                self._embedding_dim = len(test_emb)
            else:
                self._embedding_dim = self.DEFAULT_EMBEDDING_DIM
        return self._embedding_dim

    def _embed_ollama(self, text: str) -> list[float] | None:
        """Generate embedding via local Ollama (nomic-embed-text)."""
        try:
            import json as _json
            import urllib.request

            data = _json.dumps({
                "model": self.ollama_embed_model,
                "prompt": text,
            }).encode()
            req = urllib.request.Request(
                f"{self.ollama_host}/api/embeddings",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = _json.loads(resp.read())
                emb = result.get("embedding")
                if emb and len(emb) > 0:
                    return emb
        except Exception as e:
            logger.debug("Ollama embedding failed: %s", e)
        return None

    def _embed_sentence_transformers(self, text: str) -> list[float] | None:
        """Generate embedding via sentence-transformers (fallback)."""
        if self.model is None:
            return None
        try:
            embedding = self.model.encode(text, show_progress_bar=False)
            emb = embedding.tolist()
            # Pad to Ollama dimension if needed (cosine similarity survives padding)
            if self._embedding_dim and len(emb) < self._embedding_dim:
                emb = emb + [0.0] * (self._embedding_dim - len(emb))
            return emb
        except Exception as e:
            logger.debug("sentence-transformers embedding failed: %s", e)
            return None

    @property
    def model(self):
        """Lazy-load sentence-transformers model (~80MB, CPU-only)."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(
                    "sentence-transformers/all-MiniLM-L6-v2"
                )
                logger.info("Embedding model loaded: all-MiniLM-L6-v2")
            except ImportError:
                logger.debug(
                    "sentence-transformers not installed. Will try Ollama."
                )
                return None
        return self._model

    def _embed(self, text: str) -> list[float] | None:
        """Generate embedding vector for text.

        Tries backends in order:
        1. Ollama nomic-embed-text (GPU, 768-dim, free) — fastest
        2. sentence-transformers all-MiniLM-L6-v2 (CPU, 384-dim) — fallback

        Auto-detects dimension from first successful embedding.
        Returns None if no backend is available.
        """
        # 1. Try Ollama (GPU, fast, 768-dim)
        emb = self._embed_ollama(text)
        if emb:
            if self._embedding_dim is None:
                self._embedding_dim = len(emb)
            return emb

        # 2. Fallback: sentence-transformers (CPU, 384-dim)
        emb = self._embed_sentence_transformers(text)
        if emb:
            if self._embedding_dim is None:
                self._embedding_dim = len(emb)
            return emb

        logger.warning(
            "No embedding backend available. "
            "Install Ollama (ollama pull nomic-embed-text) or "
            "pip install sentence-transformers"
        )
        return None

    def _hash_query(self, text: str) -> str:
        """MD5 hash for exact lookup (faster than vector search)."""
        return hashlib.md5(text.encode()).hexdigest()


    def initialize(self) -> None:
        """Create semantic_cache table and HNSW index if they don't exist."""
        c = self.conn.cursor()

        dim = self.embedding_dim  # Auto-detect (768 for nomic-embed-text, 384 for all-MiniLM)
        logger.info("Initializing semantic cache with %d-dim embeddings", dim)

        # DDL can't use psycopg2 parameterization — use Python string formatting
        # (dim is an int we control, not user input, so this is safe)
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS semantic_cache (
                id              SERIAL PRIMARY KEY,
                query_hash      TEXT UNIQUE NOT NULL,
                query_text      TEXT NOT NULL,
                embedding       vector({dim}) NOT NULL,
                response_text   TEXT NOT NULL,
                response_type   TEXT NOT NULL DEFAULT 'chat',
                tokens_saved    INT DEFAULT 0,
                cost_saved      REAL DEFAULT 0.0,
                model_used      TEXT,
                similarity      REAL DEFAULT 1.0,
                created_at      TIMESTAMPTZ DEFAULT NOW(),
                last_hit        TIMESTAMPTZ DEFAULT NOW(),
                hit_count       INT DEFAULT 1,
                metadata        JSONB DEFAULT '{{}}'
            )
        """)

        # HNSW index (superior a IVFFlat para nosso volume)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_semantic_cache_embedding
            ON semantic_cache
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
        """)

        # Unique hash index for O(1) exact lookup
        c.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_semantic_cache_hash
            ON semantic_cache(query_hash)
        """)

        logger.info("Semantic cache tables initialized")


    def get(
        self, query: str, response_type: str = "chat"
    ) -> dict[str, Any] | None:
        """Check cache for a semantically similar query.

        Returns:
            None if no match found.
            dict with keys: response_text, similarity, query_text, hit_count, model_used
        """
        # 1. Exact hash lookup (fast path, no embedding needed)
        query_hash = self._hash_query(query)
        c = self.conn.cursor(cursor_factory=RealDictCursor)
        c.execute(
            "SELECT * FROM semantic_cache WHERE query_hash = %s",
            (query_hash,),
        )
        exact = c.fetchone()
        if exact:
            self._record_hit(exact["id"])
            return {
                "response_text": exact["response_text"],
                "similarity": 1.0,
                "query_text": exact["query_text"],
                "hit_count": exact["hit_count"] + 1,
                "model_used": exact["model_used"],
                "source": "cache_exact",
            }

        # 2. Semantic similarity search (needs embedding)
        embedding = self._embed(query)
        if embedding is None:
            return None  # model not available, skip cache

        c.execute(
            """
            SELECT *,
                   1 - (embedding <=> %(embedding)s::vector) AS similarity
            FROM semantic_cache
            WHERE response_type = %(resp_type)s
              AND 1 - (embedding <=> %(embedding)s::vector) >= %(threshold)s
            ORDER BY embedding <=> %(embedding)s::vector
            LIMIT 1
            """,
            {
                "embedding": str(embedding),
                "resp_type": response_type,
                "threshold": self.similarity_threshold,
            },
        )
        result = c.fetchone()
        if result is None:
            return None

        self._record_hit(result["id"])
        similarity = float(result["similarity"])

        return {
            "response_text": result["response_text"],
            "similarity": similarity,
            "query_text": result["query_text"],
            "hit_count": result["hit_count"] + 1,
            "model_used": result["model_used"],
            "source": "cache_exact" if similarity >= 0.95 else "cache_similar",
        }

    def set(
        self,
        query: str,
        response: str,
        response_type: str = "chat",
        model: str = "unknown",
        tokens_used: int = 0,
        cost: float = 0.0,
        metadata: dict | None = None,
    ) -> int | None:
        """Store a response in the semantic cache.

        Returns the cache entry ID, or None if embedding model unavailable.
        """
        embedding = self._embed(query)
        if embedding is None:
            return None

        query_hash = self._hash_query(query)

        c = self.conn.cursor()
        c.execute(
            """
            INSERT INTO semantic_cache
                (query_hash, query_text, embedding, response_text,
                 response_type, tokens_saved, cost_saved,
                 model_used, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (query_hash) DO UPDATE SET
                last_hit = NOW(),
                hit_count = semantic_cache.hit_count + 1,
                tokens_saved = semantic_cache.tokens_saved + EXCLUDED.tokens_saved,
                cost_saved = semantic_cache.cost_saved + EXCLUDED.cost_saved
            RETURNING id
            """,
            (
                query_hash,
                query,
                str(embedding),
                response,
                response_type,
                tokens_used,
                cost,
                model,
                json.dumps(metadata or {}),
            ),
        )
        result = c.fetchone()
        cache_id = result[0] if result else None

        logger.debug(
            "Cached response hash=%s type=%s tokens_saved=%d cost_saved=$%.6f",
            query_hash[:8],
            response_type,
            tokens_used,
            cost,
        )
        return cache_id

    def _record_hit(self, cache_id: int) -> None:
        """Update last_hit timestamp and hit_count."""
        c = self.conn.cursor()
        c.execute(
            "UPDATE semantic_cache SET last_hit = NOW(), hit_count = hit_count + 1 WHERE id = %s",
            (cache_id,),
        )


    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        c = self.conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT COUNT(*) as total FROM semantic_cache")
        total = c.fetchone()["total"]

        c.execute("SELECT COALESCE(SUM(hit_count), 0) as hits FROM semantic_cache")
        hits = c.fetchone()["hits"]

        c.execute(
            "SELECT COALESCE(SUM(tokens_saved), 0) as tokens, "
            "COALESCE(SUM(cost_saved), 0.0) as cost "
            "FROM semantic_cache"
        )
        savings = c.fetchone()

        return {
            "total_entries": total,
            "total_hits": int(hits),
            "tokens_saved": int(savings["tokens"]),
            "cost_saved": float(savings["cost"]),
        }

    def clear(self, response_type: str | None = None) -> int:
        """Clear cache entries. Returns number of deleted rows."""
        c = self.conn.cursor()
        if response_type:
            c.execute(
                "DELETE FROM semantic_cache WHERE response_type = %s",
                (response_type,),
            )
        else:
            c.execute("DELETE FROM semantic_cache")
        deleted = c.rowcount
        logger.info("Cleared %d cache entries (type=%s)", deleted, response_type or "all")
        return deleted

    def cleanup_expired(self, max_age_days: int = 30) -> int:
        """Remove entries not hit in max_age_days. Returns deleted count."""
        c = self.conn.cursor()
        c.execute(
            "DELETE FROM semantic_cache WHERE last_hit < NOW() - INTERVAL '%s days'",
            (max_age_days,),
        )
        deleted = c.rowcount
        if deleted:
            logger.info("Cleaned up %d expired cache entries", deleted)
        return deleted


class CostLog:
    """Registro de gastos com LLM para dashboard e budget tracking."""

    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or os.getenv("AIW_DB_URL", "postgresql:///ai_workspace")
        self._conn = None

    @property
    def conn(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.db_url)
            self._conn.autocommit = True
        return self._conn

    def initialize(self) -> None:
        """Create cost_log table. No-op if DB is unavailable."""
        try:
            c = self.conn.cursor()
            c.execute("""
                CREATE TABLE IF NOT EXISTS cost_log (
                    id                  SERIAL PRIMARY KEY,
                    timestamp           TIMESTAMPTZ DEFAULT NOW(),
                    provider            TEXT NOT NULL,
                    model               TEXT NOT NULL,
                    task_type           TEXT NOT NULL,
                    input_tokens        INT DEFAULT 0,
                    output_tokens       INT DEFAULT 0,
                    cost                REAL NOT NULL DEFAULT 0.0,
                    cache_hit           BOOLEAN DEFAULT FALSE,
                    cached_response_id  INT REFERENCES semantic_cache(id),
                    query_hash          TEXT,
                    duration_ms         INT,
                    success             BOOLEAN DEFAULT TRUE,
                    error               TEXT
                )
            """)
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_cost_timestamp ON cost_log(timestamp)
            """)
            c.execute("""
                CREATE INDEX IF NOT EXISTS idx_cost_provider ON cost_log(provider)
            """)
            logger.info("Cost log tables initialized")
        except psycopg2.OperationalError:
            logger.warning("PostgreSQL unavailable — cost logging disabled")
            self._conn = None

    def log(
        self,
        provider: str,
        model: str,
        task_type: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        cache_hit: bool = False,
        cached_response_id: int | None = None,
        query_hash: str | None = None,
        duration_ms: int = 0,
        success: bool = True,
        error: str | None = None,
    ) -> int:
        """Record an LLM call cost. Returns log entry ID."""
        c = self.conn.cursor()
        c.execute(
            """
            INSERT INTO cost_log
                (provider, model, task_type, input_tokens, output_tokens,
                 cost, cache_hit, cached_response_id, query_hash,
                 duration_ms, success, error)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                provider, model, task_type, input_tokens, output_tokens,
                cost, cache_hit, cached_response_id, query_hash,
                duration_ms, success, error,
            ),
        )
        return c.fetchone()[0]

    def today_cost(self) -> float:
        """Total cost in last 24 hours. Returns 0.0 if DB is unavailable."""
        try:
            c = self.conn.cursor()
            c.execute(
                "SELECT COALESCE(SUM(cost), 0.0) FROM cost_log "
                "WHERE timestamp > NOW() - INTERVAL '24 hours'"
            )
            return float(c.fetchone()[0])
        except psycopg2.OperationalError:
            return 0.0

    def month_cost(self) -> float:
        """Total cost in last 30 days. Returns 0.0 if DB is unavailable."""
        try:
            c = self.conn.cursor()
            c.execute(
                "SELECT COALESCE(SUM(cost), 0.0) FROM cost_log "
                "WHERE timestamp > NOW() - INTERVAL '30 days'"
            )
            return float(c.fetchone()[0])
        except psycopg2.OperationalError:
            return 0.0


class CircuitBreaker:
    """Circuit breaker per provider — prevents cascading failures.

    Opens after N consecutive failures. Auto-resets after timeout.
    half_open: allows one probe request to test recovery.
    """

    def __init__(
        self,
        provider: str,
        failure_threshold: int = 3,
        reset_timeout: float = 60.0,
    ):
        self.provider = provider
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.state = "closed"  # closed → open → half_open → closed

    def record_failure(self) -> None:
        """Record a failure. Opens circuit if threshold reached."""
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                "Circuit OPEN for %s (%d failures, resets in %ds)",
                self.provider, self.failure_count, self.reset_timeout,
            )

    def record_success(self) -> None:
        """Record a success. Resets circuit if half-open or closed."""
        if self.state == "half_open":
            self.state = "closed"
            self.failure_count = 0
            logger.info("Circuit CLOSED for %s (probe succeeded)", self.provider)
        elif self.state == "closed":
            self.failure_count = 0

    def allow_request(self) -> bool:
        """Check if a request is allowed through.

        - closed: always allow
        - open: check if timeout elapsed → transition to half_open
        - half_open: allow (probe request)
        """
        if self.state == "closed":
            return True
        if self.state == "open":
            elapsed = time.monotonic() - self.last_failure_time
            if elapsed >= self.reset_timeout:
                self.state = "half_open"
                logger.info(
                    "Circuit HALF_OPEN for %s (testing recovery)", self.provider
                )
                return True
            return False
        # half_open: allow one probe
        return True


DEFAULT_CIRCUIT_BREAKERS: dict[str, dict] = {
    "deepseek": {"failure_threshold": 3, "reset_timeout": 60},
    "gemini": {"failure_threshold": 5, "reset_timeout": 30},
    "ollama": {"failure_threshold": 2, "reset_timeout": 120},
}


class BudgetEnforcer:
    """Budget enforcement with per-call, daily, and monthly limits.

    Also manages circuit breakers per provider to prevent cascading
    failures from burning through retry budgets.

    Usage:
        budget = BudgetEnforcer()

        # Before calling LLM:
        estimated = estimate_cost(prompt, model)
        if not budget.can_call(estimated, provider="deepseek"):
            raise BudgetExceededError("Daily budget exceeded")

        # After calling LLM:
        budget.record_call(provider="deepseek", model="deepseek-chat",
                           task_type="research", input_tokens=500,
                           output_tokens=200, cost=0.0001)
    """

    DAILY_BUDGET = 1.00    # $1/day
    MONTHLY_BUDGET = 10.00  # $10/month
    PER_CALL_LIMIT = 0.01   # $0.01/call max

    def __init__(self, db_url: str | None = None):
        self.logger = CostLog(db_url=db_url)
        self._circuits: dict[str, CircuitBreaker] = {}
        for prov, cfg in DEFAULT_CIRCUIT_BREAKERS.items():
            self._circuits[prov] = CircuitBreaker(provider=prov, **cfg)

    def initialize(self) -> None:
        """Ensure cost_log table exists."""
        self.logger.initialize()

    # ── Auto-tuning ────────────────────────────────────────

    def auto_tune(self, dry_run: bool = True) -> dict[str, Any]:
        """Analyze historical cost data and suggest optimal budget limits.

        Uses a 7-day rolling average per provider to set:
        - daily_budget = avg_daily * 1.5  (50% headroom)
        - monthly_budget = avg_daily * 30 * 1.2  (20% headroom)

        Args:
            dry_run: If True, only report suggestions without applying.
                     If False, update the class constants in-place.

        Returns:
            Dict with provider-wise current vs suggested budgets.
        """
        try:
            result: dict[str, Any] = {"providers": {}, "dry_run": dry_run}
            c = self.logger.conn.cursor()

            # Aggregate daily cost per provider over last 30 days
            c.execute("""
                SELECT
                    provider,
                    DATE(timestamp) AS day,
                    SUM(cost) AS daily_cost
                FROM cost_log
                WHERE timestamp > NOW() - INTERVAL '30 days'
                GROUP BY provider, DATE(timestamp)
                ORDER BY provider, day
            """)
            rows = c.fetchall()

            # Group by provider
            from collections import defaultdict
            daily_by_prov: dict[str, list[float]] = defaultdict(list)
            for prov, _day, cost in rows:
                daily_by_prov[prov].append(float(cost))

            for prov, costs in daily_by_prov.items():
                if not costs:
                    continue
                avg_daily = sum(costs) / len(costs)
                suggested_daily = round(avg_daily * 1.5, 2)
                suggested_monthly = round(avg_daily * 30 * 1.2, 2)

                # Get current limits
                cur_daily = getattr(self, f"DAILY_BUDGET_{prov.upper()}", self.DAILY_BUDGET)
                cur_monthly = getattr(self, f"MONTHLY_BUDGET_{prov.upper()}", self.MONTHLY_BUDGET)

                result["providers"][prov] = {
                    "avg_daily_cost": round(avg_daily, 4),
                    "days_with_data": len(costs),
                    "current_daily_budget": cur_daily,
                    "suggested_daily_budget": max(suggested_daily, 0.50),
                    "current_monthly_budget": cur_monthly,
                    "suggested_monthly_budget": max(suggested_monthly, 5.00),
                }

                if not dry_run:
                    # Store as instance overrides (per-provider budgets)
                    setattr(self, f"DAILY_BUDGET_{prov.upper()}", suggested_daily)
                    setattr(self, f"MONTHLY_BUDGET_{prov.upper()}", suggested_monthly)

            result["total_providers"] = len(result["providers"])
            return result
        except Exception as exc:
            logger.warning("Auto-tune failed: %s", exc)
            return {"error": str(exc), "dry_run": dry_run}

    def can_call(
        self,
        estimated_cost: float,
        provider: str = "deepseek",
    ) -> tuple[bool, str]:
        """Check if a call is within budget and circuit is closed.

        Returns (allowed, reason).
        """
        # 1. Circuit breaker
        circuit = self._circuits.get(provider)
        if circuit and not circuit.allow_request():
            return False, f"Circuit OPEN for {provider}"

        # 2. Per-call limit
        if estimated_cost > self.PER_CALL_LIMIT:
            return False, (
                f"Estimated cost ${estimated_cost:.4f} exceeds "
                f"per-call limit ${self.PER_CALL_LIMIT:.2f}"
            )

        # 3. Daily limit (per-provider override if set)
        daily_budget = getattr(self, f"DAILY_BUDGET_{provider.upper()}", self.DAILY_BUDGET)
        today = self.logger.today_cost()
        if today + estimated_cost > daily_budget:
            return False, (
                f"Daily budget would be exceeded: "
                f"${today:.4f} + ${estimated_cost:.4f} > ${daily_budget:.2f}"
            )

        # 4. Monthly limit (per-provider override if set)
        monthly_budget = getattr(self, f"MONTHLY_BUDGET_{provider.upper()}", self.MONTHLY_BUDGET)
        month = self.logger.month_cost()
        if month + estimated_cost > monthly_budget:
            return False, (
                f"Monthly budget would be exceeded: "
                f"${month:.4f} + ${estimated_cost:.4f} > ${monthly_budget:.2f}"
            )

        return True, "ok"


    def record_success(
        self,
        provider: str,
        model: str,
        task_type: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        cache_hit: bool = False,
        duration_ms: int = 0,
    ) -> int:
        """Record a successful LLM call."""
        circuit = self._circuits.get(provider)
        if circuit:
            circuit.record_success()

        return self.logger.log(
            provider=provider,
            model=model,
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            cache_hit=cache_hit,
            duration_ms=duration_ms,
            success=True,
        )

    def record_failure(
        self,
        provider: str,
        model: str,
        task_type: str,
        error: str,
        duration_ms: int = 0,
    ) -> int:
        """Record a failed LLM call. Opens circuit breaker if threshold reached."""
        circuit = self._circuits.get(provider)
        if circuit:
            circuit.record_failure()

        return self.logger.log(
            provider=provider,
            model=model,
            task_type=task_type,
            cost=0.0,
            duration_ms=duration_ms,
            success=False,
            error=error[:500],
        )


    def today_spent(self) -> float:
        """Total spent in last 24 hours."""
        return self.logger.today_cost()

    def month_spent(self) -> float:
        """Total spent in last 30 days."""
        return self.logger.month_cost()

    def budget_summary(self) -> dict:
        """Human-readable budget status."""
        today = self.today_spent()
        month = self.month_spent()
        circuits = {
            prov: cb.state
            for prov, cb in self._circuits.items()
        }
        return {
            "today_spent": today,
            "today_budget": self.DAILY_BUDGET,
            "today_pct": round(today / self.DAILY_BUDGET * 100, 1),
            "month_spent": month,
            "month_budget": self.MONTHLY_BUDGET,
            "month_pct": round(month / self.MONTHLY_BUDGET * 100, 1),
            "circuits": circuits,
        }

    def reset_circuits(self) -> None:
        """Reset all circuit breakers (e.g., after network restore)."""
        for cb in self._circuits.values():
            cb.state = "closed"
            cb.failure_count = 0
        logger.info("All circuit breakers reset")


class BudgetExceededError(Exception):
    """Raised when a call would exceed budget limits."""
    pass


class CostService:
    """Facade combining semantic cache, cost logging, and budget enforcement."""

    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or os.getenv("AIW_DB_URL", "postgresql:///ai_workspace")
        self.cache = SemanticCache(db_url=self.db_url)
        self.logger = CostLog(db_url=self.db_url)
        self.budget = BudgetEnforcer(db_url=self.db_url)

    def initialize(self) -> None:
        """Create all cost-related tables and indexes."""
        self.cache.initialize()
        self.logger.initialize()
