# Spidy Multi-Agent Integration — Quick Start Checklist

Print this. Cross off as you go.

---

## ☐ Pre-flight (5 minutes)

- [ ] Download all 9 files (8 Python + 1 YAML)
  ```
  agents/
  ├── __init__.py
  ├── orchestrator.py
  ├── message_bus.py
  ├── base_agent.py
  ├── data_engineer.py
  ├── researcher.py
  ├── risk_manager.py
  ├── executor.py
  └── settings.yaml
  ```
- [ ] Open VS Code to your Spidy project root
- [ ] Open PowerShell/terminal in VS Code

---

## ☐ Option A: Automatic Setup (Recommended — 2 minutes)

```powershell
# Download setup_agents.ps1 to project root, then:
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\setup_agents.ps1
```

**This does everything below automatically. Jump to "Test Run".**

---

## ☐ Option B: Manual Setup (5 minutes)

### Step 1: Create folder structure
```bash
mkdir agents
mkdir spidy_ai\config
mkdir logs
```

### Step 2: Copy agent files
- Use the existing root `agents/` folder and create or update each `.py` file
- Paste code from each file (orchestrator.py, message_bus.py, etc.)
- Update `agents/__init__.py` (the project exports `Orchestrator` there)

### Step 3: Copy settings
- Copy `settings.yaml` to `spidy_ai/config/settings.yaml`

### Step 4: Install dependencies
```bash
pip install -r requirements.txt
# or manually:
pip install pyyaml google-generativeai MetaTrader5 pandas pandas-ta
```

---

## ☐ Environment Setup (1 minute)

### Set Google API Key (for Researcher agent)
```bash
# Windows (PowerShell)
$env:GOOGLE_API_KEY = "your-key-here"

# Or set permanently: Control Panel → System → Environment Variables
# Add: GOOGLE_API_KEY = sk-...

# Linux/Mac
export GOOGLE_API_KEY="your-key-here"
```

### Get your key
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikeys)
2. Click "Create API Key"
3. Copy it

---

## ☐ Configuration (Optional — 2 minutes)

Edit `spidy_ai/config/settings.yaml`:

```yaml
system:
  symbol: EURUSD           # Change if you want different pair
  mode: SIMULATION         # SIMULATION or LIVE (when ready)
  
risk:
  max_daily_drawdown_pct: 0.03    # 3% daily loss limit
  max_total_drawdown_pct: 0.10    # 10% total loss → kill switch
  max_open_positions: 3           # Max concurrent trades
  risk_per_trade_pct: 0.01        # 1% of balance per trade
  
execution:
  atr_sl_multiplier: 1.5          # Stop-loss width in ATR
  rr_ratio: 2.0                   # Reward:Risk ratio (2:1)
  trailing_atr_mult: 1.0          # Trailing stop aggressiveness
```

Defaults are conservative (safe). Don't change on first run.

---

## ☐ Test Run (2 minutes)

```bash
# Verify agents import
python -c "from agents import Orchestrator; print('✓ OK')"

# Start simulation
python spidy_ai/run_agents.py --mode sim
```

**Expected output:**
```
🕷️  Spidy Multi-Agent System
   Config: spidy_ai/config/settings.yaml
   Mode: SIMULATION

2026-01-15 14:23:45  INFO     spidy.orchestrator  ════════════════════════════════════════
2026-01-15 14:23:45  INFO     spidy.orchestrator    Spidy Multi-Agent System
2026-01-15 14:23:45  INFO     spidy.orchestrator    Symbol=EURUSD  Mode=SIMULATION  Agents=5
2026-01-15 14:23:45  INFO     spidy.orchestrator  ════════════════════════════════════════
2026-01-15 14:23:45  INFO     spidy.DataEngineer  [DataEngineer] Connected…
2026-01-15 14:23:45  INFO     spidy.Researcher    [Researcher] Ready…
2026-01-15 14:23:45  INFO     spidy.RiskManager   [RiskManager] Ready…
2026-01-15 14:23:45  INFO     spidy.Executor      [Executor] Ready…
```

