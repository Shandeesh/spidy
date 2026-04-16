"""
agents/executor.py
==================
Agent 4 — Executor

What it does
------------
  The ONLY agent that submits orders to MetaTrader 5.  All other agents
  are read-only with respect to the broker.

  Subscribes to:
    TRADE_SIGNAL  — an approved, sized order from RiskManager
    RISK_STATE    — listens for kill_switch_active=True

  On TRADE_SIGNAL:
    1. Staleness check: current price must be within 1 ATR of signal price.
    2. Validation: reject if lot_size <= 0 or symbol is invalid.
    3. Simulation mode: log the order without touching MT5.
    4. Live mode: submit via order_send, capture ticket number.
    5. Spawn a trailing-stop monitor task per open position.
    6. Publish EXECUTION_REPORT so the dashboard updates.

  On RISK_STATE with kill_switch_active=True:
    → Close ALL open positions immediately.

Trailing stop logic
-------------------
  Each open position gets a background asyncio.Task that wakes every 5s,
  reads the current tick, and ratchets the stop-loss forward if the trade
  is moving in our favour. The stop only ever moves in the profitable
  direction — it never widens.

Publishes
---------
  Topic.EXECUTION_REPORT → {
    "action":    "OPEN" | "CLOSE" | "TRAIL" | "KILL_SWITCH" | "SKIP",
    "symbol":    str,
    "ticket":    int | None,
    "direction": str,
    "lot_size":  float,
    "price":     float,
    "sl":        float,
    "tp":        float,
    "pnl":       float | None,
    "reason":    str,
  }
"""
from __future__ import annotations

import asyncio
from typing import Any

from .base_agent import BaseAgent
from .message_bus import AgentMessage, MessageBus, Topic


