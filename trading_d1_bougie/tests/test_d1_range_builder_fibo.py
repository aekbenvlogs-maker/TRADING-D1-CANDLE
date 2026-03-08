# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_d1_range_builder_fibo.py
# DESCRIPTION  : Tests D1RangeBuilder — précision calcul Fibo midpoint
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

import pytest

from trading_d1_bougie.core.d1_range_builder import D1RangeBuilder


class TestD1RangeBuilderFibo:
    """Test 3 : Précision du calcul Fibo midpoint (50%)."""

    def setup_method(self):
        self.builder = D1RangeBuilder(fibo_forbidden_pct=5.0, proximity_buffer_pct=10.0)

    def test_midpoint_is_exactly_50pct(self):
        """Le midpoint doit être exactement 50% de la hauteur D1."""
        d1 = self.builder.build("USDJPY", d1_high=149.500, d1_low=148.500)
        expected_mid = (149.500 + 148.500) / 2.0
        assert d1.mid == pytest.approx(expected_mid, abs=1e-7)

    def test_midpoint_eurusd_precision(self):
        """Précision à 5 décimales sur EURUSD."""
        d1 = self.builder.build("EURUSD", d1_high=1.09876, d1_low=1.09234)
        expected = (1.09876 + 1.09234) / 2.0
        assert d1.mid == pytest.approx(expected, abs=1e-7)

    def test_fibo_zone_symmetric_around_mid(self):
        """La zone Fibo doit être symétrique autour du midpoint."""
        d1 = self.builder.build("GBPUSD", d1_high=1.2800, d1_low=1.2700)
        offset_upper = d1.fibo_zone_upper - d1.mid
        offset_lower = d1.mid - d1.fibo_zone_lower
        assert offset_upper == pytest.approx(offset_lower, abs=1e-7)
