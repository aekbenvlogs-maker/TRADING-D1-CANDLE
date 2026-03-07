# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : trading_d1_bougie/engine/backtest_standalone.py
# DESCRIPTION  : Backtest standalone sans IB Gateway (données synthétiques)
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : 2026-03-07
# ============================================================

"""
Backtest standalone — aucune connexion IB Gateway requise.

Génère 2 ans de données OHLCV synthétiques (D1 + M15) via GBM calibré
sur les paramètres réels EUR/USD, puis rejoue fidèlement la stratégie :
  1. Rectangle D1 de la veille
  2. Trend M15 (HH/HL → BULLISH, LL/LH → BEARISH)
  3. BOS/CHoCH aux extrémités
  4. Validation (in range + near extremity + outside Fibo + aligned)
  5. SL/TP/lot-size calculés par les modules Cython

Usage :
    python -m trading_d1_bougie.engine.backtest_standalone
"""

import math
import random
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless — pas de fenêtre GUI
import matplotlib.pyplot as plt
import pandas as pd
import yaml
from loguru import logger

# ------------------------------------------------------------------ #
# Imports modules Cython compilés                                      #
# ------------------------------------------------------------------ #
from trading_d1_bougie.core.d1_range_builder import D1RangeBuilder
from trading_d1_bougie.core.entry_validator import EntryValidator
from trading_d1_bougie.core.order_manager import OrderManager
from trading_d1_bougie.core.risk_manager import RiskManager
from trading_d1_bougie.core.structure_detector import StructureDetector
from trading_d1_bougie.core.trend_detector import TrendDetector

logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | {message}")

# ------------------------------------------------------------------ #
# Générateur de données synthétiques                                   #
# ------------------------------------------------------------------ #

PAIR_PARAMS: dict[str, dict[str, float]] = {
    "EURUSD": {"price": 1.0950, "sigma_d1": 0.0050, "spread_pips": 1.2, "pip": 0.0001},
    "GBPUSD": {"price": 1.2700, "sigma_d1": 0.0070, "spread_pips": 1.5, "pip": 0.0001},
    "USDJPY": {"price": 149.50, "sigma_d1": 0.6500, "spread_pips": 1.8, "pip": 0.01},
}


def _gbm_candle(
    prev_close: float, sigma: float, rng: random.Random
) -> dict[str, float]:
    """
    Génère une bougie OHLCV via Geometric Brownian Motion log-normal.

    sigma est un sigma ABSOLU (en unité de prix). On le normalise par le
    prix courant pour obtenir le retour relatif, garantissant que le GBM
    reste stable même pour les paires à prix élevé (USD/JPY).
    """
    # Retour relatif quotidien : sigma_rel = sigma_abs / prev_close
    sigma_rel = sigma / max(prev_close, 1e-10)
    drift_rel = sigma_rel * 0.05 * (rng.random() - 0.5)
    body_rel = rng.gauss(0, sigma_rel)
    wick_up_rel = abs(rng.gauss(0, sigma_rel * 0.3))
    wick_dn_rel = abs(rng.gauss(0, sigma_rel * 0.3))

    o = prev_close * (1.0 + drift_rel)
    c = o * (1.0 + body_rel)
    # Assurer que les prix restent positifs
    c = max(c, o * 0.70)  # max -30% par jour
    h = max(o, c) * (1.0 + wick_up_rel)
    lo = min(o, c) * (1.0 - wick_dn_rel)
    vol = int(abs(rng.gauss(1000, 300)))

    return {"open": round(o, 5), "close": round(c, 5), "high": round(h, 5), "low": round(lo, 5), "volume": vol}


def generate_d1_candles(pair: str, days: int = 500, seed: int = 42) -> list[dict[str, float]]:
    """Génère `days` bougies D1 synthétiques pour la paire."""
    rng = random.Random(seed)
    params = PAIR_PARAMS[pair]
    price = params["price"]
    sigma = params["sigma_d1"]
    candles: list[dict[str, float]] = []
    for _ in range(days):
        c = _gbm_candle(price, sigma, rng)
        candles.append(c)
        price = c["close"]
    return candles


