"""
agents/message_bus.py
=====================
Typed async pub/sub message bus — the sole communication channel between
all Spidy agents. No agent imports another agent; they only share this bus.

Topics
------
  MARKET_SNAPSHOT   DataEngineer  → everyone   (OHLCV features, regime)
  SENTIMENT         Researcher    → everyone   (bullish/bearish/neutral)
  RISK_STATE        RiskManager   → everyone   (can_trade, drawdown stats)
  TRADE_SIGNAL      RiskManager   → Executor   (approved order params)
  EXECUTION_REPORT  Executor      → everyone   (fill, close, kill-switch)
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ── Topic enum ────────────────────────────────────────────────────────────────

class Topic(str, Enum):
    MARKET_SNAPSHOT  = "market_snapshot"
    SENTIMENT        = "sentiment"
    RISK_STATE       = "risk_state"
    TRADE_SIGNAL     = "trade_signal"
    EXECUTION_REPORT = "execution_report"


# ── Message dataclass ─────────────────────────────────────────────────────────

@dataclass
class AgentMessage:
    sender:    str
    topic:     Topic
    payload:   dict[str, Any]
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )

    def age_seconds(self) -> float:
        return (datetime.now(tz=timezone.utc) - self.timestamp).total_seconds()


# ── MessageBus ────────────────────────────────────────────────────────────────

class MessageBus:
    """
    Async pub/sub bus backed by per-subscriber asyncio.Queues.

    Design choices
    --------------
    * Each subscriber gets its OWN queue — slow consumers cannot block fast
      publishers (unlike a shared queue approach).
    * If a subscriber's queue is full (default cap = 100), the message is
      DROPPED with a warning rather than blocking the publisher.
    * Thread-safe subscription via asyncio.Lock (agents set up in sequence
      before the event loop starts spinning all tasks).
    """

    def __init__(self, maxsize: int = 100) -> None:
        self._subs:    dict[Topic, list[asyncio.Queue[AgentMessage]]] = {}
        self._lock     = asyncio.Lock()
        self._maxsize  = maxsize
        self._log      = logging.getLogger("spidy.bus")
        self._counters: dict[Topic, int] = {t: 0 for t in Topic}

    # ── Subscription ──────────────────────────────────────────────────────────

    async def subscribe(self, *topics: Topic) -> asyncio.Queue[AgentMessage]:
        """
        Register interest in one or more topics.
        Returns a single queue that receives messages for ALL requested topics.
        Typically called once inside BaseAgent.setup().
        """
        queue: asyncio.Queue[AgentMessage] = asyncio.Queue(maxsize=self._maxsize)
        async with self._lock:
            for topic in topics:
                self._subs.setdefault(topic, []).append(queue)
        self._log.debug("[Bus] New subscriber for topics: %s", [t.value for t in topics])
        return queue

    # ── Publishing ────────────────────────────────────────────────────────────

    async def publish(self, message: AgentMessage) -> None:
        """Broadcast a message to all subscribers for its topic."""
        topic = message.topic
        self._counters[topic] += 1
        for queue in self._subs.get(topic, []):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                self._log.warning(
                    "[Bus] DROP — topic=%s from=%s (queue full)",
                    topic.value, message.sender,
                )

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        """Returns message counts per topic — useful for dashboard display."""
        return {
            "published": {t.value: c for t, c in self._counters.items()},
            "subscribers": {
                t.value: len(qs) for t, qs in self._subs.items()
            },
        }
