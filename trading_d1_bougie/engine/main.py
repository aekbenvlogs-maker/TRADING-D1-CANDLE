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
from pathlib import Path

import yaml
from loguru import logger
from rich.console import Console

from trading_d1_bougie.engine.broker_api import BrokerAPI
from trading_d1_bougie.engine.dashboard import Dashboard
from trading_d1_bougie.engine.data_feed import DataFeed
from trading_d1_bougie.engine.session_manager import SessionManager

console = Console()


def _load_config() -> dict:
    config_path = Path("trading_d1_bougie/config/config.yaml")
    with open(config_path) as f:
        return yaml.safe_load(f)


def _check_paper_mode() -> None:
    """Vérifie le mode trading — affiche WARNING critique si live."""
    paper = os.getenv("PAPER_TRADING", "true").lower()
    mode = os.getenv("IB_MODE", "paper").lower()

    if paper != "true" or mode == "live":
        console.print(
            "\n[bold red]╔══════════════════════════════════════════════════════════════╗[/bold red]"
        )
        console.print(
            "[bold red]║   ⚠️  ATTENTION — MODE LIVE TRADING                         ║[/bold red]"
        )
        console.print(
            "[bold red]║                                                              ║[/bold red]"
        )
        console.print(
            "[bold red]║   Le mode live (port 4001) engage du capital RÉEL.          ║[/bold red]"
        )
        console.print(
            "[bold red]║   Ne l'activer QUE après validation complète du backtest.   ║[/bold red]"
        )
        console.print(
            "[bold red]╚══════════════════════════════════════════════════════════════╝[/bold red]\n"
        )
        confirm = input("Confirmer le mode LIVE ? Tapez 'LIVE-CONFIRMED' pour continuer : ")
        if confirm.strip() != "LIVE-CONFIRMED":
            console.print("[yellow]Annulé. Repassez en mode paper dans .env[/yellow]")
            sys.exit(0)
    else:
        console.print("[green]✅ Mode PAPER TRADING activé (port 4002)[/green]")


async def _main_loop(
    broker: BrokerAPI,
    data_feed: DataFeed,
    session_mgr: SessionManager,
    dashboard: Dashboard,
    cfg: dict,
) -> None:
    """Boucle principale asynchrone de la stratégie."""
    from trading_d1_bougie.core.d1_range_builder import D1RangeBuilder
    from trading_d1_bougie.core.entry_validator import EntryValidator
    from trading_d1_bougie.core.order_manager import OrderManager
    from trading_d1_bougie.core.risk_manager import RiskManager, RiskCheckResult
    from trading_d1_bougie.core.structure_detector import StructureDetector, StructureType
    from trading_d1_bougie.core.trend_detector import TrendDetector, TrendBias

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
    d1_ranges: dict = {}
    equity_start: float = 10_000.0  # À récupérer depuis le compte IB
    open_pairs: list[str] = []
    daily_trade_count: dict = {p: 0 for p in pairs}

    logger.info("[Main] 🚀 Starting main loop…")

    with dashboard.start_live() as live:
        # ---------------------------------------------------------------- #
        # Étape 1 — Construire les rectangles D1 au démarrage             #
        # ---------------------------------------------------------------- #
        for pair in pairs:
            try:
                candle = await broker.get_d1_candle(pair)
                if candle:
                    d1_ranges[pair] = d1_builder.build(
                        pair, candle["high"], candle["low"]
                    )
                    dashboard.update_pair(
                        pair,
                        d1_high=d1_ranges[pair].high,
                        d1_low=d1_ranges[pair].low,
                        d1_mid=d1_ranges[pair].mid,
                    )
            except Exception as exc:  # noqa: BLE001
                logger.error(f"[Main] D1 build error for {pair}: {exc}")

        while True:
            now_utc = session_mgr.now_utc()

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
                    dashboard.update_pair(pair, zone_status="SPREAD TROP ÉLEVÉ", eligible=False)
                    continue

                validation = entry_validator.validate(
                    price, d1_ranges[pair], trend_bias, signal
                )
                dashboard.update_pair(
                    pair,
                    zone_status="IN ZONE ✅" if validation.is_valid else validation.status.value,
                    eligible=validation.is_valid,
                )

                if not validation.is_valid:
                    continue

                # -------------------------------------------------------- #
                # Risk checks                                               #
                # -------------------------------------------------------- #
                equity_current = equity_start  # TODO: récupérer depuis broker
                if risk_manager.check_daily_limit(equity_start, equity_current) != RiskCheckResult.ALLOWED:
                    logger.warning("[Main] Daily loss limit reached — SHUTDOWN")
                    return

                if risk_manager.check_max_pairs(len(open_pairs)) != RiskCheckResult.ALLOWED:
                    logger.warning(f"[Main] Max open pairs ({risk_cfg['max_open_pairs']}) reached")
                    continue

                # -------------------------------------------------------- #
                # Étape 5 — Construire et envoyer l'ordre                 #
                # -------------------------------------------------------- #
                swing_sl = (
                    d1_ranges[pair].low if validation.direction == "LONG"
                    else d1_ranges[pair].high
                )
                lot_size = risk_manager.calculate_lot_size(
                    equity=equity_start, sl_pips=10.0, pair=pair  # sl_pips estimé
                )
                order_spec = order_manager.build(
                    pair=pair,
                    direction=validation.direction,
                    entry_price=price,
                    swing_sl_price=swing_sl,
                    lot_size=lot_size,
                )
                logger.info(f"[Main] 🎯 ORDER: {order_spec}")
                # TODO: broker.place_bracket_order(order_spec)

                open_pairs.append(pair)
                daily_trade_count[pair] += 1

            await asyncio.sleep(30)
            live.update(dashboard.render())


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

    logger.add(
        "trading_d1_bougie/logs/main_{time}.log",
        rotation=cfg["logging"]["rotation"],
        retention=cfg["logging"]["retention"],
        level=cfg["logging"]["level"],
    )

    try:
        await broker.connect()
        dashboard.set_ib_connected(True)
        await data_feed.start()
        await _main_loop(broker, data_feed, session_mgr, dashboard, cfg)
    except KeyboardInterrupt:
        logger.info("[Main] Interrupted by user")
    finally:
        await data_feed.stop()
        await broker.disconnect()
        dashboard.set_ib_connected(False)
        logger.info("[Main] Shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
