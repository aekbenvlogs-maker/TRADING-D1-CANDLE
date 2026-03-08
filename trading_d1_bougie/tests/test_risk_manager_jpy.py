# ============================================================
# PROJECT      : TRADING-D1-BOUGIE
# FILE         : tests/test_risk_manager_jpy.py
# DESCRIPTION  : Tests RiskManager — formule JPY corrigée (M2)
# ============================================================

import pytest

from trading_d1_bougie.core.risk_manager import RiskManager


class TestRiskManagerJPY:
    """Tests formule pip_value corrigée pour paires JPY (Sprint 6 M2)."""

    def setup_method(self):
        self.mgr = RiskManager(risk_pct=1.0, lot_type="mini")

    def test_lot_size_usdjpy_with_spot_price(self):
        """Vérifie que le sizing JPY intègre correctement le prix spot.

        Equity=10 000$, risk=1%, SL=20 pips, spot=150.00:
          dollar_risk = 10 000 × 0.01 = 100$
          pip_value_per_mini = (0.01 × 10 000) / 150 = 100/150 ≈ 0.667$/pip
          lot_size = 100 / (20 × 0.667) = 100/13.33 ≈ 7.5 lots mini
        """
        lot = self.mgr.calculate_lot_size(
            equity=10_000.0, sl_pips=20.0, pair="USDJPY", spot_price=150.0
        )
        assert abs(lot - 7.5) < 0.1, f"Expected ~7.5, got {lot}"

    def test_lot_size_usdjpy_scales_with_spot(self):
        """Plus le spot est élevé, plus le lot est grand (pip vaut moins en USD)."""
        lot_low = self.mgr.calculate_lot_size(
            equity=10_000.0, sl_pips=20.0, pair="USDJPY", spot_price=100.0
        )
        lot_high = self.mgr.calculate_lot_size(
            equity=10_000.0, sl_pips=20.0, pair="USDJPY", spot_price=200.0
        )
        assert lot_high > lot_low, "Higher spot → larger lot (pip worth less in USD)"

    def test_lot_size_eurusd_unchanged_with_spot(self):
        """EURUSD : spot_price n’affecte pas le calcul (non-JPY pair)."""
        lot_no_spot = self.mgr.calculate_lot_size(
            equity=10_000.0, sl_pips=20.0, pair="EURUSD"
        )
        lot_with_spot = self.mgr.calculate_lot_size(
            equity=10_000.0, sl_pips=20.0, pair="EURUSD", spot_price=1.09
        )
        assert lot_no_spot == lot_with_spot