def generate_m15_session(
    start_price: float,
    sigma_m15: float,
    n_bars: int = 128,
    seed: int = 0,
    drift_bias: float = 0.0,
) -> list[dict[str, float]]:
    """
    Génère n_bars bougies M15 via GBM libre (non borné).

    Le GBM libre permet au TrendDetector et StructureDetector de détecter
    des tendances (HH/HL) et des BOS/CHoCH naturels. Sigma calibré sur
    les vrais paramètres de volatilité M15 de chaque paire.

    drift_bias : biais directionnel par bougie (ex: +sigma*0.3 pour long,
                 -sigma*0.3 pour short). Utilisé pour les bougies futures
                 afin de simuler un trade dans la bonne direction.
    """
    rng = random.Random(seed)
    price = start_price
    candles: list[dict[str, float]] = []

    for _ in range(n_bars):
        o = price
        body = rng.gauss(drift_bias, sigma_m15)
        c = o + body
        h = max(o, c) + abs(rng.gauss(0, sigma_m15 * 0.3))
        lo = min(o, c) - abs(rng.gauss(0, sigma_m15 * 0.3))
        vol = max(100, int(abs(rng.gauss(1000, 300))))

        candles.append({
            "open": round(o, 5), "close": round(c, 5),
            "high": round(h, 5), "low": round(lo, 5), "volume": vol,
        })
        price = c

    return candles


# Sigma M15 calibré par paire (volatilité réelle intrajournalière)
PAIR_SIGMA_M15: dict[str, float] = {
    "EURUSD": 0.00030,   # ~3 pips par bougie M15
    "GBPUSD": 0.00040,   # ~4 pips par bougie M15
    "USDJPY": 0.035,     # ~3.5 pips par bougie M15
}


# ------------------------------------------------------------------ #
# Moteur de backtest                                                   #
# ------------------------------------------------------------------ #

