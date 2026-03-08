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
from typing import Any

from ib_insync import IB, Contract
from loguru import logger

from trading_d1_bougie.engine.broker_interface import IBroker


class BrokerAPI(IBroker):
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

    async def connect(self, timeout: float = 8.0) -> None:
        """Connecte à IB Gateway avec timeout explicite."""
        logger.info(f"Connecting to IB Gateway {self._host}:{self._port}…")
        await asyncio.wait_for(
            self.ib.connectAsync(
                host=self._host,
                port=self._port,
                clientId=self._client_id,
            ),
            timeout=timeout,
        )
        self._connected = True
        self.ib.disconnectedEvent += self._on_disconnected
        logger.info("✅ Connected to IB Gateway")

    def _on_disconnected(self) -> None:
        self._connected = False
        logger.warning("⚠️  IB Gateway disconnected — scheduling reconnect…")
        asyncio.ensure_future(self._reconnect())

    async def _reconnect(self) -> None:
        """Tentatives de reconnexion IB sans limite.

        Stratégie d'alertes :
          - Tentative 1     : WARNING + Telegram
          - Tentative 5     : ERROR + Telegram escalade
          - Tentative 12+   : CRITICAL + Telegram urgence (toutes les 12 tentatives)

        S'arrête uniquement sur reconnexion réussie ou arrêt manuel.
        """
        attempt = 0
        while True:
            attempt += 1
            delay = min(5 * attempt, 60)  # backoff plafonné à 60s

            if attempt == 1:
                logger.warning("[BrokerAPI] 🔴 Déconnexion IB — tentative de reconnexion")
                asyncio.ensure_future(
                    self._alert("🔴 <b>DÉCONNEXION IB GATEWAY</b>\nReconnexion en cours...")
                )
            elif attempt == 5:
                logger.error(f"[BrokerAPI] Reconnexion échouée après {attempt} tentatives")
                asyncio.ensure_future(
                    self._alert(
                        f"⚠️ <b>RECONNEXION DIFFICILE</b>\n"
                        f"{attempt} tentatives — Position non surveillée !"
                    )
                )
            elif attempt == 12 or (attempt > 12 and attempt % 12 == 0):
                logger.critical(
                    f"[BrokerAPI] Reconnexion impossible après {attempt} tentatives "
                    f"({attempt * 5 // 60}min écoulées)"
                )
                asyncio.ensure_future(
                    self._alert(
                        f"🚨 <b>URGENCE — IB INJOIGNABLE</b>\n"
                        f"{attempt} tentatives ({attempt * 5 // 60} min)\n"
                        "Vérifier IB Gateway manuellement !"
                    )
                )

            await asyncio.sleep(delay)

            try:
                await self.connect()
                logger.info(f"[BrokerAPI] ✅ Reconnexion réussie après {attempt} tentatives")
                asyncio.ensure_future(
                    self._alert(
                        f"✅ <b>RECONNEXION IB RÉUSSIE</b>\n"
                        f"Après {attempt} tentatives ({attempt * 5}s)"
                    )
                )
                return
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"[BrokerAPI] Tentative {attempt} échouée : {exc}")

    async def _alert(self, message: str) -> None:
        """Délègue l'alerte Telegram via callback enregistré."""
        if hasattr(self, "_telegram_callback") and self._telegram_callback:
            try:
                await self._telegram_callback(message)
            except Exception:  # noqa: BLE001
                pass


    def open_trades(self) -> list:
        """Retourne les trades ouverts (implémentation IBroker)."""
        return self.ib.openTrades()

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
        while (
            self._request_times and now - self._request_times[0] > self.THROTTLE_WINDOW
        ):
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

    async def get_d1_candle(self, pair: str) -> dict[str, Any] | None:
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

    async def get_m15_candles(self, pair: str, n: int = 100) -> list[dict[str, Any]]:
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

    async def place_bracket_order(self, order_spec: Any) -> int:
        """
        Place un bracket order (entry limit + TP limit + SL stop) sur IB Gateway.

        Args:
            order_spec: OrderSpec Cython avec entry_price, sl_price, tp_price,
                        lot_size, direction, pair.

        Returns:
            orderId de l'ordre parent (int).

        Raises:
            RuntimeError: si le contrat ne peut pas être qualifié par IB.
        """
        from ib_insync import Forex, LimitOrder, StopOrder

        base = order_spec.pair[:3]
        quote = order_spec.pair[3:]
        contract = Forex(f"{base}{quote}")
        qualified = await self.ib.qualifyContractsAsync(contract)
        if not qualified:
            raise RuntimeError(
                f"[BrokerAPI] ❌ Contrat non qualifié : {order_spec.pair}"
            )

        action = "BUY" if order_spec.direction == "LONG" else "SELL"
        close_action = "SELL" if action == "BUY" else "BUY"

        parent_id = self.ib.client.getReqId()
        tp_id = self.ib.client.getReqId()
        sl_id = self.ib.client.getReqId()

        # Ordre parent — limit entry
        parent = LimitOrder(
            action=action,
            totalQuantity=order_spec.lot_size,
            lmtPrice=order_spec.entry_price,
            orderId=parent_id,
            transmit=False,
            tif="DAY",
        )

        # Take profit — limit
        take_profit = LimitOrder(
            action=close_action,
            totalQuantity=order_spec.lot_size,
            lmtPrice=order_spec.tp_price,
            orderId=tp_id,
            parentId=parent_id,
            transmit=False,
            tif="GTC",
        )

        # Stop loss — stop (transmet le groupe entier)
        stop_loss = StopOrder(
            action=close_action,
            totalQuantity=order_spec.lot_size,
            stopPrice=order_spec.sl_price,
            orderId=sl_id,
            parentId=parent_id,
            transmit=True,
            tif="GTC",
        )

        for order in [parent, take_profit, stop_loss]:
            trade = self.ib.placeOrder(contract, order)
            logger.info(
                f"[BrokerAPI] 📤 Order placed: {trade.order.orderId} — "
                f"{trade.order.action} @ "
                f"{trade.order.lmtPrice or trade.order.stopPrice}"
            )

        return parent_id

    async def fetch_equity(self) -> float:
        """
        Retourne la valeur nette du compte IB en USD (NetLiquidation).

        Returns:
            float: equity en USD.

        Raises:
            RuntimeError: si IB ne retourne pas la valeur NetLiquidation.
        """
        summary = await self.ib.accountSummaryAsync()
        for item in summary:
            if item.tag == "NetLiquidation" and item.currency == "USD":
                return float(item.value)
        raise RuntimeError(
            "[BrokerAPI] ❌ Impossible de récupérer l'equity (NetLiquidation) depuis IB Gateway"
        )

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
        return float(spread_pips)