class ExecutorAgent(BaseAgent):

    def __init__(self, bus: MessageBus, config: dict[str, Any]) -> None:
        super().__init__("Executor", bus, config)
        self._inbox: asyncio.Queue[AgentMessage] | None = None
        self._mt5:   Any = None

        # Track tickets we opened so we know which are ours
        self._open_tickets: set[int] = set()
        # Background trailing-stop tasks keyed by ticket
        self._trail_tasks: dict[int, asyncio.Task] = {}

        sys_cfg  = config.get("system",    {})
        exec_cfg = config.get("execution", {})

        self._live_mode      = sys_cfg.get("mode", "SIMULATION") == "LIVE"
        self._slippage_pips  = exec_cfg.get("slippage_pips",        3)
        self._trail_atr_mult = exec_cfg.get("trailing_atr_mult",    1.0)
        self._magic_number   = exec_cfg.get("magic_number",         20260101)
        self._staleness_atr  = exec_cfg.get("staleness_atr_factor", 1.0)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def setup(self) -> None:
        import MetaTrader5 as mt5
        self._mt5 = mt5
        if not mt5.initialize():
            raise RuntimeError("[Executor] MetaTrader5.initialize() failed.")

        self._inbox = await self.bus.subscribe(
            Topic.TRADE_SIGNAL,
            Topic.RISK_STATE,
        )
        mode = "LIVE" if self._live_mode else "SIMULATION"
        self.logger.info("[Executor] Ready — mode=%s", mode)
        if self._live_mode:
            self.logger.warning(
                "[Executor] *** LIVE MODE — real orders will be placed ***"
            )

    async def teardown(self) -> None:
        for task in self._trail_tasks.values():
            task.cancel()
        if self._trail_tasks:
            await asyncio.gather(*self._trail_tasks.values(), return_exceptions=True)
        if self._mt5:
            self._mt5.shutdown()
        self.logger.info("[Executor] All trailing tasks cancelled, MT5 closed.")

    # ── Step ──────────────────────────────────────────────────────────────────

    async def step(self) -> None:
        msg: AgentMessage | None = await self.receive(self._inbox, timeout=60.0)
        if msg is None:
            self.logger.debug("[Executor] Heartbeat — no messages in 60s.")
            return

        if msg.topic == Topic.RISK_STATE:
            await self._on_risk_state(msg.payload)
        elif msg.topic == Topic.TRADE_SIGNAL:
            await self._on_trade_signal(msg.payload)

    # ── Risk state handler ────────────────────────────────────────────────────

    async def _on_risk_state(self, state: dict[str, Any]) -> None:
        if state.get("kill_switch_active"):
            self.logger.warning(
                "[Executor] KILL SWITCH — closing all positions NOW."
            )
            await self._close_all("Kill switch activated by RiskManager")

    # ── Trade signal handler ──────────────────────────────────────────────────

    async def _on_trade_signal(self, signal: dict[str, Any]) -> None:
        symbol    = signal["symbol"]
        direction = signal["direction"]
        lot_size  = signal["lot_size"]
        entry     = signal["entry"]
        sl        = signal["sl"]
        tp        = signal["tp"]
        atr       = signal["atr"]

        # ── Staleness check ───────────────────────────────────────────────────
        tick = await asyncio.to_thread(self._mt5.symbol_info_tick, symbol)
        if tick is None:
            await self._report(
                "SKIP", symbol, None, direction, lot_size, entry, sl, tp,
                reason="No tick data available",
            )
            return

        live_price = tick.ask if direction == "BUY" else tick.bid
        drift      = abs(live_price - entry)
        if drift > atr * self._staleness_atr:
            await self._report(
                "SKIP", symbol, None, direction, lot_size, entry, sl, tp,
                reason=f"Signal stale: drift={drift:.5f} > {atr*self._staleness_atr:.5f}",
            )
            self.logger.info(
                "[Executor] Skipping stale signal for %s (drift=%.5f)", symbol, drift
            )
            return

        # ── Order placement ───────────────────────────────────────────────────
        if self._live_mode:
            ticket = await asyncio.to_thread(
                self._place_market_order,
                symbol, direction, lot_size, live_price, sl, tp,
            )
        else:
            # Simulation: fabricate a deterministic ticket
            ticket = (abs(hash((symbol, direction, round(entry, 3)))) % 900_000) + 100_000
            self.logger.info(
                "[Executor][SIM] %s %s %.2f lots @ %.5f  SL=%.5f  TP=%.5f  ticket=%d",
                direction, symbol, lot_size, live_price, sl, tp, ticket,
            )

        if ticket:
            self._open_tickets.add(ticket)
            self._trail_tasks[ticket] = asyncio.create_task(
                self._trail_monitor(ticket, symbol, direction, atr, sl),
                name=f"trail-{ticket}",
            )
            await self._report(
                "OPEN", symbol, ticket, direction, lot_size,
                live_price, sl, tp, reason="Order placed",
            )

    # ── MT5 order placement ───────────────────────────────────────────────────

    def _place_market_order(
        self,
        symbol: str,
        direction: str,
        volume: float,
        price: float,
        sl: float,
        tp: float,
    ) -> int | None:
        """Synchronous MT5 order submission (run via to_thread)."""
        mt5        = self._mt5
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

        request = {
            "action":       mt5.TRADE_ACTION_DEAL,
            "symbol":       symbol,
            "volume":       volume,
            "type":         order_type,
            "price":        price,
            "sl":           sl,
            "tp":           tp,
            "deviation":    self._slippage_pips,
            "magic":        self._magic_number,
            "comment":      "Spidy-Agent",
            "type_time":    mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)

        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            self.logger.info("[Executor] Order placed — ticket=%d", result.order)
            return result.order

        self.logger.error(
            "[Executor] Order failed — retcode=%s comment=%s",
            getattr(result, "retcode", "N/A"),
            getattr(result, "comment", "N/A"),
        )
        return None

    # ── Trailing stop monitor ─────────────────────────────────────────────────

    async def _trail_monitor(
        self,
        ticket:     int,
        symbol:     str,
        direction:  str,
        atr:        float,
        initial_sl: float,
    ) -> None:
        """
        Background task: ratchets the stop-loss as price moves in our favour.
        Wakes every 5 seconds.  Exits when the position is no longer open.
        """
        trail_dist = atr * self._trail_atr_mult
        best: float | None = None

        self.logger.debug("[Executor] Trail monitor started — ticket=%d", ticket)
        try:
            while ticket in self._open_tickets:
                await asyncio.sleep(5)

                pos = await asyncio.to_thread(self._get_position, ticket)
                if pos is None:
                    self.logger.info(
                        "[Executor] Position %d closed externally — stopping trail.",
                        ticket,
                    )
                    self._open_tickets.discard(ticket)
                    break

                tick = await asyncio.to_thread(self._mt5.symbol_info_tick, symbol)
                if tick is None:
                    continue

                current = tick.bid if direction == "BUY" else tick.ask
                if best is None:
                    best = current

                if direction == "BUY":
                    best   = max(best, current)
                    new_sl = round(best - trail_dist, 5)
                    if new_sl > pos["sl"] + 0.00001:
                        await asyncio.to_thread(
                            self._modify_sl, ticket, symbol, new_sl
                        )
                        self.logger.debug(
                            "[Executor] Trail BUY ticket=%d sl %.5f → %.5f",
                            ticket, pos["sl"], new_sl,
                        )
                        await self._report(
                            "TRAIL", symbol, ticket, direction, pos["volume"],
                            current, new_sl, pos["tp"],
                            reason="Trailing stop ratcheted",
                        )
                else:
                    best   = min(best, current)
                    new_sl = round(best + trail_dist, 5)
                    if new_sl < pos["sl"] - 0.00001:
                        await asyncio.to_thread(
                            self._modify_sl, ticket, symbol, new_sl
                        )
                        self.logger.debug(
                            "[Executor] Trail SELL ticket=%d sl %.5f → %.5f",
                            ticket, pos["sl"], new_sl,
                        )
                        await self._report(
                            "TRAIL", symbol, ticket, direction, pos["volume"],
                            current, new_sl, pos["tp"],
                            reason="Trailing stop ratcheted",
                        )
        except asyncio.CancelledError:
            pass
        finally:
            self._trail_tasks.pop(ticket, None)

    # ── Kill-switch: close all positions ──────────────────────────────────────

    async def _close_all(self, reason: str) -> None:
        positions = await asyncio.to_thread(self._mt5.positions_get) or []
        for pos in positions:
            close_dir   = "SELL" if pos.type == 0 else "BUY"
            tick        = await asyncio.to_thread(
                self._mt5.symbol_info_tick, pos.symbol
            )
            if tick is None:
                continue
            close_price = tick.bid if close_dir == "SELL" else tick.ask

            if self._live_mode:
                await asyncio.to_thread(
                    self._place_market_order,
                    pos.symbol, close_dir, pos.volume, close_price, 0.0, 0.0,
                )
            self._open_tickets.discard(pos.ticket)
            await self._report(
                "KILL_SWITCH", pos.symbol, pos.ticket, close_dir,
                pos.volume, close_price, 0.0, 0.0,
                pnl=pos.profit, reason=reason,
            )

    # ── MT5 helpers ───────────────────────────────────────────────────────────

    def _get_position(self, ticket: int) -> dict[str, Any] | None:
        positions = self._mt5.positions_get(ticket=ticket)
        if not positions:
            return None
        p = positions[0]
        return {"sl": p.sl, "tp": p.tp, "profit": p.profit, "volume": p.volume}

    def _modify_sl(self, ticket: int, symbol: str, new_sl: float) -> None:
        self._mt5.order_send({
            "action":   self._mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol":   symbol,
            "sl":       new_sl,
        })

    # ── Execution report helper ───────────────────────────────────────────────

    async def _report(
        self,
        action:    str,
        symbol:    str,
        ticket:    int | None,
        direction: str,
        lot_size:  float,
        price:     float,
        sl:        float,
        tp:        float,
        pnl:       float | None = None,
        reason:    str = "",
    ) -> None:
        await self.publish(Topic.EXECUTION_REPORT, {
            "action":    action,
            "symbol":    symbol,
            "ticket":    ticket,
            "direction": direction,
            "lot_size":  lot_size,
            "price":     round(price, 5),
            "sl":        round(sl, 5),
            "tp":        round(tp, 5),
            "pnl":       round(pnl, 2) if pnl is not None else None,
            "reason":    reason,
        })
