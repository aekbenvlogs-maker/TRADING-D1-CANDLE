# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/engine/data_feed.py
# DESCRIPTION  : Flux données M15 asynchrone + buffer mémoire
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

import asyncio
from collections import deque
from typing import Callable, Optional

from loguru import logger

from trading_d1_bougie.engine.broker_api import BrokerAPI


class DataFeed:
    """
    Flux de données M15 asynchrone avec buffer en mémoire.

    Fonctionnalités :
      - Polling toutes les 15 minutes pour récupérer la dernière bougie M15
      - Subscribe aux ticks pour calculer le volume proxy (tick count / bar)
      - Buffer configurable des N dernières bougies
      - Filtrage spread : ignore les barres avec spread > seuil
      - Callback on_new_candle pour notifier les abonnés
    """

    def __init__(
        self,
        broker: BrokerAPI,
        pairs: list[str],
        buffer_size: int = 100,
        spread_filter_pips: float = 2.0,
        poll_interval_seconds: int = 900,
    ) -> None:
        self.broker = broker
        self.pairs = pairs
        self.buffer_size = buffer_size
        self.spread_filter_pips = spread_filter_pips
        self.poll_interval = poll_interval_seconds

        # Buffer M15 par paire
        self._buffers: dict[str, deque[dict]] = {
            pair: deque(maxlen=buffer_size) for pair in pairs
        }

        # Callbacks enregistrés
        self._callbacks: list[Callable[[str, dict], None]] = []

        self._running = False
        self._tasks: list[asyncio.Task] = []

    # ------------------------------------------------------------------ #
    # API publique                                                        #
    # ------------------------------------------------------------------ #

    def subscribe(self, callback: Callable[[str, dict], None]) -> None:
        """
        Enregistre un callback appelé à chaque nouvelle bougie M15.

        Args:
            callback: fonction(pair: str, candle: dict) → None
        """
        self._callbacks.append(callback)

    def get_candles(self, pair: str) -> list[dict]:
        """
        Retourne les bougies M15 en mémoire pour une paire.

        Args:
            pair: identifiant paire (ex: "EURUSD")

        Returns:
            list[dict]: bougies OHLCV du plus ancien au plus récent
        """
        return list(self._buffers[pair])

    async def initialize(self) -> None:
        """Charge le buffer initial pour toutes les paires."""
        for pair in self.pairs:
            candles = await self.broker.get_m15_candles(pair, n=self.buffer_size)
            for candle in candles:
                self._buffers[pair].append(candle)
            logger.info(f"[DataFeed] {pair}: {len(candles)} candles loaded")

    async def start(self) -> None:
        """Démarre le flux de données en arrière-plan."""
        if self._running:
            return
        self._running = True
        await self.initialize()
        for pair in self.pairs:
            task = asyncio.create_task(self._poll_loop(pair))
            self._tasks.append(task)
        logger.info("[DataFeed] ✅ Data feed started")

    async def stop(self) -> None:
        """Arrête proprement tous les flux."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        logger.info("[DataFeed] Stopped")

    # ------------------------------------------------------------------ #
    # Boucle interne                                                      #
    # ------------------------------------------------------------------ #

    async def _poll_loop(self, pair: str) -> None:
        """Boucle de polling toutes les `poll_interval` secondes."""
        while self._running:
            await asyncio.sleep(self.poll_interval)
            try:
                await self._fetch_latest(pair)
            except Exception as exc:  # noqa: BLE001
                logger.error(f"[DataFeed] {pair} poll error: {exc}")

    async def _fetch_latest(self, pair: str) -> None:
        """Récupère la dernière bougie M15 et la pousse dans le buffer."""
        spread = await self.broker.get_live_spread(pair)
        if spread > self.spread_filter_pips:
            logger.warning(
                f"[DataFeed] {pair}: spread {spread} pips > filter {self.spread_filter_pips} — skipped"
            )
            return

        candles = await self.broker.get_m15_candles(pair, n=1)
        if not candles:
            return

        candle = candles[-1]

        # Éviter les doublons (même timestamp)
        buffer = self._buffers[pair]
        if buffer and buffer[-1].get("date") == candle.get("date"):
            return

        buffer.append(candle)
        logger.debug(f"[DataFeed] {pair}: new M15 candle {candle['date']}")

        for cb in self._callbacks:
            try:
                cb(pair, candle)
            except Exception as exc:  # noqa: BLE001
                logger.error(f"[DataFeed] callback error: {exc}")
