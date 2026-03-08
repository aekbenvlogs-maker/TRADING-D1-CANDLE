from typing import Any

class D1Range:
    pair: str
    high: float
    low: float
    mid: float
    fibo_zone_upper: float
    fibo_zone_lower: float
    proximity_upper: float
    proximity_lower: float

class D1RangeBuilder:
    def __init__(
        self,
        fibo_forbidden_pct: float = 5.0,
        proximity_buffer_pct: float = 10.0,
    ) -> None: ...
    def build(self, pair: str, d1_high: float, d1_low: float) -> D1Range: ...
