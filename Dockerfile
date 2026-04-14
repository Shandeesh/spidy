# ── Spidy AI Trading Platform — Production Dockerfile ────────────────────────
# Targets: MT5 Bridge (port 8000) + Brain Server (port 5001)
# Base: Python 3.11 slim (minimal attack surface)
#
# Build:   docker build -t spidy:latest .
# Run:     docker-compose up (see docker-compose.yml)

FROM python:3.11-slim AS base

# System deps: keep minimal; TA-Lib build needs gcc + wget
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ wget curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Dependency layer (cached unless requirements change) ──────────────────────
COPY Trading_Backend/mt5_bridge/requirements.txt  ./req_bridge.txt
COPY AI_Engine/requirements.txt                   ./req_ai.txt
COPY Security_Module/requirements.txt             ./req_sec.txt

RUN pip install --no-cache-dir \
        -r req_bridge.txt \
        -r req_ai.txt \
        -r req_sec.txt \
        scikit-learn joblib pandas python-telegram-bot \
    && pip install --no-cache-dir python-dotenv fastapi uvicorn

# ── Source copy ───────────────────────────────────────────────────────────────
COPY Trading_Backend/       ./Trading_Backend/
COPY AI_Engine/             ./AI_Engine/
COPY Security_Module/       ./Security_Module/
COPY Extension_Module/      ./Extension_Module/
COPY Shared_Data/           ./Shared_Data/

# NOTE: MetaTrader5 module only works on Windows — bridge will run in
# paper-mode / API-only mode on Linux containers (HAS_MT5 = False).
# For live MT5, run bridge_server.py natively on Windows and use Docker
# only for brain_server + influxdb.

EXPOSE 8000 5001

# Default: start brain server (AI endpoint)
CMD ["python", "-m", "uvicorn", "AI_Engine.brain.brain_server:app", \
     "--host", "0.0.0.0", "--port", "5001", "--workers", "1"]
