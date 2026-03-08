# ============================================================
# PROJECT      : TRADING-D1-BOUGIE
# FILE         : tests/integration/test_state_manager.py
# DESCRIPTION  : Tests StateManager — persistance SQLite (ARCH3)
# ============================================================

import tempfile
from datetime import date
from pathlib import Path

import pytest

from trading_d1_bougie.engine.state_manager import StateManager


class MockSpec:
    direction = "LONG"
    entry_price = 1.0950
    sl_price = 1.0850
    tp_price = 1.1150
    lot_size = 2.0


@pytest.fixture
def state_mgr(tmp_path):
    """StateManager utilisant un fichier SQLite temporaire."""
    db = tmp_path / "test_state.db"
    sm = StateManager(db_path=db)
    yield sm
    sm.close()


class TestStateManager:
    """Tests de persistance SQLite des positions et de l’état journalier."""

    def test_save_and_load_position(self, state_mgr):
        """Sauvegarde et rechargement d’une position."""
        state_mgr.save_position("EURUSD", 12345, MockSpec())
        loaded = state_mgr.load_positions()
        assert "EURUSD" in loaded
        assert loaded["EURUSD"] == 12345

    def test_remove_position(self, state_mgr):
        """Suppression d’une position clôturée."""
        state_mgr.save_position("GBPUSD", 99999, MockSpec())
        state_mgr.remove_position("GBPUSD")
        loaded = state_mgr.load_positions()
        assert "GBPUSD" not in loaded

    def test_multiple_positions(self, state_mgr):
        """Plusieurs positions persistées indépendamment."""
        state_mgr.save_position("EURUSD", 1001, MockSpec())
        state_mgr.save_position("USDJPY", 1002, MockSpec())
        loaded = state_mgr.load_positions()
        assert len(loaded) == 2
        assert loaded["EURUSD"] == 1001
        assert loaded["USDJPY"] == 1002

    def test_save_and_load_daily_state(self, state_mgr):
        """Persistance de l’état journalier."""
        today = date(2026, 3, 7)
        counts = {"EURUSD": 1, "GBPUSD": 0, "USDJPY": 2}
        state_mgr.save_daily_state(today, 10_000.0, counts)
        result = state_mgr.load_daily_state(today)
        assert result is not None
        equity_start, loaded_counts = result
        assert equity_start == pytest.approx(10_000.0)
        assert loaded_counts == counts

    def test_load_missing_daily_state_returns_none(self, state_mgr):
        """Chargement d’une date sans données retourne None."""
        result = state_mgr.load_daily_state(date(2000, 1, 1))
        assert result is None
