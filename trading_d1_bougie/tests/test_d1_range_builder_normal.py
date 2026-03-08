# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_d1_range_builder_normal.py
# DESCRIPTION  : Tests D1RangeBuilder — données normales
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

import pytest

from trading_d1_bougie.core.d1_range_builder import D1RangeBuilder, D1Range  # noqa: F401


class TestD1RangeBuilderNormal:
    """Test 1 : Rectangle correct sur données normales."""

    def setup_method(self):
        self.builder = D1RangeBuilder(fibo_forbidden_pct=5.0, proximity_buffer_pct=10.0)

    def test_rectangle_correct_values(self):
        """Le rectangle D1 doit avoir les bonnes valeurs calculées."""
        d1 = self.builder.build("EURUSD", d1_high=1.1000, d1_low=1.0900)

        assert d1.pair == "EURUSD"
        assert d1.high == pytest.approx(1.1000)
        assert d1.low == pytest.approx(1.0900)
        assert d1.mid == pytest.approx(1.0950)  # (1.1000 + 1.0900) / 2

    def test_rectangle_fibo_zones(self):
        """Les zones Fibo doivent être correctement calculées à ±5% de la hauteur."""
        d1 = self.builder.build("EURUSD", d1_high=1.1000, d1_low=1.0900)
        # hauteur = 0.0100, offset = 0.0100 * 5 / 100 = 0.00050
        assert d1.fibo_zone_upper == pytest.approx(1.0950 + 0.0005, abs=1e-7)
        assert d1.fibo_zone_lower == pytest.approx(1.0950 - 0.0005, abs=1e-7)

    def test_rectangle_proximity_zones(self):
        """Les zones de proximité doivent être à ±10% de la hauteur des extrémités."""
        d1 = self.builder.build("EURUSD", d1_high=1.1000, d1_low=1.0900)
        # hauteur = 0.0100, offset = 0.0100 * 10 / 100 = 0.0010
        assert d1.proximity_upper == pytest.approx(1.1000 - 0.0010, abs=1e-7)
        assert d1.proximity_lower == pytest.approx(1.0900 + 0.0010, abs=1e-7)

    def test_rectangle_invalid_high_lower_than_low(self):
        """Doit lever ValueError si high <= low."""
        with pytest.raises(ValueError):
            self.builder.build("EURUSD", d1_high=1.0900, d1_low=1.1000)

    def test_rectangle_invalid_equal_high_low(self):
        """Doit lever ValueError si high == low (bougie plate)."""
        with pytest.raises(ValueError):
            self.builder.build("EURUSD", d1_high=1.0950, d1_low=1.0950)
