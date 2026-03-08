# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_risk_manager_dailylimit.py
# DESCRIPTION  : Tests RiskManager — shutdown si limite -3% atteinte
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

import pytest

from trading_d1_bougie.core.risk_manager import RiskManager, RiskCheckResult


class TestRiskManagerDailyLimit:
    """Test 2 : Shutdown automatique si perte journalière ≥ 3%."""

    def setup_method(self):
        self.mgr = RiskManager(daily_loss_limit_pct=3.0)

    def test_blocked_at_exact_limit(self):
        """Perte exactement de 3% → BLOCKED."""
        equity_start = 10_000.0
        equity_current = 9_700.0  # -3% exact
        result = self.mgr.check_daily_limit(equity_start, equity_current)
        assert result == RiskCheckResult.BLOCKED_DAILY_LIMIT

    def test_allowed_below_limit(self):
        """Perte de seulement 1% → ALLOWED."""
        result = self.mgr.check_daily_limit(10_000.0, 9_900.0)
        assert result == RiskCheckResult.ALLOWED

    def test_blocked_beyond_limit(self):
        """Perte de 5% (> 3%) → BLOCKED."""
        result = self.mgr.check_daily_limit(10_000.0, 9_500.0)
        assert result == RiskCheckResult.BLOCKED_DAILY_LIMIT

    def test_allowed_after_profit(self):
        """Equity positive (profit) → toujours ALLOWED."""
        result = self.mgr.check_daily_limit(10_000.0, 10_500.0)
        assert result == RiskCheckResult.ALLOWED
