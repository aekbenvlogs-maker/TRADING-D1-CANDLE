# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_trend_detector_neutral.py
# DESCRIPTION  : Tests TrendDetector — retourne NEUTRAL si ambigu
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

from trading_d1_bougie.core.trend_detector import TrendDetector, TrendBias
from trading_d1_bougie.tests.test_trend_detector_bullish import _make_candle


class TestTrendDetectorNeutral:
    """Test 3 : Retourne NEUTRAL si structure ambiguë ou insuffisante."""

    def setup_method(self):
        self.detector = TrendDetector(swing_lookback=3)

    def test_neutral_on_insufficient_candles(self):
        """Trop peu de bougies → NEUTRAL."""
        candles = [
            _make_candle(1.1000 + i * 0.0001, 1.0990 + i * 0.0001) for i in range(5)
        ]
        result = self.detector.detect(candles)
        assert result == TrendBias.NEUTRAL

    def test_neutral_on_flat_range(self):
        """Range latéral sans swing nets → NEUTRAL."""
        candles = [
            _make_candle(1.0950 + (i % 3) * 0.0001, 1.0948 + (i % 3) * 0.0001)
            for i in range(20)
        ]
        result = self.detector.detect(candles)
        assert result == TrendBias.NEUTRAL
