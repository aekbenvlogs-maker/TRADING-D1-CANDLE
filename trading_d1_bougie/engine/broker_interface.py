# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/engine/broker_interface.py
# DESCRIPTION  : Interface abstraite broker — testabilité + mock
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# PYTHON       : 3.11.9
# LAST UPDATED : Sprint 6
# ============================================================
"""IBroker — contrat abstrait pour les brokers (IB, mock tests, paper)."""

from abc import ABC, abstractmethod
from typing import Any


class IBroker(ABC):
    """Interface abstraite broker — permet le mock pour les tests.

    Tout broker concret (BrokerAPI, MockBroker...) doit implémenter
    cette interface pour garantir la compatibilité avec le moteur principal.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Connexion au broker. Retourne True si connecté."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Déconnexion propre."""
        ...

    @abstractmethod
    async def fetch_equity(self) -> float:
        """Retourne l’équité nette du compte en USD."""
        ...

    @abstractmethod
    async def get_d1_candle(self, pair: str) -> dict[str, float]:
        """Retourne la dernière bougie D1 {open, high, low, close}."""
        ...

    @abstractmethod
    async def get_m15_candles(self, pair: str, n: int) -> list[dict[str, Any]]:
        """Retourne les n dernières bougies M15."""
        ...

    @abstractmethod
    async def place_bracket_order(self, order_spec: Any) -> int:
        """Envoie un ordre bracket. Retourne l’orderId IB."""
        ...

    @abstractmethod
    def open_trades(self) -> list[Any]:
        """Retourne la liste des trades ouverts (synchrone)."""
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """True si connecté au broker."""
        ...
