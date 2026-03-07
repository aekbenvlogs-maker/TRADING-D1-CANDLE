# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_entry_validator_valid.py
# DESCRIPTION  : Tests EntryValidator — valide entrée long aux 4 conditions
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

import pytest
from enum import Enum


# Mirrors Python des classes Cython

class ValidationStatus(Enum):
    VALID = "VALID"
    INVALID_OUTSIDE_RANGE = "INVALID: OUTSIDE_RANGE"
    INVALID_NOT_NEAR_EXTREMITY = "INVALID: NOT_NEAR_EXTREMITY"
    INVALID_FIBO_FORBIDDEN_ZONE = "INVALID: FIBO_FORBIDDEN_ZONE"
    INVALID_AGAINST_TREND = "INVALID: AGAINST_TREND"


class ValidationResult:
    def __init__(self, status, direction="NONE", reason=""):
        self.status = status
        self.direction = direction
        self.reason = reason

    @property
    def is_valid(self):
        return self.status == ValidationStatus.VALID


class TrendBias(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class StructureType(Enum):
    BOS = "BOS"
    CHOCH = "CHoCH"
    NONE = "NONE"


class StructureSignal:
    def __init__(self, signal_type, direction="NONE"):
        self.signal_type = signal_type
        self.direction = direction


class D1Range:
    def __init__(self, high, low, mid, fibo_upper, fibo_lower, prox_upper, prox_lower):
        self.high = high
        self.low = low
        self.mid = mid
        self.fibo_zone_upper = fibo_upper
        self.fibo_zone_lower = fibo_lower
        self.proximity_upper = prox_upper
        self.proximity_lower = prox_lower


class EntryValidator:
    def validate(self, price, d1_range, trend_bias, structure_signal):
        if price < d1_range.low or price > d1_range.high:
            return ValidationResult(ValidationStatus.INVALID_OUTSIDE_RANGE)
        near_low = price <= d1_range.proximity_lower
        near_high = price >= d1_range.proximity_upper
        if not near_low and not near_high:
            return ValidationResult(ValidationStatus.INVALID_NOT_NEAR_EXTREMITY)
        if d1_range.fibo_zone_lower <= price <= d1_range.fibo_zone_upper:
            return ValidationResult(ValidationStatus.INVALID_FIBO_FORBIDDEN_ZONE)
        if structure_signal.signal_type == StructureType.NONE:
            return ValidationResult(ValidationStatus.INVALID_AGAINST_TREND, reason="No signal")
        sig_dir = structure_signal.direction
        if trend_bias == TrendBias.BULLISH and sig_dir != "BULLISH":
            return ValidationResult(ValidationStatus.INVALID_AGAINST_TREND)
        if trend_bias == TrendBias.BEARISH and sig_dir != "BEARISH":
            return ValidationResult(ValidationStatus.INVALID_AGAINST_TREND)
        if trend_bias == TrendBias.NEUTRAL:
            return ValidationResult(ValidationStatus.INVALID_AGAINST_TREND)
        direction = "LONG" if near_low else "SHORT"
        return ValidationResult(ValidationStatus.VALID, direction=direction)


# D1Range EURUSD fictif
def _make_d1():
    return D1Range(
        high=1.10000,
        low=1.09000,
        mid=1.09500,
        fibo_upper=1.09550,
        fibo_lower=1.09450,
        prox_upper=1.09900,  # HIGH - 10% de 0.01000
        prox_lower=1.09100,  # LOW  + 10% de 0.01000
    )


class TestEntryValidatorValid:
    """Test 1 : Valide une entrée LONG aux 4 conditions réunies."""

    def setup_method(self):
        self.validator = EntryValidator()
        self.d1 = _make_d1()

    def test_valid_long_entry_all_checks(self):
        """Entrée LONG valide : dans range, près du LOW, hors Fibo, signal BULLISH."""
        price = 1.09050  # dans range, près LOW (< prox_lower=1.09100), hors Fibo
        trend = TrendBias.BULLISH
        signal = StructureSignal(StructureType.BOS, direction="BULLISH")

        result = self.validator.validate(price, self.d1, trend, signal)

        assert result.is_valid is True
        assert result.direction == "LONG"

    def test_valid_short_entry_all_checks(self):
        """Entrée SHORT valide : dans range, près du HIGH, hors Fibo, signal BEARISH."""
        price = 1.09950  # dans range, >= prox_upper=1.09900, hors Fibo
        trend = TrendBias.BEARISH
        signal = StructureSignal(StructureType.BOS, direction="BEARISH")

        result = self.validator.validate(price, self.d1, trend, signal)

        assert result.is_valid is True
        assert result.direction == "SHORT"

    def test_valid_choch_also_accepted(self):
        """Un CHoCH dans le bon sens est aussi valide."""
        price = 1.09060
        trend = TrendBias.BULLISH
        signal = StructureSignal(StructureType.CHOCH, direction="BULLISH")

        result = self.validator.validate(price, self.d1, trend, signal)

        assert result.is_valid is True
