# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_d1_range_builder_fibo.py
# DESCRIPTION  : Tests D1RangeBuilder — précision calcul Fibo midpoint
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

import pytest

from trading_d1_bougie.tests.test_d1_range_builder_normal import D1RangeBuilder


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

    def test_fibo_zone_width_equals_10pct_height(self):
        """La largeur totale de la zone Fibo interdite doit être 10% de la hauteur."""
        d1 = self.builder.build("GBPUSD", d1_high=1.27000, d1_low=1.26000)
        height = 1.27000 - 1.26000
        zone_width = d1.fibo_zone_upper - d1.fibo_zone_lower
        expected_width = height * 2 * 5.0 / 100.0
        assert zone_width == pytest.approx(expected_width, abs=1e-7)

    @pytest.mark.parametrize(
        "high,low",
        [
            (1.20000, 1.19000),
            (1.35500, 1.34200),
            (150.000, 148.500),
        ],
    )
    def test_midpoint_parametrized(self, high, low):
        """Le midpoint est (high + low) / 2 pour toutes les paires."""
        d1 = self.builder.build("TEST", d1_high=high, d1_low=low)
        assert d1.mid == pytest.approx((high + low) / 2.0, abs=1e-7)
