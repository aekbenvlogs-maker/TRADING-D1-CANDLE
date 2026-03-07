# 📊 TRADING-D1-BOUGIE — Plan d'Action Complet

> **Projet :** TRADING-D1-BOUGIE — D1 Range / M15 Structure Bot  
> **Stratégie :** Bougie D1 de la veille comme référence | Entrée M15 sur BOS/CHoCH aux extrémités  
> **Stack :** Python 3.11.9 + Cython 3.0+ + IB Gateway + VSCode  
> **Mode par défaut :** ⚠️ PAPER TRADING — Ne jamais activer le live sans validation complète du backtest

---

## PHASE 0 — Prérequis & Environnement

### 0.1 Vérification Python
- [ ] Vérifier la version exacte : `python --version` → doit retourner `3.11.9`
- [ ] Si incorrect, télécharger Python 3.11.9 sur [python.org](https://python.org)
- [ ] Vérifier que `pip` correspond à Python 3.11.9 : `pip --version`

### 0.2 Création du Virtual Environment
```bash
# Créer le venv avec Python 3.11.9
python -m venv .venv

# Activer (Windows)
.venv\Scripts\activate

# Activer (Linux/macOS)
source .venv/bin/activate

# Vérifier
python --version  # → 3.11.9
```

### 0.3 Installation de VSCode + Extensions
- [ ] Installer VSCode (dernière version stable)
- [ ] Installer les extensions via `.vscode/extensions.json` :
  - `ms-python.python` (Pylance)
  - `charliermarsh.ruff`
  - `ms-python.black-formatter`
  - `ms-python.mypy-type-checker`
  - `ms-python.python` (Test Explorer)
  - `lextudio.restructuredtext` (Cython highlighting)
  - `eamodio.gitlens`
  - `redhat.vscode-yaml`
  - `mikestead.dotenv`

### 0.4 IB Gateway Setup
- [ ] Télécharger IB Gateway sur [interactivebrokers.com](https://www.interactivebrokers.com)
- [ ] Configurer en mode **Paper Trading** (port `4002`)
- [ ] Activer l'API dans les settings IB Gateway : `Enable ActiveX and Socket Clients`
- [ ] Vérifier la connexion : host `127.0.0.1`, port `4002`

---

## PHASE 1 — Structure du Projet

### 1.1 Arborescence à créer
```
TRADING-D1-BOUGIE/
│
├── trading_d1_bougie/
│   ├── core/                        # Cython — moteurs de signal
│   │   ├── __init__.py
│   │   ├── d1_range_builder.pyx     # Construction rectangle D1
│   │   ├── trend_detector.pyx       # Détection tendance M15 (HH/HL)
│   │   ├── structure_detector.pyx   # Détection BOS / CHoCH
│   │   ├── entry_validator.pyx      # Validation zone + Fibo filter
│   │   ├── order_manager.pyx        # Gestion ordres IB Gateway
│   │   └── risk_manager.pyx         # Position sizing + daily loss limit
│   │
│   ├── engine/                      # Python — orchestration
│   │   ├── __init__.py
│   │   ├── main.py                  # Point d'entrée principal
│   │   ├── data_feed.py             # Flux données IB (D1 + M15)
│   │   ├── broker_api.py            # Connexion ib_insync
│   │   ├── session_manager.py       # Gestion sessions + timezone
│   │   ├── backtest_runner.py       # Module backtesting vectorbt
│   │   └── dashboard.py             # Dashboard Rich terminal
│   │
│   ├── config/
│   │   ├── config.yaml              # Paramètres stratégie
│   │   └── .env.example             # Template variables sensibles
│   │
│   ├── logs/                        # Logs auto-générés
│   │   └── .gitkeep
│   │
│   └── tests/                       # Tests unitaires
│       ├── __init__.py
│       ├── test_d1_range_builder_*.py
│       ├── test_trend_detector_*.py
│       ├── test_structure_detector_*.py
│       ├── test_entry_validator_*.py
│       ├── test_order_manager_*.py
│       └── test_risk_manager_*.py
│
├── .vscode/
│   ├── settings.json
│   ├── extensions.json
│   └── launch.json
│
├── pyproject.toml                   # Black + Ruff + Pytest config
├── mypy.ini                         # Mypy strict mode
├── .pylintrc                        # Pylint score ≥ 8.5
├── Makefile                         # Targets QA
├── setup.py                         # Compilation Cython
├── requirements.txt                 # Dépendances pinned Python 3.11.9
├── .env                             # Variables sensibles (gitignored)
├── .gitignore
└── README.md
```

### 1.2 Initialisation Git
```bash
git init
echo ".env" >> .gitignore
echo ".venv/" >> .gitignore
echo "*.pyc" >> .gitignore
echo "trading_d1_bougie/logs/*.log" >> .gitignore
echo "build/" >> .gitignore
echo "*.so" >> .gitignore
git add .
git commit -m "init: TRADING-D1-BOUGIE project structure"
```

---

## PHASE 2 — Fichiers de Configuration

### 2.1 `requirements.txt`
```txt
# Broker
ib_insync==0.9.86

# Data & Strategy
pandas==2.1.4
numpy==1.26.4
vectorbt==0.26.1
matplotlib==3.8.2

# Cython
Cython==3.0.8

# Dashboard & Logging
rich==13.7.0
loguru==0.7.2

# Code Quality
black==23.12.1
ruff==0.1.14
pylint==3.0.3
mypy==1.8.0

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
pytest-mock==3.12.0
```

### 2.2 `pyproject.toml`
```toml
[tool.black]
line-length = 88
target-version = ["py311"]

[tool.ruff]
target-version = "py311"
select = ["E", "F", "W", "I", "N", "UP"]
line-length = 88

[tool.pytest.ini_options]
testpaths = ["trading_d1_bougie/tests"]
verbose = true
asyncio_mode = "auto"
addopts = "--cov=trading_d1_bougie --cov-report=html:TRADING_D1_BOUGIE_coverage_report.html"
```

### 2.3 `mypy.ini`
```ini
[mypy]
python_version = 3.11
strict = True
exclude = trading_d1_bougie/core/.*\.pyx
```

### 2.4 `config.yaml`
```yaml
# TRADING-D1-BOUGIE — Configuration Stratégie
strategy:
  pairs: ["EURUSD", "GBPUSD", "USDJPY"]
  rr_ratio: 2.0
  risk_pct: 1.0
  max_daily_trades: 2
  proximity_buffer_pct: 10.0      # % de la hauteur du rectangle
  fibo_forbidden_zone_pct: 5.0    # ± % autour du midpoint
  spread_filter_pips: 2.0
  lot_type: "mini"                # standard / mini / micro

risk:
  daily_loss_limit_pct: 3.0
  max_open_pairs: 1

broker:
  host: "127.0.0.1"
  port_paper: 4002
  port_live: 4001
  account_type: "Individual"

session:
  timezone: "Europe/Paris"
  active_sessions: ["london", "new_york"]

logging:
  rotation: "1 day"
  retention: "30 days"
  level: "INFO"
```

### 2.5 `.env.example`
```env
# TRADING-D1-BOUGIE — Variables sensibles
IB_ACCOUNT_ID=your_account_id_here
IB_MODE=paper            # paper ou live
IB_PORT=4002             # 4002 paper / 4001 live
PAPER_TRADING=true       # TOUJOURS true par défaut
```

### 2.6 `Makefile`
```makefile
format:
	black trading_d1_bougie/

lint:
	ruff check trading_d1_bougie/
	pylint trading_d1_bougie/

typecheck:
	mypy trading_d1_bougie/

test:
	pytest --cov --cov-fail-under=80

qa:
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test

build:
	python setup.py build_ext --inplace

all:
	$(MAKE) qa
	$(MAKE) build
```

---

## PHASE 3 — Fichiers Header (Template)

> Chaque fichier `.py` et `.pyx` doit commencer par ce bloc :

```python
# ============================================================
# PROJECT      : TRADING-D1-BOUGIE — D1 Range / M15 Entry Bot
# FILE         : <filename>
# DESCRIPTION  : <one-line purpose>
# AUTHOR       : TRADING-D1-BOUGIE Dev Team
# WORKFLOW     : VSCode + Claude + Copilot Pro + File Engineering
# PYTHON       : 3.11.9
# LAST UPDATED : YYYY-MM-DD
# ============================================================
```

---

## PHASE 4 — Développement des Modules Cython (core/)

### 4.1 `d1_range_builder.pyx`
- [ ] Récupérer la bougie D1 de la veille via IB `reqHistoricalData`
- [ ] Extraire `D1_HIGH` et `D1_LOW`
- [ ] Calculer `D1_MID` = 50% Fibo = `(D1_HIGH + D1_LOW) / 2`
- [ ] Calculer les bornes de la zone interdite Fibo : `MID ± (hauteur × fibo_pct / 100)`
- [ ] Calculer les zones de proximité des extrémités : `LOW + buffer` et `HIGH - buffer`
- [ ] Retourner un objet `D1Range` typé

### 4.2 `trend_detector.pyx`
- [ ] Recevoir une liste de bougies M15 (OHLCV)
- [ ] Identifier les swing highs et swing lows
- [ ] Détecter la séquence HH/HL → `BULLISH`
- [ ] Détecter la séquence LL/LH → `BEARISH`
- [ ] Sinon → `NEUTRAL`
- [ ] Retourner un `TrendBias` enum

### 4.3 `structure_detector.pyx`
- [ ] Recevoir les bougies M15 + dernier swing identifié
- [ ] Détecter un **BOS** : cassure franche d'un swing précédent (confirmation sur clôture de bougie)
- [ ] Détecter un **CHoCH** : cassure du dernier swing opposé
- [ ] Validation : le body de la bougie doit franchir le niveau (pas seulement la mèche)
- [ ] Retourner `StructureSignal` avec type (BOS/CHoCH/NONE) + candle déclencheur

### 4.4 `entry_validator.pyx`
- [ ] Recevoir : prix actuel + `D1Range` + `TrendBias` + `StructureSignal`
- [ ] **Check 1 :** Prix à l'intérieur du rectangle D1 → sinon `INVALID: OUTSIDE_RANGE`
- [ ] **Check 2 :** Prix dans la zone de proximité d'une extrémité → sinon `INVALID: NOT_NEAR_EXTREMITY`
- [ ] **Check 3 :** Prix hors de la zone Fibo interdite → sinon `INVALID: FIBO_FORBIDDEN_ZONE`
- [ ] **Check 4 :** Signal dans le sens de la tendance → sinon `INVALID: AGAINST_TREND`
- [ ] Si tous les checks OK → `VALID` avec direction (LONG/SHORT)

### 4.5 `order_manager.pyx`
- [ ] Recevoir : direction + prix d'entrée + swing SL + RR configuré
- [ ] Calculer SL en pips (avec buffer spread)
- [ ] Calculer TP selon RR ratio
- [ ] Gérer la précision : 4 décimales (5 pour JPY)
- [ ] Envoyer l'ordre bracket via IB Gateway (entry + SL + TP)
- [ ] Logger l'ordre avec timestamp UTC + Paris

### 4.6 `risk_manager.pyx`
- [ ] Calculer la taille de position depuis : `(equity × risk_pct) / (SL_pips × pip_value)`
- [ ] Vérifier la limite journalière : si P&L jour ≤ `-3%` → shutdown automatique
- [ ] Vérifier : max 1 paire ouverte simultanément
- [ ] Inclure slippage et spread dans le calcul du SL

---

## PHASE 5 — Développement des Modules Python (engine/)

### 5.1 `broker_api.py`
- [ ] Connexion IB Gateway via `ib_insync` (port depuis `.env`)
- [ ] Auto-reconnect si déconnexion
- [ ] Request throttler : max 50 requêtes / 10 secondes
- [ ] Méthode `get_d1_candle(pair)` → retourne la bougie D1 de la veille
- [ ] Méthode `get_m15_candles(pair, n)` → retourne les N dernières bougies M15
- [ ] Méthode `get_live_spread(pair)` → retourne le spread actuel en pips

### 5.2 `session_manager.py`
- [ ] Utiliser `zoneinfo` pour toutes les conversions timezone
- [ ] Auto-détection DST US (2ème dimanche mars → 1er dimanche nov)
- [ ] Auto-détection DST EU (dernier dimanche mars → dernier dimanche oct)
- [ ] Gérer la semaine de décalage annuelle entre les deux fuseaux
- [ ] Fournir `is_active_session()` → bool basé sur London + New York overlap
- [ ] Tous les timestamps internes en UTC

### 5.3 `data_feed.py`
- [ ] Flux de données asynchrone (`asyncio`) pour M15 en temps réel
- [ ] Subscribe aux ticks IB pour calculer le volume proxy (tick count / bar M15)
- [ ] Buffer de bougies M15 en mémoire (dernières N bougies configurables)
- [ ] Filtrage spread : ignorer les barres avec spread > seuil configuré

### 5.4 `backtest_runner.py`
- [ ] Récupérer historique D1 + M15 via IB `reqHistoricalData`
- [ ] Répliquer fidèlement la logique des 6 étapes de la stratégie
- [ ] Utiliser `vectorbt` pour la simulation
- [ ] Inclure le coût du spread par trade
- [ ] Générer le rapport : winrate, profit factor, max drawdown, Sharpe
- [ ] Exporter :
  - `TRADING_D1_BOUGIE_backtest_results.csv`
  - `TRADING_D1_BOUGIE_equity_curve.png`

### 5.5 `dashboard.py`
- [ ] Dashboard terminal `Rich` avec header : `📊 TRADING-D1-BOUGIE — D1 Range / M15 Structure Bot`
- [ ] Colonnes affichées :
  - Paire surveillée
  - Rectangle D1 : HIGH / LOW / 50% Fibo
  - Tendance M15 : BULLISH / BEARISH / NEUTRAL
  - Dernier signal structure : BOS / CHoCH / NONE
  - Statut zone entrée : IN ZONE / TOO FAR / FORBIDDEN FIBO
  - P&L position ouverte (pips + USD)
  - Stats journalières
  - Spread live
  - Éligibilité prochain trade
  - Colonne UTC | Colonne Europe/Paris
  - Indicateur connexion IB Gateway (🟢 / 🔴)

### 5.6 `main.py`
- [ ] Point d'entrée principal
- [ ] Vérifier le mode paper/live depuis `.env` → **afficher WARNING si live**
- [ ] Initialiser broker, data_feed, session_manager
- [ ] Boucle principale asynchrone :
  1. Construire le rectangle D1 au démarrage de session
  2. Analyser la tendance M15 en continu
  3. Écouter les BOS/CHoCH
  4. Valider les conditions d'entrée
  5. Exécuter l'ordre si tout est validé
  6. Mettre à jour le dashboard

---

## PHASE 6 — Tests Unitaires (tests/)

> Convention de nommage : `test_<module>_<function>_<scenario>.py`

### 6.1 Tests par module Cython (3 tests minimum chacun)

| Module | Test 1 | Test 2 | Test 3 |
|---|---|---|---|
| `d1_range_builder` | rectangle correct sur données normales | gestion bougie doji | calcul Fibo midpoint précis |
| `trend_detector` | détecte BULLISH sur HH/HL | détecte BEARISH sur LL/LH | retourne NEUTRAL si ambigu |
| `structure_detector` | détecte BOS sur cassure body | détecte CHoCH sur retournement | rejette cassure mèche seule |
| `entry_validator` | valide entrée long aux 4 conditions | invalide si hors rectangle | invalide si zone Fibo interdite |
| `order_manager` | calcul SL/TP correct sur EURUSD | précision 5 décimales USDJPY | bracket order bien formé |
| `risk_manager` | lot size calculé correctement | shutdown si limite -3% atteinte | bloque si paire déjà ouverte |

### 6.2 Commandes de test
```bash
# Lancer tous les tests avec couverture
pytest --cov --cov-fail-under=80

# Test d'un module spécifique
pytest trading_d1_bougie/tests/test_d1_range_builder_*.py -v

# Générer le rapport HTML
pytest --cov --cov-report=html:TRADING_D1_BOUGIE_coverage_report.html
```

---

## PHASE 7 — Compilation Cython

### 7.1 `setup.py`
```python
from setuptools import setup
from Cython.Build import cythonize
import numpy as np

setup(
    name="TRADING-D1-BOUGIE",
    ext_modules=cythonize(
        "trading_d1_bougie/core/*.pyx",
        compiler_directives={"language_level": "3"}
    ),
    include_dirs=[np.get_include()],
)
```

### 7.2 Compilation
```bash
# Compiler tous les modules Cython
python setup.py build_ext --inplace

# Ou via Makefile
make build
```

---

## PHASE 8 — QA Complète (avant tout backtest)

```bash
# Lancer la QA complète en une commande
make qa
```

> ✅ Tous les checks doivent passer au vert avant de continuer :

| Check | Commande | Critère |
|---|---|---|
| Formatage | `make format` | Zéro modification Black |
| Linting | `make lint` | Zéro warning Ruff + Pylint ≥ 8.5 |
| Typage | `make typecheck` | Zéro erreur Mypy strict |
| Tests | `make test` | Couverture ≥ 80% |

---

## PHASE 9 — Backtest

```bash
# Lancer le backtest (paper mode uniquement)
python -m trading_d1_bougie.engine.backtest_runner

# Les résultats seront générés dans le dossier racine :
# → TRADING_D1_BOUGIE_backtest_results.csv
# → TRADING_D1_BOUGIE_equity_curve.png
```

> Valider les métriques minimales avant de passer au paper trading live :
- Winrate ≥ 45%
- Profit Factor ≥ 1.5
- Max Drawdown ≤ 15%
- Sharpe Ratio ≥ 1.0
- Échantillon ≥ 100 trades

---

## PHASE 10 — Paper Trading Live

```bash
# ⚠️ PAPER TRADING UNIQUEMENT — port 4002
# Vérifier que PAPER_TRADING=true dans .env

python -m trading_d1_bougie.engine.main
```

> Le dashboard Rich se lance automatiquement dans le terminal.

---

## ⚠️ AVERTISSEMENT LIVE TRADING

```
╔══════════════════════════════════════════════════════════════╗
║   ⚠️  ATTENTION — MODE LIVE TRADING                         ║
║                                                              ║
║   Le mode live (port 4001) engage du capital RÉEL.          ║
║   Ne l'activer QUE après :                                   ║
║   ✅ make qa → 100% vert                                     ║
║   ✅ Backtest validé sur 100+ trades                         ║
║   ✅ Paper trading validé sur 2+ semaines                    ║
║   ✅ Paramètre PAPER_TRADING=false dans .env confirmé        ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Récapitulatif du Stack 📦

| Couche | Outil | Rôle |
|---|---|---|
| Formatage | Black 23.x | Style uniforme |
| Linting | Ruff | Erreurs + isort |
| Analyse statique | Pylint | Qualité profonde |
| Typage | Mypy strict | Zéro erreur de type |
| Tests | Pytest + cov + asyncio | Couverture ≥ 80% |
| Build | Makefile | `make qa` = tout en 1 |
| Config centrale | pyproject.toml | Black + Ruff + Pytest |
| Broker | ib_insync | IB Gateway Paper/Live |
| Dashboard | Rich | Terminal temps réel |
| Backtest | vectorbt | Validation historique |
| Logging | loguru | Rotation journalière |
| Timezone | zoneinfo | DST auto US + EU |

---

*TRADING-D1-BOUGIE — D1 Range / M15 Structure Bot | Plan d'Action v1.0*