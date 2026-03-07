# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/core/d1_range_builder.pyx
# DESCRIPTION  : Construction du rectangle D1 + zones Fibo
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

from dataclasses import dataclass


@dataclass
cdef class D1Range:
    """Rectangle D1 avec zones Fibo calculées."""
    cdef public double high
    cdef public double low
    cdef public double mid
    cdef public double fibo_zone_upper
    cdef public double fibo_zone_lower
    cdef public double proximity_upper
    cdef public double proximity_lower
    cdef public str pair


cdef class D1RangeBuilder:
    """
    Construit le rectangle D1 à partir de la bougie de la veille.

    Calcule :
      - D1_HIGH, D1_LOW
      - D1_MID = 50% Fibo = (HIGH + LOW) / 2
      - Zone Fibo interdite : MID ± (hauteur × fibo_pct / 100)
      - Zones de proximité : LOW + buffer, HIGH - buffer
    """
    cdef double fibo_forbidden_pct
    cdef double proximity_buffer_pct

    def __init__(self, double fibo_forbidden_pct=5.0, double proximity_buffer_pct=10.0):
        self.fibo_forbidden_pct = fibo_forbidden_pct
        self.proximity_buffer_pct = proximity_buffer_pct

    cpdef D1Range build(self, str pair, double d1_high, double d1_low):
        """
        Construit un objet D1Range depuis les extrêmes de la bougie D1 de la veille.

        Args:
            pair: identifiant de la paire (ex: "EURUSD")
            d1_high: plus haut de la bougie D1
            d1_low: plus bas de la bougie D1

        Returns:
            D1Range: rectangle D1 avec toutes les zones calculées

        Raises:
            ValueError: si d1_high <= d1_low
        """
        if d1_high <= d1_low:
            raise ValueError(
                f"D1Range [{pair}]: d1_high ({d1_high}) must be > d1_low ({d1_low})"
            )

        cdef double height = d1_high - d1_low
        cdef double mid = (d1_high + d1_low) / 2.0
        cdef double fibo_offset = height * self.fibo_forbidden_pct / 100.0
        cdef double proximity_offset = height * self.proximity_buffer_pct / 100.0

        cdef D1Range result = D1Range.__new__(D1Range)
        result.pair = pair
        result.high = d1_high
        result.low = d1_low
        result.mid = mid
        result.fibo_zone_upper = mid + fibo_offset
        result.fibo_zone_lower = mid - fibo_offset
        result.proximity_upper = d1_high - proximity_offset
        result.proximity_lower = d1_low + proximity_offset

        return result
