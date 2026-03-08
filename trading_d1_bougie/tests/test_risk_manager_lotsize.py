# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_risk_manager_lotsize.py
# DESCRIPTION  : Tests RiskManager — calcul lot size correct
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

import pytest

from trading_d1_bougie.core.risk_manager import RiskManager, RiskCheckResult  # noqa: F401


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
