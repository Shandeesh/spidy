"""
agents/orchestrator.py
=======================
The Orchestrator is the single entry point for the entire Spidy agent system.

Responsibilities
----------------
  1. Load and validate settings.yaml.
  2. Create the shared MessageBus.
  3. Instantiate all four agents.
  4. Run each agent as an independent asyncio.Task with supervision:
       - If an agent crashes unexpectedly, it is restarted after an
         exponential back-off (5s → 10s → 20s … capped at 120s).
       - If an agent calls stop() cleanly, it is NOT restarted.
  5. Print a health summary every 60 seconds.
  6. Listen for SIGINT / SIGTERM and perform a graceful shutdown:
       - Calls agent.stop() on all agents.
       - Cancels asyncio tasks.
       - Waits for teardown() to complete before exiting.

Run
---
  python -m agents.orchestrator
  python -m agents.orchestrator --config path/to/settings.yaml
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Any

import yaml

from .message_bus    import MessageBus
from .data_engineer  import DataEngineerAgent
from .researcher     import ResearcherAgent
from .risk_manager   import RiskManagerAgent
from .executor       import ExecutorAgent
from .bus_bridge     import BusBridgeAgent


# ── Logging setup ─────────────────────────────────────────────────────────────

def _configure_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            log_dir / "spidy_agents.log", mode="a", encoding="utf-8"
        ),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)-20s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
        force=True,
    )


# ── Orchestrator ──────────────────────────────────────────────────────────────

class Orchestrator:
    """
    Wires four specialized agents together via a shared MessageBus and
    runs them as supervised async tasks.
    """

    _RESTART_CAP_SECONDS = 120

    def __init__(
        self, config_path: str = "spidy_ai/config/settings.yaml"
    ) -> None:
        self.config = self._load_config(config_path)
        _configure_logging(
            Path(self.config.get("logging", {}).get("dir", "logs"))
        )
        self.logger = logging.getLogger("spidy.orchestrator")

        self.bus = MessageBus()

        self._agents: dict[str, Any] = {
            "DataEngineer": DataEngineerAgent(self.bus, self.config),
            "Researcher":   ResearcherAgent(self.bus,   self.config),
            "RiskManager":  RiskManagerAgent(self.bus,  self.config),
            "Executor":     ExecutorAgent(self.bus,      self.config),
            "BusBridge":    BusBridgeAgent(self.bus,    self.config),
        }
        self._tasks:          dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self) -> None:
        """Synchronous entry point — blocks until shutdown."""
        try:
            asyncio.run(self._main())
        except KeyboardInterrupt:
            pass

    # ── Async main ────────────────────────────────────────────────────────────

    async def _main(self) -> None:
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._request_shutdown)
            except (NotImplementedError, RuntimeError):
                # Windows doesn't support add_signal_handler for SIGINT
                pass

        symbol = self.config.get("system", {}).get("symbol", "EURUSD")
        mode   = self.config.get("system", {}).get("mode",   "SIMULATION")

        self.logger.info("=" * 64)
        self.logger.info("  Spidy Multi-Agent System")
        self.logger.info(
            "  Symbol=%-10s  Mode=%-12s  Agents=%d",
            symbol, mode, len(self._agents),
        )
        self.logger.info("=" * 64)

        # Start all agent tasks
        for name, agent in self._agents.items():
            self._tasks[name] = asyncio.create_task(
                self._supervised(name, agent), name=name
            )

        health_task = asyncio.create_task(self._health_loop())
        await self._shutdown_event.wait()

        self.logger.info("[Orchestrator] Shutting down…")
        health_task.cancel()
        await self._stop_all()
        self.logger.info("[Orchestrator] All agents stopped. Goodbye.")

    # ── Supervised agent wrapper ──────────────────────────────────────────────

    async def _supervised(self, name: str, agent: Any) -> None:
        """
        Runs an agent with automatic restart on crash.
        Clean exits (via agent.stop()) break the loop.
        """
        backoff = 5.0
        while not self._shutdown_event.is_set():
            try:
                await agent.run()
                break   # agent.stop() was called — don't restart
            except asyncio.CancelledError:
                self.logger.info("[Orchestrator] %s task cancelled.", name)
                break
            except Exception as exc:
                if self._shutdown_event.is_set():
                    break
                self.logger.error(
                    "[Orchestrator] %s CRASHED: %s — restarting in %.0fs",
                    name, exc, backoff, exc_info=True,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, self._RESTART_CAP_SECONDS)

    # ── Health monitor ────────────────────────────────────────────────────────

    async def _health_loop(self) -> None:
        """Logs agent task status every 60 seconds."""
        try:
            while True:
                await asyncio.sleep(60)
                self.logger.info("[Health] Bus stats: %s", self.bus.stats())
                for name, task in self._tasks.items():
                    if task.done():
                        exc    = task.exception() if not task.cancelled() else None
                        status = f"DONE (exc={exc})" if exc else "DONE (clean)"
                    else:
                        status = "RUNNING"
                    self.logger.info("[Health] %-15s → %s", name, status)
        except asyncio.CancelledError:
            pass

    # ── Shutdown ──────────────────────────────────────────────────────────────

    def _request_shutdown(self) -> None:
        self.logger.info("[Orchestrator] Shutdown signal received.")
        self._shutdown_event.set()

    async def _stop_all(self) -> None:
        """Signal all agents to stop, then cancel their tasks."""
        for agent in self._agents.values():
            agent.stop()
        for task in self._tasks.values():
            task.cancel()
        results = await asyncio.gather(
            *self._tasks.values(), return_exceptions=True
        )
        for name, result in zip(self._tasks, results):
            if isinstance(result, Exception) and not isinstance(
                result, asyncio.CancelledError
            ):
                self.logger.warning(
                    "[Orchestrator] %s teardown raised: %s", name, result
                )

    # ── Config loader ─────────────────────────────────────────────────────────

    @staticmethod
    def _load_config(path: str) -> dict[str, Any]:
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logging.getLogger("spidy.orchestrator").warning(
                "Config not found at '%s' — using built-in defaults.", path
            )
            return {}
        except yaml.YAMLError as exc:
            logging.getLogger("spidy.orchestrator").error(
                "YAML parse error in '%s': %s", path, exc
            )
            return {}


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Spidy Multi-Agent Trading System"
    )
    parser.add_argument(
        "--config",
        default="spidy_ai/config/settings.yaml",
        help="Path to settings.yaml (default: spidy_ai/config/settings.yaml)",
    )
    args = parser.parse_args()
    Orchestrator(config_path=args.config).run()


if __name__ == "__main__":
    main()
