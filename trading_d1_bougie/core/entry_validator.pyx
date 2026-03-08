# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/core/entry_validator.pyx
# DESCRIPTION  : Validation des 4 conditions d'entrée
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

from enum import Enum


class ValidationStatus(Enum):
    VALID = "VALID"
    INVALID_OUTSIDE_RANGE = "INVALID: OUTSIDE_RANGE"
    INVALID_NOT_NEAR_EXTREMITY = "INVALID: NOT_NEAR_EXTREMITY"
    INVALID_FIBO_FORBIDDEN_ZONE = "INVALID: FIBO_FORBIDDEN_ZONE"
    INVALID_AGAINST_TREND = "INVALID: AGAINST_TREND"


cdef class ValidationResult:
    """Résultat de la validation d'une entrée potentielle."""
    cdef public object status       # ValidationStatus
    cdef public str direction       # "LONG" | "SHORT" | "NONE"
    cdef public str reason

    def __init__(self, object status, str direction="NONE", str reason=""):
        self.status = status
        self.direction = direction
        self.reason = reason

    @property
    def is_valid(self):
        return self.status == ValidationStatus.VALID


cdef class EntryValidator:
    """
    Valide les 4 conditions d'entrée de la stratégie TRADING-D1-BOUGIE.

    Check 1 : Prix à l'intérieur du rectangle D1
    Check 2 : Prix dans la zone de proximité d'une extrémité
    Check 3 : Prix hors de la zone Fibo interdite (autour du midpoint)
    Check 4 : Signal dans le sens de la tendance M15
    """

    cpdef ValidationResult validate(
        self,
        double price,
        object d1_range,
        object trend_bias,
        object structure_signal,
    ):
        """
        Valide les conditions d'entrée.

        Args:
            price: prix courant (close de la bougie M15)
            d1_range: objet D1Range (high, low, mid, zones)
            trend_bias: TrendBias (BULLISH / BEARISH / NEUTRAL)
            structure_signal: StructureSignal (BOS / CHoCH / NONE)

        Returns:
            ValidationResult: statut + direction + raison
        """
        from trading_d1_bougie.core.trend_detector import TrendBias
        from trading_d1_bougie.core.structure_detector import StructureType

        # ------------------------------------------------------------------ #
        # Check 1 : Prix dans le rectangle D1                                #
        # ------------------------------------------------------------------ #
        if price < d1_range.low or price > d1_range.high:
            return ValidationResult(
                ValidationStatus.INVALID_OUTSIDE_RANGE,
                reason=f"price={price:.5f} outside D1 [{d1_range.low:.5f}, {d1_range.high:.5f}]",
            )

        # ------------------------------------------------------------------ #
        # Check 2 : Prix dans la zone de proximité d'une extrémité           #
        # ------------------------------------------------------------------ #
        cdef bint near_low = price <= d1_range.proximity_lower
        cdef bint near_high = price >= d1_range.proximity_upper

        if not near_low and not near_high:
            return ValidationResult(
                ValidationStatus.INVALID_NOT_NEAR_EXTREMITY,
                reason=f"price={price:.5f} not near extremity "
                       f"(LOW zone ≤{d1_range.proximity_lower:.5f} | "
                       f"HIGH zone ≥{d1_range.proximity_upper:.5f})",
            )

        # ------------------------------------------------------------------ #
        # Check 3 : Prix hors zone Fibo interdite                            #
        # ------------------------------------------------------------------ #
        if d1_range.fibo_zone_lower <= price <= d1_range.fibo_zone_upper:
            return ValidationResult(
                ValidationStatus.INVALID_FIBO_FORBIDDEN_ZONE,
                reason=f"price={price:.5f} inside Fibo zone "
                       f"[{d1_range.fibo_zone_lower:.5f}, {d1_range.fibo_zone_upper:.5f}]",
            )

        # ------------------------------------------------------------------ #
        # Check 4 : Signal dans le sens de la tendance                       #
        # ------------------------------------------------------------------ #
        # M4 (Option A): Cette stratégie trade BOS uniquement.
        # Un CHoCH signale un retournement de tendance — trop risqué en
        # D1/M15 sans confirmation supplémentaire (réservé Sprint 7+).
        if structure_signal.signal_type == StructureType.CHOCH:
            return ValidationResult(
                ValidationStatus.INVALID_AGAINST_TREND,
                reason="CHoCH not traded in current strategy (BOS-only)",
            )

        if structure_signal.signal_type == StructureType.NONE:
            return ValidationResult(
                ValidationStatus.INVALID_AGAINST_TREND,
                reason="No structure signal (BOS/CHoCH) detected",
            )

        cdef str signal_dir = structure_signal.direction

        if trend_bias == TrendBias.BULLISH and signal_dir != "BULLISH":
            return ValidationResult(
                ValidationStatus.INVALID_AGAINST_TREND,
                reason=f"Trend=BULLISH but signal direction={signal_dir}",
            )

        if trend_bias == TrendBias.BEARISH and signal_dir != "BEARISH":
            return ValidationResult(
                ValidationStatus.INVALID_AGAINST_TREND,
                reason=f"Trend=BEARISH but signal direction={signal_dir}",
            )

        if trend_bias.value == "NEUTRAL":
            return ValidationResult(
                ValidationStatus.INVALID_AGAINST_TREND,
                reason="Trend=NEUTRAL — no directional bias",
            )

        # ------------------------------------------------------------------ #
        # ✅ Toutes les conditions remplies                                   #
        # ------------------------------------------------------------------ #
        cdef str direction = "LONG" if near_low else "SHORT"

        return ValidationResult(
            ValidationStatus.VALID,
            direction=direction,
            reason=f"All 4 checks passed — direction={direction}",
        )
