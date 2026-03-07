# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_order_manager_bracket.py
# DESCRIPTION  : Tests OrderManager — structure bracket order complète
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

import pytest
from trading_d1_bougie.tests.test_order_manager_eurusd import OrderManager


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

    def test_bracket_lot_size_stored(self):
        """Le lot size fourni doit être stocké dans l'OrderSpec."""
        spec = self.mgr.build("EURUSD", "LONG", 1.0920, 1.0905, 0.25)
        assert spec.lot_size == 0.25

    def test_bracket_pair_stored(self):
        """La paire fournie doit être stockée dans l'OrderSpec."""
        spec = self.mgr.build("GBPUSD", "LONG", 1.2650, 1.2630, 0.1)
        assert spec.pair == "GBPUSD"

    def test_bracket_long_sl_above_entry_raises(self):
        """LONG avec SL au-dessus de l'entrée → ValueError."""
        with pytest.raises(ValueError):
            self.mgr.build("EURUSD", "LONG", 1.0900, 1.0950, 0.1)  # SL > entry pour LONG

    def test_bracket_short_sl_below_entry_raises(self):
        """SHORT avec SL en-dessous de l'entrée → ValueError."""
        with pytest.raises(ValueError):
            self.mgr.build("EURUSD", "SHORT", 1.0950, 1.0900, 0.1)  # SL < entry pour SHORT
