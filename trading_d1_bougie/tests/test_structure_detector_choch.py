# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_structure_detector_choch.py
# DESCRIPTION  : Tests StructureDetector — détection CHoCH retournement
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

from trading_d1_bougie.core.structure_detector import StructureDetector, StructureType
from trading_d1_bougie.tests.test_structure_detector_bos import _c


class TestStructureDetectorCHoCH:
    """Test 2 : Détecte CHoCH sur retournement de tendance."""

    def setup_method(self):
        self.detector = StructureDetector()

    def test_choch_bullish_to_bearish(self):
        """CHoCH : tendance BULLISH cassée → signal BEARISH."""
        candles = [_c(1.0900, 1.0905), _c(1.0902, 1.0908)]
        swing_highs = [{"index": 0, "price": 1.0908}, {"index": 1, "price": 1.0912}]
        swing_lows = [{"index": 0, "price": 1.0895}, {"index": 1, "price": 1.0898}]
        # Bougie dont le body passe SOUS le prev_swing_low (1.0895)
        candles.append(_c(1.0896, 1.0892))
        result = self.detector.detect(candles, swing_highs, swing_lows, "BULLISH")

        assert result.signal_type == StructureType.CHOCH
        assert result.direction == "BEARISH"

    def test_choch_bearish_to_bullish(self):
        """CHoCH : tendance BEARISH cassée → signal BULLISH."""
        candles = [_c(1.0910, 1.0905), _c(1.0908, 1.0902)]
        swing_highs = [{"index": 0, "price": 1.0915}, {"index": 1, "price": 1.0912}]
        swing_lows = [{"index": 0, "price": 1.0900}, {"index": 1, "price": 1.0897}]
        # Bougie dont le body passe AU-DESSUS du prev_swing_high (1.0915)
        candles.append(_c(1.0912, 1.0918))
        result = self.detector.detect(candles, swing_highs, swing_lows, "BEARISH")

        assert result.signal_type == StructureType.CHOCH
        assert result.direction == "BULLISH"
