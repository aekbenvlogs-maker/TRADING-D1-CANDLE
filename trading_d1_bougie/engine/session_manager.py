# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/engine/session_manager.py
# DESCRIPTION  : Gestion sessions trading + timezone DST auto
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

from datetime import datetime, time
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")
PARIS = ZoneInfo("Europe/Paris")
NEW_YORK = ZoneInfo("America/New_York")


class SessionManager:
    """
    Gère les sessions trading London + New York avec support DST.

    - Toutes les comparaisons sont faites en UTC
    - Les affichages sont convertis en Europe/Paris
    - La détection DST est automatique via zoneinfo (PEP 615)

    Sessions (heures UTC approximatives — ajustées automatiquement par DST) :
      London    : 07:00 – 16:00 UTC
      New York  : 13:00 – 21:00 UTC
      Overlap   : 13:00 – 16:00 UTC (meilleure liquidité)
    """

    # Heures locales fixes — la conversion UTC tient compte du DST
    LONDON_OPEN_LOCAL = time(8, 0)    # 08:00 London time
    LONDON_CLOSE_LOCAL = time(17, 0)  # 17:00 London time
    NY_OPEN_LOCAL = time(9, 30)       # 09:30 New York time
    NY_CLOSE_LOCAL = time(17, 0)      # 17:00 New York time

    def now_utc(self) -> datetime:
        """Retourne l'heure courante en UTC."""
        return datetime.now(tz=UTC)

    def now_paris(self) -> datetime:
        """Retourne l'heure courante en Europe/Paris."""
        return datetime.now(tz=PARIS)

    def _is_london_open(self, dt_utc: datetime) -> bool:
        """Retourne True si la session London est ouverte."""
        london_dt = dt_utc.astimezone(ZoneInfo("Europe/London"))
        t = london_dt.time()
        return self.LONDON_OPEN_LOCAL <= t < self.LONDON_CLOSE_LOCAL

    def _is_ny_open(self, dt_utc: datetime) -> bool:
        """Retourne True si la session New York est ouverte."""
        ny_dt = dt_utc.astimezone(NEW_YORK)
        t = ny_dt.time()
        return self.NY_OPEN_LOCAL <= t < self.NY_CLOSE_LOCAL

    def is_weekend(self, dt_utc: datetime | None = None) -> bool:
        """Retourne True si c'est le week-end Forex (vendredi 22h UTC → dimanche 22h UTC)."""
        if dt_utc is None:
            dt_utc = self.now_utc()
        weekday = dt_utc.weekday()  # 0=lundi … 6=dimanche
        if weekday == 4 and dt_utc.hour >= 22:  # vendredi soir
            return True
        if weekday == 5:  # samedi
            return True
        if weekday == 6 and dt_utc.hour < 22:  # dimanche avant réouverture
            return True
        return False

    def is_active_session(self, dt_utc: datetime | None = None) -> bool:
        """
        Retourne True si une des sessions actives (London ou New York) est ouverte.

        Args:
            dt_utc: datetime UTC (None = maintenant)

        Returns:
            bool: True si session active
        """
        if dt_utc is None:
            dt_utc = self.now_utc()

        if self.is_weekend(dt_utc):
            return False

        return self._is_london_open(dt_utc) or self._is_ny_open(dt_utc)

    def is_overlap_session(self, dt_utc: datetime | None = None) -> bool:
        """
        Retourne True si on est dans l'overlap London/New York (meilleure liquidité).

        Args:
            dt_utc: datetime UTC (None = maintenant)
        """
        if dt_utc is None:
            dt_utc = self.now_utc()

        if self.is_weekend(dt_utc):
            return False

        return self._is_london_open(dt_utc) and self._is_ny_open(dt_utc)

    def format_timestamp(self, dt_utc: datetime | None = None) -> dict:
        """
        Retourne les timestamps formatés pour l'affichage dashboard.

        Returns:
            dict: {"utc": str, "paris": str}
        """
        if dt_utc is None:
            dt_utc = self.now_utc()
        paris_dt = dt_utc.astimezone(PARIS)
        return {
            "utc": dt_utc.strftime("%Y-%m-%d %H:%M:%S UTC"),
            "paris": paris_dt.strftime("%Y-%m-%d %H:%M:%S %Z"),
        }
