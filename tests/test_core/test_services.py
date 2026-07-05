"""
End-to-end tests for core services: cache, sources, projects.

Requires AIW_TEST_DB_URL env var pointing to a PostgreSQL with pgvector.
"""

from __future__ import annotations

import os

import pytest


@pytest.fixture(scope="module")
def db_url():
    url = os.environ.get("AIW_TEST_DB_URL", "")
    if not url:
        pytest.skip("AIW_TEST_DB_URL not set")
    return url


# ─── Semantic Cache Tests ──────────────────────────────

class TestSemanticCache:
    def test_initialize_creates_tables(self, db_url):
        from ai_workspace.core.cost import SemanticCache
        cache = SemanticCache(db_url=db_url)
        cache.initialize()

        c = cache.conn.cursor()
        c.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'semantic_cache')")
        assert c.fetchone()[0] is True

    def test_exact_hash_hit(self, db_url):
        from ai_workspace.core.cost import SemanticCache
        cache = SemanticCache(db_url=db_url)
        cache.initialize()

        # Store
        cache.set("test-query-123", "test response", "chat", "test-model", 10, 0.001)

        # Retrieve via exact hash
        result = cache.get("test-query-123", "chat")
        assert result is not None
        assert result["response_text"] == "test response"
        assert result["similarity"] == 1.0
        assert result["source"] == "cache_exact"

    def test_miss_unknown_query(self, db_url):
        from ai_workspace.core.cost import SemanticCache
        cache = SemanticCache(db_url=db_url)
        cache.initialize()

        result = cache.get("completely-unique-query-xyz-999", "chat")
        # May return None (no embedding backend) or None (no match)
        # Either is fine for a miss test
        assert result is None or result.get("similarity", 0) < 0.85

    def test_stats(self, db_url):
        from ai_workspace.core.cost import SemanticCache
        cache = SemanticCache(db_url=db_url)
        cache.initialize()

        stats = cache.stats()
        assert "total_entries" in stats
        assert "total_hits" in stats
        assert "tokens_saved" in stats
        assert "cost_saved" in stats
        assert stats["total_entries"] >= 0

    def test_clear(self, db_url):
        from ai_workspace.core.cost import SemanticCache
        cache = SemanticCache(db_url=db_url)
        cache.initialize()

        cache.set("to-clear", "response", "chat", "x", 1, 0)
        before = cache.stats()["total_entries"]
        cache.clear()
        after = cache.stats()["total_entries"]
        assert after <= before


# ─── Cost Log Tests ────────────────────────────────────

class TestCostLog:
    def test_initialize_creates_table(self, db_url):
        from ai_workspace.core.cost import CostLog
        log = CostLog(db_url=db_url)
        log.initialize()

        c = log.conn.cursor()
        c.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'cost_log')")
        assert c.fetchone()[0] is True

    def test_log_and_query(self, db_url):
        from ai_workspace.core.cost import CostLog
        log = CostLog(db_url=db_url)
        log.initialize()

        log_id = log.log("deepseek", "deepseek-chat", "research", 100, 50, 0.001)
        assert log_id > 0

        today = log.today_cost()
        assert today >= 0.001


# ─── Source Reputation Tests ───────────────────────────

class TestSourceReputation:
    def test_initialize_creates_tables(self, db_url):
        from ai_workspace.core.sources import SourceReputationService
        src = SourceReputationService(db_url=db_url)
        src.initialize()

        c = src.conn.cursor()
        for table in ["domain_reputation", "source_tracking", "cross_reference_log"]:
            c.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
            assert c.fetchone()[0] is True

    def test_seed_reliable(self, db_url):
        from ai_workspace.core.sources import SourceReputationService
        src = SourceReputationService(db_url=db_url)
        src.initialize()

        count = src.seed_reliable()
        assert count >= 15  # At least the manual seed domains

    def test_get_score_trusted(self, db_url):
        from ai_workspace.core.sources import SourceReputationService
        src = SourceReputationService(db_url=db_url)
        src.initialize()
        src.seed_reliable()

        result = src.get_score("https://arxiv.org/abs/1234.5678")
        assert result["composite_score"] >= 0.85
        assert result["level"] == "trust"

    def test_filter_sources(self, db_url):
        from ai_workspace.core.sources import SourceReputationService
        src = SourceReputationService(db_url=db_url)
        src.initialize()
        src.seed_reliable()

        urls = ["https://arxiv.org/paper", "https://github.com/repo"]
        trusted, ignored = src.filter_sources(urls)
        # arxiv.org and github.com are seeded as reliable
        assert len(trusted) >= 1
        # Ignored list may be empty if no domains match blocklist
        assert isinstance(ignored, list)

    def test_extract_domain(self):
        from ai_workspace.core.sources import extract_domain
        assert extract_domain("https://www.example.com/page") == "example.com"
        assert extract_domain("arxiv.org") == "arxiv.org"
        assert extract_domain("https://sub.domain.co.uk:8080/path") == "sub.domain.co.uk"

    def test_record_use_and_stats(self, db_url):
        from ai_workspace.core.sources import SourceReputationService
        src = SourceReputationService(db_url=db_url)
        src.initialize()

        src.record_use("https://example.com", "Test Page", "A test snippet")
        stats = src.stats()
        assert stats["sources_tracked"] >= 1


# ─── Project Manager Tests ─────────────────────────────

class TestProjectManager:
    def test_initialize_creates_tables(self, db_url):
        from ai_workspace.core.projects import ProjectManager
        pm = ProjectManager(db_url=db_url)
        pm.initialize()

        c = pm.conn.cursor()
        for table in ["projects", "project_repos", "project_agents"]:
            c.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
            assert c.fetchone()[0] is True

    def test_create_and_list(self, db_url):
        from ai_workspace.core.projects import ProjectManager
        pm = ProjectManager(db_url=db_url)
        pm.initialize()

        pm.create_project("test-project", "Test project for unit tests",
                         repos=[{"name": "main", "path": "/tmp"}])

        projects = pm.list_projects()
        names = [p.name for p in projects]
        assert "test-project" in names
