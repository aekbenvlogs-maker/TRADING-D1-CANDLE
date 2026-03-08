# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_order_manager_bracket.py
# DESCRIPTION  : Tests OrderManager — structure bracket order complète
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

import pytest

from trading_d1_bougie.core.order_manager import OrderManager


class TestOrderManagerBracket:
    """Test 3 : Bracket order bien formé (entrée + SL + TP cohérents)."""

    def setup_method(self):
        self.mgr = OrderManager(rr_ratio=2.0, spread_buffer_pips=0.5)

    def test_bracket_long_coherence(self):
        """Pour un LONG : entry < tp ET entry > sl."""
        spec = self.mgr.build("EURUSD", "LONG", 1.0920, 1.0905, 0.1)
        assert spec.entry_price > spec.sl_price, "SL doit être sous l'entrée"
        assert spec.tp_price > spec.entry_price, "TP doit être au-dessus de l'entrée"

    def test_bracket_short_coherence(self):
        """Pour un SHORT : entry > tp ET entry < sl."""
        spec = self.mgr.build("GBPUSD", "SHORT", 1.2700, 1.2715, 0.05)
        assert spec.entry_price < spec.sl_price, "SL doit être au-dessus de l'entrée"
        assert spec.tp_price < spec.entry_price, "TP doit être sous l'entrée"

    def test_rr_ratio_respected(self):
        """Le ratio TP/SL doit respecter le RR configuré (2.0)."""
        spec = self.mgr.build("EURUSD", "LONG", 1.0920, 1.0900, 0.1)
        assert spec.tp_pips == pytest.approx(spec.sl_pips * 2.0, abs=0.5)
