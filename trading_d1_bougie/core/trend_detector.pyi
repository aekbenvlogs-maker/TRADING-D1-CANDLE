from enum import Enum
from typing import Any

class TrendBias(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

class TrendDetector:
    def __init__(self, swing_lookback: int = 5) -> None: ...
    def find_swing_highs(
        self,
        candles: list[dict[str, Any]],
    ) -> list[dict[str, Any]]: ...
    def find_swing_lows(
        self,
        candles: list[dict[str, Any]],
    ) -> list[dict[str, Any]]: ...
    def detect(self, candles: list[dict[str, Any]]) -> TrendBias: ...
