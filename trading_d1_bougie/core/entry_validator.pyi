from enum import Enum
from trading_d1_bougie.core.d1_range_builder import D1Range
from trading_d1_bougie.core.trend_detector import TrendBias
from trading_d1_bougie.core.structure_detector import StructureSignal

class ValidationStatus(Enum):
    VALID = "VALID"
    INVALID_OUTSIDE_RANGE = "INVALID: OUTSIDE_RANGE"
    INVALID_NOT_NEAR_EXTREMITY = "INVALID: NOT_NEAR_EXTREMITY"
    INVALID_FIBO_FORBIDDEN_ZONE = "INVALID: FIBO_FORBIDDEN_ZONE"
    INVALID_AGAINST_TREND = "INVALID: AGAINST_TREND"

class ValidationResult:
    status: ValidationStatus
    direction: str
    reason: str
    @property
    def is_valid(self) -> bool: ...
    def __init__(
        self,
        status: ValidationStatus,
        direction: str = "NONE",
        reason: str = "",
    ) -> None: ...

class EntryValidator:
    def validate(
        self,
        price: float,
        d1_range: D1Range,
        trend_bias: TrendBias,
        structure_signal: StructureSignal,
    ) -> ValidationResult: ...
