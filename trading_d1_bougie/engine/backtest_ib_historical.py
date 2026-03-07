# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/engine/backtest_ib_historical.py
# DESCRIPTION  : Backtest sur données historiques réelles IB Gateway
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-08
# ============================================================

"""
Backtest sur données historiques réelles récupérées depuis IB Gateway.

Nécessite une connexion IB Gateway active (paper ou live).
Contrairement à backtest_standalone.py, ce module utilise de vraies
données OHLCV et ne génère aucun biais directionnel.

Usage :
    python -m trading_d1_bougie.engine.backtest_ib_historical
"""

import asyncio
import math
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from ib_insync import IB, Forex
from loguru import logger

from trading_d1_bougie.core.d1_range_builder import D1RangeBuilder
from trading_d1_bougie.core.entry_validator import EntryValidator
from trading_d1_bougie.core.order_manager import OrderManager
from trading_d1_bougie.core.risk_manager import RiskManager
from trading_d1_bougie.core.structure_detector import StructureDetector
from trading_d1_bougie.core.trend_detector import TrendDetector

logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | {message}")


# ------------------------------------------------------------------ #
# Récupération données IB                                             #
# ------------------------------------------------------------------ #


async def fetch_historical_data(
    ib: IB,
    pair: str,
    duration: str = "2 Y",
    bar_size_d1: str = "1 day",
    bar_size_m15: str = "15 mins",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Récupère les bougies D1 et M15 depuis IB pour une paire.

    Args:
        ib: instance IB connectée
        pair: identifiant paire (ex: "EURUSD")
        duration: durée historique (ex: "2 Y", "1 Y", "6 M")
        bar_size_d1: timeframe D1 (ex: "1 day")
        bar_size_m15: timeframe M15 (ex: "15 mins")

    Returns:
        tuple(d1_candles, m15_candles) — listes de dicts OHLCV
    """
    base, quote = pair[:3], pair[3:]
    contract = Forex(f"{base}{quote}")
    qualified = await ib.qualifyContractsAsync(contract)
    if not qualified:
        raise RuntimeError(f"Contrat non qualifié : {pair}")

    d1_bars = await ib.reqHistoricalDataAsync(
        contract,
        endDateTime="",
        durationStr=duration,
        barSizeSetting=bar_size_d1,
        whatToShow="MIDPOINT",
        useRTH=False,
    )
    m15_bars = await ib.reqHistoricalDataAsync(
        contract,
        endDateTime="",
        durationStr=duration,
        barSizeSetting=bar_size_m15,
        whatToShow="MIDPOINT",
        useRTH=False,
    )

    def _to_dict(bar: Any) -> dict[str, Any]:
        return {
            "date": str(bar.date)[:10],
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }

    return [_to_dict(b) for b in d1_bars], [_to_dict(b) for b in m15_bars]


# ------------------------------------------------------------------ #
# Moteur de backtest sur données réelles                              #
# ------------------------------------------------------------------ #


class IBHistoricalBacktester:
    """
    Rejoue la stratégie TRADING-D1-BOUGIE sur données IB réelles.

    Processus :
    1. Pour chaque journée, rectangle D1 = range D1 de la veille
    2. Bougies M15 du jour filtrées par date
    3. Trend + Structure détectés sur les N premières bougies M15
    4. Validation entrée (EntryValidator Cython)
    5. Simulation résultat TP/SL sur les bougies suivantes du même jour
    """

    def __init__(self, cfg: dict[str, Any]) -> None:
        strategy = cfg["strategy"]
        risk_cfg = cfg["risk"]

        self.pairs: list[str] = strategy["pairs"]
        self.rr_ratio: float = float(strategy["rr_ratio"])
        self.risk_pct: float = float(strategy["risk_pct"])
        self.proximity_buffer_pct: float = float(strategy["proximity_buffer_pct"])
        self.fibo_forbidden_pct: float = float(strategy["fibo_forbidden_zone_pct"])
        self.spread_filter_pips: float = float(strategy["spread_filter_pips"])
        self.daily_loss_limit_pct: float = float(risk_cfg["daily_loss_limit_pct"])
        self.max_daily_trades: int = int(strategy.get("max_daily_trades", 2))

        self.d1_builder = D1RangeBuilder(
            fibo_forbidden_pct=self.fibo_forbidden_pct,
            proximity_buffer_pct=self.proximity_buffer_pct,
        )
        self.trend_detector = TrendDetector()
        self.structure_detector = StructureDetector()
        self.entry_validator = EntryValidator()
        self.order_manager = OrderManager(rr_ratio=self.rr_ratio)
        self.risk_manager = RiskManager(
            risk_pct=self.risk_pct,
            daily_loss_limit_pct=self.daily_loss_limit_pct,
        )

    def _simulate_pair(
        self,
        pair: str,
        d1_candles: list[dict[str, Any]],
        m15_candles: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Simule la stratégie sur une paire avec des données réelles IB."""
        trades: list[dict[str, Any]] = []
        pip_size = 0.01 if "JPY" in pair.upper() else 0.0001

        # Index M15 par date
        m15_by_date: dict[str, list[dict[str, Any]]] = {}
        for bar in m15_candles:
            m15_by_date.setdefault(bar["date"], []).append(bar)

        equity = 10_000.0

        for i in range(1, len(d1_candles)):
            equity_sod = equity
            daily_trades = 0

            d1_prev = d1_candles[i - 1]
            d1_high = d1_prev["high"]
            d1_low = d1_prev["low"]
            d1_date = d1_candles[i]["date"]

            if (d1_high - d1_low) < pip_size * 10:
                continue  # doji extrême

            if equity_sod <= 0 or equity <= 0:
                break

            risk_check = self.risk_manager.check_daily_limit(equity_sod, equity)
            if risk_check.value != "ALLOWED":
                continue

            d1_range = self.d1_builder.build(pair, d1_high, d1_low)
            day_m15 = m15_by_date.get(d1_date, [])
            if len(day_m15) < 10:
                continue

            for j in range(5, len(day_m15)):
                if daily_trades >= self.max_daily_trades:
                    break

                # Trend sur les bougies passées de la journée
                window = day_m15[:j]
                trend = self.trend_detector.detect(window)
                if trend.value == "NEUTRAL":
                    continue

                swing_highs = self.trend_detector.find_swing_highs(window)
                swing_lows = self.trend_detector.find_swing_lows(window)
                if not swing_highs or not swing_lows:
                    continue

                structure = self.structure_detector.detect(
                    window, swing_highs, swing_lows, trend.value
                )
                if structure.signal_type.value == "NONE":
                    continue

                price = window[-1]["close"]
                if not (d1_low <= price <= d1_high):
                    continue

                validation = self.entry_validator.validate(
                    price, d1_range, trend, structure
                )
                if not hasattr(validation, "status"):
                    continue
                status = str(
                    validation.status.value
                    if hasattr(validation.status, "value")
                    else validation.status
                )
                if status != "VALID":
                    continue

                direction = str(validation.direction)
                swing_sl: float = (
                    d1_range.low - pip_size * 3
                    if direction == "LONG"
                    else d1_range.high + pip_size * 3
                )
                sl_pips = round(abs(price - swing_sl) / pip_size, 1)
                if sl_pips < 2:
                    continue

                lot_size = self.risk_manager.calculate_lot_size(equity, sl_pips, pair)
                if lot_size <= 0:
                    continue

                spec = self.order_manager.build(pair, direction, price, swing_sl, lot_size)

                # Simuler résultat sur les bougies suivantes du même jour
                future = day_m15[j:]
                result = _simulate_result(direction, price, spec.sl_price, spec.tp_price, future)
                if result == "OPEN":
                    continue

                if result == "TP":
                    pnl_pips = abs(spec.tp_price - price) / pip_size
                    pnl_usd = round(pnl_pips * lot_size * pip_size * 10_000, 2)
                else:
                    pnl_pips = -abs(price - spec.sl_price) / pip_size
                    pnl_usd = round(pnl_pips * lot_size * pip_size * 10_000, 2)

                equity += pnl_usd
                daily_trades += 1

                trades.append({
                    "date": d1_date,
                    "pair": pair,
                    "direction": direction,
                    "entry": round(price, 5),
                    "sl": round(spec.sl_price, 5),
                    "tp": round(spec.tp_price, 5),
                    "lot_size": round(lot_size, 2),
                    "result": result,
                    "pnl_pips": round(pnl_pips, 1),
                    "pnl_usd": pnl_usd,
                    "equity": round(equity, 2),
                })
                break  # 1 trade par analyse de barre

        return trades

    def run(
        self,
        d1_data: dict[str, list[dict[str, Any]]],
        m15_data: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        """Lance le backtest sur toutes les paires."""
        all_trades: list[dict[str, Any]] = []
        results: dict[str, Any] = {}

        for pair in self.pairs:
            if pair not in d1_data or pair not in m15_data:
                logger.warning(f"[IB Backtest] No data for {pair} — skip")
                continue

            logger.info(f"[IB Backtest] Simulation {pair}…")
            trades = self._simulate_pair(pair, d1_data[pair], m15_data[pair])
            all_trades.extend(trades)
            metrics = _compute_metrics(trades, pair)
            results[pair] = metrics
            logger.info(
                f"[IB Backtest] {pair} → {metrics['total_trades']} trades | "
                f"WR={metrics['winrate_pct']:.1f}% | "
                f"PF={metrics['profit_factor']:.2f} | "
                f"DD={metrics['max_drawdown_pct']:.1f}% | "
                f"Sharpe={metrics['sharpe_ratio']:.2f}"
            )

        results["GLOBAL"] = _compute_metrics(all_trades, "ALL")
        self._export(all_trades)
        return results

    def _export(self, trades: list[dict[str, Any]]) -> None:
        if not trades:
            return
        df = pd.DataFrame(trades)
        fname = "TRADING_D1_BOUGIE_ib_backtest_results.csv"
        df.to_csv(fname, index=False)
        logger.info(f"[IB Backtest] Exported → {fname} ({len(df)} trades)")


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #


def _simulate_result(
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    future_bars: list[dict[str, Any]],
) -> str:
    is_long = direction in ("LONG", "long", "BUY")
    for bar in future_bars:
        if is_long:
            if bar["low"] <= sl:
                return "SL"
            if bar["high"] >= tp:
                return "TP"
        else:
            if bar["high"] >= sl:
                return "SL"
            if bar["low"] <= tp:
                return "TP"
    return "OPEN"


def _compute_metrics(trades: list[dict[str, Any]], label: str) -> dict[str, Any]:
    if not trades:
        return {"label": label, "total_trades": 0, "winrate_pct": 0.0,
                "profit_factor": 0.0, "max_drawdown_pct": 0.0, "sharpe_ratio": 0.0}
    total = len(trades)
    wins = sum(1 for t in trades if t["result"] == "TP")
    winrate = wins / total * 100
    gross_profit = sum(t["pnl_pips"] for t in trades if t["result"] == "TP")
    gross_loss = abs(sum(t["pnl_pips"] for t in trades if t["result"] == "SL"))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    equity_curve = [t["equity"] for t in trades]
    peak, max_dd = equity_curve[0], 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
    returns = [t["pnl_usd"] / 10_000.0 for t in trades]
    if len(returns) > 1:
        mean_r = sum(returns) / len(returns)
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1))
        sharpe = mean_r / std_r * math.sqrt(252) if std_r > 0 else 0.0
    else:
        sharpe = 0.0
    return {
        "label": label, "total_trades": total,
        "winrate_pct": round(winrate, 2), "profit_factor": round(profit_factor, 3),
        "max_drawdown_pct": round(max_dd, 2), "sharpe_ratio": round(sharpe, 3),
    }


