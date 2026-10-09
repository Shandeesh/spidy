# Spidy Multi-Agent Integration Guide

## Step 1: Directory Structure

After integration, your Spidy project should look like this:

```
spidy-main/
├── spidy_ai/
│   ├── config/
│   │   ├── settings.yaml          ← COPY agents/settings.yaml here
│   │   └── ...
│   ├── agents/                    ← CREATE THIS FOLDER (all 8 files)
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   ├── message_bus.py
│   │   ├── base_agent.py
│   │   ├── data_engineer.py
│   │   ├── researcher.py
│   │   ├── risk_manager.py
│   │   ├── executor.py
│   │   └── settings.yaml
│   ├── main.py                    ← Update this (old entry point)
│   ├── data_feed/
│   ├── feature_engineering/
│   ├── ml/
│   ├── regime_detection/
│   ├── risk_management/
│   ├── signal_engine/
│   ├── strategies/
│   └── ...
├── Trading_Backend/
│   ├── mt5_bridge/
│   ├── backend_api/
│   └── ...
├── AI_Engine/
├── Security_Module/
├── Distribution_Build/
└── run_spidy.bat
```

---

## Step 2: Copy Agent Files

1. **Use the root `agents/` folder** (it already exists in this project)
2. **Copy all 8 files** from the generated `agents/` folder:
   ```bash
   # From terminal/PowerShell in VS Code
    mkdir agents
   
   # Copy all files
    copy spidyfiles\*.py agents\
   copy agents\settings.yaml spidy_ai\config\settings.yaml
   ```

3. Or **manually copy-paste** in VS Code:
   - Right-click `spidy_ai/` → New Folder → `agents`
   - Create each `.py` file and paste the code
   - Copy `settings.yaml` to `spidy_ai/config/`

---

## Step 3: Update `spidy_ai/main.py`

Replace the old single-threaded `main.py` with this new entry point:

```python
"""
spidy_ai/main.py — NEW entry point
====================================
Launches the multi-agent Orchestrator instead of the old single-threaded bot.
"""
import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import Orchestrator

def main():
    """Start the multi-agent trading system."""
    config_path = Path(__file__).parent / "config" / "settings.yaml"
    orchestrator = Orchestrator(config_path=str(config_path))
    orchestrator.run()

if __name__ == "__main__":
    main()
```

---

## Step 4: Update `spidy_ai/config/settings.yaml`

Move the `agents/settings.yaml` file to `spidy_ai/config/settings.yaml` and keep it as-is. The Orchestrator will auto-load it.

If you already have a `settings.yaml`, merge the sections:

```yaml
# ── System ────────────────────────────────────────────────────────────────
system:
  symbol:                EURUSD          
  mode:                  SIMULATION      # SIMULATION | LIVE
  poll_interval_seconds: 5               
  candle_lookback:       500             

# ── Risk guardrails (RiskManagerAgent) ───────────────────────────────────
risk:
  start_balance:            10000.0      
  max_daily_drawdown_pct:   0.03         
  max_total_drawdown_pct:   0.10         
  max_open_positions:       3            
  risk_per_trade_pct:       0.01         
  max_lot_size:             1.0          
  min_signal_confidence:    0.55         
  regime_veto:                           
    - VOLATILE

# ── Execution (ExecutorAgent) ─────────────────────────────────────────────
execution:
  atr_sl_multiplier:   1.5              
  rr_ratio:            2.0              
  trailing_atr_mult:   1.0              
  staleness_atr_factor: 1.0            
  slippage_pips:       3               
  magic_number:        20260101        

# ── Logging ───────────────────────────────────────────────────────────────
logging:
  dir: logs                            
```

---

## Step 5: Fix Import Paths in Agent Files

The agent files assume Spidy modules are importable. Open each agent file and verify/update imports:

### In `agents/data_engineer.py`, line ~42-50:

