# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/core/risk_manager.pyx
# DESCRIPTION  : Position sizing, daily loss limit, max pairs
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False

from enum import Enum


class RiskCheckResult(Enum):
    ALLOWED = "ALLOWED"
    BLOCKED_DAILY_LIMIT = "BLOCKED: DAILY_LOSS_LIMIT"
    BLOCKED_MAX_PAIRS = "BLOCKED: MAX_OPEN_PAIRS"


cdef class RiskManager:
    """
    Gère le risque de position pour TRADING-D1-BOUGIE.

    Responsabilités :
      - Calcul du lot size : (equity × risk_pct) / (sl_pips × pip_value)
      - Surveillance limite journalière : shutdown si P&L ≤ -daily_loss_limit_pct%
      - Max simultané : max_open_pairs paires ouvertes en même temps
    """
    cdef double risk_pct
    cdef double daily_loss_limit_pct
    cdef int max_open_pairs
    cdef double lot_type_multiplier   # 100000 standard | 10000 mini | 1000 micro

    def __init__(
        self,
        double risk_pct=1.0,
        double daily_loss_limit_pct=3.0,
        int max_open_pairs=1,
        str lot_type="mini",
    ):
        self.risk_pct = risk_pct
        self.daily_loss_limit_pct = daily_loss_limit_pct
        self.max_open_pairs = max_open_pairs
        if lot_type == "standard":
            self.lot_type_multiplier = 100_000.0
        elif lot_type == "mini":
            self.lot_type_multiplier = 10_000.0
        elif lot_type == "micro":
            self.lot_type_multiplier = 1_000.0
        else:
            raise ValueError(f"lot_type must be standard/mini/micro, got '{lot_type}'")

    cpdef double calculate_lot_size(
        self,
        double equity,
        double sl_pips,
        str pair,
    ):
        """
        Calcule la taille de position en lots.

        Formule : (equity × risk_pct/100) / (sl_pips × pip_value_per_lot)

        Args:
            equity: capital disponible en USD
            sl_pips: distance SL en pips (incluant spread + slippage)
            pair: identifiant paire (pour détection JPY)

        Returns:
            double: taille en lots, arrondie à 2 décimales

        Raises:
            ValueError: si sl_pips <= 0 ou equity <= 0
        """
        if equity <= 0:
            raise ValueError(f"equity must be > 0, got {equity}")
        if sl_pips <= 0:
            raise ValueError(f"sl_pips must be > 0, got {sl_pips}")

        cdef double pip_size = 0.01 if "JPY" in pair.upper() else 0.0001
        # pip_value_per_lot = pip_size × lot_size_units × 1 USD (simplifié USD quote)
        cdef double pip_value_per_lot = pip_size * self.lot_type_multiplier
        cdef double risk_amount = equity * (self.risk_pct / 100.0)
        cdef double lot_size = risk_amount / (sl_pips * pip_value_per_lot)

        # Arrondir au lot inférieur (prudence)
        return round(max(0.01, round(lot_size, 2)), 2)

    cpdef object check_daily_limit(self, double equity_start, double equity_current):
        """
        Vérifie si la limite de perte journalière est atteinte.

        Args:
            equity_start: equity au début de session
            equity_current: equity actuelle

        Returns:
            RiskCheckResult: ALLOWED | BLOCKED_DAILY_LIMIT
        """
        if equity_start <= 0:
            raise ValueError("equity_start must be > 0")

        cdef double daily_pnl_pct = (
            (equity_current - equity_start) / equity_start
        ) * 100.0

        if daily_pnl_pct <= -self.daily_loss_limit_pct:
            return RiskCheckResult.BLOCKED_DAILY_LIMIT

        return RiskCheckResult.ALLOWED

    cpdef object check_max_pairs(self, int open_pairs_count):
        """
        Vérifie si le nombre maximum de paires ouvertes est atteint.

        Args:
            open_pairs_count: nombre de paires actuellement ouvertes

        Returns:
            RiskCheckResult: ALLOWED | BLOCKED_MAX_PAIRS
        """
        if open_pairs_count >= self.max_open_pairs:
            return RiskCheckResult.BLOCKED_MAX_PAIRS

        return RiskCheckResult.ALLOWED
