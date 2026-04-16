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
        self._feeds:           dict[str, Any] = {}   # {tf: MetaTraderFeed}
        self._feature_store:   Any = None
        self._regime_detector: Any = None
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

        self._add_trend      = TrendFeatures.add_features
        self._add_momentum   = MomentumFeatures.add_features
        self._add_volatility = VolatilityFeatures.add_features
        self._feature_store  = FeatureStore()
        self._regime_detector = RegimeDetector()

        symbol = self.config.get("system", {}).get("symbol", "EURUSD")
        self._candle_lookback = self.config.get("system", {}).get("candle_lookback", 500)

        # One feed per timeframe — all share the same symbol
        for tf, minutes in _TF_MINUTES.items():
            feed = MetaTraderFeed(symbol, timeframe=minutes)
            if not feed.connect():
                raise RuntimeError(
                    f"[DataEngineer] MT5 connection failed for {symbol} {tf}"
                )
            self._feeds[tf] = feed

        self.logger.info(
            "[DataEngineer] Connected — symbol=%s timeframes=%s",
            symbol, list(_TF_MINUTES),
        )

    async def teardown(self) -> None:
        for feed in self._feeds.values():
            try:
                feed.shutdown()
            except Exception:
                pass
        self.logger.info("[DataEngineer] MT5 feeds closed.")

    # ── Step ──────────────────────────────────────────────────────────────────

    async def step(self) -> None:
        poll_s = self.config.get("system", {}).get("poll_interval_seconds", 5)
        symbol = self.config.get("system", {}).get("symbol", "EURUSD")

        # ── 1. Fetch and enrich all timeframes in parallel ────────────────────
        tasks = {
            tf: asyncio.create_task(self._fetch_and_enrich(tf))
            for tf in _TF_MINUTES
        }
        results: dict[str, Any] = {}
        for tf, task in tasks.items():
            try:
                results[tf] = await task
            except Exception as exc:
                self.logger.error("[DataEngineer] Error on %s: %s", tf, exc)
                await asyncio.sleep(poll_s)
                return  # skip this cycle if any TF fails

        # ── 2. Regime detection on the M5 frame (highest frequency) ──────────
        m5_df  = results["M5"]["df"]
        regime = await asyncio.to_thread(
            self._regime_detector.detect_regime, m5_df
        )

        # ── 3. Build snapshot payload ─────────────────────────────────────────
        snapshot: dict[str, Any] = {
            "symbol":     symbol,
            "regime":     regime,
            "timeframes": {tf: r["features"] for tf, r in results.items()},
            "timestamp":  datetime.now(tz=timezone.utc).isoformat(),
        }

        await self.publish(Topic.MARKET_SNAPSHOT, snapshot)
        self.logger.debug(
            "[DataEngineer] Snapshot published — regime=%s price=%.5f",
            regime, snapshot["timeframes"]["M5"].get("close", 0),
        )

        await asyncio.sleep(poll_s)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _fetch_and_enrich(self, tf: str) -> dict[str, Any]:
        """Fetch candles for one timeframe and compute all features."""
        feed = self._feeds[tf]
        df: pd.DataFrame = await asyncio.to_thread(
            feed.get_candles, n=self._candle_lookback
        )
        if df is None or df.empty:
            raise ValueError(f"Empty candles for {tf}")

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
