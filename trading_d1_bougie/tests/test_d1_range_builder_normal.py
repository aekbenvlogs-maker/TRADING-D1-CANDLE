# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_d1_range_builder_normal.py
# DESCRIPTION  : Tests D1RangeBuilder — données normales
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================


import pytest

# ---------------------------------------------------------------------------
# Helpers — pure Python simulation du D1RangeBuilder (avant compilation Cython)
# ---------------------------------------------------------------------------


class D1Range:
    def __init__(
        self,
        pair,
        high,
        low,
        mid,
        fibo_zone_upper,
        fibo_zone_lower,
        proximity_upper,
        proximity_lower,
    ):
        self.pair = pair
        self.high = high
        self.low = low
        self.mid = mid
        self.fibo_zone_upper = fibo_zone_upper
        self.fibo_zone_lower = fibo_zone_lower
        self.proximity_upper = proximity_upper
        self.proximity_lower = proximity_lower


class D1RangeBuilder:
    def __init__(self, fibo_forbidden_pct=5.0, proximity_buffer_pct=10.0):
        self.fibo_forbidden_pct = fibo_forbidden_pct
        self.proximity_buffer_pct = proximity_buffer_pct

    def build(self, pair, d1_high, d1_low):
        if d1_high <= d1_low:
            raise ValueError("d1_high must be > d1_low")
        height = d1_high - d1_low
        mid = (d1_high + d1_low) / 2.0
        fibo_offset = height * self.fibo_forbidden_pct / 100.0
        proximity_offset = height * self.proximity_buffer_pct / 100.0
        return D1Range(
            pair=pair,
            high=d1_high,
            low=d1_low,
            mid=mid,
            fibo_zone_upper=mid + fibo_offset,
            fibo_zone_lower=mid - fibo_offset,
            proximity_upper=d1_high - proximity_offset,
            proximity_lower=d1_low + proximity_offset,
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


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
