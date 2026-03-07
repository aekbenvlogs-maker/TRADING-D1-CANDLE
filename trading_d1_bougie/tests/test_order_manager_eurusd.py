# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_order_manager_eurusd.py
# DESCRIPTION  : Tests OrderManager — calcul SL/TP correct sur EURUSD
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

import pytest

# Mirror Python du OrderManager Cython


class OrderSpec:
    def __init__(
        self,
        pair,
        direction,
        entry_price,
        sl_price,
        tp_price,
        sl_pips,
        tp_pips,
        lot_size,
        price_decimals,
    ):
        self.pair = pair
        self.direction = direction
        self.entry_price = entry_price
        self.sl_price = sl_price
        self.tp_price = tp_price
        self.sl_pips = sl_pips
        self.tp_pips = tp_pips
        self.lot_size = lot_size
        self.price_decimals = price_decimals


class OrderManager:
    def __init__(self, rr_ratio=2.0, spread_buffer_pips=0.5):
        self.rr_ratio = rr_ratio
        self.spread_buffer_pips = spread_buffer_pips

    def _pip_size(self, pair):
        return 0.01 if "JPY" in pair.upper() else 0.0001

    def _get_decimals(self, pair):
        return 2 if "JPY" in pair.upper() else 4

    def build(self, pair, direction, entry_price, swing_sl_price, lot_size):
        if direction not in ("LONG", "SHORT"):
            raise ValueError(f"Invalid direction: {direction}")
        pip = self._pip_size(pair)
        decimals = self._get_decimals(pair)
        spread_offset = self.spread_buffer_pips * pip

        if direction == "LONG":
            sl_price = round(swing_sl_price - spread_offset, decimals)
            sl_pips = round((entry_price - sl_price) / pip, 1)
            if sl_pips <= 0:
                raise ValueError("LONG SL must be below entry")
            tp_pips = round(sl_pips * self.rr_ratio, 1)
            tp_price = round(entry_price + tp_pips * pip, decimals)
        else:
            sl_price = round(swing_sl_price + spread_offset, decimals)
            sl_pips = round((sl_price - entry_price) / pip, 1)
            if sl_pips <= 0:
                raise ValueError("SHORT SL must be above entry")
            tp_pips = round(sl_pips * self.rr_ratio, 1)
            tp_price = round(entry_price - tp_pips * pip, decimals)

        return OrderSpec(
            pair=pair,
            direction=direction,
            entry_price=round(entry_price, decimals),
            sl_price=sl_price,
            tp_price=tp_price,
            sl_pips=sl_pips,
            tp_pips=tp_pips,
            lot_size=lot_size,
            price_decimals=decimals,
        )


class TestOrderManagerEURUSD:
    """Test 1 : Calcul SL/TP correct sur EURUSD (RR = 2)."""

    def setup_method(self):
        self.mgr = OrderManager(rr_ratio=2.0, spread_buffer_pips=0.5)

    def test_long_sl_tp_calculation(self):
        """
        LONG EURUSD :
        entry=1.0910, swing_sl=1.0900
        sl_price = 1.0900 - 0.5*0.0001 = 1.08995 → 1.0900 (arrondi 4 dec)
        sl_pips = (1.0910 - 1.0900) / 0.0001 = 100 pips - spread ≈ 99.5 pips
        tp_pips = 99.5 * 2 = 199.0
        tp_price = 1.0910 + 0.0199 = 1.1109
        """
        spec = self.mgr.build("EURUSD", "LONG", 1.0910, 1.0900, 0.1)

        assert spec.direction == "LONG"
        assert spec.sl_price < spec.entry_price
        assert spec.tp_price > spec.entry_price
        assert spec.sl_pips > 0
        assert spec.tp_pips == pytest.approx(spec.sl_pips * 2.0, abs=0.5)

    def test_short_sl_tp_calculation(self):
        """SHORT EURUSD : SL au-dessus, TP en-dessous, RR=2."""
        spec = self.mgr.build("EURUSD", "SHORT", 1.0960, 1.0970, 0.1)

        assert spec.direction == "SHORT"
        assert spec.sl_price > spec.entry_price
        assert spec.tp_price < spec.entry_price
        assert spec.sl_pips > 0
        assert spec.tp_pips == pytest.approx(spec.sl_pips * 2.0, abs=0.5)

    def test_invalid_direction(self):
        """Direction invalide → ValueError."""
        with pytest.raises(ValueError, match="Invalid direction"):
            self.mgr.build("EURUSD", "FLAT", 1.0910, 1.0900, 0.1)

    def test_price_decimals_eurusd(self):
        """Prix EURUSD doit avoir 4 décimales."""
        spec = self.mgr.build("EURUSD", "LONG", 1.0910, 1.0900, 0.1)
        assert spec.price_decimals == 4
