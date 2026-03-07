# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_trend_detector_bullish.py
# DESCRIPTION  : Tests TrendDetector — détection BULLISH HH/HL
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

from enum import Enum

# Pure Python mirror du TrendDetector Cython (avant compilation)


class TrendBias(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class TrendDetector:
    def __init__(self, swing_lookback=3):
        self.swing_lookback = swing_lookback

    def find_swing_highs(self, candles):
        swings = []
        n = len(candles)
        for i in range(self.swing_lookback, n - self.swing_lookback):
            price = candles[i]["high"]
            is_swing = all(
                candles[j]["high"] < price
                for j in range(i - self.swing_lookback, i + self.swing_lookback + 1)
                if j != i
            )
            if is_swing:
                swings.append({"index": i, "price": price})
        return swings

    def find_swing_lows(self, candles):
        swings = []
        n = len(candles)
        for i in range(self.swing_lookback, n - self.swing_lookback):
            price = candles[i]["low"]
            is_swing = all(
                candles[j]["low"] > price
                for j in range(i - self.swing_lookback, i + self.swing_lookback + 1)
                if j != i
            )
            if is_swing:
                swings.append({"index": i, "price": price})
        return swings

    def detect(self, candles):
        highs = self.find_swing_highs(candles)
        lows = self.find_swing_lows(candles)
        if len(highs) < 2 or len(lows) < 2:
            return TrendBias.NEUTRAL
        hh = highs[-1]["price"] > highs[-2]["price"]
        hl = lows[-1]["price"] > lows[-2]["price"]
        ll = lows[-1]["price"] < lows[-2]["price"]
        lh = highs[-1]["price"] < highs[-2]["price"]
        if hh and hl:
            return TrendBias.BULLISH
        elif ll and lh:
            return TrendBias.BEARISH
        return TrendBias.NEUTRAL


def _make_candle(h, low_, o=None, c=None):
    return {"open": o or low_, "high": h, "low": low_, "close": c or h, "volume": 100}


def _bullish_candles():
    """
    20 bougies M15 avec 2 swing highs (HH) et 2 swing lows (HL) nets.
    Validé manuellement pour lookback=2 :
      SH1 @ i=3  high=1.0930
      SL1 @ i=6  low=1.0885
      SH2 @ i=11 high=1.0945  (HH : 1.0945 > 1.0930)
      SL2 @ i=14 low=1.0895   (HL : 1.0895 > 1.0885)
    """
    return [
        _make_candle(1.0910, 1.0900),  # 0
        _make_candle(1.0920, 1.0905),  # 1
        _make_candle(1.0915, 1.0902),  # 2
        _make_candle(1.0930, 1.0908),  # 3  → SH1=1.0930
        _make_candle(1.0920, 1.0905),  # 4
        _make_candle(1.0912, 1.0894),  # 5
        _make_candle(1.0908, 1.0885),  # 6  → SL1=1.0885
        _make_candle(1.0912, 1.0890),  # 7
        _make_candle(1.0916, 1.0895),  # 8
        _make_candle(1.0920, 1.0900),  # 9
        _make_candle(1.0915, 1.0895),  # 10
        _make_candle(1.0945, 1.0905),  # 11 → SH2=1.0945 (HH)
        _make_candle(1.0935, 1.0908),  # 12
        _make_candle(1.0925, 1.0900),  # 13
        _make_candle(1.0920, 1.0895),  # 14 → SL2=1.0895 (HL)
        _make_candle(1.0925, 1.0900),  # 15
        _make_candle(1.0928, 1.0905),  # 16
        _make_candle(1.0928, 1.0902),  # 17
        _make_candle(1.0926, 1.0900),  # 18
        _make_candle(1.0924, 1.0898),  # 19
    ]


class TestTrendDetectorBullish:
    """Test 1 : Détecte BULLISH sur HH/HL."""

    def setup_method(self):
        self.detector = TrendDetector(swing_lookback=2)

    def test_detects_bullish_on_hh_hl(self):
        """Doit retourner BULLISH sur une séquence HH/HL claire."""
        candles = _bullish_candles()
        result = self.detector.detect(candles)
        assert result == TrendBias.BULLISH

    def test_swing_highs_found(self):
        """find_swing_highs retourne au moins 2 swings sur séquence bullish."""
        candles = _bullish_candles()
        highs = self.detector.find_swing_highs(candles)
        assert len(highs) >= 2

    def test_swing_highs_ascending(self):
        """Les swing highs successifs doivent être croissants (HH)."""
        candles = _bullish_candles()
        highs = self.detector.find_swing_highs(candles)
        if len(highs) >= 2:
            assert highs[-1]["price"] > highs[-2]["price"]
