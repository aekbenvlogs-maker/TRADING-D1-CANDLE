from enum import Enum

class RiskCheckResult(Enum):
    ALLOWED = "ALLOWED"
    BLOCKED_DAILY_LIMIT = "BLOCKED: DAILY_LOSS_LIMIT"
    BLOCKED_MAX_PAIRS = "BLOCKED: MAX_OPEN_PAIRS"

class RiskManager:
    def __init__(
        self,
        risk_pct: float = 1.0,
        daily_loss_limit_pct: float = 3.0,
        max_open_pairs: int = 1,
        lot_type: str = "mini",
    ) -> None: ...
    def calculate_lot_size(
        self,
        equity: float,
        sl_pips: float,
        pair: str,
        spot_price: float = 1.0,
    ) -> float: ...
    def check_daily_limit(
        self,
        equity_start: float,
        equity_current: float,
    ) -> RiskCheckResult: ...
    def check_max_pairs(self, open_pairs_count: int) -> RiskCheckResult: ...
