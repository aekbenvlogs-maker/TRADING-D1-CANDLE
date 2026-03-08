# ============================================================
# TRADING-D1-BOUGIE — Docker image (Python 3.11 + Cython)
# ============================================================
FROM python:3.11-slim

WORKDIR /app

# Dépendances système pour la compilation Cython
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source
COPY . .

# Compilation Cython
RUN make build

# Variables d’environnement (surcharger via .env ou docker-compose)
ENV IB_HOST=host.docker.internal \
    IB_PORT=4002 \
    IB_CLIENT_ID=1 \
    TELEGRAM_BOT_TOKEN="" \
    TELEGRAM_CHAT_ID=""

# Créer le dossier de logs
RUN mkdir -p trading_d1_bougie/logs trading_d1_bougie/data

# Héalthcheck : vérifie que le process Python est actif
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "import trading_d1_bougie" || exit 1

CMD ["python", "-m", "trading_d1_bougie.engine.main"]
