class OrderSpec:
    pair: str
    direction: str
    entry_price: float
    sl_price: float
    tp_price: float
    sl_pips: float
    tp_pips: float
    lot_size: float
    price_decimals: int
    def __repr__(self) -> str: ...

class OrderManager:
    def __init__(
        self,
        rr_ratio: float = 2.0,
        spread_buffer_pips: float = 0.5,
    ) -> None: ...
    def build(
        self,
        pair: str,
        direction: str,
        entry_price: float,
        swing_sl_price: float,
        lot_size: float,
    ) -> OrderSpec: ...