class StandaloneBacktester:
    """
    Rejoue la stratégie TRADING-D1-BOUGIE sur données synthétiques.

    Utilise les 6 modules Cython compilés — identique au live.
    """

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        strategy = cfg["strategy"]
        risk_cfg = cfg["risk"]

        self.pairs: list[str] = strategy["pairs"]
        self.rr_ratio: float = float(strategy["rr_ratio"])
        self.risk_pct: float = float(strategy["risk_pct"])
        # Buffer de proximité aligné sur config.yaml (10%)
        self.proximity_buffer_pct: float = float(strategy["proximity_buffer_pct"])
        self.fibo_forbidden_pct: float = float(strategy["fibo_forbidden_zone_pct"])
        self.spread_filter_pips: float = float(strategy["spread_filter_pips"])
        self.daily_loss_limit_pct: float = float(risk_cfg["daily_loss_limit_pct"])

        # Modules Cython
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
        self, pair: str, days: int = 500
    ) -> list[dict[str, Any]]:
        """
        Simule la stratégie jour par jour sur une paire.

        Approche :
        - Rectangle D1 = range de la bougie D1 de la veille
        - Fenêtre M15 = 128 bars GBM libre centrée sur le milieu du range D1
          (sigma calibré sur la vraie volatilité M15 de chaque paire)
        - Trend + Structure détectés sur toute la fenêtre M15
        - Validation : prix d'entrée = close du dernier bar M15, ramené
          dans le D1 range pour la vérification de proximité
        - Pour chaque trade valide, 32 bars supplémentaires servent à
          simuler le résultat TP/SL
        """
        trades: list[dict[str, Any]] = []
        d1_candles = generate_d1_candles(pair, days=days + 1)
        pip_size = PAIR_PARAMS[pair]["pip"]
        spread_pips = PAIR_PARAMS[pair]["spread_pips"]
        sigma_m15 = PAIR_SIGMA_M15[pair]

        equity = 10_000.0
        daily_trades = 0
        MAX_DAILY_TRADES = int(self.cfg["strategy"].get("max_daily_trades", 2))

        for day_idx in range(1, len(d1_candles)):
            # Nouvelle journée → reset compteurs
            equity_start_of_day = equity  # équité en début de journée
            daily_trades = 0

            # Bougie D1 de la veille → définit le rectangle du jour
            d1_prev = d1_candles[day_idx - 1]
            d1_high = d1_prev["high"]
            d1_low = d1_prev["low"]

            # Vérifier hauteur minimale (évite les dojis extrêmes)
            if (d1_high - d1_low) < pip_size * 10:
                continue

            # Construire le rectangle D1
            d1_range = self.d1_builder.build(pair, d1_high, d1_low)

            # Filtrer spread
            if spread_pips > self.spread_filter_pips:
                continue

            # Vérif limite journalière (début de journée)
            # Signature: check_daily_limit(equity_start, equity_current)
            # Protéger contre equity ≤ 0 (ruine)
            if equity_start_of_day <= 0 or equity <= 0:
                break
            risk_check = self.risk_manager.check_daily_limit(equity_start_of_day, equity)
            if risk_check.value != "ALLOWED":
                continue

            # Générer 128 bars M15 GBM libre, partant du milieu du D1 range
            mid_price = (d1_high + d1_low) / 2.0
            m15_window = generate_m15_session(
                start_price=mid_price,
                sigma_m15=sigma_m15,
                n_bars=128,
                seed=day_idx * 1337,
            )

            # Détecter la tendance sur toute la fenêtre
            trend = self.trend_detector.detect(m15_window)
            trend_value: str = str(trend.value if hasattr(trend, "value") else trend)

            # Ignorer les journées sans tendance claire
            if trend_value == "NEUTRAL":
                continue

            # Détecter swings et structure sur toute la fenêtre
            swing_highs = self.trend_detector.find_swing_highs(m15_window)
            swing_lows = self.trend_detector.find_swing_lows(m15_window)

            if not swing_highs or not swing_lows:
                continue

            structure = self.structure_detector.detect(
                m15_window, swing_highs, swing_lows, trend_value
            )

            # Vérifier qu'un signal BOS ou CHoCH a été détecté
            struct_type = str(
                structure.signal_type.value
                if hasattr(structure.signal_type, "value")
                else structure.signal_type
            )
            if struct_type == "NONE":
                continue

            # Prix d'entrée = close de la dernière bougie M15, ramené dans D1 range
            raw_price = m15_window[-1]["close"]
            price = raw_price

            # Guard explicite : skip si le prix est sorti du range D1
            if not (d1_low <= price <= d1_high):
                continue

            # Valider l'entrée via EntryValidator
            validation = self.entry_validator.validate(price, d1_range, trend, structure)
            if not hasattr(validation, "status"):
                continue

            status_name = str(
                validation.status.value
                if hasattr(validation.status, "value")
                else validation.status
            )
            if status_name != "VALID":
                continue

            if daily_trades >= MAX_DAILY_TRADES:
                continue

            # Déterminer direction et swing SL
            direction = str(validation.direction) if hasattr(validation, "direction") else "LONG"
            if direction in ("LONG", "long", "BUY"):
                swing_sl_price = d1_range.low - pip_size * 3
            else:
                swing_sl_price = d1_range.high + pip_size * 3

            # Position sizing
            sl_pips = abs(price - swing_sl_price) / pip_size
            if sl_pips < 2:
                continue

            lot_size = self.risk_manager.calculate_lot_size(equity, sl_pips, pair)
            if lot_size <= 0:
                continue

            # Construire l'ordre (calcule TP via RR ratio)
            spec = self.order_manager.build(pair, direction, price, swing_sl_price, lot_size)
            tp_price = spec.tp_price
            sl_actual = spec.sl_price

            # Générer 32 bars futurs pour simuler le résultat TP/SL.
            # Un léger biais directionnel (0.4σ) simule le fait que la
            # stratégie trade dans la direction de la tendance (BOS confirmé).
            # GBM neutre — aucun biais directionnel (simulation honnête)
            future_candles = generate_m15_session(
                start_price=price,
                sigma_m15=sigma_m15,
                n_bars=48,  # fenêtre plus large → moins de trades OPEN
                seed=day_idx * 2741,
                drift_bias=0.0,   # GBM neutre — aucun look-forward bias
            )

            result = _simulate_trade_result(
                direction, price, sl_actual, tp_price, future_candles, pip_size
            )
            if result == "OPEN":
                continue  # trade non résolu → ignoré

            # Calculer P&L (mini-lot = 10_000 units)
            # pnl_usd = pips * lot * pip_value_per_lot
            # pip_value_per_lot (mini) = pip_size * 10_000 * usd_factor
            if result == "TP":
                pnl_pips = abs(tp_price - price) / pip_size
                pnl_usd = round(pnl_pips * lot_size * pip_size * 10_000 * _get_usd_factor(pair, tp_price), 2)
            else:  # SL
                pnl_pips = -abs(price - sl_actual) / pip_size
                pnl_usd = round(pnl_pips * lot_size * pip_size * 10_000 * _get_usd_factor(pair, sl_actual), 2)

            equity += pnl_usd
            daily_trades += 1

            trades.append({
                "day": day_idx,
                "pair": pair,
                "direction": direction,
                "entry": round(price, 5),
                "sl": round(sl_actual, 5),
                "tp": round(tp_price, 5),
                "lot_size": round(lot_size, 2),
                "result": result,
                "pnl_pips": round(pnl_pips, 1),
                "pnl_usd": pnl_usd,
                "equity": round(equity, 2),
            })

        return trades

    def run(self, days: int = 500) -> dict[str, Any]:
        """Lance le backtest complet sur toutes les paires."""
        all_trades: list[dict[str, Any]] = []
        pair_results: dict[str, Any] = {}

        for pair in self.pairs:
            logger.info(f"[Backtest] Simulation {pair} sur {days} jours…")
            trades = self._simulate_pair(pair, days=days)
            all_trades.extend(trades)
            metrics = _compute_metrics(trades, pair)
            pair_results[pair] = metrics
            logger.info(
                f"[Backtest] {pair} → {metrics['total_trades']} trades | "
                f"WR={metrics['winrate_pct']:.1f}% | "
                f"PF={metrics['profit_factor']:.2f} | "
                f"DD={metrics['max_drawdown_pct']:.1f}% | "
                f"Sharpe={metrics['sharpe_ratio']:.2f}"
            )

        # Métriques globales (toutes paires agrégées)
        global_metrics = _compute_metrics(all_trades, "ALL")
        pair_results["GLOBAL"] = global_metrics

        logger.info(
            f"\n[Backtest] ══ RÉSULTATS GLOBAUX ══\n"
            f"  Total trades   : {global_metrics['total_trades']}\n"
            f"  Winrate        : {global_metrics['winrate_pct']:.1f}%   (seuil ≥ 45%)\n"
            f"  Profit Factor  : {global_metrics['profit_factor']:.3f}  (seuil ≥ 1.5)\n"
            f"  Max Drawdown   : {global_metrics['max_drawdown_pct']:.1f}%   (seuil ≤ 15%)\n"
            f"  Sharpe Ratio   : {global_metrics['sharpe_ratio']:.3f}  (seuil ≥ 1.0)\n"
        )

        _print_validation(global_metrics)
        _export_csv(all_trades)
        _export_equity_curve(all_trades, pair_results)

        return pair_results


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _simulate_trade_result(
    direction: str,
    entry: float,
    sl: float,
    tp: float,
    future_candles: list[dict[str, float]],
    pip_size: float,
) -> str:
    """Retourne 'TP', 'SL' ou 'OPEN' en regardant les bougies futures."""
    is_long = direction in ("LONG", "long", "BUY")
    for bar in future_candles:
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


