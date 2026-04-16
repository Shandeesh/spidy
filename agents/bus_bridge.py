"""
agents/bus_bridge.py
====================
Agent 5 — Bus Bridge  (read-only, no orders placed)

What it does
------------
  Subscribes to ALL five message bus topics and forwards every message
  to the existing Node.js Socket.IO relay server (port 5000) via a
  lightweight HTTP POST to /agent-event.

  The relay server then socket.io.emit()s the payload to every connected
  frontend client, so the React dashboard gets real-time updates for:
    • market_snapshot  → live price, regime, technical features
    • sentiment        → Gemini analysis result
    • risk_state       → drawdown bars, can_trade indicator
    • trade_signal     → pending order preview
    • execution_report → fills, trailing stop moves, kill-switch events

Design
------
  * Uses aiohttp for non-blocking HTTP POST (no extra thread needed)
  * If the relay server is down, messages are silently dropped after a
    short timeout — the trading system never stalls because of a UI outage
  * Serialises datetime objects to ISO strings so JSON encoding always works
  * Topic payloads are wrapped in a standard envelope:
      { "topic": "<name>", "sender": "<agent>", "age_ms": <float>, "data": {…} }

Port
----
  Relay server default: http://127.0.0.1:5000/agent-event
  Override via config:  bridge.relay_url
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Any

from .base_agent import BaseAgent
from .message_bus import AgentMessage, MessageBus, Topic

log = logging.getLogger("spidy.BusBridge")


def _serialise(obj: Any) -> Any:
    """JSON-safe coercion for non-serialisable types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, set):
        return list(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serialisable")


class BusBridgeAgent(BaseAgent):
    """
    Mirrors every MessageBus event to the Socket.IO relay server
    so the frontend receives live agent data without polling.
    """

    _ALL_TOPICS = (
        Topic.MARKET_SNAPSHOT,
        Topic.SENTIMENT,
        Topic.RISK_STATE,
        Topic.TRADE_SIGNAL,
        Topic.EXECUTION_REPORT,
    )

    def __init__(self, bus: MessageBus, config: dict[str, Any]) -> None:
        super().__init__("BusBridge", bus, config)
        bridge_cfg = config.get("bridge", {})
        self._relay_url = bridge_cfg.get(
            "relay_url", "http://127.0.0.1:5000/agent-event"
        )
        self._timeout   = bridge_cfg.get("post_timeout_seconds", 2.0)
        self._inbox:    asyncio.Queue[AgentMessage] | None = None
        self._session:  Any = None   # aiohttp.ClientSession

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def setup(self) -> None:
        import aiohttp
        self._session = aiohttp.ClientSession()
        self._inbox   = await self.bus.subscribe(*self._ALL_TOPICS)
        self.logger.info(
            "[BusBridge] Ready — forwarding all topics → %s", self._relay_url
        )

    async def teardown(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
        self.logger.info("[BusBridge] HTTP session closed.")

    # ── Step ──────────────────────────────────────────────────────────────────

    async def step(self) -> None:
        msg: AgentMessage | None = await self.receive(self._inbox, timeout=30.0)
        if msg is None:
            return

        envelope = {
            "topic":   msg.topic.value,
            "sender":  msg.sender,
            "age_ms":  round(msg.age_seconds() * 1000, 1),
            "data":    msg.payload,
        }

        await self._post(envelope)

    # ── HTTP POST ─────────────────────────────────────────────────────────────

    async def _post(self, envelope: dict[str, Any]) -> None:
        """Fire-and-forget POST to the relay server."""
        import aiohttp
        try:
            body = json.dumps(envelope, default=_serialise)
            async with self._session.post(
                self._relay_url,
                data=body,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=self._timeout),
            ) as resp:
                if resp.status not in (200, 204):
                    self.logger.warning(
                        "[BusBridge] Relay returned HTTP %d for topic=%s",
                        resp.status, envelope["topic"],
                    )
        except asyncio.TimeoutError:
            self.logger.debug(
                "[BusBridge] POST timeout (relay down?) — topic=%s dropped",
                envelope["topic"],
            )
        except Exception as exc:
            self.logger.debug("[BusBridge] POST error: %s", exc)
