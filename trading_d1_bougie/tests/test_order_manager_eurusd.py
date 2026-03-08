# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_order_manager_eurusd.py
# DESCRIPTION  : Tests OrderManager — calcul SL/TP correct sur EURUSD
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

import pytest

from trading_d1_bougie.core.order_manager import OrderManager, OrderSpec  # noqa: F401


class TestOrderManagerEURUSD:
    """Test 1 : Calcul SL/TP correct sur EURUSD (RR = 2)."""

    def setup_method(self):
        self.mgr = OrderManager(rr_ratio=2.0, spread_buffer_pips=0.5)

    def test_long_sl_tp_calculation(self):
        """
        LONG EURUSD :
        entry=1.0910, swing_sl=1.0900
        sl_price = 1.0900 - 0.5*0.0001 = 1.08995 → 1.0900 (arrondi 4 dec)
        sl_pips = (1.0910 - 1.0900) / 0.0001 = 100 pips - spread ≈ 99.5 pips
        tp_pips = 99.5 * 2 = 199.0
        tp_price = 1.0910 + 0.0199 = 1.1109
        """
        spec = self.mgr.build("EURUSD", "LONG", 1.0910, 1.0900, 0.1)

        assert spec.direction == "LONG"
        assert spec.sl_price < spec.entry_price
        assert spec.tp_price > spec.entry_price
        assert spec.sl_pips > 0
        assert spec.tp_pips == pytest.approx(spec.sl_pips * 2.0, abs=0.5)

    def test_short_sl_tp_calculation(self):
        """SHORT EURUSD : SL au-dessus, TP en-dessous, RR=2."""
        spec = self.mgr.build("EURUSD", "SHORT", 1.0960, 1.0970, 0.1)

        assert spec.direction == "SHORT"
        assert spec.sl_price > spec.entry_price
        assert spec.tp_price < spec.entry_price
        assert spec.sl_pips > 0
        assert spec.tp_pips == pytest.approx(spec.sl_pips * 2.0, abs=0.5)

    def test_invalid_direction(self):
        """Direction invalide → ValueError."""
        with pytest.raises(ValueError, match="direction must be LONG or SHORT"):
            self.mgr.build("EURUSD", "FLAT", 1.0910, 1.0900, 0.1)

    def test_price_decimals_eurusd(self):
        """Prix EURUSD doit avoir 4 décimales."""
        spec = self.mgr.build("EURUSD", "LONG", 1.0910, 1.0900, 0.1)
        assert spec.price_decimals == 4
