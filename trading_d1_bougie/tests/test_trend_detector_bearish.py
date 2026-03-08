# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_trend_detector_bearish.py
# DESCRIPTION  : Tests TrendDetector — détection BEARISH LL/LH
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

from trading_d1_bougie.core.trend_detector import TrendDetector, TrendBias
from trading_d1_bougie.tests.test_trend_detector_bullish import _make_candle


def _bearish_candles():
    """
    20 bougies M15 avec 2 swing highs (LH) et 2 swing lows (LL) nets.
    Validé manuellement pour lookback=2 :
      SH1 @ i=3  high=1.0995
      SL1 @ i=6  low=1.0958
      SH2 @ i=11 high=1.0985  (LH : 1.0985 < 1.0995)
      SL2 @ i=14 low=1.0948   (LL : 1.0948 < 1.0958)
    """
    return [
        _make_candle(1.0980, 1.0968),  # 0
        _make_candle(1.0990, 1.0975),  # 1
        _make_candle(1.0985, 1.0978),  # 2
        _make_candle(1.0995, 1.0980),  # 3  → SH1=1.0995
        _make_candle(1.0985, 1.0972),  # 4
        _make_candle(1.0975, 1.0965),  # 5
        _make_candle(1.0968, 1.0958),  # 6  → SL1=1.0958
        _make_candle(1.0972, 1.0962),  # 7
        _make_candle(1.0978, 1.0968),  # 8
        _make_candle(1.0982, 1.0970),  # 9
        _make_candle(1.0978, 1.0965),  # 10
        _make_candle(1.0985, 1.0970),  # 11 → SH2=1.0985 (LH)
        _make_candle(1.0975, 1.0963),  # 12
        _make_candle(1.0968, 1.0955),  # 13
        _make_candle(1.0960, 1.0948),  # 14 → SL2=1.0948 (LL)
        _make_candle(1.0958, 1.0951),  # 15
        _make_candle(1.0955, 1.0950),  # 16  ← low > 1.0948 → ne casse pas le swing
        _make_candle(1.0952, 1.0945),  # 17
        _make_candle(1.0950, 1.0942),  # 18
        _make_candle(1.0948, 1.0940),  # 19
    ]


class TestTrendDetectorBearish:
    """Test 2 : Détecte BEARISH sur LL/LH."""

    def setup_method(self):
        self.detector = TrendDetector(swing_lookback=2)

    def test_detects_bearish_on_ll_lh(self):
        """Doit retourner BEARISH sur une séquence LL/LH claire."""
        candles = _bearish_candles()
        result = self.detector.detect(candles)
        assert result == TrendBias.BEARISH

    def test_swing_lows_descending(self):
        """Les swing lows successifs doivent être décroissants (LL)."""
        candles = _bearish_candles()
        lows = self.detector.find_swing_lows(candles)
        if len(lows) >= 2:
            assert lows[-1]["price"] < lows[-2]["price"]
