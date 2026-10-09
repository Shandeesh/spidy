"""Launch the root-level Spidy multi-agent system.

Usage::

    python spidy_ai/run_agents.py --mode sim
    python spidy_ai/run_agents.py --mode live --config path/to/settings.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents import Orchestrator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Spidy Multi-Agent Forex Trading System"
    )
    parser.add_argument(
        "--config",
        default=str(PROJECT_ROOT / "spidy_ai" / "config" / "settings.yaml"),
        help="Path to settings.yaml",
    )
    parser.add_argument(
        "--mode",
        choices=("sim", "live"),
        default=None,
        help="Override the configured mode (sim or live)",
    )
    args = parser.parse_args()

    orchestrator = Orchestrator(config_path=args.config)
    if args.mode:
        orchestrator.config.setdefault("system", {})["mode"] = (
            "LIVE" if args.mode == "live" else "SIMULATION"
        )
    orchestrator.run()


if __name__ == "__main__":
    main()