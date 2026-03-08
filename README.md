# 📊 TRADING-D1-BOUGIE — D1 Range / M15 Structure Bot

[![CI — Quality Gate](https://github.com/aekbenvlogs-maker/TRADING-D1-CANDLE/actions/workflows/ci.yml/badge.svg)](https://github.com/aekbenvlogs-maker/TRADING-D1-CANDLE/actions/workflows/ci.yml)

> **Stratégie :** Bougie D1 de la veille comme rectangle de référence | Entrée M15 sur **BOS uniquement** aux extrémités  
> **Stack :** Python 3.11.9 + Cython 3.0+ + IB Gateway + Docker  
> **Mode par défaut :** ⚠️ PAPER TRADING — Ne jamais activer le live sans validation complète

---

## 🎯 Stratégie — BOS-only (Sprint 6 M4)

La stratégie trade exclusivement les **Break of Structure (BOS)** aux extrémités du rectangle D1.

| Signal | Statut | Raison |
|--------|--------|--------|
| **BOS BULLISH** près du D1_LOW | ✅ Tradé | Confirmation direction + tendance |
| **BOS BEARISH** près du D1_HIGH | ✅ Tradé | Confirmation direction + tendance |
| CHoCH (toute direction) | ❌ Rejeté | Signal de retournement non validé paper trading |

**Filtres actifs :**
- Range D1 minimum : **20 pips** (évite les dojis)
- ATR(14) D1 minimum : **40 pips** (évite les marchés comprimés)
- Fenêtre news haute volatilité : **±30 min** autour NFP/FOMC/BCE/BOE
- Limite journalière : **2 trades** par paire, **-3%** equity stop

---

## 📦 Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make build
```

---

## 🚀 Lancement

### Mode direct (Python)

```bash
# Paper Trading (IB Gateway port 4002)
python -m trading_d1_bougie.engine.main

# Backtest synthétique avec walk-forward IS/OOS
python -m trading_d1_bougie.engine.backtest_standalone

# Backtest sur données IB réelles (nécessite IB Gateway actif)
python -m trading_d1_bougie.engine.backtest_ib_historical \
    --pairs EURUSD GBPUSD USDJPY --duration "2 Y" --port 4002
```

### Mode Docker (recommandé en production)

```bash
# Copier et configurer l'environnement
cp .env.example .env   # renseigner IB_HOST, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

# Démarrer le bot en conteneur
docker-compose up -d

# Voir les logs en temps réel
docker-compose logs -f trading-bot

# Arrêter
docker-compose down
```

---

## 📰 Calendrier économique (news filter)

Le filtre news bloque automatiquement le trading **30 minutes avant et après** chaque publication HIGH-impact.

Mettre à jour `trading_d1_bougie/config/news_calendar.csv` chaque trimestre (format ForexFactory) :

```csv
date,time,currency,impact,event
2026-04-03,14:30,USD,HIGH,Non-Farm Payrolls
2026-04-29,20:00,USD,HIGH,FOMC Rate Decision
2026-04-17,12:15,EUR,HIGH,ECB Rate Decision
```

---

## 🧪 QA

```bash
make qa          # format + lint + typecheck + test (0 erreur requis)
make test        # tests uniquement (couverture ≥ 80%)
make build       # compilation Cython
```

**Coverage actuelle : 99.83% — 86 tests**

---

## 📁 Architecture

```
trading_d1_bougie/
├── core/           # Modules Cython compilés
│   ├── d1_range_builder.pyx    # Rectangle D1 + zones Fibonacci
│   ├── trend_detector.pyx      # HH/HL/LL/LH sur M15 (swing_lookback=5)
│   ├── structure_detector.pyx  # BOS / CHoCH détection
│   ├── entry_validator.pyx     # Validation entrée (BOS-only)
│   ├── order_manager.pyx       # Bracket order + TP dynamique D1
│   └── risk_manager.pyx        # Sizing JPY-aware + daily limit
├── engine/
│   ├── main.py                 # Boucle principale live
│   ├── broker_api.py           # IB Gateway (reconnexion infinie)
│   ├── broker_interface.py     # IBroker ABC (testabilité)
│   ├── session_manager.py      # Sessions + filtre news
│   ├── data_feed.py            # Feed M15 aligné sur boundaries UTC
│   ├── state_manager.py        # Persistance SQLite open_pairs
│   ├── backtest_runner.py      # Backtest rapide
│   ├── backtest_standalone.py  # Backtest synthétique + walk-forward
│   └── backtest_ib_historical.py # Backtest données IB réelles
├── config/
│   ├── config.yaml             # Paramètres stratégie et risque
│   └── news_calendar.csv       # Calendrier NFP/FOMC/BCE/BOE
└── tests/                      # 86 tests unitaires + intégration
```

---

## ⚠️ AVERTISSEMENT

Le mode live (port 4001) engage du capital **RÉEL**.  
N'activer QUE après :
1. `make qa` 100% vert
2. Backtest walk-forward OOS/IS ratio > 0.70
3. 60 jours paper trading validés
4. Toutes les alertes Telegram testées manuellement

```yaml
# config.yaml — activer le live (un seul changement)
broker:
  port_live: 4001   # au lieu de port_paper: 4002
```
