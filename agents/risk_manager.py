"""
agents/risk_manager.py
======================
Agent 3 — Risk Manager

What it does
------------
  The sole authority on whether a trade may be placed.  Subscribes to both
  MARKET_SNAPSHOT (for price/ATR context) and SENTIMENT (for hold_off flag).

  On every new message it:
    1. Queries MetaTrader 5 for live account stats (balance, equity, leverage,
       open position count).
    2. Runs all risk guardrails in order (daily DD → total DD → max positions
       → sentiment hold_off → regime veto).
    3. Publishes a RISK_STATE so the dashboard always has current status.
    4. If trading is allowed, builds a candidate trade signal (direction from
       sentiment + sizing from ATR) and publishes on TRADE_SIGNAL.
       → The Executor only places orders it receives here; this is the single
         chokepoint that stops over-trading.

Guardrails (all configurable via settings.yaml)
-----------------------------------------------
  max_daily_drawdown_pct    Default 3%    — pauses trading
  max_total_drawdown_pct    Default 10%   — hard stop, kill switch
  max_open_positions        Default 3     — prevents pyramid risk
  risk_per_trade_pct        Default 1%    — Kelly-lite position sizing
  sentiment_hold_off        from Researcher — macro risk veto
  regime_veto               "VOLATILE"    — no trading in erratic conditions

Publishes
---------
  Topic.RISK_STATE  → { can_trade, kill_switch_active, drawdowns, balance… }
  Topic.TRADE_SIGNAL (only when can_trade is True) → { symbol, direction,
                      lot_size, entry, sl, tp, atr, regime, sentiment… }
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from typing import Any

from .base_agent import BaseAgent
from .message_bus import AgentMessage, MessageBus, Topic


@dataclass
class RiskState:
    can_trade:          bool
    kill_switch_active: bool
    daily_drawdown_pct: float
    total_drawdown_pct: float
    open_positions:     int
    balance:            float
    equity:             float
    leverage:           int
    reason:             str


class RiskManagerAgent(BaseAgent):

    def __init__(self, bus: MessageBus, config: dict[str, Any]) -> None:
        super().__init__("RiskManager", bus, config)
        self._inbox:  asyncio.Queue[AgentMessage] | None = None
        self._mt5:    Any = None

        # Cache latest data from each upstream agent
        self._latest_snapshot:  dict[str, Any] = {}
        self._latest_sentiment: dict[str, Any] = {}

        # ── Risk parameters from config ───────────────────────────────────────
        cfg = config.get("risk", {})
        self._start_balance  = cfg.get("start_balance",               10_000.0)
        self._max_daily_dd   = cfg.get("max_daily_drawdown_pct",         0.03)
        self._max_total_dd   = cfg.get("max_total_drawdown_pct",         0.10)
        self._max_open       = cfg.get("max_open_positions",                3)
        self._risk_per_trade = cfg.get("risk_per_trade_pct",             0.01)
        self._max_lot        = cfg.get("max_lot_size",                    1.0)
        self._min_confidence = cfg.get("min_signal_confidence",          0.55)
        self._regime_veto    = set(cfg.get("regime_veto", ["VOLATILE"]))

        exec_cfg = config.get("execution", {})
        self._atr_sl_mult    = exec_cfg.get("atr_sl_multiplier",         1.5)
        self._rr_ratio       = exec_cfg.get("rr_ratio",                  2.0)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def setup(self) -> None:
        import MetaTrader5 as mt5
        self._mt5 = mt5
        if not mt5.initialize():
            raise RuntimeError("[RiskManager] MetaTrader5.initialize() failed.")

        self._inbox = await self.bus.subscribe(
            Topic.MARKET_SNAPSHOT,
            Topic.SENTIMENT,
        )
        self.logger.info(
            "[RiskManager] Ready — daily_dd=%.0f%% total_dd=%.0f%% max_pos=%d",
            self._max_daily_dd * 100,
            self._max_total_dd * 100,
            self._max_open,
        )

    async def teardown(self) -> None:
        if self._mt5:
            self._mt5.shutdown()

    # ── Step ──────────────────────────────────────────────────────────────────

    async def step(self) -> None:
        msg: AgentMessage | None = await self.receive(self._inbox, timeout=30.0)
        if msg is None:
            self.logger.warning(
                "[RiskManager] No messages in 30s — is DataEngineer alive?"
            )
            return

        if msg.topic == Topic.MARKET_SNAPSHOT:
            self._latest_snapshot = msg.payload
        elif msg.topic == Topic.SENTIMENT:
            self._latest_sentiment = msg.payload

        # Need BOTH before we can make a decision
        if not self._latest_snapshot or not self._latest_sentiment:
            return

        account = await asyncio.to_thread(self._query_account)
        if account is None:
            self.logger.warning("[RiskManager] MT5 account query failed.")
            return

        state = self._evaluate_risk(account)
        await self.publish(Topic.RISK_STATE, asdict(state))

        if state.can_trade:
            signal = self._build_signal(state, account)
            if signal:
                await self.publish(Topic.TRADE_SIGNAL, signal)
                self.logger.info(
                    "[RiskManager] Signal approved — %s %s %.2f lots entry=%.5f",
                    signal["direction"], signal["symbol"],
                    signal["lot_size"],  signal["entry"],
                )
        else:
            self.logger.debug("[RiskManager] Trading paused — %s", state.reason)

    # ── Risk evaluation ───────────────────────────────────────────────────────

    def _query_account(self) -> dict[str, Any] | None:
        """Synchronous MT5 account query (called via to_thread)."""
        info = self._mt5.account_info()
        if info is None:
            return None
        positions = self._mt5.positions_get() or []
        return {
            "balance":    info.balance,
            "equity":     info.equity,
            "leverage":   info.leverage,
            "open_count": len(positions),
        }

    def _evaluate_risk(self, account: dict[str, Any]) -> RiskState:
        balance  = account["balance"]
        equity   = account["equity"]
        leverage = int(account.get("leverage", 100))
        open_cnt = account["open_count"]

        daily_dd = max(0.0, (self._start_balance - equity)  / self._start_balance)
        total_dd = max(0.0, (self._start_balance - balance) / self._start_balance)

        base = dict(
            kill_switch_active=False,
            daily_drawdown_pct=round(daily_dd, 4),
            total_drawdown_pct=round(total_dd, 4),
            open_positions=open_cnt,
            balance=balance,
            equity=equity,
            leverage=leverage,
        )

        # ── Guardrail 1: total drawdown kill switch ───────────────────────────
        if total_dd >= self._max_total_dd:
            return RiskState(
                can_trade=False,
                kill_switch_active=True,
                reason=f"Total DD {total_dd*100:.1f}% ≥ limit {self._max_total_dd*100:.0f}%",
                **base,
            )

        # ── Guardrail 2: daily drawdown pause ────────────────────────────────
        if daily_dd >= self._max_daily_dd:
            return RiskState(
                can_trade=False,
                reason=f"Daily DD {daily_dd*100:.1f}% ≥ limit {self._max_daily_dd*100:.0f}%",
                **base,
            )

        # ── Guardrail 3: max open positions ───────────────────────────────────
        if open_cnt >= self._max_open:
            return RiskState(
                can_trade=False,
                reason=f"Max open positions ({self._max_open}) reached",
                **base,
            )

        # ── Guardrail 4: researcher hold_off ─────────────────────────────────
        if self._latest_sentiment.get("hold_off", True):
            events = self._latest_sentiment.get("risk_events", [])
            return RiskState(
                can_trade=False,
                reason=f"Researcher hold_off: {events or 'risk event flagged'}",
                **base,
            )

        # ── Guardrail 5: regime veto ──────────────────────────────────────────
        regime = self._latest_snapshot.get("regime", "UNKNOWN")
        if regime in self._regime_veto:
            return RiskState(
                can_trade=False,
                reason=f"Regime '{regime}' is in veto list {self._regime_veto}",
                **base,
            )

        # ── Guardrail 6: minimum signal confidence ────────────────────────────
        confidence = float(self._latest_sentiment.get("confidence", 0.0))
        if confidence < self._min_confidence:
            return RiskState(
                can_trade=False,
                reason=f"Confidence {confidence:.2f} < minimum {self._min_confidence:.2f}",
                **base,
            )

        # ── Guardrail 7: sentiment must be directional ────────────────────────
        sentiment = self._latest_sentiment.get("sentiment", "NEUTRAL")
        if sentiment == "NEUTRAL":
            return RiskState(
                can_trade=False,
                reason="Sentiment is NEUTRAL",
                **base,
            )

        return RiskState(can_trade=True, reason="All guardrails passed", **base)

    # ── Signal construction ───────────────────────────────────────────────────

    def _build_signal(
        self, state: RiskState, account: dict[str, Any]
    ) -> dict[str, Any] | None:
        snap = self._latest_snapshot
        sent = self._latest_sentiment

        symbol    = snap.get("symbol", "EURUSD")
        regime    = snap.get("regime", "UNKNOWN")
        sentiment = sent.get("sentiment", "NEUTRAL")

        m5    = snap.get("timeframes", {}).get("M5", {})
        close = float(m5.get("close", 0.0))
        atr   = float(m5.get("ATR",   0.0010))

        if close == 0 or atr == 0:
            self.logger.warning(
                "[RiskManager] close=0 or ATR=0 — cannot build signal."
            )
            return None

        direction = "BUY" if sentiment == "BULLISH" else "SELL"
        sl_dist   = atr * self._atr_sl_mult
        tp_dist   = sl_dist * self._rr_ratio

        if direction == "BUY":
            sl_price = close - sl_dist
            tp_price = close + tp_dist
        else:
            sl_price = close + sl_dist
            tp_price = close - tp_dist

        # Position sizing: 1% of balance per trade
        # pip_value = $10 per pip per standard lot for EURUSD
        risk_amount = account["balance"] * self._risk_per_trade
        pip_value   = 10.0
        sl_pips     = sl_dist / 0.0001
        lot_raw     = risk_amount / max(sl_pips * pip_value, 0.01)
        lot_size    = round(max(0.01, min(lot_raw, self._max_lot)), 2)

        return {
            "symbol":     symbol,
            "direction":  direction,
            "lot_size":   lot_size,
            "entry":      round(close, 5),
            "sl":         round(sl_price, 5),
            "tp":         round(tp_price, 5),
            "atr":        round(atr, 6),
            "regime":     regime,
            "sentiment":  sentiment,
            "confidence": round(float(sent.get("confidence", 0.0)), 3),
            "leverage":   state.leverage,
        }
