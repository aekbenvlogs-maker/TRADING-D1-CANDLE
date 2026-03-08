# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_order_manager_usdjpy.py
# DESCRIPTION  : Tests OrderManager — précision 2 décimales USDJPY
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

import pytest

from trading_d1_bougie.core.order_manager import OrderManager


class TestOrderManagerUSDJPY:
    """Test 2 : Précision 2 décimales pour les paires JPY."""

    def setup_method(self):
        self.mgr = OrderManager(rr_ratio=2.0, spread_buffer_pips=0.5)

    def test_usdjpy_price_decimals(self):
        """USDJPY doit utiliser 2 décimales."""
        spec = self.mgr.build("USDJPY", "LONG", 149.50, 149.00, 0.1)
        assert spec.price_decimals == 2

    def test_usdjpy_pip_size_is_001(self):
        """Le pip USDJPY = 0.01 → ~50 pips d'entrée à SL."""
        spec = self.mgr.build("USDJPY", "LONG", 149.50, 149.00, 0.1)
        # sl_pips = (149.50 - sl_price) / 0.01 ≈ 49.5 pips (spread_buffer=0.5)
        assert spec.sl_pips == pytest.approx(49.5, abs=1.0)

    def test_usdjpy_tp_rr2(self):
        """TP doit être à RR×2 du SL sur USDJPY."""
        spec = self.mgr.build("USDJPY", "LONG", 149.50, 149.00, 0.1)
        assert spec.tp_pips == pytest.approx(spec.sl_pips * 2.0, abs=1.0)
