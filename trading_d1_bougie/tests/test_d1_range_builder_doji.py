# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_d1_range_builder_doji.py
# DESCRIPTION  : Tests D1RangeBuilder — gestion bougie doji
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

import pytest
from trading_d1_bougie.tests.test_d1_range_builder_normal import D1RangeBuilder


class TestD1RangeBuilderDoji:
    """Test 2 : Gestion bougie doji (très petite hauteur)."""

    def setup_method(self):
        self.builder = D1RangeBuilder(fibo_forbidden_pct=5.0, proximity_buffer_pct=10.0)

    def test_doji_tiny_range(self):
        """Un doji avec écart minimal doit quand même produire un D1Range valide."""
        # Écart de 1 pip seulement
        d1 = self.builder.build("EURUSD", d1_high=1.10001, d1_low=1.10000)
        assert d1.high > d1.low
        assert d1.mid == pytest.approx((1.10001 + 1.10000) / 2.0)

    def test_doji_fibo_smaller_than_proximity(self):
        """Sur un doji, la zone Fibo doit rester entre les zones de proximité."""
        d1 = self.builder.build("EURUSD", d1_high=1.10010, d1_low=1.10000)
        # Les zones Fibo sont autour du mid
        assert d1.fibo_zone_lower >= d1.low
        assert d1.fibo_zone_upper <= d1.high

    def test_doji_zones_are_symmetric(self):
        """Les zones Fibo doivent être symétriques par rapport au mid."""
        d1 = self.builder.build("GBPUSD", d1_high=1.26005, d1_low=1.26000)
        assert d1.mid - d1.fibo_zone_lower == pytest.approx(
            d1.fibo_zone_upper - d1.mid, abs=1e-10
        )
