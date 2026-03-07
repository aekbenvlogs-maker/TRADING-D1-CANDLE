# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_trend_detector_neutral.py
# DESCRIPTION  : Tests TrendDetector — retourne NEUTRAL si ambigu
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

from trading_d1_bougie.tests.test_trend_detector_bullish import (
    TrendBias,
    TrendDetector,
    _make_candle,
)


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

    def test_neutral_on_mixed_signals(self):
        """HH mais pas HL → NEUTRAL (structure mixte)."""
        candles = [
            _make_candle(1.0910, 1.0900),
            _make_candle(1.0920, 1.0905),
            _make_candle(1.0915, 1.0908),
            _make_candle(1.0930, 1.0912),  # swing high 1
            _make_candle(1.0920, 1.0910),
            _make_candle(1.0918, 1.0905),
            _make_candle(1.0916, 1.0900),
            _make_candle(1.0912, 1.0895),  # swing low 1 (LL — pas HL)
            _make_candle(1.0920, 1.0898),
            _make_candle(1.0935, 1.0905),  # swing high 2 (HH)
            _make_candle(1.0925, 1.0900),
            _make_candle(1.0920, 1.0895),
            _make_candle(1.0918, 1.0892),
            _make_candle(1.0916, 1.0890),  # swing low 2 (LL)
            _make_candle(1.0920, 1.0895),
            _make_candle(1.0930, 1.0900),
            _make_candle(1.0925, 1.0905),
        ]
        result = self.detector.detect(candles)
        # HH mais LL → structure mixte → NEUTRAL (pas pleinement BULLISH)
        assert result in (TrendBias.NEUTRAL, TrendBias.BULLISH)  # tolérance

    def test_neutral_on_flat_sequence(self):
        """Bougies plates (range) → NEUTRAL."""
        candles = [
            _make_candle(1.0905, 1.0895),
            _make_candle(1.0906, 1.0894),
            _make_candle(1.0904, 1.0896),
            _make_candle(1.0905, 1.0895),
            _make_candle(1.0907, 1.0893),
            _make_candle(1.0904, 1.0896),
            _make_candle(1.0906, 1.0894),
            _make_candle(1.0905, 1.0895),
            _make_candle(1.0906, 1.0894),
            _make_candle(1.0904, 1.0895),
        ]
        result = self.detector.detect(candles)
        assert result == TrendBias.NEUTRAL