def _get_usd_factor(pair: str, price: float) -> float:
    """Facteur de conversion vers USD."""
    if pair.endswith("USD"):
        return 1.0
    if pair.startswith("USD"):
        return 1.0 / price if price > 0 else 1.0
    return 1.0


def _compute_metrics(trades: list[dict[str, Any]], label: str) -> dict[str, Any]:
    """Calcule les métriques de performance."""
    if not trades:
        return {
            "label": label, "total_trades": 0,
            "winrate_pct": 0.0, "profit_factor": 0.0,
            "max_drawdown_pct": 0.0, "sharpe_ratio": 0.0,
        }

    total = len(trades)
    wins = sum(1 for t in trades if t["result"] == "TP")
    winrate = wins / total * 100

    gross_profit = sum(t["pnl_pips"] for t in trades if t["result"] == "TP")
    gross_loss = abs(sum(t["pnl_pips"] for t in trades if t["result"] == "SL"))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Courbe d'equity et Max Drawdown
    equity_curve: list[float] = []
    eq = 10_000.0
    for t in trades:
        eq += t["pnl_usd"]
        equity_curve.append(eq)

    peak = equity_curve[0]
    max_dd = 0.0
    for eq_val in equity_curve:
        if eq_val > peak:
            peak = eq_val
        dd = (peak - eq_val) / peak * 100
        if dd > max_dd:
            max_dd = dd

    # Sharpe (annualisé, 252 jours de trading)
    returns = [t["pnl_usd"] / 10_000.0 for t in trades]
    if len(returns) > 1:
        mean_r = sum(returns) / len(returns)
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1))
        sharpe = (mean_r / std_r * math.sqrt(252)) if std_r > 0 else 0.0
    else:
        sharpe = 0.0

    return {
        "label": label,
        "total_trades": total,
        "winrate_pct": round(winrate, 2),
        "profit_factor": round(profit_factor, 3),
        "max_drawdown_pct": round(max_dd, 2),
        "sharpe_ratio": round(sharpe, 3),
        "equity_final": round(equity_curve[-1] if equity_curve else 10_000.0, 2),
    }


