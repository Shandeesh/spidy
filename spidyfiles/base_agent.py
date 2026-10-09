"""
agents/base_agent.py
====================
Abstract base class every Spidy agent inherits from.

Lifecycle
---------
  Orchestrator calls: asyncio.create_task(agent.run())

  Inside run():
    1. setup()   — one-time async init (connect APIs, subscribe to bus…)
    2. loop:
         step()  — one unit of work per iteration
       [on exception: log + sleep 5s, retry]
    3. teardown() — clean shutdown (close sockets, flush logs…)

  Orchestrator calls: agent.stop() → sets _running=False → loop exits after
  the current step() completes.

Convenience helpers
-------------------
  self.publish(topic, payload)   — wraps bus.publish() with sender filled in
  self.receive(queue, timeout)   — awaits a message with optional timeout
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

from .message_bus import AgentMessage, MessageBus, Topic


class BaseAgent(ABC):

    def __init__(
        self,
        name:   str,
        bus:    MessageBus,
        config: dict[str, Any],
    ) -> None:
        self.name    = name
        self.bus     = bus
        self.config  = config
        self.logger  = logging.getLogger(f"spidy.{name}")
        self._running = False

    # ── Public API (called by Orchestrator) ───────────────────────────────────

    async def run(self) -> None:
        """
        Full agent lifecycle.  Override setup/step/teardown — not this method.
        """
        self._running = True
        self.logger.info("[%s] Starting…", self.name)
        try:
            await self.setup()
            while self._running:
                try:
                    await self.step()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:           # noqa: BLE001
                    self.logger.error(
                        "[%s] Unhandled error in step(): %s",
                        self.name, exc, exc_info=True,
                    )
                    await asyncio.sleep(5)         # back-off before retrying
        except asyncio.CancelledError:
            self.logger.info("[%s] Cancelled.", self.name)
        finally:
            await self.teardown()
            self.logger.info("[%s] Shutdown complete.", self.name)

    def stop(self) -> None:
        """Signal the agent to exit cleanly after the current step() finishes."""
        self._running = False
        self.logger.info("[%s] Stop requested.", self.name)

    # ── Convenience helpers ───────────────────────────────────────────────────

    async def publish(self, topic: Topic, payload: dict[str, Any]) -> None:
        """Publish a typed message attributed to this agent."""
        await self.bus.publish(
            AgentMessage(sender=self.name, topic=topic, payload=payload)
        )

    async def receive(
        self,
        queue:   asyncio.Queue[AgentMessage],
        timeout: float | None = None,
    ) -> AgentMessage | None:
        """
        Await the next message from a subscribed queue.
        Returns None on timeout (instead of raising asyncio.TimeoutError),
        so callers can handle the "no data" case gracefully.
        """
        try:
            return await asyncio.wait_for(queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None

    # ── Hooks (override in subclasses) ────────────────────────────────────────

    async def setup(self) -> None:
        """One-time async initialisation. Called once before the step loop."""

    async def teardown(self) -> None:
        """Clean shutdown. Called once after the step loop exits."""

    @abstractmethod
    async def step(self) -> None:
        """
        Core per-cycle work unit.  Must be implemented by every agent.
        Each call should do one meaningful action then return
        (blocking I/O should use asyncio.sleep or asyncio.to_thread).
        """