```python
# BEFORE (may not work)
from spidy_ai.data_feed.metatrader_feed import MetaTraderFeed
from spidy_ai.feature_engineering.feature_store import FeatureStore
from spidy_ai.feature_engineering.trend_features import TrendFeatures
...

# AFTER (if modules don't exist, create stubs or import from correct path)
try:
    from spidy_ai.data_feed.metatrader_feed import MetaTraderFeed
    from spidy_ai.feature_engineering.feature_store import FeatureStore
    ...
except ImportError as e:
    print(f"Warning: {e} — using mock data feed")
    MetaTraderFeed = None
```

### In `agents/researcher.py`, line ~72-75:

```python
# BEFORE
import google.generativeai as genai
from AI_Engine.internet_gathering.news_fetcher import NewsFetcher

# AFTER (adjust path as needed)
try:
    import google.generativeai as genai
except ImportError:
    print("Warning: google-generativeai not installed")
    
try:
    from AI_Engine.internet_gathering.news_fetcher import NewsFetcher
except ImportError:
    NewsFetcher = None
```

### In `agents/risk_manager.py` and `agents/executor.py`:

```python
# BEFORE
import MetaTrader5 as mt5

# AFTER (add try-except)
try:
    import MetaTrader5 as mt5
except ImportError:
    print("Warning: MetaTrader5 not installed")
    mt5 = None
```

---

## Step 6: Install Missing Dependencies

Open terminal in VS Code and run:

```bash
# Python packages
pip install pyyaml google-generativeai MetaTrader5

# Optional: if you don't have these
pip install pandas pandas-ta numpy
```

---

## Step 7: Create a Launcher Script

Create `spidy_ai/run_agents.py`:

```python
"""
spidy_ai/run_agents.py
======================
Simple launcher for the multi-agent system.
Run from terminal: python spidy_ai/run_agents.py
"""
import sys
import argparse
from pathlib import Path

# Add parent directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents import Orchestrator

def main():
    parser = argparse.ArgumentParser(
        description="Spidy Multi-Agent Forex Trading System"
    )
    parser.add_argument(
        "--config",
        default="spidy_ai/config/settings.yaml",
        help="Path to settings.yaml",
    )
    parser.add_argument(
        "--mode",
        choices=["sim", "live"],
        default="sim",
        help="SIMULATION or LIVE mode",
    )
    args = parser.parse_args()

    print(f"🕷️  Spidy Multi-Agent System")
    print(f"   Config: {args.config}")
    print(f"   Mode: {args.mode.upper()}")
    print()

    try:
        orch = Orchestrator(config_path=args.config)
        orch.run()
    except KeyboardInterrupt:
        print("\n[Launcher] Shutdown signal received.")
    except Exception as e:
        print(f"\n[Launcher] Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

Then run from VS Code terminal:
```bash
python spidy_ai/run_agents.py --mode sim
python spidy_ai/run_agents.py --mode live  # (when ready)
```

---

## Step 8: Update `run_spidy.bat` (Windows Launcher)

Replace or update your `run_spidy.bat`:

```batch
@echo off
REM Spidy Multi-Agent Trading System Launcher

echo.
echo ╔════════════════════════════════════════╗
echo ║   🕷️  SPIDY MULTI-AGENT SYSTEM        ║
echo ║      Autonomous Forex Trading          ║
echo ╚════════════════════════════════════════╝
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python not found. Install Python 3.9+ and add to PATH.
    pause
    exit /b 1
)

REM Check if required packages are installed
python -m pip show pyyaml >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies...
    python -m pip install -q pyyaml google-generativeai MetaTrader5
)

REM Run the agent system
echo.
echo Starting Orchestrator...
echo.
python spidy_ai/run_agents.py --mode sim

pause
```

Save this as `run_spidy_agents.bat` and double-click to launch.

---

## Step 9: Verify Integration

Run a quick check:

```bash
# From VS Code terminal, in project root
python -c "from agents import Orchestrator; print('✓ Agents imported successfully')"
python -c "import yaml; print('✓ YAML support OK')"
python -c "import MetaTrader5; print('✓ MT5 available')"
```

If all three pass, you're ready to run.

---

## Step 10: Run the System

### Simulation Mode (No Real Money)

```bash
# Option A: Run from terminal
python spidy_ai/run_agents.py --mode sim

