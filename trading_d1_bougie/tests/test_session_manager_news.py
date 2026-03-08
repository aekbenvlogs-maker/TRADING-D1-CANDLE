# ============================================================
# PROJECT      : TRADING-D1-BOUGIE
# FILE         : tests/test_session_manager_news.py
# DESCRIPTION  : Tests SessionManager — filtre news calendario (M8)
# ============================================================

from datetime import datetime, timezone

from trading_d1_bougie.engine.session_manager import SessionManager


class TestSessionManagerNews:
    """Tests du filtre calendrier économique (Sprint 6 M8)."""

    def setup_method(self):
        self.sm = SessionManager()
        # Simuler un NFP à 14h30 UTC le 6 mars 2026
        nfp_dt = datetime(2026, 3, 6, 14, 30, tzinfo=timezone.utc)
        self.sm._news_events = [nfp_dt]

    def test_blocked_20min_before_nfp(self):
        """20 minutes avant le NFP : trading bloqué."""
        check_dt = datetime(2026, 3, 6, 14, 10, tzinfo=timezone.utc)
        assert self.sm.is_news_window(dt=check_dt) is True

    def test_blocked_during_nfp(self):
        """Au moment exact du NFP : trading bloqué."""
        check_dt = datetime(2026, 3, 6, 14, 30, tzinfo=timezone.utc)
        assert self.sm.is_news_window(dt=check_dt) is True

    def test_blocked_20min_after_nfp(self):
        """20 minutes après le NFP : trading bloqué."""
        check_dt = datetime(2026, 3, 6, 14, 50, tzinfo=timezone.utc)
        assert self.sm.is_news_window(dt=check_dt) is True

    def test_not_blocked_31min_before(self):
        """31 minutes avant le NFP : trading autorisé (hors fenêtre)."""
        check_dt = datetime(2026, 3, 6, 13, 59, tzinfo=timezone.utc)
        assert self.sm.is_news_window(dt=check_dt) is False

    def test_not_blocked_31min_after(self):
        """31 minutes après le NFP : trading autorisé."""
        check_dt = datetime(2026, 3, 6, 15, 1, tzinfo=timezone.utc)
        assert self.sm.is_news_window(dt=check_dt) is False

    def test_no_events_never_blocked(self):
        """Sans événements chargés : jamais bloqué."""
        sm_empty = SessionManager()
        sm_empty._news_events = []
        assert sm_empty.is_news_window() is False
