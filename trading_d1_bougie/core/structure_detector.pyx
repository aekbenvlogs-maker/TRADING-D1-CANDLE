# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/core/structure_detector.pyx
# DESCRIPTION  : Détection BOS / CHoCH sur bougies M15
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

from enum import Enum
from dataclasses import dataclass, field


class StructureType(Enum):
    BOS = "BOS"
    CHOCH = "CHoCH"
    NONE = "NONE"


cdef class StructureSignal:
    """Signal de structure détecté sur les bougies M15."""
    cdef public object signal_type   # StructureType
    cdef public double trigger_price
    cdef public int trigger_index
    cdef public str direction        # "BULLISH" | "BEARISH" | "NONE"

    def __init__(
        self,
        object signal_type,
        double trigger_price=0.0,
        int trigger_index=-1,
        str direction="NONE",
    ):
        self.signal_type = signal_type
        self.trigger_price = trigger_price
        self.trigger_index = trigger_index
        self.direction = direction


cdef class StructureDetector:
    """
    Détecte les événements de structure de marché (BOS / CHoCH).

    Règles :
      - BOS  : le BODY de la bougie clôture AU-DELÀ du dernier swing précédent
      - CHoCH: cassure du dernier swing opposé (retournement de structure)
      - Cassure par mèche seule → rejetée (body uniquement)
    """

    cpdef StructureSignal detect(
        self,
        list candles,
        list swing_highs,
        list swing_lows,
        str current_trend,
    ):
        """
        Analyse les bougies M15 pour détecter BOS ou CHoCH.

        Args:
            candles: liste de bougies M15 dict {"open","high","low","close"}
            swing_highs: liste de swing highs [{index, price}]
            swing_lows:  liste de swing lows  [{index, price}]
            current_trend: "BULLISH" | "BEARISH" | "NEUTRAL"

        Returns:
            StructureSignal: résultat de la détection
        """
        if not candles or not swing_highs or not swing_lows:
            return StructureSignal(StructureType.NONE)

        cdef int nc = len(candles)
        cdef int nsh = len(swing_highs)
        cdef int nsl = len(swing_lows)
        cdef int last_idx = nc - 1

        cdef dict last_candle = candles[last_idx]
        cdef double body_high = max(last_candle["open"], last_candle["close"])
        cdef double body_low = min(last_candle["open"], last_candle["close"])

        # Dernier swing high et low
        cdef double last_swing_high = swing_highs[nsh - 1]["price"]
        cdef double last_swing_low = swing_lows[nsl - 1]["price"]
        cdef double prev_swing_high = swing_highs[nsh - 2]["price"] if nsh >= 2 else last_swing_high
        cdef double prev_swing_low = swing_lows[nsl - 2]["price"] if nsl >= 2 else last_swing_low

        # ------------------------------------------------------------------ #
        # BOS haussier : body clôture AU-DESSUS du dernier swing high         #
        # ------------------------------------------------------------------ #
        if current_trend == "BULLISH" and body_high > last_swing_high:
            return StructureSignal(
                StructureType.BOS,
                trigger_price=last_candle["close"],
                trigger_index=last_idx,
                direction="BULLISH",
            )

        # ------------------------------------------------------------------ #
        # BOS baissier : body clôture EN-DESSOUS du dernier swing low         #
        # ------------------------------------------------------------------ #
        if current_trend == "BEARISH" and body_low < last_swing_low:
            return StructureSignal(
                StructureType.BOS,
                trigger_price=last_candle["close"],
                trigger_index=last_idx,
                direction="BEARISH",
            )

        # ------------------------------------------------------------------ #
        # CHoCH haussier → BEARISH : body clôture sous le dernier swing low   #
        # (retournement de la tendance haussière)                             #
        # ------------------------------------------------------------------ #
        if current_trend == "BULLISH" and body_low < prev_swing_low:
            return StructureSignal(
                StructureType.CHOCH,
                trigger_price=last_candle["close"],
                trigger_index=last_idx,
                direction="BEARISH",
            )

        # ------------------------------------------------------------------ #
        # CHoCH baissier → BULLISH : body clôture au-dessus du dernier HH     #
        # ------------------------------------------------------------------ #
        if current_trend == "BEARISH" and body_high > prev_swing_high:
            return StructureSignal(
                StructureType.CHOCH,
                trigger_price=last_candle["close"],
                trigger_index=last_idx,
                direction="BULLISH",
            )

        return StructureSignal(StructureType.NONE)
