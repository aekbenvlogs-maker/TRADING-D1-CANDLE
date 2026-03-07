# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/tests/test_entry_validator_fibo.py
# DESCRIPTION  : Tests EntryValidator — invalide si zone Fibo interdite
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

import pytest
from trading_d1_bougie.tests.test_entry_validator_valid import (
    EntryValidator, TrendBias, StructureSignal, StructureType,
    ValidationStatus, D1Range, _make_d1
)


def _make_d1_wide_proximity():
    """
    D1Range avec zones de proximité larges (60% de la hauteur).
    Permet de tester la zone Fibo interdite : le prix près du midpoint
    est aussi considéré "près d'une extrémité" (check 2 passe, check 3 échoue).
    high=1.10000, low=1.09000, mid=1.09500
    fibo=[1.09450, 1.09550]
    prox_lower=1.09600 (LOW + 60%), prox_upper=1.09400 (HIGH - 60%)
    """
    return D1Range(
        high=1.10000,
        low=1.09000,
        mid=1.09500,
        fibo_upper=1.09550,
        fibo_lower=1.09450,
        prox_upper=1.09400,
        prox_lower=1.09600,
    )


class TestEntryValidatorFiboForbidden:
    """Test 3 : Invalide si prix dans la zone Fibo interdite (autour du mid)."""

    def setup_method(self):
        self.validator = EntryValidator()
        # Utilise un D1Range avec larges zones de proximité pour que
        # le midpoint soit à la fois 'près d'une extrémité' ET dans la zone Fibo
        self.d1 = _make_d1_wide_proximity()
        # fibo_zone_lower=1.09450, fibo_zone_upper=1.09550
        # prox_lower=1.09600 → tout prix ≤1.09600 passe le check 2

    def test_invalid_at_exact_midpoint(self):
        """Prix exactement au midpoint → INVALID: FIBO_FORBIDDEN_ZONE."""
        # 1.09500 ≤ prox_lower (1.09600) → près du LOW (check 2 OK)
        # 1.09450 ≤ 1.09500 ≤ 1.09550 → zone Fibo interdite (check 3 échoue)
        result = self.validator.validate(
            1.09500,
            self.d1,
            TrendBias.BULLISH,
            StructureSignal(StructureType.BOS, "BULLISH"),
        )
        assert result.status == ValidationStatus.INVALID_FIBO_FORBIDDEN_ZONE

    def test_invalid_slightly_above_mid(self):
        """Prix légèrement au-dessus du mid mais dans la zone → INVALID."""
        # 1.09510 ≤ 1.09600 → près du LOW ✓ ; dans Fibo [1.09450, 1.09550] ✓
        result = self.validator.validate(
            1.09510,
            self.d1,
            TrendBias.BULLISH,
            StructureSignal(StructureType.BOS, "BULLISH"),
        )
        assert result.status == ValidationStatus.INVALID_FIBO_FORBIDDEN_ZONE

    def test_invalid_slightly_below_mid(self):
        """Prix légèrement en-dessous du mid mais dans la zone → INVALID."""
        # 1.09480 ≤ 1.09600 → près du LOW ✓ ; dans Fibo [1.09450, 1.09550] ✓
        result = self.validator.validate(
            1.09480,
            self.d1,
            TrendBias.BEARISH,
            StructureSignal(StructureType.BOS, "BEARISH"),
        )
        assert result.status == ValidationStatus.INVALID_FIBO_FORBIDDEN_ZONE

    def test_valid_just_below_fibo_zone(self):
        """Prix juste en-dessous de la zone Fibo + près du LOW → valide si autres checks OK."""
        # 1.09440 < fibo_zone_lower (1.09450) et <= prox_lower (1.09100)
        # Prix 1.09050 est près du LOW et hors Fibo
        result = self.validator.validate(
            1.09050,
            self.d1,
            TrendBias.BULLISH,
            StructureSignal(StructureType.BOS, "BULLISH"),
        )
        assert result.status == ValidationStatus.VALID
