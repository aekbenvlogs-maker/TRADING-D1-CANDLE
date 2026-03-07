# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/core/order_manager.pyx
# DESCRIPTION  : Calcul SL/TP + envoi bracket order IB Gateway
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

import math
from dataclasses import dataclass


cdef class OrderSpec:
    """Spécifications complètes d'un ordre bracket."""
    cdef public str pair
    cdef public str direction       # "LONG" | "SHORT"
    cdef public double entry_price
    cdef public double sl_price
    cdef public double tp_price
    cdef public double sl_pips
    cdef public double tp_pips
    cdef public double lot_size
    cdef public int price_decimals

    def __repr__(self):
        return (
            f"OrderSpec({self.pair} {self.direction} "
            f"@ {self.entry_price:.{self.price_decimals}f} | "
            f"SL={self.sl_price:.{self.price_decimals}f} "
            f"TP={self.tp_price:.{self.price_decimals}f} "
            f"lots={self.lot_size})"
        )


cdef class OrderManager:
    """
    Calcule les niveaux SL/TP et construit le bracket order IB.

    Précision :
      - 4 décimales pour les paires standard (EURUSD, GBPUSD…)
      - 2 décimales pour les paires JPY (USDJPY…)
    Pip value :
      - 1 pip = 0.0001 pour paires standard
      - 1 pip = 0.01   pour paires JPY
    """
    cdef double rr_ratio
    cdef double spread_buffer_pips

    def __init__(self, double rr_ratio=2.0, double spread_buffer_pips=0.5):
        self.rr_ratio = rr_ratio
        self.spread_buffer_pips = spread_buffer_pips

    cdef int _get_decimals(self, str pair):
        return 2 if "JPY" in pair.upper() else 4

    cdef double _pip_size(self, str pair):
        return 0.01 if "JPY" in pair.upper() else 0.0001

    cpdef OrderSpec build(
        self,
        str pair,
        str direction,
        double entry_price,
        double swing_sl_price,
        double lot_size,
    ):
        """
        Construit les niveaux d'un bracket order.

        Args:
            pair: identifiant paire (ex: "EURUSD")
            direction: "LONG" | "SHORT"
            entry_price: prix d'entrée (close de la bougie signal)
            swing_sl_price: niveau swing servant de stop loss
            lot_size: taille de position calculée par RiskManager

        Returns:
            OrderSpec: spécification complète de l'ordre

        Raises:
            ValueError: si direction invalide ou sl du mauvais côté
        """
        if direction not in ("LONG", "SHORT"):
            raise ValueError(f"direction must be LONG or SHORT, got '{direction}'")

        cdef int decimals = self._get_decimals(pair)
        cdef double pip = self._pip_size(pair)
        cdef double spread_offset = self.spread_buffer_pips * pip

        cdef double sl_price
        cdef double tp_price
        cdef double sl_pips
        cdef double tp_pips

        if direction == "LONG":
            sl_price = round(swing_sl_price - spread_offset, decimals)
            sl_pips = round((entry_price - sl_price) / pip, 1)
            if sl_pips <= 0:
                raise ValueError(
                    f"LONG SL must be below entry. sl_pips={sl_pips}"
                )
            tp_pips = round(sl_pips * self.rr_ratio, 1)
            tp_price = round(entry_price + tp_pips * pip, decimals)
        else:  # SHORT
            sl_price = round(swing_sl_price + spread_offset, decimals)
            sl_pips = round((sl_price - entry_price) / pip, 1)
            if sl_pips <= 0:
                raise ValueError(
                    f"SHORT SL must be above entry. sl_pips={sl_pips}"
                )
            tp_pips = round(sl_pips * self.rr_ratio, 1)
            tp_price = round(entry_price - tp_pips * pip, decimals)

        cdef OrderSpec spec = OrderSpec.__new__(OrderSpec)
        spec.pair = pair
        spec.direction = direction
        spec.entry_price = round(entry_price, decimals)
        spec.sl_price = sl_price
        spec.tp_price = tp_price
        spec.sl_pips = sl_pips
        spec.tp_pips = tp_pips
        spec.lot_size = lot_size
        spec.price_decimals = decimals

        return spec
