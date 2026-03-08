# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_entry_validator_valid.py
# DESCRIPTION  : Tests EntryValidator — valide entrée long aux 4 conditions
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

from trading_d1_bougie.core.d1_range_builder import D1RangeBuilder
from trading_d1_bougie.core.entry_validator import (
    EntryValidator,
    ValidationResult,  # noqa: F401
    ValidationStatus,
)
from trading_d1_bougie.core.trend_detector import TrendBias
from trading_d1_bougie.core.structure_detector import StructureSignal, StructureType


def _make_d1():
    """
    D1Range EURUSD fictif : high=1.10000, low=1.09000.
    fibo_forbidden_pct=5% → zone=[1.09450, 1.09550]
    proximity_buffer_pct=10% → prox_lower=1.09100, prox_upper=1.09900
    """
    return D1RangeBuilder(
        fibo_forbidden_pct=5.0, proximity_buffer_pct=10.0
    ).build("EURUSD", d1_high=1.10000, d1_low=1.09000)


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
