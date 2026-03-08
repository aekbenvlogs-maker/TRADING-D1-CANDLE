# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/engine/main.py
# DESCRIPTION  : Point d'entrée principal — boucle asynchrone
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

import asyncio
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml
from dotenv import load_dotenv
from loguru import logger
from rich.console import Console

# Charger .env avant toute lecture d'os.getenv
load_dotenv(Path(".env"), override=False)

from trading_d1_bougie.engine.broker_api import BrokerAPI
from trading_d1_bougie.engine.dashboard import Dashboard
from trading_d1_bougie.engine.data_feed import DataFeed
from trading_d1_bougie.engine.session_manager import SessionManager

console = Console()
UTC = timezone.utc


async def _send_telegram(message: str) -> None:
    """Envoie une alerte Telegram. Silencieux si les vars d'env ne sont pas définies."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                url,
                json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[Telegram] Échec envoi alerte : {exc}")


def _load_config() -> dict[str, Any]:
    config_path = Path("trading_d1_bougie/config/config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)  # type: ignore[no-any-return]


def _check_paper_mode() -> None:
    """Vérifie le mode trading — affiche WARNING critique si live."""
    paper = os.getenv("PAPER_TRADING", "true").lower()
    mode = os.getenv("IB_MODE", "paper").lower()

    if paper != "true" or mode == "live":
        console.print(
            "\n[bold red]╔══════════════════════════════════════════════════════════════╗[/bold red]"  # noqa: E501
        )
        console.print(
            "[bold red]║   ⚠️  ATTENTION — MODE LIVE TRADING                         ║[/bold red]"  # noqa: E501
        )
        console.print(
            "[bold red]║                                                              ║[/bold red]"  # noqa: E501
        )
        console.print(
            "[bold red]║   Le mode live (port 4001) engage du capital RÉEL.          ║[/bold red]"  # noqa: E501
        )
        console.print(
            "[bold red]║   Ne l'activer QUE après validation complète du backtest.   ║[/bold red]"  # noqa: E501
        )
        console.print(
            "[bold red]╚══════════════════════════════════════════════════════════════╝[/bold red]\n"  # noqa: E501
        )
        confirm = input(
            "Confirmer le mode LIVE ? Tapez 'LIVE-CONFIRMED' pour continuer : "
        )
        if confirm.strip() != "LIVE-CONFIRMED":
            console.print("[yellow]Annulé. Repassez en mode paper dans .env[/yellow]")
            sys.exit(0)
    else:
        console.print("[green]✅ Mode PAPER TRADING activé (port 4002)[/green]")


async def _maybe_refresh_d1_ranges(
    broker: BrokerAPI,
    d1_builder: Any,
    d1_ranges: dict[str, Any],
    dashboard: Any,
    pairs: list[str],
    last_refresh: date,
) -> date:
    """Rafraîchit les ranges D1 si la date UTC a changé depuis le dernier refresh."""
    today = datetime.now(UTC).date()
    if today == last_refresh:
        return last_refresh
    for pair in pairs:
        try:
            candle = await broker.get_d1_candle(pair)
            if candle:
                d1_ranges[pair] = d1_builder.build(pair, candle["high"], candle["low"])
                dashboard.update_pair(
                    pair,
                    d1_high=d1_ranges[pair].high,
                    d1_low=d1_ranges[pair].low,
                    d1_mid=d1_ranges[pair].mid,
                )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[Main] D1 refresh error for {pair}: {exc}")
    logger.info(f"[Main] 🔄 D1 ranges rafraîchis pour {pairs} ({today})")
    return today


async def _rebuild_open_pairs(broker: "BrokerAPI") -> "dict[str, int]":
    """Reconstruit open_pairs depuis les trades IB actifs au démarrage.

    Évite les doubles positions après redémarrage du bot.
    """
    result: dict[str, int] = {}
    try:
        trades = broker.ib.openTrades()
        for trade in trades:
            symbol = getattr(trade.contract, "symbol", "")
            currency = getattr(trade.contract, "currency", "")
            if not symbol or not currency:
                continue
            pair = f"{symbol}{currency}"
            order_id = trade.order.orderId
            # Ne conserver que l'ordre parent (parentId == 0)
            if trade.order.parentId == 0:
                result[pair] = order_id
                logger.warning(
                    f"[Main] ⚠️ Position existante détectée au démarrage : "
                    f"{pair} — orderId {order_id}"
                )
        if result:
            await _send_telegram(
                f"⚠️ <b>REDÉMARRAGE</b> — {len(result)} position(s) existante(s) détectée(s)\n"
                + "\n".join(f"• {p}" for p in result)
            )
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[Main] Erreur reconstruction open_pairs : {exc}")
    return result


async def _main_loop(
    broker: BrokerAPI,
    data_feed: DataFeed,
    session_mgr: SessionManager,
    dashboard: Dashboard,
    cfg: dict[str, Any],
) -> None:
    """Boucle principale asynchrone de la stratégie."""
    from trading_d1_bougie.core.d1_range_builder import D1RangeBuilder
    from trading_d1_bougie.core.entry_validator import EntryValidator
    from trading_d1_bougie.core.order_manager import OrderManager
    from trading_d1_bougie.core.risk_manager import RiskCheckResult, RiskManager
    from trading_d1_bougie.core.structure_detector import (
        StructureDetector,
    )
    from trading_d1_bougie.core.trend_detector import TrendDetector

    strategy = cfg["strategy"]
    risk_cfg = cfg["risk"]

    d1_builder = D1RangeBuilder(
        fibo_forbidden_pct=strategy["fibo_forbidden_zone_pct"],
        proximity_buffer_pct=strategy["proximity_buffer_pct"],
    )
    trend_detector = TrendDetector()
    structure_detector = StructureDetector()
    entry_validator = EntryValidator()
    order_manager = OrderManager(rr_ratio=strategy["rr_ratio"])
    risk_manager = RiskManager(
        risk_pct=strategy["risk_pct"],
        daily_loss_limit_pct=risk_cfg["daily_loss_limit_pct"],
        max_open_pairs=risk_cfg["max_open_pairs"],
        lot_type=strategy["lot_type"],
    )

    pairs = strategy["pairs"]
    d1_ranges: dict[str, Any] = {}
    # C3: Reconstruire open_pairs depuis les trades IB actifs (survie au redémarrage)
    open_pairs: dict[str, int] = await _rebuild_open_pairs(broker)
    daily_trade_count: dict[str, int] = {p: 0 for p in pairs}
    last_d1_refresh: date = date.min
    previous_date: date = date.min

    # Callback IB : retire la paire d'open_pairs quand la position se ferme
    def _on_order_status(trade: Any) -> None:  # noqa: ANN001
        if trade.orderStatus.status in ("Filled", "Cancelled", "Inactive"):
            for pair_key, oid in list(open_pairs.items()):
                if oid == trade.order.orderId:
                    del open_pairs[pair_key]
                    logger.info(
                        f"[Main] 🔒 Position fermée, retiré d'open_pairs : {pair_key}"
                    )
                    break

    broker.ib.orderStatusEvent += _on_order_status

    logger.info("[Main] 🚀 Starting main loop…")

    # ---------------------------------------------------------------- #
    # Récupérer l'equity initiale depuis IB                           #
    # ---------------------------------------------------------------- #
    equity_start: float = await broker.fetch_equity()
    equity_current: float = equity_start
    logger.info(f"[Main] 💰 Equity initiale : ${equity_start:,.2f}")

    with dashboard.start_live() as live:
        # ---------------------------------------------------------------- #
        # Étape 1 — Construire les rectangles D1 au démarrage             #
        # ---------------------------------------------------------------- #
        last_d1_refresh = await _maybe_refresh_d1_ranges(
            broker, d1_builder, d1_ranges, dashboard, pairs, last_d1_refresh
        )

        while True:
            now_utc = session_mgr.now_utc()

            # -------------------------------------------------------- #
            # Refresh D1 si nouvelle journée + reset compteurs         #
            # -------------------------------------------------------- #
            last_d1_refresh = await _maybe_refresh_d1_ranges(
                broker, d1_builder, d1_ranges, dashboard, pairs, last_d1_refresh
            )
            today = datetime.now(UTC).date()
            if today != previous_date:
                daily_trade_count = {p: 0 for p in pairs}
                previous_date = today
                # C2: Réinitialiser equity_start pour le calcul daily limit correct
                try:
                    equity_start = await broker.fetch_equity()
                    logger.info(
                        f"[Main] 🗓️ Nouvelle journée {today} — "
                        "equity_start réinitialisée : $"
                        f"{equity_start:,.2f}"
                    )
                    await _send_telegram(
                        f"📅 <b>NOUVELLE SESSION</b> — {today}\n"
                        "Equity de référence : $"
                        f"{equity_start:,.2f}"
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"[Main] equity_start refresh failed : {exc}")
                logger.info("[Main] 🗓️ Nouvelle journée — compteurs remis à zéro")

            # -------------------------------------------------------- #
            # Mise à jour equity courante                              #
            # -------------------------------------------------------- #
            try:
                equity_current = await broker.fetch_equity()
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[Main] Equity fetch failed : {exc}")

            if not session_mgr.is_active_session(now_utc):
                logger.debug("[Main] Outside active session — waiting…")
                await asyncio.sleep(60)
                live.update(dashboard.render())
                continue

            for pair in pairs:
                if pair not in d1_ranges:
                    continue
                if daily_trade_count[pair] >= strategy["max_daily_trades"]:
                    continue

                # C4: Filtre hauteur minimale D1 (aligne main.py sur backtest_standalone)
                _pip_size_c4: float = 0.01 if "JPY" in pair else 0.0001
                _d1_height_pips: float = (
                    d1_ranges[pair].high - d1_ranges[pair].low
                ) / _pip_size_c4
                _min_range: float = float(strategy.get("min_d1_range_pips", 20.0))
                if _d1_height_pips < _min_range:
                    logger.debug(
                        f"[Main] ⏭️ {pair} — range D1 trop étroit "
                        f"({_d1_height_pips:.1f}p < {_min_range}p) — skip"
                    )
                    continue

                # -------------------------------------------------------- #
                # Étape 2 — Analyser la tendance M15                       #
                # -------------------------------------------------------- #
                candles = data_feed.get_candles(pair)
                if len(candles) < 10:
                    continue

                trend_bias = trend_detector.detect(candles)
                dashboard.update_pair(pair, trend=trend_bias.value)

                # -------------------------------------------------------- #
                # Étape 3 — Détecter BOS / CHoCH                          #
                # -------------------------------------------------------- #
                swing_highs = trend_detector.find_swing_highs(candles)
                swing_lows = trend_detector.find_swing_lows(candles)
                signal = structure_detector.detect(
                    candles, swing_highs, swing_lows, trend_bias.value
                )
                dashboard.update_pair(pair, structure=signal.signal_type.value)

                # -------------------------------------------------------- #
                # Étape 4 — Valider les conditions d'entrée               #
                # -------------------------------------------------------- #
                price = candles[-1]["close"]
                spread = await broker.get_live_spread(pair)
                dashboard.update_pair(pair, spread_pips=spread)

                if spread > strategy["spread_filter_pips"]:
                    dashboard.update_pair(
                        pair, zone_status="SPREAD TROP ÉLEVÉ", eligible=False
                    )
                    continue

                validation = entry_validator.validate(
                    price, d1_ranges[pair], trend_bias, signal
                )
                val_status = str(
                    validation.status.value
                    if hasattr(validation.status, "value")
                    else validation.status
                )
                is_valid = val_status == "VALID"
                dashboard.update_pair(
                    pair,
                    zone_status="IN ZONE ✅" if is_valid else val_status,
                    eligible=is_valid,
                )

                if not is_valid:
                    continue

                # -------------------------------------------------------- #
                # -------------------------------------------------------- #
                # Risk checks                                               #
                # -------------------------------------------------------- #
                if (
                    risk_manager.check_daily_limit(equity_start, equity_current)
                    != RiskCheckResult.ALLOWED
                ):
                    msg = (
                        f"⚠️ <b>DAILY LIMIT ATTEINT</b>\n"
                        f"Trading suspendu — equity: ${equity_current:,.2f}"
                    )
                    logger.warning("[Main] Daily loss limit reached — SHUTDOWN")
                    await _send_telegram(msg)
                    return

                if (
                    risk_manager.check_max_pairs(len(open_pairs))
                    != RiskCheckResult.ALLOWED
                ):
                    logger.warning(
                        f"[Main] Max open pairs ({risk_cfg['max_open_pairs']}) reached"
                    )
                    continue

                if pair in open_pairs:
                    logger.debug(f"[Main] {pair} already in open_pairs — skip")
                    continue

                # -------------------------------------------------------- #
                # Étape 5 — Sizing avec SL réel                           #
                # -------------------------------------------------------- #
                swing_sl: float = (
                    d1_ranges[pair].low
                    if validation.direction == "LONG"
                    else d1_ranges[pair].high
                )
                pip_size: float = 0.01 if "JPY" in pair else 0.0001
                real_sl_pips: float = round(abs(price - swing_sl) / pip_size, 1)

                if real_sl_pips <= 0:
                    logger.warning(f"[Main] ⚠️ {pair} — sl_pips=0, skip")
                    continue

                lot_size = risk_manager.calculate_lot_size(
                    equity=equity_current,
                    sl_pips=real_sl_pips,
                    pair=pair,
                )

                # -------------------------------------------------------- #
                # Étape 6 — Construire et envoyer l'ordre bracket          #
                # -------------------------------------------------------- #
                order_spec = order_manager.build(
                    pair=pair,
                    direction=validation.direction,
                    entry_price=price,
                    swing_sl_price=swing_sl,
                    lot_size=lot_size,
                )
                logger.info(f"[Main] 🎯 Sending order: {order_spec}")

                order_id = await broker.place_bracket_order(order_spec)
                open_pairs[pair] = order_id
                daily_trade_count[pair] += 1

                logger.info(
                    f"[Main] ✅ Bracket order placed — ID:{order_id} | "
                    f"{pair} {validation.direction} @ {price} | "
                    f"SL={order_spec.sl_price} ({real_sl_pips:.1f}p) | "
                    f"TP={order_spec.tp_price} | lots={lot_size}"
                )
                await _send_telegram(
                    f"🎯 <b>NEW TRADE</b>\n"
                    f"Paire: {pair}\n"
                    f"Direction: {validation.direction}\n"
                    f"Entry: {order_spec.entry_price}\n"
                    f"SL: {order_spec.sl_price} ({real_sl_pips:.1f} pips)\n"
                    f"TP: {order_spec.tp_price}\n"
                    f"Lots: {order_spec.lot_size}\n"
                    f"Equity: ${equity_current:,.2f}"
                )

            live.update(dashboard.render())
            await asyncio.sleep(30)


async def _connect_with_retry(
    broker: BrokerAPI,
    dashboard: Dashboard,
    max_attempts: int = 0,
    delay: float = 10.0,
) -> bool:
    """
    Tente de se connecter à IB Gateway.

    max_attempts=0 → boucle infinie (attend jusqu'à ce que IB Gateway
    soit disponible). Retourne True dès la connexion réussie.
    """
    attempt = 0
    while True:
        attempt += 1
        try:
            await broker.connect()
            dashboard.set_ib_connected(True)
            logger.info(f"[Main] ✅ IB Gateway connecté (tentative {attempt})")
            return True
        except Exception as exc:  # noqa: BLE001
            dashboard.set_ib_connected(False)
            logger.warning(
                f"[Main] IB Gateway non disponible (tentative {attempt}) : {exc}\n"
                f"       → Retry dans {delay:.0f}s … (Ctrl+C pour quitter)"
            )
            if attempt == 1:
                asyncio.ensure_future(
                    _send_telegram(
                        "🔴 <b>DÉCONNEXION IB GATEWAY</b>\n"
                        "Tentative de reconnexion..."
                    )
                )
            if max_attempts > 0 and attempt >= max_attempts:
                logger.error("[Main] Nombre maximum de tentatives atteint")
                return False
            await asyncio.sleep(delay)


async def main() -> None:
    _check_paper_mode()

    cfg = _load_config()
    pairs = cfg["strategy"]["pairs"]

    # Initialisation des composants
    broker = BrokerAPI()
    session_mgr = SessionManager()
    dashboard = Dashboard(pairs)
    data_feed = DataFeed(
        broker=broker,
        pairs=pairs,
        spread_filter_pips=cfg["strategy"]["spread_filter_pips"],
    )

    logger.remove()
    logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | {message}")
    logger.add(
        "trading_d1_bougie/logs/main_{time}.log",
        rotation=cfg["logging"]["rotation"],
        retention=cfg["logging"]["retention"],
        level=cfg["logging"]["level"],
    )

    logger.info("══════════════════════════════════════════════════════")
    logger.info("  TRADING-D1-BOUGIE — Paper Trading Live (Phase 10)")
    logger.info(f"  Paires : {', '.join(pairs)}")
    logger.info(f"  IB Gateway : {os.getenv('IB_HOST', '127.0.0.1')}:{os.getenv('IB_PORT', '4002')}")
    logger.info("══════════════════════════════════════════════════════")

    try:
        # Connexion avec retry infini — attend IB Gateway
        connected = await _connect_with_retry(broker, dashboard, delay=10.0)
        if not connected:
            logger.error("[Main] Impossible de se connecter — arrêt")
            return

        await data_feed.start()
        await _main_loop(broker, data_feed, session_mgr, dashboard, cfg)
    except KeyboardInterrupt:
        logger.info("[Main] Interrupted by user (Ctrl+C)")
    finally:
        await data_feed.stop()
        await broker.disconnect()
        dashboard.set_ib_connected(False)
        logger.info("[Main] Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
