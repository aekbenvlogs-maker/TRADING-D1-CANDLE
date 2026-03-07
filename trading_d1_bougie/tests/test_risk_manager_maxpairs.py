# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_risk_manager_maxpairs.py
# DESCRIPTION  : Tests RiskManager — bloque si paire déjà ouverte
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

import pytest
from trading_d1_bougie.tests.test_risk_manager_lotsize import RiskManager, RiskCheckResult


class TestRiskManagerMaxPairs:
    """Test 3 : Bloque un nouveau trade si max_open_pairs déjà atteint."""

    def setup_method(self):
        self.mgr = RiskManager(max_open_pairs=1)

    def test_blocked_when_one_pair_open(self):
        """1 paire ouverte avec max=1 → BLOCKED."""
        result = self.mgr.check_max_pairs(open_pairs_count=1)
        assert result == RiskCheckResult.BLOCKED_MAX_PAIRS

    def test_allowed_when_zero_pairs_open(self):
        """0 paire ouverte avec max=1 → ALLOWED."""
        result = self.mgr.check_max_pairs(open_pairs_count=0)
        assert result == RiskCheckResult.ALLOWED

    def test_blocked_exceeds_max(self):
        """2 paires ouvertes avec max=1 → BLOCKED."""
        result = self.mgr.check_max_pairs(open_pairs_count=2)
        assert result == RiskCheckResult.BLOCKED_MAX_PAIRS

    def test_max_pairs_2_allows_first(self):
        """max=2 : 1 paire ouverte → ALLOWED."""
        mgr2 = RiskManager(max_open_pairs=2)
        assert mgr2.check_max_pairs(1) == RiskCheckResult.ALLOWED

    def test_max_pairs_2_blocks_second(self):
        """max=2 : 2 paires ouvertes → BLOCKED."""
        mgr2 = RiskManager(max_open_pairs=2)
        assert mgr2.check_max_pairs(2) == RiskCheckResult.BLOCKED_MAX_PAIRS
