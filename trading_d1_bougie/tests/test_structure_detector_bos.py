# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_structure_detector_bos.py
# DESCRIPTION  : Tests StructureDetector — détection BOS sur cassure body
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

from enum import Enum


class StructureType(Enum):
    BOS = "BOS"
    CHOCH = "CHoCH"
    NONE = "NONE"


class StructureSignal:
    def __init__(
        self, signal_type, trigger_price=0.0, trigger_index=-1, direction="NONE"
    ):
        self.signal_type = signal_type
        self.trigger_price = trigger_price
        self.trigger_index = trigger_index
        self.direction = direction


class StructureDetector:
    def detect(self, candles, swing_highs, swing_lows, current_trend):
        if not candles or not swing_highs or not swing_lows:
            return StructureSignal(StructureType.NONE)

        last_candle = candles[-1]
        body_high = max(last_candle["open"], last_candle["close"])
        body_low = min(last_candle["open"], last_candle["close"])
        last_idx = len(candles) - 1

        last_swing_high = swing_highs[-1]["price"]
        last_swing_low = swing_lows[-1]["price"]
        prev_swing_high = (
            swing_highs[-2]["price"] if len(swing_highs) >= 2 else last_swing_high
        )
        prev_swing_low = (
            swing_lows[-2]["price"] if len(swing_lows) >= 2 else last_swing_low
        )

        if current_trend == "BULLISH" and body_high > last_swing_high:
            return StructureSignal(
                StructureType.BOS, last_candle["close"], last_idx, "BULLISH"
            )
        if current_trend == "BEARISH" and body_low < last_swing_low:
            return StructureSignal(
                StructureType.BOS, last_candle["close"], last_idx, "BEARISH"
            )
        if current_trend == "BULLISH" and body_low < prev_swing_low:
            return StructureSignal(
                StructureType.CHOCH, last_candle["close"], last_idx, "BEARISH"
            )
        if current_trend == "BEARISH" and body_high > prev_swing_high:
            return StructureSignal(
                StructureType.CHOCH, last_candle["close"], last_idx, "BULLISH"
            )

        return StructureSignal(StructureType.NONE)


def _c(o, c, h=None, low_=None):
    return {"open": o, "close": c, "high": h or max(o, c), "low": low_ or min(o, c)}


class TestStructureDetectorBOS:
    """Test 1 : Détecte BOS sur cassure du body au-delà d'un swing."""

    def setup_method(self):
        self.detector = StructureDetector()

    def test_bos_bullish_body_breaks_swing_high(self):
        """BOS haussier : le body de la bougie dépasse le dernier swing high."""
        candles = [_c(1.0900, 1.0905), _c(1.0905, 1.0910)]
        swing_highs = [{"index": 0, "price": 1.0903}, {"index": 1, "price": 1.0909}]
        swing_lows = [{"index": 0, "price": 1.0895}, {"index": 1, "price": 1.0900}]

        # Bougie qui clôture au-dessus du swing high
        candles.append(_c(1.0908, 1.0912))
        result = self.detector.detect(candles, swing_highs, swing_lows, "BULLISH")

        assert result.signal_type == StructureType.BOS
        assert result.direction == "BULLISH"

    def test_bos_bearish_body_breaks_swing_low(self):
        """BOS baissier : le body de la bougie descend sous le dernier swing low."""
        candles = [_c(1.0905, 1.0900), _c(1.0900, 1.0895)]
        swing_highs = [{"index": 0, "price": 1.0910}, {"index": 1, "price": 1.0906}]
        swing_lows = [{"index": 0, "price": 1.0900}, {"index": 1, "price": 1.0895}]

        candles.append(_c(1.0897, 1.0892))  # body clôture sous le swing low
        result = self.detector.detect(candles, swing_highs, swing_lows, "BEARISH")

        assert result.signal_type == StructureType.BOS
        assert result.direction == "BEARISH"

    def test_no_bos_without_body_breakout(self):
        """Pas de BOS si le body ne dépasse pas le swing (mèche seule)."""
        candles = [_c(1.0900, 1.0905)]
        swing_highs = [{"index": 0, "price": 1.0906}, {"index": 0, "price": 1.0910}]
        swing_lows = [{"index": 0, "price": 1.0895}, {"index": 0, "price": 1.0898}]

        # Bougie dont la mèche dépasse mais le body non
        # (open=1.0907, close=1.0905 < swing_high=1.0910)
        candles.append({"open": 1.0907, "close": 1.0905, "high": 1.0912, "low": 1.0904})
        result = self.detector.detect(candles, swing_highs, swing_lows, "BULLISH")

        # Body (max=1.0907) < swing_high (1.0910) → pas de BOS
        assert result.signal_type == StructureType.NONE
