# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/core/trend_detector.pyx
# DESCRIPTION  : Détection tendance M15 via swing highs/lows (HH/HL)
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

from enum import Enum


class TrendBias(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


cdef class TrendDetector:
    """
    Détecte la tendance M15 via l'analyse des swing highs/lows.

    Logique :
      - HH (Higher High) + HL (Higher Low)  → BULLISH
      - LL (Lower Low)   + LH (Lower High)  → BEARISH
      - Sinon                                → NEUTRAL
    """
    cdef int swing_lookback

    def __init__(self, int swing_lookback=3):
        """
        Args:
            swing_lookback: nombre de bougies de chaque côté pour identifier un swing
        """
        self.swing_lookback = swing_lookback

    cpdef list find_swing_highs(self, list candles):
        """
        Identifie les swing highs dans une liste de bougies OHLCV.

        Args:
            candles: liste de dict {"open","high","low","close","volume"}

        Returns:
            list[dict]: swing highs avec index + price
        """
        cdef list swings = []
        cdef int n = len(candles)
        cdef int i, j
        cdef double price
        cdef bint is_swing

        for i in range(self.swing_lookback, n - self.swing_lookback):
            price = candles[i]["high"]
            is_swing = True
            for j in range(i - self.swing_lookback, i + self.swing_lookback + 1):
                if j != i and candles[j]["high"] >= price:
                    is_swing = False
                    break
            if is_swing:
                swings.append({"index": i, "price": price})

        return swings

    cpdef list find_swing_lows(self, list candles):
        """
        Identifie les swing lows dans une liste de bougies OHLCV.

        Args:
            candles: liste de dict {"open","high","low","close","volume"}

        Returns:
            list[dict]: swing lows avec index + price
        """
        cdef list swings = []
        cdef int n = len(candles)
        cdef int i, j
        cdef double price
        cdef bint is_swing

        for i in range(self.swing_lookback, n - self.swing_lookback):
            price = candles[i]["low"]
            is_swing = True
            for j in range(i - self.swing_lookback, i + self.swing_lookback + 1):
                if j != i and candles[j]["low"] <= price:
                    is_swing = False
                    break
            if is_swing:
                swings.append({"index": i, "price": price})

        return swings

    cpdef object detect(self, list candles):
        """
        Détecte la tendance depuis les bougies M15.

        Args:
            candles: liste d'au moins 2*(swing_lookback+1)+1 bougies M15

        Returns:
            TrendBias: BULLISH / BEARISH / NEUTRAL
        """
        cdef list highs = self.find_swing_highs(candles)
        cdef list lows = self.find_swing_lows(candles)

        if len(highs) < 2 or len(lows) < 2:
            return TrendBias.NEUTRAL

        cdef int nh = len(highs)
        cdef int nl = len(lows)

        # Deux derniers swing highs
        cdef double last_hh = highs[nh - 1]["price"]
        cdef double prev_hh = highs[nh - 2]["price"]

        # Deux derniers swing lows
        cdef double last_hl = lows[nl - 1]["price"]
        cdef double prev_hl = lows[nl - 2]["price"]

        cdef bint higher_highs = last_hh > prev_hh
        cdef bint higher_lows = last_hl > prev_hl
        cdef bint lower_lows = last_hl < prev_hl
        cdef bint lower_highs = last_hh < prev_hh

        if higher_highs and higher_lows:
            return TrendBias.BULLISH
        elif lower_lows and lower_highs:
            return TrendBias.BEARISH
        else:
            return TrendBias.NEUTRAL