def _print_validation(metrics: dict[str, Any]) -> None:
    """Affiche le tableau de validation Phase 9."""
    checks = [
        ("Winrate ≥ 45%", metrics["winrate_pct"], 45.0, ">="),
        ("Profit Factor ≥ 1.5", metrics["profit_factor"], 1.5, ">="),
        ("Max Drawdown ≤ 15%", metrics["max_drawdown_pct"], 15.0, "<="),
        ("Sharpe ≥ 1.0", metrics["sharpe_ratio"], 1.0, ">="),
        ("Échantillon ≥ 100 trades", metrics["total_trades"], 100, ">="),
    ]
    print("\n┌─────────────────────────────────────────┐")
    print("│   VALIDATION PHASE 9 — CRITÈRES PLAN   │")
    print("├───────────────────────┬────────┬────────┤")
    print("│ Critère               │ Valeur │ Statut │")
    print("├───────────────────────┼────────┼────────┤")
    for label, value, threshold, op in checks:
        if op == ">=":
            passed = float(value) >= threshold
        else:
            passed = float(value) <= threshold
        status = "  ✅  " if passed else "  ❌  "
        val_str = f"{value:.1f}" if isinstance(value, float) else str(value)
        print(f"│ {label:<21} │ {val_str:>6} │{status}│")
    print("└───────────────────────┴────────┴────────┘")


def _export_csv(trades: list[dict[str, Any]]) -> None:
    """Exporte les trades en CSV."""
    if not trades:
        logger.warning("[Backtest] Aucun trade à exporter")
        return
    df = pd.DataFrame(trades)
    fname = "TRADING_D1_BOUGIE_backtest_results.csv"
    df.to_csv(fname, index=False)
    logger.info(f"[Backtest] Exporté → {fname} ({len(df)} trades)")


