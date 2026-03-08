# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_structure_detector_wick.py
# DESCRIPTION  : Tests StructureDetector — rejette cassure mèche seule
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

from trading_d1_bougie.core.structure_detector import StructureDetector, StructureType


class TestStructureDetectorWickRejection:
    """Test 3 : Rejette une cassure par mèche seule (body rule)."""

    def setup_method(self):
        self.detector = StructureDetector()

    def test_wick_only_above_swing_high_not_bos(self):
        """
        Mèche haute dépasse le swing high mais body ne dépasse pas → pas de BOS.
        open=1.0908, close=1.0905 → body_high=1.0908
        swing_high=1.0910 → body_high (1.0908) < swing_high (1.0910) → NONE
        """
        candles = [{"open": 1.0900, "close": 1.0905, "high": 1.0907, "low": 1.0899}]
        swing_highs = [
            {"index": 0, "price": 1.0906},
            {"index": 0, "price": 1.0910},
        ]
        swing_lows = [
            {"index": 0, "price": 1.0895},
            {"index": 0, "price": 1.0898},
        ]
        candles.append({"open": 1.0908, "close": 1.0905, "high": 1.0915, "low": 1.0903})
        result = self.detector.detect(candles, swing_highs, swing_lows, "BULLISH")
        assert result.signal_type == StructureType.NONE

    def test_wick_only_below_swing_low_not_bos(self):
        """
        Mèche basse dépasse le swing low mais body ne descend pas → pas de BOS.
        open=1.0902, close=1.0904 → body_low=1.0902
        swing_low=1.0900 → body_low (1.0902) > swing_low (1.0900) → NONE
        """
        candles = [{"open": 1.0905, "close": 1.0902, "high": 1.0906, "low": 1.0901}]
        swing_highs = [
            {"index": 0, "price": 1.0910},
            {"index": 0, "price": 1.0908},
        ]
        swing_lows = [
            {"index": 0, "price": 1.0900},
            {"index": 0, "price": 1.0898},
        ]
        candles.append({"open": 1.0902, "close": 1.0904, "high": 1.0905, "low": 1.0895})
        result = self.detector.detect(candles, swing_highs, swing_lows, "BEARISH")
        assert result.signal_type == StructureType.NONE
