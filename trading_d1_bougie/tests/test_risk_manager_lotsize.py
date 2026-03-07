# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_risk_manager_lotsize.py
# DESCRIPTION  : Tests RiskManager — calcul lot size correct
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

import pytest
from enum import Enum


class RiskCheckResult(Enum):
    ALLOWED = "ALLOWED"
    BLOCKED_DAILY_LIMIT = "BLOCKED: DAILY_LOSS_LIMIT"
    BLOCKED_MAX_PAIRS = "BLOCKED: MAX_OPEN_PAIRS"


class RiskManager:
    def __init__(self, risk_pct=1.0, daily_loss_limit_pct=3.0,
                 max_open_pairs=1, lot_type="mini"):
        self.risk_pct = risk_pct
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_open_pairs = max_open_pairs
        multipliers = {"standard": 100_000.0, "mini": 10_000.0, "micro": 1_000.0}
        if lot_type not in multipliers:
            raise ValueError(f"Invalid lot_type: {lot_type}")
        self.lot_type_multiplier = multipliers[lot_type]

    def calculate_lot_size(self, equity, sl_pips, pair):
        if equity <= 0:
            raise ValueError("equity must be > 0")
        if sl_pips <= 0:
            raise ValueError("sl_pips must be > 0")
        pip_size = 0.01 if "JPY" in pair.upper() else 0.0001
        pip_value_per_lot = pip_size * self.lot_type_multiplier
        risk_amount = equity * (self.risk_pct / 100.0)
        lot_size = risk_amount / (sl_pips * pip_value_per_lot)
        return round(max(0.01, round(lot_size, 2)), 2)

    def check_daily_limit(self, equity_start, equity_current):
        if equity_start <= 0:
            raise ValueError("equity_start must be > 0")
        daily_pnl_pct = ((equity_current - equity_start) / equity_start) * 100.0
        if daily_pnl_pct <= -self.daily_loss_limit_pct:
            return RiskCheckResult.BLOCKED_DAILY_LIMIT
        return RiskCheckResult.ALLOWED

    def check_max_pairs(self, open_pairs_count):
        if open_pairs_count >= self.max_open_pairs:
            return RiskCheckResult.BLOCKED_MAX_PAIRS
        return RiskCheckResult.ALLOWED


class TestRiskManagerLotSize:
    """Test 1 : Lot size calculé correctement."""

    def setup_method(self):
        self.mgr = RiskManager(risk_pct=1.0, lot_type="mini")

    def test_lot_size_eurusd_10k_equity(self):
        """
        Equity=10000 USD, risk=1%, SL=20 pips, EURUSD mini:
        risk_amount = 100 USD
        pip_value_per_lot = 0.0001 × 10000 = 1.0 USD/pip
        lot_size = 100 / (20 × 1.0) = 5.0 lots mini
        """
        lots = self.mgr.calculate_lot_size(equity=10_000, sl_pips=20, pair="EURUSD")
        assert lots == pytest.approx(5.0, abs=0.05)

    def test_lot_size_minimum_is_001(self):
        """Lot size minimum doit être 0.01 (jamais < 0.01)."""
        # Très grand SL → lot_size naturellement très petit
        lots = self.mgr.calculate_lot_size(equity=100, sl_pips=10_000, pair="EURUSD")
        assert lots >= 0.01

    def test_lot_size_scales_with_equity(self):
        """Doubler l'equity → doubler le lot size."""
        lots_10k = self.mgr.calculate_lot_size(equity=10_000, sl_pips=20, pair="EURUSD")
        lots_20k = self.mgr.calculate_lot_size(equity=20_000, sl_pips=20, pair="EURUSD")
        assert lots_20k == pytest.approx(lots_10k * 2, abs=0.05)

    def test_lot_size_invalid_equity(self):
        with pytest.raises(ValueError, match="equity must be > 0"):
            self.mgr.calculate_lot_size(equity=0, sl_pips=20, pair="EURUSD")

    def test_lot_size_invalid_sl_pips(self):
        with pytest.raises(ValueError, match="sl_pips must be > 0"):
            self.mgr.calculate_lot_size(equity=10_000, sl_pips=0, pair="EURUSD")