def _export_equity_curve(
    trades: list[dict[str, Any]], pair_results: dict[str, Any]
) -> None:
    """Génère et exporte la courbe d'equity PNG."""
    if not trades:
        return

    fig, axes = plt.subplots(2, 1, figsize=(14, 8))
    fig.suptitle("📊 TRADING-D1-BOUGIE — Backtest Results", fontsize=14, fontweight="bold")

    # --- Courbe d'equity globale ---
    eq = 10_000.0
    equity_vals: list[float] = [eq]
    for t in trades:
        eq += t["pnl_usd"]
        equity_vals.append(eq)

    ax1 = axes[0]
    ax1.plot(equity_vals, linewidth=1.5, color="#00b4d8")
    ax1.axhline(y=10_000, color="gray", linestyle="--", linewidth=0.8, label="Départ 10k$")
    ax1.fill_between(range(len(equity_vals)), 10_000, equity_vals,
                     where=[v >= 10_000 for v in equity_vals], alpha=0.2, color="green")
    ax1.fill_between(range(len(equity_vals)), 10_000, equity_vals,
                     where=[v < 10_000 for v in equity_vals], alpha=0.2, color="red")
    ax1.set_title("Courbe d'Equity Globale (toutes paires)", fontsize=11)
    ax1.set_xlabel("Trade #")
    ax1.set_ylabel("Equity (USD)")
    ax1.legend(fontsize=9)
    ax1.grid(alpha=0.3)

    # --- Métriques par paire (bar chart winrate) ---
    ax2 = axes[1]
    pairs_shown = [k for k in pair_results if k != "GLOBAL"]
    winrates = [pair_results[p]["winrate_pct"] for p in pairs_shown]
    pfs = [pair_results[p]["profit_factor"] for p in pairs_shown]
    x = range(len(pairs_shown))
    bar_width = 0.35
    bars1 = ax2.bar([i - bar_width / 2 for i in x], winrates, bar_width,
                    label="Winrate (%)", color="#0096c7", alpha=0.85)
    ax2_twin = ax2.twinx()
    bars2 = ax2_twin.bar([i + bar_width / 2 for i in x], pfs, bar_width,
                         label="Profit Factor", color="#48cae4", alpha=0.75)
    ax2.axhline(y=45, color="orange", linestyle="--", linewidth=1, label="Seuil WR 45%")
    ax2_twin.axhline(y=1.5, color="red", linestyle="--", linewidth=1, label="Seuil PF 1.5")
    ax2.set_title("Winrate & Profit Factor par paire", fontsize=11)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(pairs_shown)
    ax2.set_ylabel("Winrate (%)")
    ax2_twin.set_ylabel("Profit Factor")

    # Labels sur les barres
    for bar in bars1:
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                 f"{bar.get_height():.1f}%", ha="center", va="bottom", fontsize=9)
    for bar in bars2:
        ax2_twin.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                      f"{bar.get_height():.2f}", ha="center", va="bottom", fontsize=9)

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2_twin.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper right")
    ax2.grid(alpha=0.2)

    plt.tight_layout()
    fname = "TRADING_D1_BOUGIE_equity_curve.png"
    fig.savefig(fname, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"[Backtest] Exporté → {fname}")


# ------------------------------------------------------------------ #
# Point d'entrée                                                       #
# ------------------------------------------------------------------ #

def main() -> None:
    """Lance le backtest standalone."""
    config_path = Path("trading_d1_bougie/config/config.yaml")
    with open(config_path) as f:
        cfg: dict[str, Any] = yaml.safe_load(f)  # type: ignore[no-any-return]

    logger.info("═" * 60)
    logger.info("  TRADING-D1-BOUGIE — Backtest Standalone (sans IB Gateway)")
    logger.info("  Données synthétiques GBM calibrées EUR/USD, GBP/USD, USD/JPY")
    logger.info("═" * 60)

    backtester = StandaloneBacktester(cfg)
    results = backtester.run(days=500)

    global_metrics = results.get("GLOBAL", {})
    checks_passed = (
        global_metrics.get("winrate_pct", 0) >= 45
        and global_metrics.get("profit_factor", 0) >= 1.5
        and global_metrics.get("max_drawdown_pct", 100) <= 15
        and global_metrics.get("sharpe_ratio", 0) >= 1.0
        and global_metrics.get("total_trades", 0) >= 100
    )

    if checks_passed:
        logger.info("✅ PHASE 9 VALIDÉE — Tous les critères du plan sont atteints")
        logger.info("   → Prêt pour la Phase 10 (Paper Trading Live)")
    else:
        logger.warning("⚠️  Certains critères non atteints — Ajuster les paramètres config.yaml")

    return


if __name__ == "__main__":
    main()
