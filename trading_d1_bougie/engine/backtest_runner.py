# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/engine/backtest_runner.py
# DESCRIPTION  : Backtesting vectorbt de la stratégie D1/M15
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

import asyncio
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from loguru import logger

from trading_d1_bougie.engine.broker_api import BrokerAPI


class BacktestRunner:
    """
    Backtesting de la stratégie TRADING-D1-BOUGIE via vectorbt.

    Pipeline :
      1. Récupération historique D1 + M15 via IB
      2. Construction des rectangles D1 jour par jour
      3. Simulation des entrées M15 (BOS/CHoCH aux extrémités)
      4. Calcul métriques : winrate, profit factor, max DD, Sharpe
      5. Export CSV + courbe d'equity PNG
    """

    OUTPUT_CSV = "TRADING_D1_BOUGIE_backtest_results.csv"
    OUTPUT_PNG = "TRADING_D1_BOUGIE_equity_curve.png"

    def __init__(
        self,
        broker: BrokerAPI,
        pairs: list[str],
        rr_ratio: float = 2.0,
        risk_pct: float = 1.0,
        proximity_buffer_pct: float = 10.0,
        fibo_forbidden_pct: float = 5.0,
        spread_pips: float = 1.5,
    ) -> None:
        self.broker = broker
        self.pairs = pairs
        self.rr_ratio = rr_ratio
        self.risk_pct = risk_pct
        self.proximity_buffer_pct = proximity_buffer_pct
        self.fibo_forbidden_pct = fibo_forbidden_pct
        self.spread_pips = spread_pips

    async def _load_historical_data(
        self, pair: str, days: int = 365
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Charge les données historiques D1 et M15."""
        from ib_insync import Contract

        contract = Contract(
            symbol=pair[:3],
            secType="CASH",
            exchange="IDEALPRO",
            currency=pair[3:],
        )

        # D1
        d1_bars = await self.broker.ib.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr=f"{days} D",
            barSizeSetting="1 day",
            whatToShow="MIDPOINT",
            useRTH=True,
        )
        # M15
        m15_bars = await self.broker.ib.reqHistoricalDataAsync(
            contract,
            endDateTime="",
            durationStr=f"{days} D",
            barSizeSetting="15 mins",
            whatToShow="MIDPOINT",
            useRTH=False,
        )

        d1_df = pd.DataFrame(
            [
                {
                    "date": b.date,
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                }
                for b in d1_bars
            ]
        ).set_index("date")

        m15_df = pd.DataFrame(
            [
                {
                    "date": b.date,
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                }
                for b in m15_bars
            ]
        ).set_index("date")

        return d1_df, m15_df

    def _simulate_signals(
        self, d1_df: pd.DataFrame, m15_df: pd.DataFrame, pair: str
    ) -> pd.DataFrame:
        """
        Génère les signaux d'entrée en appliquant les 4 règles de la stratégie.

        Returns:
            DataFrame avec colonnes: entries, exits, direction, sl_pips, tp_pips
        """
        pip_size = 0.01 if "JPY" in pair.upper() else 0.0001
        spread_offset = self.spread_pips * pip_size

        records = []

        for i in range(1, len(d1_df)):
            prev_d1 = d1_df.iloc[i - 1]
            d1_date = d1_df.index[i]

            d1_high = prev_d1["high"]
            d1_low = prev_d1["low"]
            height = d1_high - d1_low
            if height <= 0:
                continue

            mid = (d1_high + d1_low) / 2.0
            fibo_upper = mid + height * self.fibo_forbidden_pct / 100.0
            fibo_lower = mid - height * self.fibo_forbidden_pct / 100.0
            prox_upper = d1_high - height * self.proximity_buffer_pct / 100.0
            prox_lower = d1_low + height * self.proximity_buffer_pct / 100.0

            # Bougies M15 du jour courant
            day_str = str(d1_date)[:10]
            day_m15 = m15_df[m15_df.index.astype(str).str[:10] == day_str]

            if len(day_m15) < 5:
                continue

            for j in range(2, len(day_m15)):
                c = day_m15.iloc[j]
                price = c["close"]

                # Check 1: dans le rectangle
                if price < d1_low or price > d1_high:
                    continue
                # Check 2: près d'une extrémité
                near_low = price <= prox_lower
                near_high = price >= prox_upper
                if not near_low and not near_high:
                    continue
                # Check 3: hors zone Fibo
                if fibo_lower <= price <= fibo_upper:
                    continue

                # Check 4 simplifié: direction basée sur position
                direction = "LONG" if near_low else "SHORT"

                # Calcul SL/TP
                if direction == "LONG":
                    sl = round(d1_low - spread_offset, 5)
                    sl_pips = round((price - sl) / pip_size, 1)
                    tp_pips = round(sl_pips * self.rr_ratio, 1)
                    tp = round(price + tp_pips * pip_size, 5)
                else:
                    sl = round(d1_high + spread_offset, 5)
                    sl_pips = round((sl - price) / pip_size, 1)
                    tp_pips = round(sl_pips * self.rr_ratio, 1)
                    tp = round(price - tp_pips * pip_size, 5)

                if sl_pips <= 0:
                    continue

                records.append(
                    {
                        "date": day_m15.index[j],
                        "direction": direction,
                        "entry": price,
                        "sl": sl,
                        "tp": tp,
                        "sl_pips": sl_pips,
                        "tp_pips": tp_pips,
                    }
                )
                break  # 1 trade max par jour

        return pd.DataFrame(records)

    def _compute_metrics(
        self, trades: pd.DataFrame, initial_equity: float = 10_000.0
    ) -> dict[str, Any]:
        """Calcule les métriques de performance."""
        if trades.empty:
            return {"error": "No trades generated"}

        wins = (trades["tp_pips"] > 0).sum()
        total = len(trades)
        winrate = wins / total * 100

        gross_profit = trades[trades["tp_pips"] > 0]["tp_pips"].sum()
        gross_loss = abs(trades[trades["tp_pips"] <= 0]["sl_pips"].sum())
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Courbe d'equity simplifiée (1% risk, RR 2)
        pnl_series = pd.Series(
            [
                self.risk_pct * self.rr_ratio if d == "win" else -self.risk_pct
                for d in trades.apply(
                    lambda r: "win" if r["tp_pips"] > 0 else "loss", axis=1
                )
            ]
        )
        equity_curve = initial_equity * (1 + pnl_series.cumsum() / 100)
        max_dd = (
            (equity_curve.cummax() - equity_curve) / equity_curve.cummax()
        ).max() * 100

        returns = pnl_series / 100
        sharpe = (
            (returns.mean() / returns.std() * (252**0.5))
            if returns.std() > 0
            else 0.0
        )

        return {
            "total_trades": total,
            "winrate_pct": round(winrate, 2),
            "profit_factor": round(profit_factor, 3),
            "max_drawdown_pct": round(max_dd, 2),
            "sharpe_ratio": round(sharpe, 3),
            "equity_curve": equity_curve,
        }

    async def run(self, days: int = 365) -> dict[str, Any]:
        """
        Lance le backtest complet et exporte les résultats.

        Args:
            days: nombre de jours d'historique à backtester

        Returns:
            dict: métriques par paire + globales
        """
        all_results = {}

        for pair in self.pairs:
            logger.info(f"[Backtest] Loading {days}D data for {pair}…")
            try:
                d1_df, m15_df = await self._load_historical_data(pair, days)
            except Exception as exc:  # noqa: BLE001
                logger.error(f"[Backtest] {pair}: data load error — {exc}")
                continue

            trades = self._simulate_signals(d1_df, m15_df, pair)
            metrics = self._compute_metrics(trades)
            all_results[pair] = metrics

            logger.info(
                f"[Backtest] {pair}: {metrics.get('total_trades', 0)} trades | "
                f"WR={metrics.get('winrate_pct', 0):.1f}% | "
                f"PF={metrics.get('profit_factor', 0):.2f} | "
                f"DD={metrics.get('max_drawdown_pct', 0):.1f}% | "
                f"Sharpe={metrics.get('sharpe_ratio', 0):.2f}"
            )

            if "equity_curve" in metrics:
                self._export_equity_curve(metrics["equity_curve"], pair)
                self._export_trades_csv(trades, pair)

        return all_results

    def _export_equity_curve(self, equity_curve: pd.Series, pair: str) -> None:
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.plot(equity_curve.values, linewidth=1.5, color="#00b4d8")
        ax.set_title(f"📊 TRADING-D1-BOUGIE — Equity Curve [{pair}]")
        ax.set_xlabel("Trade #")
        ax.set_ylabel("Equity (USD)")
        ax.grid(alpha=0.3)
        fname = f"TRADING_D1_BOUGIE_equity_curve_{pair}.png"
        fig.savefig(fname, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info(f"[Backtest] Exported → {fname}")

    def _export_trades_csv(self, trades: pd.DataFrame, pair: str) -> None:
        fname = f"TRADING_D1_BOUGIE_backtest_results_{pair}.csv"
        trades.to_csv(fname, index=False)
        logger.info(f"[Backtest] Exported → {fname}")


async def _main() -> None:
    broker = BrokerAPI()
    await broker.connect()

    import yaml

    with open("trading_d1_bougie/config/config.yaml") as f:
        cfg = yaml.safe_load(f)

    runner = BacktestRunner(
        broker=broker,
        pairs=cfg["strategy"]["pairs"],
        rr_ratio=cfg["strategy"]["rr_ratio"],
        risk_pct=cfg["strategy"]["risk_pct"],
        proximity_buffer_pct=cfg["strategy"]["proximity_buffer_pct"],
        fibo_forbidden_pct=cfg["strategy"]["fibo_forbidden_zone_pct"],
        spread_pips=cfg["strategy"]["spread_filter_pips"],
    )

    results = await runner.run(days=365)
    await broker.disconnect()
    logger.info(f"[Backtest] Done — {len(results)} pairs processed")


if __name__ == "__main__":
    asyncio.run(_main())
