"""Analyser les trades USDJPY du CSV pour comprendre DD=47%."""
import sys

sys.path.insert(0, "/Users/ben/Documents/TRADING-D1-BOUGE")
import pandas as pd

df = pd.read_csv("/Users/ben/Documents/TRADING-D1-BOUGE/TRADING_D1_BOUGIE_backtest_results.csv")
print(df.columns.tolist())
print()

usdjpy = df[df["pair"] == "USDJPY"].copy()
print(f"USDJPY: {len(usdjpy)} trades")
print(usdjpy[["day", "direction", "entry", "sl", "tp", "lot_size", "result", "pnl_pips", "pnl_usd", "equity"]].head(20).to_string())
print()

# Stats
print(f"pnl_usd stats: min={usdjpy['pnl_usd'].min():.2f}, max={usdjpy['pnl_usd'].max():.2f}, mean={usdjpy['pnl_usd'].mean():.2f}")
print(f"sl_pips range: {abs(usdjpy[usdjpy['result']=='SL']['pnl_pips'].min()):.1f} to {abs(usdjpy[usdjpy['result']=='SL']['pnl_pips'].max()):.1f}")

# Equity curve
eq_final = usdjpy["equity"].iloc[-1]
eq_start = 10_000
print(f"Equity: start={eq_start}, end={eq_final:.2f}")
