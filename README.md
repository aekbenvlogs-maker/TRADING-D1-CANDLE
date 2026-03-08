# 📊 TRADING-D1-BOUGIE — D1 Range / M15 Structure Bot

[![CI — Quality Gate](https://github.com/aekbenvlogs-maker/TRADING-D1-CANDLE/actions/workflows/ci.yml/badge.svg)](https://github.com/aekbenvlogs-maker/TRADING-D1-CANDLE/actions/workflows/ci.yml)

> **Stratégie :** Bougie D1 de la veille comme référence | Entrée M15 sur BOS/CHoCH aux extrémités  
> **Stack :** Python 3.11.9 + Cython 3.0+ + IB Gateway + VSCode  
> **Mode par défaut :** ⚠️ PAPER TRADING — Ne jamais activer le live sans validation complète

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make build
```

## Lancement

```bash
# Paper Trading
python -m trading_d1_bougie.engine.main

# Backtest
python -m trading_d1_bougie.engine.backtest_runner
```

## QA

```bash
make qa          # format + lint + typecheck + test
make test        # tests uniquement (couverture ≥ 80%)
make build       # compilation Cython
```

## ⚠️ AVERTISSEMENT

Le mode live (port 4001) engage du capital RÉEL.  
N'activer QUE après `make qa` 100% vert + backtest validé + 2 semaines paper trading.
