from enum import Enum
from typing import Any

class StructureType(Enum):
    BOS = "BOS"
    CHOCH = "CHoCH"
    NONE = "NONE"

class StructureSignal:
    signal_type: StructureType
    trigger_price: float
    trigger_index: int
    direction: str
    def __init__(
        self,
        signal_type: StructureType,
        trigger_price: float = 0.0,
        trigger_index: int = -1,
        direction: str = "NONE",
    ) -> None: ...

class StructureDetector:
    def detect(
        self,
        candles: list[dict[str, Any]],
        swing_highs: list[dict[str, Any]],
        swing_lows: list[dict[str, Any]],
        current_trend: str,
    ) -> StructureSignal: ...