# ------------------------------------------------------------------ #
# Point d'entrée                                                       #
# ------------------------------------------------------------------ #


async def main() -> None:
    config_path = Path("trading_d1_bougie/config/config.yaml")
    with open(config_path) as f:
        cfg: dict[str, Any] = yaml.safe_load(f)  # type: ignore[no-any-return]

    ib = IB()
    host = "127.0.0.1"
    port = 4002  # paper trading
    logger.info(f"Connecting to IB Gateway {host}:{port}…")
    await ib.connectAsync(host=host, port=port, clientId=10)
    logger.info("✅ Connected")

    pairs = cfg["strategy"]["pairs"]
    d1_data: dict[str, list[dict[str, Any]]] = {}
    m15_data: dict[str, list[dict[str, Any]]] = {}

    backtester = IBHistoricalBacktester(cfg)

    for pair in pairs:
        logger.info(f"Fetching 2Y historical data for {pair}…")
        d1, m15 = await fetch_historical_data(ib, pair, duration="2 Y")
        d1_data[pair] = d1
        m15_data[pair] = m15
        logger.info(f"  {pair}: {len(d1)} D1 bars, {len(m15)} M15 bars")

    ib.disconnect()

    results = backtester.run(d1_data, m15_data)
    g = results.get("GLOBAL", {})
    logger.info(
        f"\n══ RÉSULTATS IB RÉELS ══\n"
        f"  Trades : {g.get('total_trades', 0)}\n"
        f"  WR     : {g.get('winrate_pct', 0):.1f}%\n"
        f"  PF     : {g.get('profit_factor', 0):.3f}\n"
        f"  MaxDD  : {g.get('max_drawdown_pct', 0):.1f}%\n"
        f"  Sharpe : {g.get('sharpe_ratio', 0):.3f}\n"
    )


if __name__ == "__main__":
    asyncio.run(main())
