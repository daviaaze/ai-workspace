"""Smoke tests for BudgetEnforcer.auto_tune().

Covers dry_run (no mutation) and apply paths, the per-provider override
setattr/getattr mechanism, and the empty-cost-table edge case.
"""

from __future__ import annotations

from ai_workspace.core.cost import BudgetEnforcer


class _FakeCursor:
    """Minimal cursor returning canned rows, recording executed SQL."""

    def __init__(self, rows):
        self._rows = rows
        self.executed: list[str] = []

    def execute(self, sql, params=None):
        self.executed.append(sql)

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def close(self):
        pass


class _FakeConn:
    """Mimics the psycopg2 connection BudgetEnforcer expects."""

    def __init__(self, rows):
        self._cursor = _FakeCursor(rows)
        self.closed = False  # psycopg2 connection exposes '.closed' bool

    def cursor(self):
        return self._cursor


class TestAutoTune:
    def _make_budget(self, rows):
        budget = BudgetEnforcer()
        # CostLog.conn is a read-only property; assign to the backing _conn.
        budget.logger._conn = _FakeConn(rows)
        return budget

    def test_dry_run_returns_suggestions_without_applying(self):
        rows = [
            ("deepseek", "2026-06-01", 0.50),
            ("deepseek", "2026-06-02", 0.70),
            ("deepseek", "2026-06-03", 0.30),
        ]
        budget = self._make_budget(rows)

        initial_daily = budget.DAILY_BUDGET
        initial_monthly = budget.MONTHLY_BUDGET

        result = budget.auto_tune(dry_run=True)

        assert result["dry_run"] is True
        assert "deepseek" in result["providers"]
        ds = result["providers"]["deepseek"]
        # avg_daily = (0.50+0.70+0.30)/3 = 0.50
        # suggested_daily = 0.50 * 1.5 = 0.75
        assert ds["avg_daily_cost"] == 0.5
        assert ds["suggested_daily_budget"] == 0.75
        assert ds["days_with_data"] == 3
        # Dry run should NOT mutate the instance budgets
        assert budget.DAILY_BUDGET == initial_daily
        assert budget.MONTHLY_BUDGET == initial_monthly
        # No per-provider attr set during dry_run
        assert not hasattr(budget, "DAILY_BUDGET_DEEPSEEK")

    def test_apply_mutates_per_provider_budgets(self):
        rows = [
            ("gemini", "2026-06-01", 2.00),
            ("gemini", "2026-06-02", 2.00),
        ]
        budget = self._make_budget(rows)

        result = budget.auto_tune(dry_run=False)

        assert result["dry_run"] is False
        # avg_daily = 2.00; suggested = 2.00 * 1.5 = 3.00
        assert result["providers"]["gemini"]["suggested_daily_budget"] == 3.00
        # Per-provider budget override should be set on the instance
        assert getattr(budget, "DAILY_BUDGET_GEMINI") == 3.00
        assert getattr(budget, "MONTHLY_BUDGET_GEMINI") == 2.00 * 30 * 1.2

    def test_empty_cost_log_returns_no_providers(self):
        budget = self._make_budget([])

        result = budget.auto_tune(dry_run=True)

        assert result["providers"] == {}
        assert result.get("total_providers", 0) == 0
        assert result["dry_run"] is True

    def test_apply_floor_minimum_enforced(self):
        rows = [
            ("ollama", "2026-06-01", 0.01),
        ]
        budget = self._make_budget(rows)

        result = budget.auto_tune(dry_run=True)
        ds = result["providers"]["ollama"]
        # floor is max(suggested, 0.50)
        assert ds["suggested_daily_budget"] >= 0.50
        assert ds["suggested_monthly_budget"] >= 5.00
