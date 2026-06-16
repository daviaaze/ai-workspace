"""
Source Reputation Service — CRED-1 + empirical tracking + cross-reference.

Fase 1: Toda fonte recebe score 0.0-1.0. Fontes < 0.4 são ignoradas.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("aiw.sources")


def extract_domain(url: str) -> str:
    """Normalize URL to domain (e.g., 'https://sub.example.com/page' → 'example.com')."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www prefix
        if domain.startswith("www."):
            domain = domain[4:]
        # Remove port
        if ":" in domain:
            domain = domain.split(":")[0]
        return domain
    except Exception:
        return url.lower().strip()


class SourceReputationService:
    """Gerencia reputação de fontes: CRED-1 seed, tracking empírico, cross-reference."""

    # Weights for composite score
    W_CRED1 = 0.40
    W_EMPIRICAL = 0.30
    W_CROSSREF = 0.20
    W_USER = 0.10

    # Thresholds
    THRESHOLD_TRUST = 0.60   # >= use normally
    THRESHOLD_WARN = 0.40    # >= use with warning
                               # < 0.40 → ignore

    # Manual seed of known-reliable domains (CRED-1 focuses on misinformation)
    RELIABLE_SEED = {
        "arxiv.org": 0.95,
        "github.com": 0.90,
        "wikipedia.org": 0.85,
        "reuters.com": 0.95,
        "apnews.com": 0.95,
        "nature.com": 0.95,
        "paperswithcode.com": 0.90,
        "huggingface.co": 0.85,
        "python.org": 0.90,
        "docs.python.org": 0.95,
        "nixos.org": 0.85,
        "kernel.org": 0.90,
        "stackoverflow.com": 0.75,
        "medium.com": 0.50,
        "dev.to": 0.65,
        "reddit.com": 0.40,
        "w3.org": 0.90,
        "opensource.org": 0.90,
        "apache.org": 0.90,
        "mit.edu": 0.90,
    }

    def __init__(self, db_url: str | None = None):
        self.db_url = db_url or os.getenv("AIW_DB_URL", "postgresql:///ai_workspace")
        self._conn = None

    @property
    def conn(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.db_url)
            self._conn.autocommit = True
        return self._conn

    # ── DB initialization ──────────────────────────────────

    def initialize(self) -> None:
        """Create source reputation tables."""
        c = self.conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS domain_reputation (
                domain              TEXT PRIMARY KEY,
                cred1_score         REAL,
                cred1_category      TEXT,
                cred1_sources       INT DEFAULT 0,
                cred1_last_updated  TIMESTAMPTZ,
                credinet_credible   BOOLEAN,
                credinet_last_checked TIMESTAMPTZ,
                times_used          INT DEFAULT 0,
                times_accurate      INT DEFAULT 0,
                times_inaccurate    INT DEFAULT 0,
                accuracy_rate       REAL,
                cross_ref_score     REAL,
                cross_ref_samples   INT DEFAULT 0,
                user_rating         REAL,
                user_flags          INT DEFAULT 0,
                user_endorsements   INT DEFAULT 0,
                composite_score     REAL DEFAULT 0.5,
                composite_updated   TIMESTAMPTZ DEFAULT NOW(),
                first_seen          TIMESTAMPTZ DEFAULT NOW(),
                last_seen           TIMESTAMPTZ DEFAULT NOW(),
                notes               TEXT
            )
        """)

        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_domain_composite
            ON domain_reputation(composite_score)
        """)
        c.execute("""
            CREATE INDEX IF NOT EXISTS idx_domain_cred1
            ON domain_reputation(cred1_score)
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS source_tracking (
                id              SERIAL PRIMARY KEY,
                url             TEXT NOT NULL,
                domain          TEXT NOT NULL REFERENCES domain_reputation(domain),
                title           TEXT DEFAULT '',
                snippet         TEXT DEFAULT '',
                score_at_time   REAL DEFAULT 0.5,
                first_used      TIMESTAMPTZ DEFAULT NOW(),
                last_used       TIMESTAMPTZ DEFAULT NOW(),
                times_used      INT DEFAULT 1,
                was_accurate    BOOLEAN,
                verified_by     TEXT DEFAULT '',
                research_id     INT,
                sub_question    TEXT DEFAULT ''
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_source_domain ON source_tracking(domain)")

        c.execute("""
            CREATE TABLE IF NOT EXISTS cross_reference_log (
                id                  SERIAL PRIMARY KEY,
                research_id         INT,
                claim_hash          TEXT NOT NULL,
                claim_summary       TEXT NOT NULL,
                sources_agreeing    INT DEFAULT 0,
                sources_disagreeing INT DEFAULT 0,
                total_sources       INT DEFAULT 0,
                agreement_ratio     REAL DEFAULT 0.0,
                consensus           TEXT DEFAULT '',
                created_at          TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_crossref_claim ON cross_reference_log(claim_hash)")

        logger.info("Source reputation tables initialized")

    # ── CRED-1 seeding ─────────────────────────────────────

    def seed_cred1(self, dataset_path: str | None = None) -> int:
        """Load CRED-1 dataset into domain_reputation. Returns count of domains seeded."""
        if dataset_path is None:
            dataset_path = os.path.expanduser("~/.ai-workspace/cred1_current.json")

        if not os.path.exists(dataset_path):
            logger.warning("CRED-1 dataset not found at %s", dataset_path)
            return 0

        with open(dataset_path) as f:
            data = json.load(f)

        c = self.conn.cursor()
        count = 0
        for domain, info in data.items():
            c.execute("""
                INSERT INTO domain_reputation (
                    domain, cred1_score, cred1_category, cred1_sources,
                    composite_score, cred1_last_updated, first_seen
                ) VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (domain) DO UPDATE SET
                    cred1_score = EXCLUDED.cred1_score,
                    cred1_category = EXCLUDED.cred1_category,
                    cred1_sources = EXCLUDED.cred1_sources,
                    composite_score = EXCLUDED.composite_score,
                    cred1_last_updated = NOW()
            """, (
                domain,
                info.get("credibility_score"),
                info.get("category"),
                info.get("sources", 0),
                info.get("credibility_score", 0.5),
            ))
            count += 1

        logger.info("Seeded %d domains from CRED-1", count)
        return count

    def seed_reliable(self) -> int:
        """Add manual seed of known-reliable domains."""
        c = self.conn.cursor()
        count = 0
        for domain, score in self.RELIABLE_SEED.items():
            c.execute("""
                INSERT INTO domain_reputation (domain, composite_score, notes, first_seen)
                VALUES (%s, %s, 'manual reliable seed', NOW())
                ON CONFLICT (domain) DO UPDATE SET
                    composite_score = GREATEST(domain_reputation.composite_score, EXCLUDED.composite_score),
                    notes = COALESCE(domain_reputation.notes, '') || ' [manual seed]'
            """, (domain, score))
            count += 1
        logger.info("Seeded %d reliable domains manually", count)
        return count

    # ── Scoring ────────────────────────────────────────────

    def get_score(self, url: str) -> dict[str, Any]:
        """Get composite credibility score for a URL.

        Returns dict with: domain, composite_score, level (trust/warn/ignore),
        cred1_score, accuracy_rate, cross_ref_score
        """
        domain = extract_domain(url)
        c = self.conn.cursor(cursor_factory=RealDictCursor)

        c.execute(
            "SELECT * FROM domain_reputation WHERE domain = %s",
            (domain,),
        )
        row = c.fetchone()

        if row is None:
            # Unknown domain → insert with neutral score
            c.execute(
                "INSERT INTO domain_reputation (domain, composite_score, first_seen) "
                "VALUES (%s, 0.5, NOW()) ON CONFLICT (domain) DO NOTHING",
                (domain,),
            )
            return {
                "domain": domain,
                "composite_score": 0.5,
                "level": "warn",
                "cred1_score": None,
                "accuracy_rate": None,
                "cross_ref_score": None,
            }

        score = float(row["composite_score"] or 0.5)

        if score >= self.THRESHOLD_TRUST:
            level = "trust"
        elif score >= self.THRESHOLD_WARN:
            level = "warn"
        else:
            level = "ignore"

        return {
            "domain": domain,
            "composite_score": score,
            "level": level,
            "cred1_score": row.get("cred1_score"),
            "accuracy_rate": row.get("accuracy_rate"),
            "cross_ref_score": row.get("cross_ref_score"),
        }

    def should_use(self, url: str) -> bool:
        """Quick check: should this source be used? (score >= 0.4)"""
        result = self.get_score(url)
        return result["composite_score"] >= self.THRESHOLD_WARN

    def filter_sources(self, urls: list[str]) -> tuple[list[str], list[dict]]:
        """Filter list of URLs, returning (trusted, ignored_with_reasons)."""
        trusted = []
        ignored = []
        for url in urls:
            result = self.get_score(url)
            if result["composite_score"] >= self.THRESHOLD_WARN:
                trusted.append(url)
            else:
                ignored.append({"url": url, **result})

        if ignored:
            logger.info(
                "Filtered %d/%d sources (score < %.2f)",
                len(ignored), len(urls), self.THRESHOLD_WARN,
            )

        return trusted, ignored

    def record_use(self, url: str, title: str = "", snippet: str = "", research_id: int = None) -> None:
        """Record that a source was used in research."""
        domain = extract_domain(url)
        score = self.get_score(url)["composite_score"]

        c = self.conn.cursor()
        c.execute("""
            INSERT INTO source_tracking (url, domain, title, snippet, score_at_time, research_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (url, domain, title, snippet, score, research_id))

        # Update domain usage counter
        c.execute("""
            UPDATE domain_reputation
            SET times_used = times_used + 1, last_seen = NOW()
            WHERE domain = %s
        """, (domain,))

    def endorse(self, url: str) -> None:
        """User marks a source as good."""
        domain = extract_domain(url)
        c = self.conn.cursor()
        c.execute("""
            UPDATE domain_reputation
            SET user_endorsements = user_endorsements + 1,
                user_rating = COALESCE(user_rating, 0) + 0.1,
                composite_score = LEAST(1.0, composite_score + 0.05),
                composite_updated = NOW()
            WHERE domain = %s
        """, (domain,))

    def flag(self, url: str) -> None:
        """User marks a source as bad."""
        domain = extract_domain(url)
        c = self.conn.cursor()
        c.execute("""
            UPDATE domain_reputation
            SET user_flags = user_flags + 1,
                user_rating = COALESCE(user_rating, 0) - 0.1,
                composite_score = GREATEST(0.0, composite_score - 0.05),
                composite_updated = NOW()
            WHERE domain = %s
        """, (domain,))

    def stats(self) -> dict[str, Any]:
        """Get source reputation system statistics."""
        c = self.conn.cursor(cursor_factory=RealDictCursor)
        c.execute("SELECT COUNT(*) as total FROM domain_reputation")
        total = c.fetchone()["total"]

        c.execute("SELECT COUNT(*) as cred1 FROM domain_reputation WHERE cred1_score IS NOT NULL")
        cred1 = c.fetchone()["cred1"]

        c.execute("SELECT COUNT(*) as tracked FROM source_tracking")
        tracked = c.fetchone()["tracked"]

        c.execute("SELECT AVG(composite_score) as avg_score FROM domain_reputation")
        avg = c.fetchone()["avg_score"] or 0.5

        return {
            "total_domains": total,
            "cred1_coverage": cred1,
            "sources_tracked": tracked,
            "avg_score": round(float(avg), 3),
        }