# Option B: Double-click run_spidy_agents.bat (Windows)

# Option C: From old main.py entry point
python spidy_ai/main.py
```

**Expected output:**
```
2026-01-15 14:23:45  INFO     spidy.orchestrator  ════════════════════════════════════════
2026-01-15 14:23:45  INFO     spidy.orchestrator    Spidy Multi-Agent System
2026-01-15 14:23:45  INFO     spidy.orchestrator    Symbol=EURUSD  Mode=SIMULATION  Agents=5
2026-01-15 14:23:45  INFO     spidy.orchestrator  ════════════════════════════════════════
2026-01-15 14:23:45  INFO     spidy.DataEngineer  [DataEngineer] Connected — symbol=EURUSD timeframes=M5,H1,H4
2026-01-15 14:23:45  INFO     spidy.Researcher    [Researcher] Ready — using Gemini 2.0 Flash.
2026-01-15 14:23:45  INFO     spidy.RiskManager   [RiskManager] Ready — daily_dd=3% total_dd=10% max_pos=3
2026-01-15 14:23:45  INFO     spidy.Executor      [Executor] Ready — mode=SIMULATION
...
```

Check `logs/spidy_agents.log` for the full trace.

---

## Step 11: Go Live (MetaTrader 5)

When you're ready to trade real money:

1. **Update `settings.yaml`:**
   ```yaml
   system:
     mode: LIVE          # ← Change from SIMULATION
   risk:
     start_balance: 50000   # ← Your actual account balance
   ```

2. **Ensure MT5 is running** and your account is logged in.

3. **Start the system:**
   ```bash
   python spidy_ai/run_agents.py --mode live
   ```

4. **Monitor the logs:**
   ```bash
   # In another terminal, tail the log file
   tail -f logs/spidy_agents.log
   ```

---

## Step 12: Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: No module named 'agents'` | Ensure `agents/` folder is in `spidy_ai/` and `__init__.py` exists |
| `FileNotFoundError: settings.yaml` | Copy `agents/settings.yaml` to `spidy_ai/config/settings.yaml` |
| `MetaTrader5 not available` | Run `pip install MetaTrader5` |
| `google.generativeai not found` | Run `pip install google-generativeai` and set `GOOGLE_API_KEY` env var |
| Agents keep crashing | Check `logs/spidy_agents.log` — most errors show in first 30 lines |
| No trades executing | Check if RiskManager is holding off (settings.yaml too conservative?) |

---

## What's Next?

✅ **Core System**: DataEngineer, Researcher, RiskManager, Executor running  
✅ **Config**: All parameters tweakable via YAML (no code edits needed)  
✅ **Logging**: Full audit trail to `logs/` folder  
✅ **Graceful Shutdown**: `Ctrl+C` stops all agents cleanly  

🔄 **To extend:**
- Add a 5th agent (e.g., `BacktesterAgent` that paper-trades in parallel)
- Integrate with your Dashboard (`Frontend_Dashboard/`)
- Add webhook notifications (Telegram, Discord)
- Hook the bus to InfluxDB (already partially done in Trading_Backend/)

---

## Quick Reference: File Locations

| File | Purpose |
|------|---------|
| `agents/orchestrator.py` | Main supervisor — starts all agents |
| `agents/message_bus.py` | Pub/sub backbone — agents talk here |
| `agents/data_engineer.py` | Agent 1: MT5 data fetcher |
| `agents/researcher.py` | Agent 2: Gemini sentiment analyzer |
| `agents/risk_manager.py` | Agent 3: Kill-switch gatekeeper |
| `agents/executor.py` | Agent 4: Order router + trailing stops |
| `agents/bus_bridge.py` | Agent 5: Dashboard event relay |
| `spidy_ai/config/settings.yaml` | All tunable parameters |
| `logs/spidy_agents.log` | Full audit log |
