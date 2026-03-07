# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/engine/broker_api.py
# DESCRIPTION  : Connexion IB Gateway via ib_insync
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

import asyncio
import os
import time
from collections import deque
from typing import Optional

from ib_insync import IB, Contract, util
from loguru import logger


class BrokerAPI:
    """
    Interface IB Gateway via ib_insync.

    Fonctionnalités :
      - Connexion / déconnexion / auto-reconnect
      - Request throttler : max 50 requêtes / 10 secondes
      - Récupération bougie D1 de la veille
      - Récupération N bougies M15
      - Spread live en pips
    """

    MAX_REQUESTS = 50
    THROTTLE_WINDOW = 10.0  # secondes

    def __init__(self) -> None:
        self.ib = IB()
        self._host: str = os.getenv("IB_HOST", "127.0.0.1")
        self._port: int = int(os.getenv("IB_PORT", "4002"))
        self._client_id: int = 1
        self._request_times: deque[float] = deque()
        self._connected: bool = False

    # ------------------------------------------------------------------ #
    # Connexion                                                           #
    # ------------------------------------------------------------------ #

    async def connect(self) -> None:
        """Connecte à IB Gateway avec auto-reconnect."""
        logger.info(f"Connecting to IB Gateway {self._host}:{self._port}…")
        await self.ib.connectAsync(
            host=self._host,
            port=self._port,
            clientId=self._client_id,
        )
        self._connected = True
        self.ib.disconnectedEvent += self._on_disconnected
        logger.info("✅ Connected to IB Gateway")

    def _on_disconnected(self) -> None:
        self._connected = False
        logger.warning("⚠️  IB Gateway disconnected — scheduling reconnect…")
        asyncio.ensure_future(self._reconnect())

    async def _reconnect(self, retries: int = 10, delay: float = 5.0) -> None:
        for attempt in range(1, retries + 1):
            await asyncio.sleep(delay)
            try:
                await self.connect()
                logger.info(f"✅ Reconnected (attempt {attempt})")
                return
            except Exception as exc:  # noqa: BLE001
                logger.error(f"Reconnect attempt {attempt} failed: {exc}")
        logger.critical("❌ Could not reconnect to IB Gateway after all retries")

    async def disconnect(self) -> None:
        self.ib.disconnect()
        self._connected = False
        logger.info("Disconnected from IB Gateway")

    @property
    def is_connected(self) -> bool:
        return self._connected and self.ib.isConnected()

    # ------------------------------------------------------------------ #
    # Request throttler                                                   #
    # ------------------------------------------------------------------ #

    async def _throttle(self) -> None:
        """Limite à MAX_REQUESTS requêtes par THROTTLE_WINDOW secondes."""
        now = time.monotonic()
        # Purger les timestamps hors fenêtre
        while self._request_times and now - self._request_times[0] > self.THROTTLE_WINDOW:
            self._request_times.popleft()
        if len(self._request_times) >= self.MAX_REQUESTS:
            wait = self.THROTTLE_WINDOW - (now - self._request_times[0])
            if wait > 0:
                logger.debug(f"Rate limit: sleeping {wait:.2f}s")
                await asyncio.sleep(wait)
        self._request_times.append(time.monotonic())

    # ------------------------------------------------------------------ #
    # Données marché                                                      #
    # ------------------------------------------------------------------ #

    def _make_forex_contract(self, pair: str) -> Contract:
        """Construit un contrat Forex IB depuis une paire (ex: 'EURUSD')."""
        return Contract(
            symbol=pair[:3],
            secType="CASH",
            exchange="IDEALPRO",
            currency=pair[3:],
        )

    async def get_d1_candle(self, pair: str) -> Optional[dict]:
        """
        Retourne la bougie D1 de la veille.

        Args:
            pair: identifiant paire (ex: "EURUSD")

        Returns:
            dict: {"open", "high", "low", "close", "volume", "date"} ou None
        """
        await self._throttle()
        contract = self._make_forex_contract(pair)
        bars = await self.ib.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr="2 D",
            barSizeSetting="1 day",
            whatToShow="MIDPOINT",
            useRTH=True,
        )
        if len(bars) < 2:
            logger.warning(f"Not enough D1 data for {pair}")
            return None
        bar = bars[-2]  # bougie de la veille
        return {
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }

    async def get_m15_candles(self, pair: str, n: int = 100) -> list[dict]:
        """
        Retourne les N dernières bougies M15.

        Args:
            pair: identifiant paire
            n: nombre de bougies à récupérer (max ~96 pour 1 day)

        Returns:
            list[dict]: bougies OHLCV triées du plus ancien au plus récent
        """
        await self._throttle()
        contract = self._make_forex_contract(pair)
        duration = f"{max(1, (n * 15) // (60 * 6))} D"
        bars = await self.ib.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting="15 mins",
            whatToShow="MIDPOINT",
            useRTH=False,
        )
        candles = [
            {
                "date": b.date,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in bars[-n:]
        ]
        return candles

    async def get_live_spread(self, pair: str) -> float:
        """
        Retourne le spread actuel en pips.

        Args:
            pair: identifiant paire

        Returns:
            float: spread en pips
        """
        await self._throttle()
        contract = self._make_forex_contract(pair)
        ticker = self.ib.reqMktData(contract, "", False, False)
        await asyncio.sleep(1.0)
        pip_size = 0.01 if "JPY" in pair.upper() else 0.0001
        if ticker.ask and ticker.bid and ticker.ask > ticker.bid:
            spread_pips = round((ticker.ask - ticker.bid) / pip_size, 1)
        else:
            spread_pips = 0.0
        self.ib.cancelMktData(contract)
        return spread_pips
