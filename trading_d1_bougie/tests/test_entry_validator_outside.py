# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_entry_validator_outside.py
# DESCRIPTION  : Tests EntryValidator — invalide si hors rectangle D1
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

import pytest

from trading_d1_bougie.core.entry_validator import EntryValidator, ValidationStatus
from trading_d1_bougie.core.trend_detector import TrendBias
from trading_d1_bougie.core.structure_detector import StructureSignal, StructureType
from trading_d1_bougie.tests.test_entry_validator_valid import _make_d1


class TestEntryValidatorOutsideRange:
    """Test 2 : Invalide si prix hors du rectangle D1."""

    def setup_method(self):
        self.validator = EntryValidator()
        self.d1 = _make_d1()  # high=1.10000, low=1.09000

    def test_invalid_above_d1_high(self):
        """Prix au-dessus du D1 HIGH → INVALID: OUTSIDE_RANGE."""
        result = self.validator.validate(
            1.10500,
            self.d1,
            TrendBias.BULLISH,
            StructureSignal(StructureType.BOS, direction="BULLISH"),
        )
        assert result.status == ValidationStatus.INVALID_OUTSIDE_RANGE
        assert result.is_valid is False

    def test_invalid_below_d1_low(self):
        """Prix en-dessous du D1 LOW → INVALID: OUTSIDE_RANGE."""
        result = self.validator.validate(
            1.08500,
            self.d1,
            TrendBias.BEARISH,
            StructureSignal(StructureType.BOS, direction="BEARISH"),
        )
        assert result.status == ValidationStatus.INVALID_OUTSIDE_RANGE
        assert result.is_valid is False

    def test_invalid_exactly_at_boundary_above(self):
        """Prix exactement au HIGH avec dépassement → INVALID."""
        result = self.validator.validate(
            1.10001,
            self.d1,
            TrendBias.BULLISH,
            StructureSignal(StructureType.BOS, direction="BULLISH"),
        )
        assert result.status == ValidationStatus.INVALID_OUTSIDE_RANGE

    @pytest.mark.parametrize("price", [1.08000, 1.07500, 1.11000, 1.15000])
    def test_invalid_far_outside_range(self, price):
        """Prix très loin du range → toujours INVALID: OUTSIDE_RANGE."""
        result = self.validator.validate(
            price,
            self.d1,
            TrendBias.BULLISH,
            StructureSignal(StructureType.BOS, direction="BULLISH"),
        )
        assert result.status == ValidationStatus.INVALID_OUTSIDE_RANGE
