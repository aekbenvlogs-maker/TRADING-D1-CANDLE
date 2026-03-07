# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_structure_detector_wick.py
# DESCRIPTION  : Tests StructureDetector — rejette cassure mèche seule
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

from trading_d1_bougie.tests.test_structure_detector_bos import (
    StructureDetector,
    StructureType,
)


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
            {"index": 0, "price": 1.0897},
        ]

        # Bougie avec mèche à 1.0915 mais body max = 1.0908 (< swing_high 1.0910)
        candles.append(
            {
                "open": 1.0908,
                "close": 1.0905,
                "high": 1.0915,  # mèche dépasse
                "low": 1.0904,
            }
        )
        result = self.detector.detect(candles, swing_highs, swing_lows, "BULLISH")
        assert result.signal_type == StructureType.NONE

    def test_wick_only_below_swing_low_not_bos(self):
        """
        Mèche basse dépasse le swing low mais body ne dépasse pas → pas de BOS.
        """
        candles = [{"open": 1.0905, "close": 1.0900, "high": 1.0907, "low": 1.0899}]
        swing_highs = [
            {"index": 0, "price": 1.0910},
            {"index": 0, "price": 1.0908},
        ]
        swing_lows = [
            {"index": 0, "price": 1.0896},
            {"index": 0, "price": 1.0898},
        ]

        # Bougie avec mèche à 1.0892 mais body min = close=1.0900 (> swing_low 1.0898)
        candles.append(
            {
                "open": 1.0902,
                "close": 1.0900,
                "high": 1.0904,
                "low": 1.0892,  # mèche dépasse
            }
        )
        result = self.detector.detect(candles, swing_highs, swing_lows, "BEARISH")
        assert result.signal_type == StructureType.NONE

    def test_body_breakout_is_bos(self):
        """
        Confirmation : si le body dépasse effectivement → BOS détecté.
        """
        candles = [{"open": 1.0900, "close": 1.0905, "high": 1.0907, "low": 1.0899}]
        swing_highs = [
            {"index": 0, "price": 1.0904},
            {"index": 0, "price": 1.0906},
        ]
        swing_lows = [
            {"index": 0, "price": 1.0895},
            {"index": 0, "price": 1.0897},
        ]

        # body_high = max(open=1.0905, close=1.0908) = 1.0908 > swing_high=1.0906 → BOS
        candles.append({"open": 1.0905, "close": 1.0908, "high": 1.0910, "low": 1.0904})
        result = self.detector.detect(candles, swing_highs, swing_lows, "BULLISH")
        assert result.signal_type == StructureType.BOS
