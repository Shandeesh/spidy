"""
agents/data_engineer.py
========================
Agent 1 — Data Engineer

What it does
------------
  Fetches live OHLCV candles from MetaTrader 5 across three timeframes
  (M5, H1, H4) in parallel, computes technical features via the existing
  FeatureStore pipeline, detects the current market regime, and publishes
  a MarketSnapshot every `poll_interval_seconds` (default: 5).

Publishes
---------
  Topic.MARKET_SNAPSHOT → {
    "symbol":     str,
    "regime":     "TRENDING" | "RANGING" | "VOLATILE",
    "timeframes": {
        "M5": { "close": float, "ATR": float, "RSI": float, … },
        "H1": { … },
        "H4": { … },
    },
    "timestamp":  str  (ISO-8601 UTC),
  }

Why three timeframes?
---------------------
  * H4 — macro trend direction (which way is the big money flowing?)
  * H1 — structural confirmation (is the trend still intact?)
  * M5 — entry timing (is now a good micro-entry point?)
  The Researcher and RiskManager agents use this multi-TF context when
  building and approving trade signals.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .base_agent import BaseAgent
from .message_bus import MessageBus, Topic


# Map human-readable labels to MT5 timeframe constants (minutes)
_TF_MINUTES: dict[str, int] = {"M5": 5, "H1": 60, "H4": 240}


class DataEngineerAgent(BaseAgent):

    def __init__(self, bus: MessageBus, config: dict[str, Any]) -> None:
        super().__init__("DataEngineer", bus, config)
        self._feeds:           dict[str, dict[str, Any]] = {}   # {symbol: {tf: MetaTraderFeed}}
        self._feature_store:   Any = None
        self._regime_detector: Any = None
        self._strategy_registry: Any = None
        self._candle_lookback: int = 500
        # Feature-adder callables (set in setup after lazy import)
        self._add_trend:     Any = None
        self._add_momentum:  Any = None
        self._add_volatility: Any = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def setup(self) -> None:
        # Lazy imports — keeps startup fast if MT5 is not installed
        from spidy_ai.data_feed.metatrader_feed import MetaTraderFeed
        from spidy_ai.feature_engineering.feature_store import FeatureStore
        from spidy_ai.feature_engineering.trend_features import TrendFeatures
        from spidy_ai.feature_engineering.momentum_features import MomentumFeatures
        from spidy_ai.feature_engineering.volatility_features import VolatilityFeatures
        from spidy_ai.regime_detection.regime_detector import RegimeDetector
        from spidy_ai.strategies.registry import StrategyRegistry

        self._add_trend      = TrendFeatures.add_features
        self._add_momentum   = MomentumFeatures.add_features
        self._add_volatility = VolatilityFeatures.add_features
        self._feature_store  = FeatureStore()
        self._regime_detector = RegimeDetector()
        self._strategy_registry = StrategyRegistry()

        symbols = self.config.get("symbols", ["EURUSD"])
        self._candle_lookback = self.config.get("system", {}).get("candle_lookback", 500)

        # Load MT5 connection details from config
        mt5_cfg = self.config.get("mt5", {})
        login = int(mt5_cfg.get("login", 0))
        password = mt5_cfg.get("password", "")
        server = mt5_cfg.get("server", "")
        path = mt5_cfg.get("path", "")

        # Connect feeds for all configured symbols
        for symbol in symbols:
            self._feeds[symbol] = {}
            for tf, minutes in _TF_MINUTES.items():
                feed = MetaTraderFeed(
                    symbol=symbol,
                    timeframe=minutes,
                    login=login if login > 0 else None,
                    password=password if password else None,
                    server=server if server else None,
                    path=path if path else None
                )
                if not feed.connect():
                    raise RuntimeError(
                        f"[DataEngineer] MT5 connection failed for {symbol} {tf}"
                    )
                self._feeds[symbol][tf] = feed

        self.logger.info(
            "[DataEngineer] Connected — symbols=%s timeframes=%s",
            symbols, list(_TF_MINUTES),
        )

    async def teardown(self) -> None:
        for symbol_feeds in self._feeds.values():
            for feed in symbol_feeds.values():
                try:
                    feed.shutdown()
                except Exception:
                    pass
        self.logger.info("[DataEngineer] MT5 feeds closed.")

    # ── Step ──────────────────────────────────────────────────────────────────

    async def step(self) -> None:
        poll_s = self.config.get("system", {}).get("poll_interval_seconds", 5)
        symbols = self.config.get("symbols", ["EURUSD"])

        for symbol in symbols:
            # ── 1. Fetch and enrich all timeframes in parallel for this symbol ────
            tasks = {
                tf: asyncio.create_task(self._fetch_and_enrich(symbol, tf))
                for tf in _TF_MINUTES
            }
            results: dict[str, Any] = {}
            skip_symbol = False
            for tf, task in tasks.items():
                try:
                    results[tf] = await task
                except Exception as exc:
                    self.logger.error("[DataEngineer] Error on %s %s: %s", symbol, tf, exc)
                    skip_symbol = True

            if skip_symbol:
                continue

            # ── 2. Regime detection on the M5 frame ──────────────────────────
            m5_df  = results["M5"]["df"]
            regime = await asyncio.to_thread(
                self._regime_detector.detect_regime, m5_df
            )

            # ── 3. Technical Strategy Signals Integration ────────────────────
            strategy_signals = {}
            try:
                active_strategies = self._strategy_registry.get_active_strategies(regime)
                for strategy in active_strategies:
                    res = strategy.generate_signal(m5_df)
                    strategy_signals[strategy.name] = {
                        "signal": res.get("signal", "NEUTRAL"),
                        "confidence": res.get("confidence", 0.0),
                        "metadata": res.get("metadata", {})
                    }
            except Exception as e:
                self.logger.error("[DataEngineer] Error running technical strategies for %s: %s", symbol, e)

            # ── 4. Build snapshot payload ─────────────────────────────────────────
            snapshot: dict[str, Any] = {
                "symbol":     symbol,
                "regime":     regime,
                "timeframes": {tf: r["features"] for tf, r in results.items()},
                "strategy_signals": strategy_signals,
                "timestamp":  datetime.now(tz=timezone.utc).isoformat(),
            }

            await self.publish(Topic.MARKET_SNAPSHOT, snapshot)
            self.logger.debug(
                "[DataEngineer] Snapshot published — %s regime=%s price=%.5f",
                symbol, regime, snapshot["timeframes"]["M5"].get("close", 0),
            )

        await asyncio.sleep(poll_s)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _fetch_and_enrich(self, symbol: str, tf: str) -> dict[str, Any]:
        """Fetch candles for one timeframe and compute all features."""
        feed = self._feeds[symbol][tf]
        df: pd.DataFrame = await asyncio.to_thread(
            feed.get_candles, n=self._candle_lookback
        )
        if df is None or df.empty:
            raise ValueError(f"Empty candles for {symbol} {tf}")

        # Feature engineering is CPU-bound — run in thread pool
        df = await asyncio.to_thread(self._enrich, df)

        # Extract the single most-recent row as a flat feature dict
        self._feature_store.load_data(df)
        latest = self._feature_store.get_latest()
        features = {
            k: round(float(v), 6)
            for k, v in latest.items()
            if isinstance(v, (int, float))
        }
        return {"df": df, "features": features}

    def _enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all feature layers synchronously (called via to_thread)."""
        df = self._add_trend(df)
        df = self._add_momentum(df)
        df = self._add_volatility(df)
        return df