Hit `Ctrl+C` to stop.

---

## ☐ Check Logs

```bash
# View log file
type logs\spidy_agents.log    # Windows
cat logs/spidy_agents.log     # Linux/Mac

# Tail in real-time
tail -f logs/spidy_agents.log
```

---

## ☐ Troubleshooting

| Problem | Solution |
|---------|----------|
| `ModuleNotFoundError: agents` | Make sure `agents/` folder is in `spidy_ai/` with `__init__.py` |
| `settings.yaml not found` | Copy `agents/settings.yaml` to `spidy_ai/config/settings.yaml` |
| `MetaTrader5 not installed` | Run `pip install MetaTrader5` |
| `GOOGLE_API_KEY not set` | Set env var: `$env:GOOGLE_API_KEY = "..."`  |
| Agents keep crashing | Check `logs/spidy_agents.log` for error messages |
| No trades happening | Likely RiskManager hold-off or low confidence — check log |

---

## ☐ Launchers (Optional)

Use these to start without typing commands:

### Windows — Double-click either:
- `run_spidy_agents.bat` (simplest)
- `run_spidy_agents.ps1` (if PowerShell is your default)

### Create shortcut on desktop
1. Right-click `run_spidy_agents.bat`
2. Create shortcut
3. Right-click shortcut → Properties
4. Start in: `C:\path\to\spidy-main`
5. Pin to taskbar

---

## ☐ Going Live (MetaTrader 5) — LATER

Only do this when you've tested in simulation for 1+ week.

1. **Ensure MT5 is running** and logged into your broker account
2. **Update settings.yaml:**
   ```yaml
   system:
     mode: LIVE                   # ← Change from SIMULATION
   risk:
     start_balance: 50000.0       # ← Your actual account balance
   ```
3. **Start:**
   ```bash
   python spidy_ai/run_agents.py --mode live
   ```
4. **Monitor logs constantly:**
   ```bash
   tail -f logs/spidy_agents.log
   ```
5. **First trade?** You'll see execution report in logs and terminal

---

## 📞 Reference

| File | What it does |
|------|-------------|
| `orchestrator.py` | Starts all 5 agents + health monitor |
| `message_bus.py` | Pub/sub backbone — agents communicate here |
| `base_agent.py` | Template for all agents (setup → step loop → teardown) |
| `data_engineer.py` | Agent 1: fetches EUR/USD candles + computes indicators |
| `researcher.py` | Agent 2: calls Gemini to analyze sentiment + news |
| `risk_manager.py` | Agent 3: checks 7 guardrails + approves signals |
| `executor.py` | Agent 4: places orders + manages trailing stops |
| `settings.yaml` | All tunable parameters (no code edits needed) |

---

## 🎓 How the Agents Work

```
every 2 seconds:
  DataEngineer    fetches price → computes RSI, ATR, EMA → MARKET_SNAPSHOT
         ↓
every 10 ticks:
  Researcher      reads news + MARKET_SNAPSHOT → SENTIMENT
         ↓
every tick:
  RiskManager     checks 7 guardrails + SENTIMENT → RISK_STATE
         ↓
  (if canTrade == True)
         ↓
every 15 ticks:
  Executor        routes order to MT5 + monitors trail stops → EXECUTION_REPORT
         ↓
every 3 ticks:
  Executor        ratchets trailing stop as price moves in favour
         ↓
continuous:
  MessageBus      logs all messages to logs/spidy_agents.log
```

---

## ✅ You're Done!

System is running. Agents are trading autonomously. Check logs for details.

Next: Read `INTEGRATION_GUIDE.md` for advanced config, adding more agents, or connecting to your dashboard.

**Questions?** Check logs first — errors tell you exactly what's wrong.
