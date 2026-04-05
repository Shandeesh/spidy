from fastapi import FastAPI, Body, WebSocket, BackgroundTasks, Depends, HTTPException, status, Security
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import json
import subprocess # Added for process management
import time

import asyncio
import threading
import winreg # Added for Registry Lookup
from datetime import datetime, timedelta
import financial_db # Import the new DB module
from economic_calendar import calendar # Import Economic Calendar
import pandas as pd
from strategy_manager import StrategyManager
import watchdog_service # START WATCHDOG MODULE
import sys
# Add AI_Engine to path for SentimentAnalyzer
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "AI_Engine"))
from sentiment_analyzer import SentimentAnalyzer # SENTIMENT BRAIN

# Add Trading_Backend to path for InfluxDB Manager
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
try:
    from influxdb_manager import init_influxdb, influx_db  # TIME-SERIES DB
except ImportError:
    print("WARNING: InfluxDB dependencies not found. Metrics will be disabled.")
    influx_db = None
    def init_influxdb(): return False

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    HAS_MT5 = False
    print("CRITICAL: MetaTrader5 module not found. Please install it.")

# DEBUG: Startup Logging
with open("bridge_startup.log", "w") as f:
    f.write(f"Startup Time: {datetime.now()}\n")
    f.write(f"Python Executable: {sys.executable}\n")
    f.write(f"HAS_MT5: {HAS_MT5}\n")
    f.write(f"CWD: {os.getcwd()}\n")



from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("INFO: Auto-connecting to MT5...")
    try:
        financial_db.init_db() # Init Database
    except Exception as e:
        print(f"CRITICAL: Financial DB Init Failed: {e}")
        
    # Run MT5 connection in background so API server starts immediately
    asyncio.create_task(connect_mt5(force=True))
    asyncio.create_task(auto_trader_loop())
    asyncio.create_task(update_technical_indicators()) # Add Analysis Loop
    asyncio.create_task(trailing_stop_manager())
    asyncio.create_task(oil_watcher_manager()) # The Oil Watcher
    asyncio.create_task(ai_general_loop()) # The General (Strategy Update)
    asyncio.create_task(history_sync_manager()) # Add History Sync
    asyncio.create_task(update_global_pulse()) # GLOBAL TETHER (Phase 4)
    asyncio.create_task(sentiment_sync_loop()) # SENTIMENT BRAIN (Phase 2)
    asyncio.create_task(monitor_mt5_process()) # NEW: Monitor MT5 Process Liveness
    asyncio.create_task(sanitize_old_trades()) # FIX: Remove SL from Pre-Update Trades

    
    # --- WATCHDOG START ---
    loop = asyncio.get_running_loop()
    class BridgeContext:
        def __init__(self, loop):
            self.loop = loop
            self.mt5_state = mt5_state
            self.auto_trade_state = auto_trade_state
            self.broadcast_log = broadcast_log
            self._process_close_all_background = _process_close_all_background
            
    bridge_ctx = BridgeContext(loop)
    # Load loss limit from settings or default to $100
    loss_limit = risk_settings.get("max_daily_loss", 50.0) 
    
    global watchdog_instance
    watchdog_instance = watchdog_service.Watchdog(bridge_ctx, max_daily_loss=loss_limit)
    watchdog_instance.start()
    
    # --- SENTIMENT ANALYZER START ---
    global sentiment_analyzer
    sentiment_analyzer = SentimentAnalyzer(update_interval=300)  # Every 5 mins
    sentiment_analyzer.start()
    
    # --- INFLUXDB START (Optional) ---
    print("INFO: Attempting InfluxDB connection...")
    try:
        if init_influxdb():
            print("✅ InfluxDB: Metrics logging enabled")
        else:
            print("⚠️ InfluxDB: Running without metrics DB (optional feature)")
    except Exception as e:
        print(f"⚠️ InfluxDB: Initialization failed ({e}), continuing without metrics DB")
    # --------------------------------
    # --------------------------------
    # ----------------------
    
    yield
    # Shutdown logic (optional)

# --- GLOBAL TETHER (PHASE 4) ---
async def update_global_pulse():
    """Calculates Global Correlation (DXY, Oil) and writes to shared file."""
    while True:
        try:
            await safe_mt5_call(mt5.symbol_select, "DX-Y.NYB", True)
            await safe_mt5_call(mt5.symbol_select, "XBRUSD", True)
            
            # Fetch Data
            dxy_tick = await safe_mt5_call(mt5.symbol_info_tick, "DX-Y.NYB")
            oil_tick = await safe_mt5_call(mt5.symbol_info_tick, "XBRUSD")
            
            dxy_price = dxy_tick.last if dxy_tick else 0.0
            oil_price = oil_tick.last if oil_tick else 0.0
            
            data = {
                "DXY": dxy_price,
                "OIL": oil_price,
                "timestamp": time.time(),
                "sentiment": "NEUTRAL"
            }
            
            # Simple Analysis
            if dxy_price > 105.0: data["sentiment"] = "BEARISH_RUPEE" # Strong Dollar = Weak Rupee
            elif dxy_price < 100.0: data["sentiment"] = "BULLISH_RUPEE"
            
            # Write to Shared File (ATOMICALLY)
            # Path: Trading_Backend/market_pulse.json (One level up from mt5_bridge)
            file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "market_pulse.json")
            temp_path = file_path + ".tmp"
            
            try:
                with open(temp_path, "w") as f:
                    json.dump(data, f)
                    f.flush()
                    os.fsync(f.fileno()) # Ensure write to disk
                
                os.replace(temp_path, file_path) # Atomic Swap
            except Exception as e:
                print(f"Global Pulse Write Error: {e}")
            
            # print(f"🌍 Pulse: DXY {dxy_price} | Oil {oil_price}") # Verbose
            
        except Exception as e:
            print(f"Global Pulse Error: {e}")
            
        await asyncio.sleep(5)
    print("INFO: Shutting down Bridge...")

# --- SENTIMENT SYNC (PHASE 2) ---
async def sentiment_sync_loop():
    """Reads sentiment.json from AI_Engine and updates mt5_state."""
    while True:
        try:
            # Path: AI_Engine/sentiment.json
            ai_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "AI_Engine", "sentiment.json")
            
            if os.path.exists(ai_path):
                with open(ai_path, "r") as f:
                    sentiment_data = json.load(f)
                    
                # Check freshness (< 10 minutes)
                ts = sentiment_data.get("timestamp", 0)
                if time.time() - ts < 600:
                    mt5_state["sentiment"] = sentiment_data.get("sentiment", "NEUTRAL")
                    mt5_state["sentiment_score"] = sentiment_data.get("score", 0.0)
                else:
                    mt5_state["sentiment"] = "NEUTRAL"  # Stale data
                    
        except Exception as e:
            # Silent fail - sentiment is optional
            pass
            
        await asyncio.sleep(10)  # Check every 10s


# --- MONITOR MT5 PROCESS (Fix for Zombie Relaunch) ---
async def monitor_mt5_process():
    """
    Periodically checks if 'terminal64.exe' is actually running.
    If not, updates mt5_state["connected"] = False.
    This prevents other modules (like Watchdog) from trying to 'initialize' (relaunch) it.
    """
    print("INFO: MT5 Process Monitor Started.")
    while True:
        try:
            # Simple check using tasklist (lightweight enough for 5s interval)
            # using tasklist is safer than psutil if not installed
            # Check if terminal64.exe is in the output of tasklist
            proc = await asyncio.create_subprocess_shell(
                'tasklist /FI "IMAGENAME eq terminal64.exe" /NH',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            output = stdout.decode('utf-8', errors='ignore')
            
            is_running = "terminal64.exe" in output
            
            if not is_running:
                if mt5_state.get("connected", False):
                    print("⚠️ MONITOR: MT5 Process gone! Setting connected = False.")
                    mt5_state["connected"] = False
            else:
                pass
                
        except Exception as e:
            print(f"Monitor Error: {e}")
            
        await asyncio.sleep(5)




app = FastAPI(lifespan=lifespan)

# API Auth Setup
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Shared_Data/configs/.env")))
API_KEY = os.getenv("SPIDY_API_KEY", "spidy_secure_123")
api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Forbidden: Invalid or missing X-API-KEY header."
        )

# FIX #3: Restrict CORS to known local origins (was wildcard "*")
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:5001",
    "http://127.0.0.1:5001",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock shared state (fallback)
mt5_state = {"connected": False, "equity": 10000.0}
auto_trade_state = {"running": True, "sentiment": "NEUTRAL", "analysis": {}} # Default to True
risk_settings = {"auto_secure": {"enabled": False, "threshold": 10.0}, "use_technical_filters": True}

# PHASE 3: Performance Optimization - Bar Cache
from collections import deque
technical_bars_cache = {}  # {symbol: {'m1': deque(maxlen=500), 'h1': deque(maxlen=300), 'initialized': bool}}
clients = set()  # FIX #10: Use set for O(1) add/discard (was list with O(n) remove)
log_history = deque(maxlen=200)  # FIX #4: deque with maxlen for O(1) thread-safe append/eviction
technical_cache = {}  # Cache for RSI/EMA: { symbol: { rsi, trend, ema, updated } }
profit_peaks = {}  # Tracks High Water Mark for open positions { ticket_id: max_profit }
strategy_manager = StrategyManager()
latest_strategy_signals = {}  # Cache for Strategy Signals { symbol: { signal, confidence, reason, time } }

# --- CONCURRENCY HELPER ---
async def safe_mt5_call(func, *args, **kwargs):
    """
    Executes a blocking MT5 function in a separate thread to prevent 
    freezing the FastAPI event loop.
    """
    if not HAS_MT5: return None
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

# Load history from file on startup

try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_file_path = os.path.join(current_dir, "system_logs.txt")
    if os.path.exists(log_file_path):
        with open(log_file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            log_history.extend([line.strip() for line in lines[-50:]])
            print(f"INFO: Loaded {len(log_history)} logs from history.")
except Exception as e:
    print(f"WARN: Could not load log history: {e}")


# Concurrency Control
ticket_lock = threading.Lock()
processing_tickets = set()


@app.get("/symbols")
def get_symbols():
    """Returns a list of tradable symbols."""
    # Use the dynamic logic if MT5 is connected
    if HAS_MT5 and mt5_state["connected"]:
        symbols = mt5.symbols_get()
        if symbols:
             return {"symbols": [s.name for s in symbols if s.select]}
    
    # Fallback default list
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "BTCUSD", "ETHUSD", "SP500", "US30", "NAS100"]
    return {"symbols": symbols}

@app.get("/api")
def home():
    return {"status": "MT5 Bridge Running", "has_mt5_lib": HAS_MT5}

@app.get("/logs/download")
def download_logs():
    """Download the system logs file."""
    # Use absolute path relative to this script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, "system_logs.txt")
    
    # If file doesn't exist but we have memory logs, dump them first
    if not os.path.exists(file_path) and log_history:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                for line in log_history:
                    f.write(line + "\n")
        except Exception as e:
            print(f"Failed to dump buffer to file: {e}")

    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='text/plain', filename="system_logs.txt")
    else:
        return {"error": "No logs available yet."}

print("DEBUG: Registering /history endpoint...")
@app.get("/history")
def get_history():
    """Returns trade history from the database."""
    # INCREASED LIMIT TO 1000
    history = financial_db.get_trade_history(limit=1000)
    return {"history": history}

@app.get("/test")
def get_test():
    return {"status": "ok"}

# UPGRADE 4: Daily P&L endpoint — exposes financial_db.get_daily_pnl() which had no API route
@app.get("/pnl")
def get_daily_pnl_endpoint():
    """Returns the total realized P&L for the current trading day."""
    try:
        pnl = financial_db.get_daily_pnl()
        # Also add unrealized (floating) P&L from open positions
        floating = mt5_state.get("profit", 0.0)
        return {
            "daily_realized_pnl": round(pnl, 2),
            "floating_pnl": round(floating, 2),
            "total_pnl": round(pnl + floating, 2),
            "currency": mt5_state.get("currency", "USD")
        }
    except Exception as e:
        return {"error": str(e)}

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)  # FIX #10: O(1) set add
    
    # Send history to new client
    for msg in list(log_history):  # snapshot deque for safe iteration
        try:
             await websocket.send_text(msg)
        except:
             pass
             
    try:
        while True:
            # UPGRADE 2: Send heartbeat ping every 30s to prevent silent proxy timeouts
            await asyncio.sleep(30)
            try:
                await websocket.send_text("__ping__")
            except:
                break
    except:
        pass
    finally:
        clients.discard(websocket)  # FIX #10: O(1) set discard, no KeyError

async def broadcast_log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] {message}"
    
    # UPGRADE 3: Write to file with log rotation (cap at 5000 lines)
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "system_logs.txt")
        # Read + trim if too large (only every 100 writes to avoid overhead)
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
        # Rotate: trim to last 5000 lines if file is large
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
            if len(all_lines) > 5000:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(all_lines[-5000:])
        except:
            pass
    except Exception as e:
        print(f"Log Write Error: {e}")

    # FIX #4: deque with maxlen auto-evicts oldest — no manual pop needed
    log_history.append(formatted_msg)
    
    # Broadcast to all connected clients
    if not clients:
         print(f"DEBUG: No clients connected. Log buffered: {message[:30]}...")
    else:
         print(f"DEBUG: Broadcasting to {len(clients)} clients: {message[:30]}...")

    # FIX #10: Snapshot set, collect dead clients, remove after iteration
    dead_clients = []
    for client in list(clients):  # snapshot for safe iteration
        try:
            await client.send_text(formatted_msg)
        except:
            dead_clients.append(client)
    for dc in dead_clients:
        clients.discard(dc)



# Helper: Determine Filling Mode
def get_filling_mode(symbol):
    """
    Determines the correct filling mode for the symbol.
    """
    if not HAS_MT5: return mt5.ORDER_FILLING_FOK # Default for mock/disconnected

    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return mt5.ORDER_FILLING_FOK
        
    # Manually define flags if missing in older lib versions
    # SYMBOL_FILLING_FOK = 1
    # SYMBOL_FILLING_IOC = 2
    SYMBOL_FILLING_FOK = 1
    SYMBOL_FILLING_IOC = 2
    
    modes = symbol_info.filling_mode
    
    if modes & SYMBOL_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    elif modes & SYMBOL_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC
    else:
        # Fallback to RETURN if FOK/IOC not allowed
        return mt5.ORDER_FILLING_RETURN


# --- HELPER: Dynamic Risk Calculation ---
def calculate_max_sl_risk(symbol_info, volume, max_risk_usd=3.0):
    """
    Calculates the Maximum Stop Loss Distance (in Price) 
    allowed to stay within max_risk_usd.
    
    Formula: Risk = Volume * ContractSize * (Entry - SL)
    Diff = Risk / (Volume * ContractSize)
    """
    contract_size = symbol_info.trade_contract_size
    if contract_size == 0 or volume <= 0: return 0.0
    
    # Calculate Max Price Difference allowed
    max_price_diff = max_risk_usd / (volume * contract_size)
    
    return max_price_diff

# --- HELPER: Technical Analysis ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0 # Default neutral
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
            
    # Simple Average (First RSI)
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        return 100.0
        
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Smoothed RSI for remaining
    for i in range(period, len(prices)-1):
        change = prices[i+1] - prices[i]
        gain = change if change > 0 else 0
        loss = abs(change) if change < 0 else 0
        
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
        
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
    return rsi

def calculate_ema(prices, period=50):
    if len(prices) < period:
        return prices[-1] if prices else 0.0
        
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period # Start with SMA
    
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
        
    return ema

# PHASE 3: Optimized Symbol Processing (Parallel)
async def process_symbol_technical(symbol, do_h1_update):
    """Process technical indicators for a single symbol (async)."""
    try:
        # Initialize cache if needed
        if symbol not in technical_bars_cache:
            print(f"⚡ Initializing bar cache for {symbol}...")
            # First-time full fetch
            m1_bars = await safe_mt5_call(mt5.copy_rates_from_pos, symbol, mt5.TIMEFRAME_M1, 0, 500)
            h1_bars = await safe_mt5_call(mt5.copy_rates_from_pos, symbol, mt5.TIMEFRAME_H1, 0, 300)
            
            if m1_bars is None or h1_bars is None:
                return
                
            technical_bars_cache[symbol] = {
                'm1': deque(m1_bars, maxlen=500),
                'h1': deque(h1_bars, maxlen=300),
                'initialized': True
            }
        else:
            # Incremental update (OPTIMIZATION: only fetch last 5 bars)
            m1_new = await safe_mt5_call(mt5.copy_rates_from_pos, symbol, mt5.TIMEFRAME_M1, 0, 5)
            if m1_new is not None:
                for bar in m1_new:
                    technical_bars_cache[symbol]['m1'].append(bar)
                    
            if do_h1_update:
                h1_new = await safe_mt5_call(mt5.copy_rates_from_pos, symbol, mt5.TIMEFRAME_H1, 0, 5)
                if h1_new is not None:
                    for bar in h1_new:
                        technical_bars_cache[symbol]['h1'].append(bar)
        
        # Use cached bars
        bars = list(technical_bars_cache[symbol]['m1'])
        if len(bars) < 50:
            return
            
        close_prices = [x['close'] for x in bars]
        current_price = close_prices[-1]
        
        # Convert to DataFrame for Strategy Manager
        try:
            df = pd.DataFrame(list(bars))
            df['time'] = pd.to_datetime(df['time'], unit='s')
            strategy_manager.update_technical_state(symbol, df, current_price)
        except Exception as e:
            print(f"Strategy Update Error: {e}")

        # --- H1 Trend Update (Triple Screen) ---
        if do_h1_update:
            h1_bars = list(technical_bars_cache[symbol]['h1'])
            if len(h1_bars) > 200:
                try:
                    df_h1 = pd.DataFrame(list(h1_bars))
                    df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
                    strategy_manager.update_h1_trend(symbol, df_h1)
                except Exception as e:
                    print(f"H1 Update Error: {e}")

        # --- Gap Strategy (Morning Momentum) ---
        gap_sig = strategy_manager.check_gap_signal(symbol, current_price)
        if gap_sig:
            has_pos = any(p['symbol'] == symbol for p in mt5_state.get('positions', []))
            if not has_pos:
                await broadcast_log(f"🚀 GAP SIGNAL: {gap_sig['signal']} on {symbol} (Reason: {gap_sig['reason']})")

        # Calculate RSI/EMA and store
        rsi = calculate_rsi(close_prices, 14)
        ema_50 = calculate_ema(close_prices, 50)
        
        if current_price > ema_50:
            trend = "BULLISH"
        elif current_price < ema_50:
            trend = "BEARISH"
        
        technical_cache[symbol] = {
            "rsi": rsi,
            "ema": ema_50,
            "trend": trend,
            "updated": datetime.now()
        }

        # --- NEW: EXECUTE 50+ STRATEGY ENGINE SIGNALS ---
        # Only check if we successfully updated state
        strategy_signal = strategy_manager.generate_signal(symbol)
        
        if strategy_signal:
             # STORE IN CACHE FOR GUARDIAN (EXIT LOGIC)
             latest_strategy_signals[symbol] = {
                 "signal": strategy_signal['signal'],
                 "confidence": strategy_signal.get('confidence', 0.5),
                 "reason": strategy_signal.get('reason', 'Unknown'),
                 "time": datetime.now().timestamp()
             }
             
             # Check if we already have a position for this symbol
             has_pos = any(p['symbol'] == symbol for p in mt5_state.get('positions', []))
             
             if not has_pos and auto_trade_state["running"]: # Only open if no position & Auto-Trade ON
                  
                  signal_type = strategy_signal['signal']
                  reason = f"{strategy_signal['strategy']}: {strategy_signal['reason']}"
                  confidence = strategy_signal.get('confidence', 0.5)
                  
                  await broadcast_log(f"🧠 AI STRATEGY SIGNAL: {signal_type} on {symbol} | {reason} (Conf: {confidence})")
                  
                  # FIX #7: Dynamic Volume Calculation based on account balance and risk %
                  risk_pct = risk_settings.get("risk_per_trade_pct", 1.0)  # Default 1% risk
                  account_balance = mt5_state.get("balance", 10000.0)
                  risk_amount = account_balance * (risk_pct / 100.0)
                  # Approximate: risk_amount / (contract_size * SL_distance)
                  # Simplified: use balance-proportional sizing with floor/ceiling
                  volume = round(max(0.01, min(risk_amount / 500.0, 0.50)), 2)
                  
                  # Execute
                  await place_market_order(symbol, signal_type, volume, strategy_tag=strategy_signal['strategy'])

        
    except Exception as e:
        print(f"ERROR: Symbol {symbol} analysis failed: {e}")


async def update_technical_indicators():
    """Background loop to calculate RSI & Trend for active symbols (OPTIMIZED)"""
    print("INFO: Market Analyzer (Technical) Started.")
    last_h1_update = datetime.now()
    last_heartbeat = datetime.now()
    
    while True:
        # ADAPTIVE SLEEP (Phase 3 Optimization)
        if not mt5_state["connected"] or not auto_trade_state["running"]:
            await asyncio.sleep(60)  # Market closed/disconnected: slow poll
            continue

        # Check for H1 Update Cycle
        do_h1_update = (datetime.now() - last_h1_update).total_seconds() > 60
        if do_h1_update:
            last_h1_update = datetime.now()
            
        try:
            # Get list of symbols we care about
            symbols = list(set([p['symbol'] for p in mt5_state.get('positions', [])] + 
                             ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US30", "BTCUSD"]))
            
            # PARALLEL PROCESSING (Phase 3 Optimization)
            tasks = [process_symbol_technical(symbol, do_h1_update) for symbol in symbols]
            await asyncio.gather(*tasks, return_exceptions=True)
            # Verbose Log (Heartbeat - Every 60s)
            if (datetime.now() - last_heartbeat).total_seconds() > 60:
                count = len(technical_cache)
                if count > 0:
                    await broadcast_log(f"INFO: Technical Analysis Updated for {count} symbols (Parallel Mode).")
                last_heartbeat = datetime.now()
                await asyncio.sleep(1.0)  # Prevent duplicate logs
                
        except Exception as e:
            print(f"ERROR: Analysis Loop Failed: {e}")
        
        # ADAPTIVE SLEEP INTERVAL (Phase 3 Optimization)
        # Check volatility proxy (using cached ATR if available)
        atr = mt5_state.get("latest_atr", 0.0005)
        
        if atr > 0.0010:  # High volatility
            sleep_time = 2.0
        else:  # Normal/Low volatility
            sleep_time = 5.0
            
        await asyncio.sleep(sleep_time)


# Helper: Kill MT5 Process
def kill_mt5_process():
    """Forcefully kills the MT5 terminal process to ensure a clean restart."""
    try:
        # Windows command to kill terminal64.exe
        subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe"], capture_output=True, check=False)
        subprocess.run(["taskkill", "/F", "/IM", "terminal.exe"], capture_output=True, check=False)
    except Exception as e:
        print(f"Error killing MT5: {e}")

def discover_mt5_path():
    """Scans Registry and common locations for terminal64.exe."""
    
    # 0. Check User Settings Override
    # (Future: Load from settings.json if exists)

    # 1. Check Windows Registry (Most Reliable)
    print("INFO: Checking Registry for MT5...")
    try:
        # Common keys for MetaQuotes
        keys = [
            r"Software\MetaQuotes\MetaTrader 5",
            r"Software\MetaQuotes\Terminal"
        ]
        
        for key_path in keys:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                    # Look for Install Location
                    path, _ = winreg.QueryValueEx(key, "InstallLocation")
                    candidate = os.path.join(path, "terminal64.exe")
                    if os.path.exists(candidate):
                        print(f"INFO: Found MT5 in Registry: {candidate}")
                        return candidate
            except: pass
    except Exception as e:
        print(f"Registry Scan Error: {e}")

    possible_roots = [
        os.environ.get("ProgramFiles", "C:\\Program Files"),
        os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")
    ]
    
    # 2. Check Standard Metatrader Folder
    for root in possible_roots:
        check_path = os.path.join(root, "MetaTrader 5", "terminal64.exe")
        if os.path.exists(check_path):
            return check_path
            
    # 3. Recursive Scan for Broker-Specific Folders
    # Limiting depth to avoid slow scan
    print("INFO: Scanning Program Files for MT5 (Deep Scan)...")
    for root in possible_roots:
        if os.path.exists(root):
            try:
                # List directories only
                dirs = [d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))]
                for d in dirs:
                    # Filter keywords
                    if any(x in d for x in ["MetaTrader", "MT5", "Forex", "Market", "Global", "Trade"]):
                        candidate = os.path.join(root, d, "terminal64.exe")
                        if os.path.exists(candidate):
                            print(f"INFO: Found MT5 Candidate: {candidate}")
                            return candidate
            except: pass
            
    return None

def _connect_mt5_logic(force=False, loop=None):
    """Synchronous blocking logic for MT5 connection."""
    if not HAS_MT5: return {"error": "MT5 Module Missing"}
    
    # Smart Connect: Check if already fine (ONLY if not forcing)
    if not force:
        if mt5.initialize():
            term_info = mt5.terminal_info()
            if term_info and term_info.connected:
                 if loop: asyncio.run_coroutine_threadsafe(broadcast_log("INFO: Smart Connect: Already connected to MT5."), loop)
                 return {"status": "CONNECTED_EXISTING"}
            else:
                 mt5.shutdown()
        else:
             mt5.shutdown()
    else:
        if loop: asyncio.run_coroutine_threadsafe(broadcast_log("INFO: Manual Reconnect -> Forcing Shutdown of existing instances..."), loop)
        try:
            mt5.shutdown()
        except: pass
        kill_mt5_process()
        time.sleep(1)

    # DISCOVERY PHASE
    exe_path = discover_mt5_path()
    
    if not exe_path:
        # Fallback to hardcoded default just in case
        exe_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    
    if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"INFO: Target MT5 Path: {exe_path}"), loop)

    if not os.path.exists(exe_path):
         err = f"ERROR: MT5 executable not found at {exe_path}"
         if loop: asyncio.run_coroutine_threadsafe(broadcast_log(err), loop)
         return {"error": "MT5 executable not found"}

    # FORCE LAUNCH SEQUENCE (NATIVE)
    if force or not mt5.initialize(path=exe_path):
        if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"INFO: Launching MT5 Native: {exe_path}"), loop)
        
        try:
            # Native Run (Like Double Click)
            # This is non-blocking on Windows
            os.startfile(exe_path)
            
            # warm up
            time.sleep(15) 
            
            # Connect explicitly to this path
            if mt5.initialize(path=exe_path):
                 if loop: asyncio.run_coroutine_threadsafe(broadcast_log("SUCCESS: Connected after Native Launch."), loop)
                 return {"status": "CONNECTED_FORCE"}
            else:
                 raise Exception(f"Failed to attach after launch: {mt5.last_error()}")
                 
        except OSError as e:
            if e.winerror == 14001:
                err_msg = "CRITICAL: Side-by-Side Configuration Error (WinError 14001). Please run 'spidy/Trading_Backend/setup/fix_vc_redist.ps1' to fix missing C++ libraries."
                if loop: asyncio.run_coroutine_threadsafe(broadcast_log(err_msg), loop)
                print(err_msg)
                return {"error": "Missing VC++ Redistributable. Run fix_vc_redist.ps1"}
            
            if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"ERROR: Launch failed: {e}"), loop)
            return {"error": str(e)}
        except Exception as e:
            if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"ERROR: Launch failed: {e}"), loop)
            return {"error": str(e)}

    return {"status": "CONNECTED"}

@app.post("/connect")
async def connect_mt5_endpoint():
    """Manual Reconnect Trigger - Forces Restart."""
    return await connect_mt5(force=True)

async def connect_mt5(force=False):
    """Async Wrapper for Connection Logic."""
    if not HAS_MT5: return {"status": "ERROR", "detail": "No MT5 Lib"}
    
    if force:
        await broadcast_log("COMMAND: Force Reconnect Requested (Restarting MT5)...")
    else:
        await broadcast_log("INFO: Checking MT5 Connection...")
    
    loop = asyncio.get_running_loop()
    # Run blocking logic in thread
    res = await loop.run_in_executor(None, lambda: _connect_mt5_logic(force=force, loop=loop))
    
    if "error" in res:
        await broadcast_log(f"ERROR: Connect Failed: {res['error']}")
        # DO NOT RETURN ERROR OBJECT - Just stay disconnected but alive
        return res
        
    mt5_state["connected"] = True
    await broadcast_log(f"SUCCESS: MT5 Connected ({res.get('status', 'OK')})")
    
    # FIX #2: All code below was DEAD (unreachable after return). Now executes on successful connect.
    
    # CALCULATE TIME OFFSET (Dynamic)
    try:
         # Use EURUSD as proxy for server time
         eurusd_selected = await safe_mt5_call(mt5.symbol_select, "EURUSD", True)
         if eurusd_selected:
             tick = await safe_mt5_call(mt5.symbol_info_tick, "EURUSD")
             if tick:
                  server_ts = tick.time
                  local_ts = datetime.now().timestamp()
                  diff = server_ts - local_ts
                  mt5_state["time_offset"] = diff
                  await broadcast_log(f"INFO: Time Offset Calculated: {diff:.2f}s (Server ahead of Local)")
             else:
                  mt5_state["time_offset"] = 7200 # Fallback
         else:
             mt5_state["time_offset"] = 7200 # Fallback
    except Exception as e:
         print(f"Time Offset Error: {e}")
         mt5_state["time_offset"] = 7200

    # Trigger state update immediately
    try:
        account_info = await safe_mt5_call(mt5.account_info)
        if account_info:
            mt5_state["equity"] = account_info.equity
            mt5_state["balance"] = round(account_info.balance, 2)
            mt5_state["profit"] = round(account_info.profit, 2)
            
            # Fetch Open Positions
            positions = await safe_mt5_call(mt5.positions_get)
            mt5_state["positions"] = []

            # FIRE OFF DEEP SYNC (Background)
            asyncio.get_running_loop().call_later(2.0, lambda: asyncio.create_task(run_deep_history_sync(days=3)))
            
            time_offset = mt5_state.get("time_offset", 7200)
            
            if positions:
                for pos in positions:
                    local_ts = pos.time - time_offset
                    
                    # Calculate standardized ROI for frontend
                    comm = getattr(pos, 'commission', 0.0)
                    swap = getattr(pos, 'swap', 0.0)
                    net_profit_roi = pos.profit + comm + swap
                    margin = (pos.volume if getattr(pos, 'volume', 0) > 0 else 0.01) * 200.0
                    roi = (net_profit_roi / margin) * 100.0 if margin > 0 else 0.0
                    
                    mt5_state["positions"].append({
                        "ticket": pos.ticket,
                        "symbol": pos.symbol,
                        "type": "BUY" if pos.type == 0 else "SELL",
                        "volume": pos.volume,
                        "price": pos.price_open,
                        "profit": pos.profit,
                        "roi": roi,
                        "time": str(datetime.fromtimestamp(local_ts))
                    })
            
            # 4. Check Margin Mode (Netting vs Hedging)
            mode = "UNKNOWN"
            if account_info.margin_mode == mt5.ACCOUNT_MARGIN_MODE_RETAIL_NETTING: mode = "NETTING"
            elif account_info.margin_mode == mt5.ACCOUNT_MARGIN_MODE_EXCHANGE: mode = "EXCHANGE"
            elif account_info.margin_mode == mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING: mode = "HEDGING"
                
            # Log Sanitization: Mask Account Number
            safe_login = str(account_info.login)
            if len(safe_login) > 4:
                safe_login = "*" * (len(safe_login) - 4) + safe_login[-4:]
            else:
                safe_login = "****"
                
            print(f"INFO: MT5 Connected. Account: {safe_login} ({mode}, {account_info.currency}) Balance: {account_info.balance}")
            await broadcast_log(f"INFO: MT5 Connected. Account: {safe_login} ({mode})")
        else:
            await broadcast_log("INFO: MT5 Connected (No account info)")
    except Exception as e:
        print(f"Post-connect state update error: {e}")
    
    return res




# Helper: Check Market Status
def is_market_open():
    """Checks if market is open and trading is allowed."""
    # FIX #12: Use UTC to avoid local timezone issues on non-UTC systems
    # 1. Check Weekend (Saturday=5, Sunday=6)
    # Note: Market usually closes Friday 5PM EST and opens Sunday 5PM EST.
    now = datetime.utcnow()
    if now.weekday() >= 5: 
        mt5_state["market_status"] = "CLOSED_WEEKEND"
        return False

    # Rollover Check (Daily 17:00 - 18:00)
    # Standard NY Rollover time where spreads are high and market is effectively closed.
    if now.hour == 17:
         mt5_state["market_status"] = "CLOSED_ROLLOVER"
         return False
        
    # 2. Check Connection
    if not HAS_MT5 or not mt5_state["connected"]:
         mt5_state["market_status"] = "DISCONNECTED"
         return False

    # 3. Check Terminal Status (Algo Enabled)
    try:
        term_info = mt5.terminal_info()
        if not term_info.trade_allowed:
             mt5_state["market_status"] = "ALGO_DISABLED"
             return False
    except:
        pass
        
    # 4. Check Connection to Trade Server
    # if not mt5.terminal_info().connected: ... (Already handled by bridge connect loop mostly)

    mt5_state["market_status"] = "OPEN"
    return True

# Helper: Strict Pre-Trade Validation (Millisecond Optimized)
def validate_entry(symbol, signal, tick, strategy_tag="General"):
    """
    Performs ALL checks before a trade. Returns (bool, reason).
    Checks: Market Open, Fresh Data, Spread, Account Health, Sentiment, Shield.
    """
    # 1. Market Open
    if mt5_state.get("market_status") != "OPEN":
        # Double check independent source just in case state is stale
        if not is_market_open():
             return False, f"Market Closed ({mt5_state.get('market_status')})"

    # 1.5 KILL SWITCH (Max Daily Loss)
    # Check updated Daily PnL from background sync
    daily_pnl = mt5_state.get("daily_pnl", 0.0)
    max_loss = risk_settings.get("max_daily_loss", 100.0)
    # If PnL is negative and exceeds max loss (e.g. -150 < -100)
    if daily_pnl < (-1 * abs(max_loss)):
         return False, f"KILL SWITCH ACTIVE: Daily Loss {daily_pnl:.2f} exceeds Limit {max_loss}"

    # 2. Connection
    if not HAS_MT5 or not mt5_state["connected"]:
        return False, "MT5 Disconnected"

    # 3. Data Freshness (< 5s)
    # FIX #8: Account for time_offset between server and local clock.
    # tick.time is in server epoch seconds; we convert to local epoch for comparison.
    time_offset = mt5_state.get("time_offset", 0)
    server_time_as_local = tick.time - time_offset  # Convert server time to local epoch
    local_time = datetime.now().timestamp()
    data_age = abs(local_time - server_time_as_local)
    if data_age > 5.0:
        return False, f"Stale Data (Lag: {data_age:.2f}s)"

    # 3.5. SYMBOL PERMISSIONS (Fix for 10017)
    # We need to fetch symbol info to check trade mode
    # Optimization: This adds an API call, but prevents failed orders.
    sym_info = mt5.symbol_info(symbol)
    if not sym_info:
        return False, "Symbol Info Not Found"
        
    # Check Trade Mode
    # 0=Disabled, 1=LongOnly, 2=ShortOnly, 3=CloseOnly, 4=Full
    # We want Full(4) or Partial if direction matches
    if sym_info.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
        return False, "Trade Mode DISABLED"
    if sym_info.trade_mode == mt5.SYMBOL_TRADE_MODE_CLOSEONLY:
        return False, "Trade Mode CLOSE ONLY"
    
    if signal == "BUY" and sym_info.trade_mode == mt5.SYMBOL_TRADE_MODE_SHORTONLY:
         return False, "Trade Mode SHORT ONLY"
    if signal == "SELL" and sym_info.trade_mode == mt5.SYMBOL_TRADE_MODE_LONGONLY:
         return False, "Trade Mode LONG ONLY"

    # 4. TECHNICAL FILTER (Smart HFT)
    # Prevent buying high or selling low
    
    # --- STRATEGY MANAGER CHECK (ADX / VWAP) ---
    current_price = tick.ask if signal == "BUY" else tick.bid
    allowed, reason = strategy_manager.filter_signal(symbol, signal, current_price, strategy_tag)
    if not allowed:
         return False, reason

    # We use risk_settings check if implemented, default True
    if risk_settings.get("use_technical_filters", True) and symbol in technical_cache:
        tech = technical_cache[symbol]
        
        # Age check (don't use stale analysis)
        if (datetime.now() - tech["updated"]).total_seconds() < 10:
            
            # A. GLOBAL SENTIMENT CHECK (News Integration)
            global_sent = mt5_state.get("sentiment", "NEUTRAL")
            if signal == "BUY" and global_sent == "BEARISH":
                return False, f"Against Global Sentiment ({global_sent})"
            if signal == "SELL" and global_sent == "BULLISH":
                return False, f"Against Global Sentiment ({global_sent})"
                
            # B. MOMENTUM CHECK (ADX)
            # Avoid Choppy Markets (running into spread)
            # ADX < 20 usually means range/chop
            if tech.get("adx", 25) < 20:
                 return False, f"Market Choppy (ADX {tech.get('adx', 0):.1f})"

            if signal == "BUY":
                # Don't BUY if RSI is Overbought (>70) or Trend is Bearish (Counter-trend)
                if tech["rsi"] > 70:
                    return False, f"RSI Overbought ({tech['rsi']:.1f})"
                if tech["trend"] == "BEARISH":
                     return False, f"Trend is BEARISH (Price < EMA50)"
            
            elif signal == "SELL":
                # Don't SELL if RSI is Oversold (<30) or Trend is Bullish
                if tech["rsi"] < 30:
                    return False, f"RSI Oversold ({tech['rsi']:.1f})"
                if tech["trend"] == "BULLISH":
                     return False, f"Trend is BULLISH (Price > EMA50)"
    elif not risk_settings.get("use_technical_filters", True):
        # FIX #9: Even with filters disabled, enforce minimum safety checks
        # Global sentiment still applies as a baseline guardrail
        global_sent = mt5_state.get("sentiment", "NEUTRAL")
        if signal == "BUY" and global_sent == "BEARISH":
            return False, f"Against Global Sentiment ({global_sent}) [Filters OFF]"
        if signal == "SELL" and global_sent == "BULLISH":
            return False, f"Against Global Sentiment ({global_sent}) [Filters OFF]"
    
    # 5. Spread Check
    if tick.ask > 0:
        spread = tick.ask - tick.bid
        profit_points = spread / tick.ask
        # Tightened from 0.0005 (0.05%) to 0.0003 (0.03%)
        # EURUSD: 0.03% = ~3 pips. US30: 0.03% = ~10 pts.
        if profit_points > 0.0003: 
            return False, f"Spread too high ({profit_points:.5f}) - Limit 0.0003"
            
    # 5. Account Health (Free Margin)
    # We rely on cached state first for speed, update if critical
    # Actually, verify_guardian runs frequently, checking account_info here adds overhead.
    # We will assume if "margin_level" < 100 we stop.
    # Let's skip heavy API call and trust internal state safeguards or just check minimal
    # account = mt5.account_info() # Adds ~1ms. Acceptable.
    # if account and account.margin_free < 100: return False, "Low Margin"

    # 6. Global Sentiment & Shield (Logic extracted from HFT loop)
    # This acts as the final "Gatekeeper"
    global_bias = auto_trade_state.get("sentiment", "NEUTRAL")
    
    if global_bias == "BULLISH" and signal == "SELL":
        return False, "Sentiment Mismatch (Global is BULLISH)"
    if global_bias == "BEARISH" and signal == "BUY":
        return False, "Sentiment Mismatch (Global is BEARISH)"

    # Shield (DXY)
    dxy_info = auto_trade_state.get("dxy", {})
    dxy_status = dxy_info.get("status", "NEUTRAL")
    
    if symbol.endswith("USD"):
        if signal == "BUY" and dxy_status == "BULLISH": return False, "Shield Block (DXY Bullish)"
        if signal == "SELL" and dxy_status == "BEARISH": return False, "Shield Block (DXY Bearish)"
    elif symbol.startswith("USD") and "USDT" not in symbol:
        if signal == "BUY" and dxy_status == "BEARISH": return False, "Shield Block (DXY Bearish)"
        if signal == "SELL" and dxy_status == "BULLISH": return False, "Shield Block (DXY Bullish)"

    # 7. Economic Calendar Check (Hard Block on HIGH-impact events within 5 min)
    # Also checks the local economic_calendar module
    is_event_local, event_msg_local = calendar.is_event_nearby(symbol)
    if is_event_local and "Upcoming" in str(event_msg_local):
        return False, f"Calendar Shield: {event_msg_local}"

    # 7b. Market Intelligence Calendar (ForexFactory via internet)
    if HAS_MARKET_INTEL:
        try:
            near_event, near_event_name = is_near_high_impact_event(symbol, buffer_minutes=5)
            if near_event:
                return False, f"HIGH-IMPACT EVENT in <5min: {near_event_name[:60]}"
        except Exception:
            pass  # Don't let calendar check break trading

    return True, "OK"


# Helper: Internal Trade Execution

async def place_market_order(symbol: str, action: str, volume: float = 0.01, strategy_tag="Manual"):
    """Executes a market order internally."""
    action = action.upper()
    symbol = symbol.upper()
    
    if not mt5_state["connected"]:
        await broadcast_log("ERROR: Auto-Trade failed. MT5 not connected.")
        return False

    # Safety: Market Closed Check
    if not is_market_open():
         await broadcast_log(f"ERROR: Market Closed ({mt5_state.get('market_status')}). Trade {symbol} Rejected.")
         return False

    if not HAS_MT5:
        await broadcast_log(f"ERROR: Cannot trade. MT5 library missing.")
        return False

    # 1. Symbol Select (Async Wrap)
    is_selected = await safe_mt5_call(mt5.symbol_select, symbol, True)
    if not is_selected:
        await broadcast_log(f"ERROR: Symbol {symbol} not found")
        return False

    # 2. Price & Type (Async Wrap)
    symbol_info = await safe_mt5_call(mt5.symbol_info, symbol)
    if not symbol_info:
        await broadcast_log(f"ERROR: No info for {symbol}")
        return False

    # 2.4 Safety Cap for Metals (XAU/XAG) - FIX VERY LOSS
    # 2.4 Safety Cap for Metals (XAU/XAG) - FIX VERY LOSS
    if "XAU" in symbol or "XAG" in symbol:
        safe_max = 0.01
        if volume > safe_max:
             await broadcast_log(f"WARNING: Safety Cap Enforced: Reduced {symbol} volume from {volume} to {safe_max}")
             volume = safe_max
    else:
        # General Cap for Majors
        safe_max = 5.0 
        if volume > safe_max:
             await broadcast_log(f"WARNING: Safety Cap Enforced: Reduced {symbol} volume from {volume} to {safe_max}")
             volume = safe_max

    # 2.5 Volume Correction (Fix for 10014)
    if volume < symbol_info.volume_min:
        await broadcast_log(f"WARNING: Volume {volume} too small for {symbol}. Adjusting to {symbol_info.volume_min}")
        volume = symbol_info.volume_min
    
    if action == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = symbol_info.ask
    else:
        order_type = mt5.ORDER_TYPE_SELL
        price = symbol_info.bid

    # 3. Request
    point = symbol_info.point
    
    # --- FIX #1: EMERGENCY BACKSTOP STOP LOSS ---
    # Guardian handles normal exits, but we add a wide emergency SL
    # as a safety net in case Guardian/Watchdog crashes or restarts.
    # This prevents infinite drawdown from a single network hiccup.
    emergency_sl_points = 500  # Default: 500 points for forex (~50 pips)
    if "XAU" in symbol or "XAG" in symbol:
        emergency_sl_points = 5000  # Metals: wider due to volatility
    elif any(idx in symbol for idx in ["US30", "SP500", "NAS100", "GER30", "UK100"]):
        emergency_sl_points = 5000  # Indices: wider
    elif "BTC" in symbol or "ETH" in symbol or "LTC" in symbol or "XRP" in symbol:
        emergency_sl_points = 10000  # Crypto: very wide
    
    emergency_sl_dist = emergency_sl_points * point
    
    if action == "BUY":
        initial_sl = round(price - emergency_sl_dist, symbol_info.digits)
    else:
        initial_sl = round(price + emergency_sl_dist, symbol_info.digits)
    
    await broadcast_log(f"DEBUG RISK: {symbol} Vol:{volume} | Emergency SL: {initial_sl} ({emergency_sl_points}pts from entry)")
         
    # TP can be standard or Risk based (1:1 minimum)
    tp_dist = 500 * point # Standard Target

    # FIX 6: Actually use the tp_dist that was calculated above
    if action == "BUY":
        initial_tp = round(price + tp_dist, symbol_info.digits)
    else:
        initial_tp = round(price - tp_dist, symbol_info.digits)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": initial_sl,
        "tp": initial_tp,
        "deviation": 20,
        "magic": 234000,
        "comment": "Spidy AI SMA",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": get_filling_mode(symbol), 
    }

    # 4. Send (Sync - Direct Main Thread to avoid context loss)
    await broadcast_log(f"DEBUG: Sending Order (MainThread): action={action} vol={volume} price={price}")
    # Direct call to ensure MT5 context is valid
    try:
        result = mt5.order_send(request)
    except Exception as e:
        await broadcast_log(f"CRITICAL: order_send Exception: {e}")
        return False
    
    if not result or result.retcode != mt5.TRADE_RETCODE_DONE:
        err_code = result.retcode if result else "Unknown"
        err_comm = result.comment if result else "No Result"
        await broadcast_log(f"ERROR: Auto-Trade Order Failed: {err_comm} ({err_code})")
        return False
    
    await broadcast_log(f"SUCCESS: Auto-Trade {action} Filled @ {price}")
    
    # Save to DB
    trade_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # DB Save is synchronous but fast (sqlite). Can wrap if needed, but usually OK.
    current_sentiment = auto_trade_state.get("sentiment", "NEUTRAL")
    financial_db.save_trade(result.order, symbol, action, volume, price, trade_time, strategy=strategy_tag, sentiment=current_sentiment)
    
    return True

@app.post("/trade")
async def execute_trade(signal: dict = Body(...), api_key: str = Depends(verify_api_key)):
    # FIX #6: Input validation on trade API
    if not mt5_state["connected"]:
        await broadcast_log("ERROR: Trade failed. MT5 not connected.")
        return {"error": "MT5 not connected"}
    
    action = signal.get('action', '').upper()
    symbol = signal.get('symbol', '').upper()
    volume = 0.01
    try:
        volume = float(signal.get('volume', 0.01))
    except (ValueError, TypeError):
        return {"error": "Invalid volume value"}
    
    # Validate action is BUY or SELL only
    if action not in ("BUY", "SELL"):
        await broadcast_log(f"ERROR: Invalid trade action '{action}'. Must be BUY or SELL.")
        return {"error": f"Invalid action: {action}. Must be BUY or SELL."}
    
    # Validate symbol format (alphanumeric, 3-10 chars)
    import re
    if not re.match(r'^[A-Z0-9._]{2,15}$', symbol):
        return {"error": f"Invalid symbol format: {symbol}"}
    
    # Validate volume bounds (reasonable limits)
    if volume < 0.01 or volume > 5.0:
        await broadcast_log(f"ERROR: Volume {volume} out of bounds (0.01 - 5.0)")
        return {"error": f"Volume {volume} out of safe range (0.01 - 5.0)"}
    
    log_msg = f"TRADE: Received Manual {action} on {symbol} (Vol: {volume})"
    print(log_msg)
    await broadcast_log(log_msg)
    
    success = await place_market_order(symbol, action, volume, strategy_tag="Manual_API")
    if success:
        return {"status": "FILLED"}
    else:
        return {"status": "FAILED"}


# Helper: Internal Close Position (Sync)
def _close_position_sync(ticket: int, symbol: str, reason: str = "Manual", require_profit: bool = False):
    """Synchronous blocking function to close a position."""
    
    # 1. Concurrency Check
    with ticket_lock:
        if ticket in processing_tickets:
             return False, "BUSY_PROCESSING", 0.0, 0.0
        processing_tickets.add(ticket)
    
    try:
        if not mt5_state["connected"] or not HAS_MT5:
            return False, "MT5_NOT_CONNECTED", 0.0, 0.0

        # Check if position exists
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return False, "NOT_FOUND", 0.0, 0.0
        
        pos = positions[0]

        # --- FAILSAFE CHECK: Require Profit ---
        if require_profit:
             # Safe attribute access
             swap = getattr(pos, 'swap', 0.0)
             commission = getattr(pos, 'commission', 0.0)
             profit = getattr(pos, 'profit', 0.0)
             
             net_profit = profit + swap + commission
             if net_profit < 0:
                  return False, f"FAILSAFE_ABORT: Net Profit {net_profit:.2f} < 0", 0.0, 0.0
        # Ensure symbol is selected to get fresh prices
        if not mt5.symbol_select(symbol, True):
             return False, f"SYMBOL_SELECT_FAILED ({symbol})", 0.0, 0.0

        # Get fresh tick data
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
             return False, f"NO_TICK_DATA ({symbol})", 0.0, 0.0
        
        # Close means opening an opposing order
        action = mt5.TRADE_ACTION_DEAL
        type_op = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        
        # Use explicit tick prices to ensure valid fill
        price = tick.bid if type_op == mt5.ORDER_TYPE_SELL else tick.ask
        
        request = {
            "action": action,
            "symbol": symbol,
            "volume": pos.volume,
            "type": type_op,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": f"Spidy: {reason}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": get_filling_mode(symbol),
        }
        
        result = mt5.order_send(request)
        # FIX 7: Guard against None result before accessing .retcode
        if not result or result.retcode != mt5.TRADE_RETCODE_DONE:
            err_code = result.retcode if result else "NO_RESULT"
            err_msg = result.comment if result else "order_send returned None"
            return False, f"{err_msg} ({err_code})", 0.0, 0.0
            
        # --- PROFIT ESTIMATION FIX ---
        # Calculate instant profit for UI feedback
        estimated_profit = 0.0
        try:
             # FIX: Use built-in calc function to handle Currency Conversion (e.g. JPY -> USD)
             # Manual math returns Quote Currency (e.g. 100 JPY), but we want Account Currency ($0.60)
             calc_type = mt5.ORDER_TYPE_BUY if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_SELL
             estimated_profit = mt5.order_calc_profit(calc_type, symbol, pos.volume, pos.price_open, price)
        except Exception as e:
             # print(f"Profit Calc Error: {e}")
             estimated_profit = 0.0
             
        return True, "CLOSED", price, estimated_profit
        
    except Exception as e:
        print(f"CRITICAL: Close Logic Exception: {e}")
        return False, f"EXCEPTION: {e}", 0.0, 0.0
        
    finally:
        # Always release the ticket
        with ticket_lock:
             processing_tickets.discard(ticket)


async def close_position(ticket: int, symbol: str, reason: str = "Manual", require_profit: bool = False):
    """Async wrapper for closing position."""
    loop = asyncio.get_running_loop()
    
    # Run blocking call in thread
    success, msg, price, est_profit = await loop.run_in_executor(None, _close_position_sync, ticket, symbol, reason, require_profit)
    
    if success:
        if msg == "MOCK_CLOSE":
             await broadcast_log(f"MOCK: Closed position {ticket}")
        else:
             await broadcast_log(f"SUCCESS: Closed {symbol} ({ticket}) @ {price} [{reason}]")
             # Update DB with Estimated Profit
             close_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
             financial_db.update_trade_close(ticket, price, est_profit, close_time, exit_reason=reason)
    else:
        if msg == "BUSY_PROCESSING":
             # Optional: Don't spam log for busy
             pass
        elif msg == "NOT_FOUND":
             await broadcast_log(f"WARN: Position {ticket} not found (likely closed by SL/TP/User).")
        elif "No prices" in msg:
             # Downgrade "No prices" to WARN as well, as it's transient
             await broadcast_log(f"WARN: Close Failed: {msg}")
        else:
             await broadcast_log(f"ERROR: Close Failed: {msg}")

             
    return success


@app.post("/close_trade")
async def close_single_trade(payload: dict = Body(...), api_key: str = Depends(verify_api_key)):
    """API Endpoint to close a trade."""
    ticket = int(payload.get("ticket"))
    symbol = payload.get("symbol")
    
    if not ticket or not symbol:
        return {"error": "Missing ticket or symbol"}
        
    success = await close_position(ticket, symbol, reason="User (API)")
    if success:
        return {"status": "CLOSED", "ticket": ticket}
    else:
        return {"status": "FAILED", "ticket": ticket}

async def _process_close_all_background(profitable_only: bool, threshold: float = 0.05):
    """Background task to close positions."""
    await broadcast_log(f"COMMAND: Starting Close All (Profitable Only: {profitable_only}, Threshold: ${threshold})...")
    
    # FIX 3: was "and" — now correctly "or" so it catches both no-MT5 and disconnected
    if not mt5_state["connected"] or not HAS_MT5:
         await broadcast_log("ERROR: MT5 Not Connected")
         return 

    closed_count = 0
    # 1. Get Current positions
    if HAS_MT5:
        # Offload positions_get to thread
        loop = asyncio.get_running_loop()
        positions = await loop.run_in_executor(None, mt5.positions_get)
        
        await broadcast_log(f"DEBUG: Close All found {len(positions) if positions else 0} positions.")

        if positions:
            for pos in positions:
                try:
                    should_close = True
                    
                    # Filter by Profit
                    # FIX: Calculate Net Profit (Inc. Swap/Comm) to avoid losing money
                    # Use getattr to prevent AttributeError if broker doesn't provide swap/commission
                    swap = getattr(pos, 'swap', 0.0)
                    commission = getattr(pos, 'commission', 0.0)
                    profit = getattr(pos, 'profit', 0.0)
                    
                    net_profit = profit + swap + commission
                    
                    await broadcast_log(f"DEBUG: Ticket {pos.ticket} | Profit: {profit} | Net: {net_profit:.2f} | Threshold: {threshold}")

                    if profitable_only:
                        # User Threshold Logic:
                        # If Threshold is 0.0, we close anything > 0.0
                        # If Threshold > 0.0, we close anything > Threshold
                        if net_profit <= threshold: 
                            await broadcast_log(f"SKIPING: Ticket {pos.ticket} (Net Profit: {net_profit:.2f} <= Threshold {threshold})")
                            should_close = False
                        else:
                            await broadcast_log(f"TARGET: Ticket {pos.ticket} (Net Profit: {net_profit:.2f} > Threshold {threshold})")
                    
                    if should_close:
                        await broadcast_log(f"CLOSING: Ticket {pos.ticket} (Profit: {profit}, Net: {net_profit:.2f})")
                        if await close_position(pos.ticket, pos.symbol, reason="Secure Now", require_profit=profitable_only):
                            closed_count += 1
                            # Small delay to prevent flooding
                            await asyncio.sleep(0.1)
                except Exception as e:
                    await broadcast_log(f"ERROR: Processing Ticket {pos.ticket} Failed: {e}")
                    continue

        else:
            await broadcast_log("INFO: No open positions found to close.")
    else:
        await broadcast_log("ERROR: Cannot Close All. MT5 not connected.")

        
    await broadcast_log(f"COMMAND: Close All Completed. Total Closed: {closed_count}")

@app.post("/close_all_trades")
async def close_all_trades_api(payload: dict = Body(...), background_tasks: BackgroundTasks = BackgroundTasks(), api_key: str = Depends(verify_api_key)):
    """
    Closes all trades match criteria (Background Task).
    payload: { "profitable_only": bool, "threshold": float }
    """
    profitable_only = payload.get("profitable_only", False)
    threshold = float(payload.get("threshold", 0.05))
    
    # Start in background
    background_tasks.add_task(_process_close_all_background, profitable_only, threshold)
    
    return {"status": "ACCEPTED", "message": f"Close All started in background (Threshold: {threshold})."}


async def enforce_sentiment_bias(sentiment):
    """
    Closes existing positions that contradict the new global sentiment.
    Example: If Sentiment -> BEARISH, Close all BUYS.
    """

    # FIX 4: Don't call mt5.initialize() here — it can relaunch the terminal unexpectedly.
    # Use the shared state flag like the rest of the codebase.
    if not HAS_MT5 or not mt5_state["connected"]: return
    if not is_market_open(): return # Safety Check

    await broadcast_log(f"🛡️ DEFENSE: Enforcing Sentiment Bias: {sentiment}")
    
    # FIX #5: Use safe_mt5_call instead of blocking mt5.positions_get() in async context
    positions = await safe_mt5_call(mt5.positions_get)
    if not positions: return
    
    closed_count = 0
    
    for pos in positions:
        should_close = False
        reason = ""
        
        # Logic:
        # BULLISH -> Close SELLS
        # BEARISH -> Close BUYS
        # NEUTRAL -> Do nothing (allow organic exit)
        
        if sentiment == "BULLISH" and pos.type == 1: # 1 is SELL
            should_close = True
            reason = "BULLISH News"
            
        elif sentiment == "BEARISH" and pos.type == 0: # 0 is BUY
            should_close = True
            reason = "BEARISH News"
            
        if should_close:
            # FIX: Only close if we are not in deep loss. 
            # User complained about "Closing in loss".
            # If we are profitable, secure it. 
            # If we are in small noise loss (spread), maybe close.
            # If we are in deep loss, let the SL/Trailing Stop handle it (don't panic close).
            
            # Let's be conservative: Only close if Profit is STRICTLY POSITIVE (covers some swap/comm)
            # User complained about "Closing in loss".
            
            net_profit = pos.profit + pos.swap + pos.commission
            if net_profit > 0.05: # Ensure we actually make money (Buffer 0.05)
                 await broadcast_log(f"⚠️ CLOSING {pos.symbol} (Ticket {pos.ticket}) due to {reason} (Profit: {pos.profit})")
                 await close_position(pos.ticket, pos.symbol, require_profit=True)
                 closed_count += 1
                 await asyncio.sleep(0.1) # Throttle
            else:
                 # Optional: We could tighten SL here instead, but Guardian does that.
                 # Just log for awareness
                 # await broadcast_log(f"🛡️ Holding counter-trend {pos.symbol} (Ticket {pos.ticket}) due to Loss ({pos.profit}). Waiting for SL or Rebound.")
                 pass
            
    if closed_count > 0:
        await broadcast_log(f"🛡️ DEFENSE: Closed {closed_count} counter-trend positions.")





@app.post("/set_sentiment")
async def api_set_sentiment(payload: dict = Body(...), api_key: str = Depends(verify_api_key)):
    """Updates the global market sentiment (driven by AI)."""
    s = payload.get("sentiment", "NEUTRAL").upper()
    auto_trade_state["sentiment"] = s
    await broadcast_log(f"SENTIMENT: Updated Global Sentiment to {s}")
    return {"status": "OK", "sentiment": s}

# Persistence File
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "server_settings.json")

# Default Settings
DEFAULT_SETTINGS = {
    "atr_multiplier": 1.5, # Aggressive Trailing
    "fixed_lot_size": 0.05, # Higher Volume
    "scalp_target_usd": 1.0, # Rapid Scalping Target
    "breakeven_pct": 0.005, # 0.5% profit triggers BE
    "mode": "TIGHT", # Default to TIGHT
    "auto_secure": {
        "enabled": True,
        "threshold": 1.0 # Secure quickly
    },
    "auto_trade_enabled": True, # Force Auto-Mode Default
    "max_daily_loss": 50.0 # WATCHDOG LIMIT
}

def load_settings():
    """Loads settings from file or returns defaults."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved = json.load(f)
                # Merge with defaults to ensure all keys exist (basic migration)
                # For deep merge, we'd need more logic, but this is simple enough for now
                for k, v in DEFAULT_SETTINGS.items():
                    if k not in saved:
                        saved[k] = v
                return saved
        except Exception as e:
            print(f"Error loading settings: {e}")
    return DEFAULT_SETTINGS.copy()

def save_settings():
    """Saves current risk_settings to file."""
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump(risk_settings, f, indent=4)
    except Exception as e:
        return f"Error executing {basename}: {e}"

# NEW Mount Static Files
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Frontend_Dashboard/dashboard_app/out"))
if os.path.exists(FRONTEND_DIR):
    print(f"INFO: Mounting Static Frontend from {FRONTEND_DIR}")
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    print(f"WARN: Frontend build not found at {FRONTEND_DIR}. Run 'npm run build' in Frontend_Dashboard.")

# Initialize Settings
risk_settings = load_settings()

# Sync Auto-Trade State from Persistence
if "auto_trade_enabled" in risk_settings:
    auto_trade_state["running"] = risk_settings["auto_trade_enabled"]
    print(f"INFO: Restored Auto-Trade State: {auto_trade_state['running']}")

async def update_spider_web(symbols, shared_ticks=None):
    """
    STRATEGY 2: THE SPIDER WEB (Dynamic Grid).
    Places Limit Orders based on Volatility.
    Uses shared_ticks (dict of symbol->tick) if provided to save time.
    """
    if not HAS_MT5 or not mt5_state["connected"]: return
    if not is_market_open(): return # Safety Check

    for symbol in symbols:
        # Optimization: Use shared tick if available
        tick = None
        if shared_ticks and symbol in shared_ticks:
            tick = shared_ticks[symbol]
        else:
            tick = mt5.symbol_info_tick(symbol)
            
        if not tick: continue
        
        # Validation
        # checking "BUY_LIMIT" logic means we intend to BUY eventually
        # So we check if "BUY" is allowed by Sentiment/Shield
        valid_buy, reason_buy = validate_entry(symbol, "BUY", tick, "SpiderWeb")
        valid_sell, reason_sell = validate_entry(symbol, "SELL", tick, "SpiderWeb")
        
        # If sentiment is strict, we might only place one side
        allow_buy = valid_buy
        allow_sell = valid_sell
        # 1. Determine Grid Step based on Volatility (ATR)
        # Using default high volatility assumption if ATR missing
        step_pips = 0.00050 # 5 Pips (Standard)
        
        atr = mt5_state.get("latest_atr")
        if atr:
            # If Volatility is High (ATR > 0.0010), Expand Web
            if atr > 0.0010:
                step_pips = 0.0020 # 20 Pips
            elif atr < 0.0002:
                 step_pips = 0.00020 # 2 Pips (Scalp Grid)
        
        # 2. Check Existing Orders
        open_orders = mt5.orders_get(symbol=symbol)
        buy_limits = []
        sell_limits = []
        
        if open_orders:
            for o in open_orders:
                if o.type == mt5.ORDER_TYPE_BUY_LIMIT: buy_limits.append(o)
                if o.type == mt5.ORDER_TYPE_SELL_LIMIT: sell_limits.append(o)
        
        # 3. Maintain 'The Web' (One above, One below closest to price)
        # We simplify to 1 layer for safety in this version.
        
        tick = mt5.symbol_info_tick(symbol)
        if not tick: continue
        
        ask = tick.ask
        bid = tick.bid
        
        target_buy_price = bid - step_pips
        target_sell_price = ask + step_pips
        
        # A. Place BUY LIMIT if missing (Web Floor)
        if not buy_limits and allow_buy:
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": 0.01,
                "type": mt5.ORDER_TYPE_BUY_LIMIT,
                "price": target_buy_price,
                "sl": target_buy_price - (step_pips * 2), # Safety Net
                "tp": target_buy_price + step_pips, # Scalp Target
                "magic": 888888,
                "comment": "Spidy Web Buy",
                "type_time": mt5.ORDER_TIME_DAY,
                "type_filling": get_filling_mode(symbol),  # FIX 8: use broker-correct filling mode
            }
            mt5.order_send(request)
            
        # B. Place SELL LIMIT if missing (Web Ceiling)
        if not sell_limits and allow_sell:
            request = {
                "action": mt5.TRADE_ACTION_PENDING,
                "symbol": symbol,
                "volume": 0.01,
                "type": mt5.ORDER_TYPE_SELL_LIMIT,
                "price": target_sell_price,
                "sl": target_sell_price + (step_pips * 2),
                "tp": target_sell_price - step_pips,
                "magic": 888888,
                "comment": "Spidy Web Sell",
                "type_time": mt5.ORDER_TIME_DAY,
                "type_filling": get_filling_mode(symbol),  # FIX 8: use broker-correct filling mode
            }
            mt5.order_send(request)


def calculate_atr(rates, period=14):
    """Calculates Average True Range (ATR)."""
    if len(rates) < period + 1:
        return None

    tr_list = []
    # rates is list of tuples or dicts with high, low, close
    # Assuming rates is list of dicts from mt5.copy_rates_from_pos
    
    for i in range(1, len(rates)):
        high = rates[i]['high']
        low = rates[i]['low']
        prev_close = rates[i-1]['close']
        
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list.append(tr)
        
    if len(tr_list) < period:
        return None
        
    # Simple SMA of TRs for ATR
    atr = sum(tr_list[-period:]) / period
    return atr

def calculate_sma(prices, period):
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period

def calculate_rsi(prices, period=14):
    """Calculates RSI for a given price list."""
    if len(prices) < period + 1:
        return None
        
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i-1]
        if delta > 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))
            
    # Simple average for first RSI step (approximation for speed)
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
        
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def analyze_trend(closes, period=50):
    """Determines trend based on Price vs SMA."""
    if len(closes) < period:
        return "NEUTRAL"
    
    sma = sum(closes[-period:]) / period
    current_price = closes[-1]
    
    if current_price > sma:
        return "BULLISH"
    elif current_price < sma:
        return "BEARISH"
    else:
        return "NEUTRAL"

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Calculates Bollinger Bands (Upper, Middle, Lower)."""
    if len(prices) < period:
        return None, None, None
        
    # SMA (Middle Band)
    sma = sum(prices[-period:]) / period
    
    # Standard Deviation
    variance = sum([((x - sma) ** 2) for x in prices[-period:]]) / period
    std = variance ** 0.5
    
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    
    return upper, sma, lower

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calculates MACD (Swap-free). Returns macd_line, signal_line, histogram."""
    if len(prices) < slow + signal:
        return None, None, None
        
    # Helper for EMA
    def calculate_ema(data, span):
        alpha = 2 / (span + 1)
        ema = [data[0]]
        for i in range(1, len(data)):
            ema.append(alpha * data[i] + (1 - alpha) * ema[-1])
        return ema
        
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    # MACD Line = Fast - Slow
    # Arrays must be aligned from end.
    # EMA calc mirrors length.
    macd_line = []
    for i in range(len(prices)):
         macd_line.append(ema_fast[i] - ema_slow[i])
         
    # Signal Line = EMA of MACD Line
    signal_line = calculate_ema(macd_line, signal)
    
    # Histogram = MACD - Signal
    histogram = []
    for i in range(len(prices)):
         histogram.append(macd_line[i] - signal_line[i])
         
    return macd_line, signal_line, histogram

def calculate_stochastic(highs, lows, closes, period=14, smooth_k=3, smooth_d=3):
    """Calculates Stochastic Oscillator %K and %D."""
    if len(closes) < period:
        return None, None
        
    k_line = []
    for i in range(len(closes)):
        if i < period - 1:
            k_line.append(50.0) # Middle default
            continue
            
        window_high = max(highs[i-period+1:i+1])
        window_low = min(lows[i-period+1:i+1])
        current_close = closes[i]
        
        if window_high == window_low:
            k = 50.0
        else:
            k = ((current_close - window_low) / (window_high - window_low)) * 100
        k_line.append(k)
        
    # Helper for SMA of list
    def simple_ma(data, p):
        sma = []
        for i in range(len(data)):
             if i < p - 1:
                 sma.append(data[i])
             else:
                 val = sum(data[i-p+1:i+1]) / p
                 sma.append(val)
        return sma
        
    # Smooth K
    k_smooth = simple_ma(k_line, smooth_k)
    # Smooth D (SMA of K)
    d_line = simple_ma(k_smooth, smooth_d)
    
    return k_smooth, d_line

async def sanitize_old_trades():
    """
    On Startup, iterate all open trades.
    FIX #1 UPDATE: Only remove TIGHT stop losses that were set by old pre-update logic.
    Preserve WIDE emergency backstop SLs (>= 200 points from entry).
    """
    # Wait for MT5 connection
    await asyncio.sleep(5) 
    if not HAS_MT5 or not mt5_state["connected"]:
        print("Sanitize Skipped: No Connection")
        return

    print("INFO: Sanitizing Old Trades (Checking Stop Losses)...")
    positions = await safe_mt5_call(mt5.positions_get)
    if positions:
        for pos in positions:
            if pos.sl > 0.0:
                # Calculate distance from entry to SL in points
                sym_info = await safe_mt5_call(mt5.symbol_info, pos.symbol)
                if sym_info:
                    sl_distance = abs(pos.price_open - pos.sl) / sym_info.point
                    # Only remove TIGHT SLs (< 200 points) that were from old logic
                    # Preserve Emergency Backstop SLs (>= 200 points)
                    if sl_distance < 200:
                        print(f"Sanitizing Ticket {pos.ticket} (Removing tight SL {pos.sl}, dist={sl_distance:.0f}pts)...")
                        request = {
                            "action": mt5.TRADE_ACTION_SLTP,
                            "position": pos.ticket,
                            "symbol": pos.symbol,
                            "sl": 0.0,
                            "tp": pos.tp,
                            "magic": 234000
                        }
                        await safe_mt5_call(mt5.order_send, request)
                        await asyncio.sleep(0.1)
                    else:
                        print(f"Keeping emergency SL for Ticket {pos.ticket} (dist={sl_distance:.0f}pts)")
    print("INFO: Sanitize Complete.")

# FIX 2: Removed two duplicate definitions of calculate_bollinger_bands (was defined 3x total)
# The single canonical definition is above at the first occurrence.

# Import News Fetcher + Market Intelligence
import sys
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../AI_Engine/internet_gathering")))
    from news_fetcher import NewsFetcher
    news_engine = NewsFetcher()
    HAS_NEWS = True
except ImportError as e:
    print(f"WARNING: NewsFetcher not found. AI General will be disabled. Error: {e}")
    HAS_NEWS = False
except Exception as e:
    print(f"WARNING: Unexpected error importing NewsFetcher: {e}")
    HAS_NEWS = False

# Import Market Intelligence (Fear & Greed + Economic Calendar)
try:
    from market_intelligence import get_market_pulse, is_near_high_impact_event, get_upcoming_events
    HAS_MARKET_INTEL = True
    print("INFO: Market Intelligence module loaded.")
except ImportError as e:
    print(f"WARNING: market_intelligence not found: {e}")
    HAS_MARKET_INTEL = False
    def get_market_pulse(): return {}
    def is_near_high_impact_event(symbol="", buffer_minutes=5): return False, ""
    def get_upcoming_events(hours_ahead=4): return []

# Import Strategy Optimizer (optional)
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../AI_Engine/strategy_optimizer")))
    from pack_generator import StrategyOptimizer
    strategy_engine = StrategyOptimizer()
except ImportError:
    strategy_engine = None
    print("WARNING: StrategyOptimizer not found.")

# Import Local Brain
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../AI_Engine/brain")))
    from local_brain import LocalBrain
    local_ai = LocalBrain()
    HAS_LOCAL_AI = True
except ImportError:
    print("WARNING: LocalBrain not found. AI Deep Analysis disabled.")
    HAS_LOCAL_AI = False

async def ai_general_loop():
    """
    The General (Master Logic) - Uses REAL Internet Information via NewsFetcher.
    Updates global sentiment based on Yahoo Finance Data + Deep AI Analysis.
    """
    print("INFO: AI General (Real-Time News) Started.")
    
    if not HAS_NEWS:
        await broadcast_log("WARNING: NewsFetcher missing. Defaulting to NEUTRAL mode.")
        return
        
    last_sentiment = "NEUTRAL"
    ai_consecutive_errors = 0

    while True:
        try:
            # 1. Fetch Real News
            headlines = await asyncio.to_thread(news_engine.get_latest_headlines)
            
            # 1b. Fetch GLOBAL SHIELD (DXY)
            dxy_data = await asyncio.to_thread(news_engine.get_dxy_status)
            auto_trade_state["dxy"] = dxy_data
            
            if headlines:
                new_sentiment = "NEUTRAL"
                log_digest = "NEWS UPDATE:\n"
                
                # --- DEEP AI ANALYSIS (All Resources) ---
                # If Local Brain is available, ask IT to decide sentiment
                ai_decision_made = False
                
                if HAS_LOCAL_AI and local_ai.is_available:
                     try:
                         # Construct Prompt
                         # Simplify headlines for the model
                         text_digest = "\n".join([f"- {h['title']}" for h in headlines[:5]])
                         prompt = f"""
                         Analyze these financial news headlines for immediate market sentiment (EURUSD/USD).
                         HEADLINES:
                         {text_digest}
                         
                         INSTRUCTIONS:
                         - Decide if the sentiment is BULLISH, BEARISH, or NEUTRAL for USD.
                         - If USD is Strong -> EURUSD is BEARISH.
                         - If USD is Weak -> EURUSD is BULLISH.
                         - Return ONLY one word: BULLISH, BEARISH, or NEUTRAL.
                         """
                         
                         # Run in thread (Blocking IO)
                         response = await asyncio.to_thread(local_ai.generate_content, prompt)
                         ai_result = response.text.upper().strip()
                         
                         if "BULLISH" in ai_result: new_sentiment = "BULLISH"
                         elif "BEARISH" in ai_result: new_sentiment = "BEARISH"
                         else: new_sentiment = "NEUTRAL"
                         
                         await broadcast_log(f"🧠 AI BRAIN ANALYSIS: {new_sentiment} (Deep Thought)")
                         ai_decision_made = True
                         ai_consecutive_errors = 0
                         
                     except Exception as e:
                         ai_consecutive_errors += 1
                         if ai_consecutive_errors > 5:
                             print(f"AI Brain Error: {e}") # Reduce log spam
                
                if not ai_decision_made:
                    bullish_score = 0
                    bearish_score = 0
                    
                    for h in headlines[:5]: 
                        s = h.get('sentiment', 'neutral')
                        log_digest += f"- {h['title']} ({s})\n"
                        if s == "positive": bullish_score += 1
                        if s == "negative": bearish_score += 1

                # --- 2. CALENDAR SNIPER (Safety Check) ---
                # Check for High Impact Events nearby
                # We do this here as it's part of the "General" oversight loop
                # Logic: If Event in < 5 mins, CLOSE ALL TRADES.
                if HAS_MT5 and mt5_state["connected"]:
                    # Get unique symbols from open positions
                    open_symbols = list(set([p['symbol'] for p in mt5_state.get('positions', [])]))
                    for sym in open_symbols:
                         is_event, msg = calendar.is_event_nearby(sym, minutes_before=5, minutes_after=1)
                         if is_event and "Upcoming" in msg:
                              await broadcast_log(f"🚨 CALENDAR SNIPER: {msg}. Initiating Safety Close (Profitable Only).")
                              # Close this symbol's trades IF Profitable
                              for pos in mt5_state.get('positions', []):
                                   if pos['symbol'] == sym:
                                        # Calculate Net Profit
                                        # note: pos is a dict here from mt5_state, not the raw object
                                        # We need to be careful about keys. 
                                        # existing keys: ticket, symbol, type, volume, price, profit, time. 
                                        # Swap/Comm might NOT be in the dict if we didn't put them there in the loop at line 2821
                                        # Let's check line 2821.
                                        # mt5_state["positions"].append({ ... "profit": pos.profit ... })
                                        # It does NOT seem to include swap/commission in the cache update loop at line 2817+ or 774+
                                        # We should probably trust 'profit' from the cache or fetch fresh.
                                        # But let's look at how we get 'positions' in mt5_state. 
                                        # Lines 774 and 2817.
                                        
                                        # To be safe and accurate, let's just check raw profit > 0 for now as 'swap' isn't cached.
                                        # Or better, let's fetch the position freshly to be sure? 
                                        # No, that might be slow inside this loop. 
                                        # Let's assume 'profit' in mt5_state is the main "profit" field from MT5 which is gross profit.
                                        # The user wants "Close in Profit OR Zero".
                                        
                                        raw_profit = pos.get('profit', 0.0)
                                        if raw_profit >= 0:
                                             await close_position(pos['ticket'], pos['symbol'], reason="Event Safety", require_profit=True)
                                        else:
                                             await broadcast_log(f"⚠️ HOLDING {sym} (Ticket {pos['ticket']}) through Event (Profit: {raw_profit:.2f} < 0)")

                # --- 3. Sentiment Decision ---
                    
                    if bullish_score > bearish_score: new_sentiment = "BULLISH"
                    elif bearish_score > bullish_score: new_sentiment = "BEARISH"
                
                # Update State only if changed
                if new_sentiment != auto_trade_state.get("sentiment"):
                     auto_trade_state["sentiment"] = new_sentiment
                     source_tag = "AI BRAIN" if ai_decision_made else "KEYWORD MATRIX"
                     msg = f"GLOBAL SENTIMENT SHIFT ({source_tag}): {new_sentiment}"
                     await broadcast_log(msg)
                
                # Log Shield Status
                if dxy_data:
                     try:
                         dxy_status = dxy_data.get("status")
                         dxy_change = dxy_data.get("change_pct", 0.0)
                         await broadcast_log(f"SHIELD: DXY is {dxy_status} ({dxy_change}%)")
                     except:
                         pass

                # --- PHASE 4: GLOBAL TETHER EXPORT ---
                # Export Sentiment & Shield data for Shoonya (The Cloud)
                try:
                    payload_export = {
                        "sentiment": new_sentiment,
                        "dxy_status": dxy_data.get("status", "NEUTRAL") if dxy_data else "NEUTRAL",
                        "dxy_value": dxy_data.get("current", 0.0) if dxy_data else 0.0,
                        "oil_status": "NEUTRAL",  # Default
                        "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }

                    # OIL WATCHER LOGIC (Real MT5 Data)
                    if HAS_MT5 and mt5_state["connected"]:
                        oil_sym = "BRENT" # Adjust if your broker uses "UKOIL" or "WTI"
                        if not mt5.symbol_select(oil_sym, True):
                            oil_sym = "WTI" 
                            mt5.symbol_select(oil_sym, True)
                        
                        tick_oil = mt5.symbol_info_tick(oil_sym)
                        if tick_oil:
                             # Simple Logic: Only close > open doesn't tell us trend. 
                             # We need daily change % or MA. 
                             # Let's use simple Change % if available from symbol_info, else just spot check vs prev close? 
                             # mt5.symbol_info doesn't easily give change %. 
                             # We will fetch close of yesterday.
                             # Multi-Timeframe Analysis for precision
                             daily_rates = mt5.copy_rates_from(oil_sym, mt5.TIMEFRAME_D1, datetime.now(), 2)
                             m15_rates = mt5.copy_rates_from(oil_sym, mt5.TIMEFRAME_M15, datetime.now(), 5)
                             
                             status = "NEUTRAL"
                             change_pct = 0.0

                             if daily_rates is not None and len(daily_rates) > 1:
                                 prev_close = daily_rates[0]['close']
                                 curr_price = tick_oil.ask
                                 change_pct = ((curr_price - prev_close)/prev_close) * 100
                                 
                                 # 1. Daily Bias
                                 if change_pct > 0.3: status = "BULLISH" 
                                 elif change_pct < -0.3: status = "BEARISH"
                                 
                                 # 2. M15 Momentum (Refining)
                                 if m15_rates is not None and len(m15_rates) >= 3:
                                     # Check last 3 candles close
                                     c1, c2, c3 = m15_rates[-3]['close'], m15_rates[-2]['close'], m15_rates[-1]['close']
                                     if c3 > c2 > c1: # Consistent Up Trend
                                         if status == "BULLISH": status = "STRONG_BULLISH"
                                         elif status == "NEUTRAL": status = "BULLISH_IMPULSE"
                                     elif c3 < c2 < c1: # Consistent Down Trend
                                         if status == "BEARISH": status = "STRONG_BEARISH"
                                         elif status == "NEUTRAL": status = "BEARISH_IMPULSE"

                                 payload_export["oil_status"] = status
                                 payload_export["oil_change"] = round(change_pct, 2)
                    
                    pulse_path = os.path.join(os.path.dirname(__file__), "..", "market_pulse.json")
                    with open(pulse_path, "w") as f:
                        json.dump(payload_export, f)
                    # await broadcast_log(f"TETHER: Synced Global Pulse.")
                except Exception as e:
                    print(f"Market Pulse Write Failed: {e}")

                # 4. ACTIVE DEFENSE: Enforce Sentiment Bias
                if new_sentiment != last_sentiment:
                     await enforce_sentiment_bias(new_sentiment)
                     last_sentiment = new_sentiment

                # 5. STRATEGY OPTIMIZATION (Dynamic Risk)
                if headlines:
                    pack = strategy_engine.generate_strategy_pack(headlines)
                    new_mode = pack.get("mode", "TIGHT") # Default to safe in HFT
                    
                    # Respect User JSON settings if manually set? 
                    # No, AI Resource should optimize.
                    
                    if risk_settings.get("mode") != new_mode:
                        risk_settings["mode"] = new_mode
                        save_settings()

            else:
                pass
            
            # Poll every 60 seconds (Faster Internet Analysis)
            await asyncio.sleep(60) 
            
        except Exception as e:
             print(f"General AI Error: {e}")
             await asyncio.sleep(60)


async def auto_trader_loop():
    """
    HFT SCALPER ENGINE + SPIDER WEB (Grid).
    Executes trades based on sub-second Tick Velocity AND Internet Logic.
    """
    logger_msg = "INFO: Spidy HFT Scalper + Spider Web Started (Speed: ULTRA - 0.01s)"
    print(logger_msg)
    await broadcast_log(logger_msg)
    
    # STARTUP WARMUP: Reduced for faster activation
    warmup_duration = 5 # Seconds (Was 15)
    start_time = datetime.now().timestamp()
    await broadcast_log(f"INFO: System Warmup Active. Trading paused for {warmup_duration}s...")
    
    # Symbols to HFT on
    symbols_to_scan = []
    
    tick_state = {}
    
    # Grid Cooldown to prevent spamming limit orders
    grid_last_update = 0
    scanner_last_update = 0 # Technical Analysis Timer
    symbols_refresh_time = 0
    
    while True:
        try:
            # Check Global Kill Switch
            if not auto_trade_state["running"]:
                await asyncio.sleep(1)
                continue
                
            if not HAS_MT5 or not mt5_state["connected"]:
                await asyncio.sleep(1)
                continue
            
            # WARMUP CHECK
            if (datetime.now().timestamp() - start_time) < warmup_duration:
                await asyncio.sleep(1)
                continue

            # 0. STRICT MARKET CHECK
            if not is_market_open():
                if datetime.now().second % 10 == 0: # Log only occasionally
                    print("INFO: Market Closed. HFT Sleeping...")
                await asyncio.sleep(5)
                continue

            # 0. Refresh Symbol List (Every 10s to pick up new Market Watch items)
            if datetime.now().timestamp() - symbols_refresh_time > 10:
                # Optimized Candidate List for Maximum Opportunity
                candidates = [
                    # Majors
                    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
                    # Crosses
                    "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY",
                    # Metals/Energy
                    "XAUUSD", "XAGUSD", "WTI", "BRENT",
                    # Indices
                    "US30", "SP500", "NAS100", "GER30", "UK100",
                    # Crypto
                    "BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD"
                ]
                
                new_symbols = []
                for s in candidates:
                    if mt5.symbol_select(s, True): # Checks if available/visible
                        new_symbols.append(s)
                
                symbols_to_scan = new_symbols
                symbols_refresh_time = datetime.now().timestamp()
                
                # Ensure EURUSD is first for Lead-Lag logic
                if "EURUSD" in symbols_to_scan and symbols_to_scan[0] != "EURUSD":
                     symbols_to_scan.remove("EURUSD")
                     symbols_to_scan.insert(0, "EURUSD")

            # Loop through symbols rapidly for HFT (Strategy 1)
            # Optimization: Collect ticks ONLY once per loop
            current_ticks = {} # Map symbol -> tick
            
            for symbol in symbols_to_scan:
                # 1. Get Real-Time Tick
                tick = mt5.symbol_info_tick(symbol)
                if not tick: continue
                current_ticks[symbol] = tick
                
                curr_price = tick.bid # Use Bid for simplicity of 'current value' tracking
                curr_time = tick.time_msc # Milliseconds
                
                # Init State
                if symbol not in tick_state:
                    tick_state[symbol] = { "last_price": curr_price, "last_time": curr_time }
                    continue
                
                prev_price = tick_state[symbol]["last_price"]
                
                # Velocity Analysis (Milliseconds)
                pct_change = (curr_price - prev_price) / prev_price if prev_price else 0
                
                # SENSITIVITY ADJUSTMENT: Ultra-Sensitive for "Every Second" request
                # 0.0001 = 1 pip approx. 
                # 0.00001 = 1 point approx.
                # Let's set to ~1.5 points to avoid pure noise but catch micro-moves.
                is_pump = pct_change > 0.000015 
                is_dump = pct_change < -0.000015
                
                signal = None
                
                # --- STRATEGY: HFT SNIPER ---
                # "All Resources Together": validate_entry below checks Sentiment + Shield + Account
                
                if is_pump: signal = "BUY"
                if is_dump: signal = "SELL"
                
                # Lead-Lag Logic (EURUSD -> XAUUSD)
                if symbol == "EURUSD":
                    tick_state["EURUSD"]["trend"] = "PUMP" if is_pump else "DUMP" if is_dump else "FLAT"
                    tick_state["EURUSD"]["ts"] = datetime.now().timestamp()
                
                if symbol == "XAUUSD":
                    eur_data = tick_state.get("EURUSD", {})
                    eur_trend = eur_data.get("trend", "FLAT")
                    eur_ts = eur_data.get("ts", 0)
                    if datetime.now().timestamp() - eur_ts < 1.0:
                         if eur_trend == "PUMP" and not is_pump: signal = "BUY"
                         elif eur_trend == "DUMP" and not is_dump: signal = "SELL"

                if signal:
                     # 4. STRICT MILLISECOND VALIDATION
                     # This function integrates Sentiment, Shield (DXY), and Market Status
                     is_valid, reason = validate_entry(symbol, signal, tick, "HFT")
                     
                     if is_valid:
                         # Extra HFT Check: Max Positions (Async Wrap)
                         open_positions = await safe_mt5_call(mt5.positions_get, symbol=symbol)
                         if not open_positions or len(open_positions) < 3: # Allow stacking up to 3 for aggressive profit
                             
                             logger_tag = f"HFT_Vel_{pct_change*10000:.2f}"
                             await broadcast_log(f"HFT: {signal} {symbol} (Vel {pct_change*100:.5f}%)")
                             
                             # Execute!
                             # Use the Aggressive Lot Size
                             lot_size = risk_settings.get("fixed_lot_size", 0.05)
                             # Sync Call Fixed
                             await place_market_order(symbol, signal, volume=lot_size, strategy_tag=logger_tag)
                             
                             # Cooldown
                             tick_state[symbol]["last_price"] = curr_price
                             await asyncio.sleep(0.2) # Reduced Cooldown for more trades
                             continue
                     else:
                         # Log rejection for User Visibility (Why is it not trading?)
                         await broadcast_log(f"HFT FILTER: {symbol} Signal Ignored: {reason}")
                         pass

                # Update State
                tick_state[symbol]["last_price"] = curr_price
                
                
            # --- STRATEGY: TECHNICAL SCANNER (Every 1 Second) ---
            # Analyzes RSI / Trend for Symbols
            if datetime.now().timestamp() - scanner_last_update > 1.0:
                 for symbol in symbols_to_scan:
                     # 1. Fetch M15 Data (Async Wrap - Heavy)
                     rates = await safe_mt5_call(mt5.copy_rates_from_pos, symbol, mt5.TIMEFRAME_M15, 0, 20)
                     if rates is None or len(rates) < 15: continue
                     
                     closes = [x['close'] for x in rates]
                     
                     # 2. Indicators
                     rsi = calculate_rsi(closes, 14)
                     trend = analyze_trend(closes, 50) # SMA 50
                     
                     if not rsi: continue
                     
                     # 3. Signals (RSI Extremes + Trend)
                     scan_signal = None
                     
                     # Overbought + Bearish Trend -> SELL
                     if rsi > 70 and trend == "BEARISH":
                         scan_signal = "SELL"
                     
                     # Oversold + Bullish Trend -> BUY
                     elif rsi < 30 and trend == "BULLISH":
                         scan_signal = "BUY"
                         
                     if scan_signal:
                         # 4. Strict Validation (Internet + Shield + Market)
                         tick = current_ticks.get(symbol) or mt5.symbol_info_tick(symbol)
                         if not tick: continue
                         
                         is_valid, reason = validate_entry(symbol, scan_signal, tick, "Scanner")
                         
                         if is_valid:
                             # Check max positions (Async Wrap)
                             open_positions = await safe_mt5_call(mt5.positions_get, symbol=symbol)
                             if not open_positions or len(open_positions) < 3:
                                  tag = f"RSI_{rsi:.1f}_{trend}"
                                  await broadcast_log(f"SCANNER: {scan_signal} {symbol} (RSI {rsi:.1f}, {trend})")
                                  
                                  lot = risk_settings.get("fixed_lot_size", 0.05)
                                  await place_market_order(symbol, scan_signal, volume=lot, strategy_tag=tag)
                                  
                 scanner_last_update = datetime.now().timestamp()


            # Update Spider Web (Grid) every 10 seconds (Strategy 2)
            if datetime.now().timestamp() - grid_last_update > 10:
                await update_spider_web(symbols_to_scan, shared_ticks=current_ticks)
                grid_last_update = datetime.now().timestamp()

            # EXTREME SPEED
            # Log Heartbeat occasionally (every 60s)
            if datetime.now().second == 0:
                await broadcast_log(f"INFO: HFT Active | Scanning {len(symbols_to_scan)} symbols")
                await asyncio.sleep(1.0) 
            
            await asyncio.sleep(0.01) # 10ms Loop (ULTRA SPEED)

        except Exception as e:
            print(f"HFT Error: {e}")
            print(f"HFT Error: {e}")
            await asyncio.sleep(1)

def get_required_breakeven_distance(symbol, volume, cost_usd, min_profit_usd=0.50):
    """
    Calculates the Price Distance (formatted to points) required to cover Cost + MinProfit.
    Formula: Required_Profit = (Distance / Tick_Size) * Tick_Value * Volume
    => Distance = (Required_Profit * Tick_Size) / (Tick_Value * Volume)
    """
    info = mt5.symbol_info(symbol)
    if not info: 
        return 0.00200 # Fallback 200 points
        
    tick_value = info.trade_tick_value
    tick_size = info.trade_tick_size
    point = info.point
    
    if tick_value == 0 or volume == 0:
        return 200 * point # Safe Fallback
        
    required_profit = cost_usd + min_profit_usd
    
    # Calculate Raw Distance
    distance = (required_profit * tick_size) / (tick_value * volume)
    
    # Add a 10% safety margin for slippage
    distance = distance * 1.1
    
    # Ensure it's never LESS than 50 points (Basic Scalp)
    if distance < (50 * point):
        distance = 50 * point
        
    return distance

# Startup logic moved to lifespan
# @app.on_event("startup") deprecated

# Helper: Sync Single Position Processing (Guardian)
def _process_single_pos_guardian_sync(pos_ticket, loop=None):
    """Sync function to check and update stops for ONE position."""
    if not mt5_state["connected"] or not HAS_MT5:
        return

    # Concurrency Check: Don't touch if being processed (closed)
    with ticket_lock:
        if pos_ticket in processing_tickets:
            return

    # Re-fetch position to be fresh and safe
    positions = mt5.positions_get(ticket=pos_ticket)
    if not positions:
        return

    pos = positions[0]
    symbol = pos.symbol

    # FIX: Define entry_price and current_price early so all sub-blocks can use them
    entry_price = pos.price_open
    tick_now = mt5.symbol_info_tick(symbol)
    if tick_now:
        current_price = tick_now.bid if pos.type == 0 else tick_now.ask
    else:
        current_price = entry_price  # fallback

    # --- 0. ROI GUARD (30% Loss / 70% Profit) ---
    # Logic: ROI = (Net Profit / Estimated Margin) * 100
    try:
        # Standardize margin to approximate $200 per 1.00 lot, matching UX expectations
        margin = (pos.volume if getattr(pos, 'volume', 0) > 0 else 0.01) * 200.0
        if margin <= 0:
            margin = 2.0  # safe fallback for 0.01 lot

        # Calculate Net Profit
        comm = getattr(pos, 'commission', 0.0)
        swap = getattr(pos, 'swap', 0.0)
        net_profit_roi = pos.profit + comm + swap

        roi = (net_profit_roi / margin) * 100.0

        # Debug: print scan result so we can see ROI values in backend logs
        print(f"ROI_SCAN: {symbol} #{pos.ticket} Vol:{pos.volume} Net:{net_profit_roi:.2f} ROI:{roi:.2f}%")

        # Check Limits
        roi_close = False
        roi_reason = ""

        if roi <= -30.0:
            roi_close = True
            roi_reason = f"Stop Loss (ROI {roi:.2f}% <= -30%)"
        elif roi >= 70.0:
            roi_close = True
            roi_reason = f"Take Profit (ROI {roi:.2f}% >= 70%)"

        if roi_close:
            if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"⚖️ ROI GUARD TRIGGERED: Closing {symbol} ({roi_reason}) [Net: ${net_profit_roi:.2f}]"), loop)
            print(f"ROI GUARD TRIGGERED: {symbol} {roi_reason} - Attempting close...")
            res, msg, _, _ = _close_position_sync(pos.ticket, symbol, "ROI_Guard", require_profit=False)
            if res:
                print(f"ROI GUARD SUCCESS: {symbol} closed.")
                if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"✅ ROI GUARD: {symbol} closed successfully."), loop)
                return  # Exit immediately
            else:
                print(f"ROI GUARD FAILED: {symbol} close rejected - {msg}")
                if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"❌ ROI GUARD FAILED: {symbol} - {msg}"), loop)

    except Exception as e:
        print(f"ROI Guard Error: {e}")
        if loop:
            asyncio.run_coroutine_threadsafe(broadcast_log(f"❌ ROI Guard Exception: {symbol} - {e}"), loop)

    # --- 0. Auto-Secure Profit Trigger (PRIORITY) ---
    secure_conf = risk_settings.get("auto_secure", {})
    if secure_conf.get("enabled"):
            threshold = float(secure_conf.get("threshold", 50.0)) # RAISED DEFAULT to $50 (Let Smart Exit decide)
            # FIX: Use Net Profit to ensure we don't close in loss due to commissions
            # Handle potential missing attributes if mock/older lib
            comm = getattr(pos, 'commission', 0.0)
            swap = getattr(pos, 'swap', 0.0)
            net_profit_final = pos.profit + comm + swap
            
            if net_profit_final >= threshold:
                # print(f"DEBUG: Auto-Secure TRIGGERED {symbol} Net:{net_profit_final:.2f} >= Threshold:{threshold}")
                if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"💰 AUTO-SECURE: Closing {symbol} (+${net_profit_final:.2f} Net)"), loop)
                res, msg, _, _ = _close_position_sync(pos.ticket, symbol, "AutoSecure", require_profit=True)
                if res:
                     return # Exit immediately if closed
                else:
                     if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"ERROR: AutoSecure Failed {symbol}: {msg}"), loop)

    
    # --- MICRO SCALP EXIT (HFT Mode) ---
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        # SENSIBLE HFT TARGET: Minimum $0.50 guaranteed NET
        target_usd = risk_settings.get("scalp_target_usd", 0.50)
        if target_usd < 0.50: target_usd = 0.50 # Force minimum catch
        
        # Calculate Net Profit (Gross + Swap + Commission)
        # Commission is usually negative, so adding it reduces profit
        net_profit = pos.profit + pos.swap + pos.commission

        # --- NEW: TRACK PROFIT PEAK (High Water Mark) ---
        current_peak = profit_peaks.get(pos.ticket, 0.0)
        if net_profit > current_peak:
            profit_peaks[pos.ticket] = net_profit
            # print(f"DEBUG: New Peak for #{pos.ticket}: ${net_profit:.2f}")

        # --- NEW: TRAILING FROM PEAK LOGIC (Bank It) ---
        # If we have seen a Good Peak (> $2.00) and we dropped 20% from it, CLOSE.
        # But ONLY if we are still profitable (e.g. Peak $10, drop to $8 -> Close).
        if current_peak > 2.00:
            pullback_threshold = current_peak * 0.80 # Allow 20% pullback
            if net_profit < pullback_threshold and net_profit > 0.50:
                 # We dropped too much from peak! Bank it now!
                 if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"📉 TRAILING PEAK: Closing {symbol} (Peak ${current_peak:.2f} -> Now ${net_profit:.2f})"), loop)
                 res, msg, _, _ = _close_position_sync(pos.ticket, symbol, "TrailingPeak", require_profit=True)
                 if res: return
        
        # --- STRATEGY REVERSAL EXIT (Collaboration with 52+ Strategies) ---
        # If the Strategy Manager says "SELL" with High Confidence, but we are holding "BUY", CLOSE IT.
        # This allows the entry strategies to also act as exit strategies.
        
        cached_sig = latest_strategy_signals.get(symbol)
        if cached_sig:
             # Check freshness (e.g. signal must be < 1 minute old)
             if (datetime.now().timestamp() - cached_sig["time"]) < 60:
                 sig_type = cached_sig["signal"]     # BUY or SELL
                 sig_conf = cached_sig["confidence"] # 0.0 to 1.0
                 
                 should_reverse = False
                 rev_reason = ""
                 
                 # Logic: Only reverse if confidence is decent (> 0.7) to avoid noise
                 if sig_conf >= 0.7:
                     if pos.type == 0 and sig_type == "SELL": # Long vs Sell Signal
                         should_reverse = True
                         rev_reason = f"Strategy Reversal (SELL {sig_conf:.2f})"
                     elif pos.type == 1 and sig_type == "BUY": # Short vs Buy Signal
                         should_reverse = True
                         rev_reason = f"Strategy Reversal (BUY {sig_conf:.2f})"
                 
                 if should_reverse:
                     # Check if we are in huge loss? Maybe we hold for SL? 
                     # Strategy Reversal usually implies trend change, so getting out is better than SL.
                     # But let's log it clearly.
                     if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"🔄 EXIT: {symbol} triggered by {rev_reason}"), loop)
                     res, msg, _, _ = _close_position_sync(pos.ticket, symbol, "StrategyReversal", require_profit=False) # Allow small loss to save big loss
                     if res: return

        # Hard Take Profit (Scalp) using NET profit
        if net_profit >= target_usd:
             # SMART SCALP: Check if we should Let Winners Run?
             should_close = True
             tech_data = technical_cache.get(symbol)
             
             if tech_data:
                 trend = tech_data.get("trend", "NEUTRAL")
                 rsi = tech_data.get("rsi", 50)
                 
                 # Logic: If Trend matches position and RSI is not extreme, HOLD.
                 # STRICTER: Only hold if Momentum is supporting (RSI > 55 for Buy, < 45 for Sell)
                 if pos.type == 0: # BUY
                     if trend == "BULLISH" and rsi < 70:
                         # Extra Check: Is momentum strong enough to risk holding?
                         if rsi > 55:
                             if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"📈 LETTING WINNER RUN: {symbol} (+${net_profit:.2f}) RSI {rsi:.1f} > 55"), loop)
                             should_close = False # SKIP CLOSE
                             
                             # GREED LOCK: Ensure we lock at least enough to cover Cost + Profit
                             current_sl = pos.sl
                             cost_usd = abs(pos.commission + pos.swap)
                             req_dist = get_required_breakeven_distance(symbol, pos.volume, cost_usd, 0.50)
                             
                             lock_price = entry_price + req_dist
                             if current_sl < lock_price:
                                 # Place Lock
                                 req = {
                                     "action": mt5.TRADE_ACTION_SLTP,
                                     "position": pos.ticket,
                                     "symbol": symbol,
                                     "sl": lock_price,
                                     "tp": pos.tp,
                                     "magic": 234000
                                 }
                                 mt5.order_send(req)
                         
                 elif pos.type == 1: # SELL
                     if trend == "BEARISH" and rsi > 30:
                         if rsi < 45: 
                             if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"📉 LETTING WINNER RUN: {symbol} (+${net_profit:.2f}) RSI {rsi:.1f} < 45"), loop)
                             should_close = False # SKIP CLOSE

                             # GREED LOCK for SELL
                             current_sl = pos.sl
                             cost_usd = abs(pos.commission + pos.swap)
                             req_dist = get_required_breakeven_distance(symbol, pos.volume, cost_usd, 0.50)
                             
                             lock_price = entry_price - req_dist
                             if current_sl == 0 or current_sl > lock_price:
                                 req = {
                                     "action": mt5.TRADE_ACTION_SLTP,
                                     "position": pos.ticket,
                                     "symbol": symbol,
                                     "sl": lock_price,
                                     "tp": pos.tp,
                                     "magic": 234000
                                 }
                                 mt5.order_send(req)
             
             if should_close:
                 # LOG for verification
                 print(f"DEBUG: Micro Scalp TRIGGERED {symbol} NetProfit:{net_profit:.2f} >= Target:{target_usd}")
                 if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"💰 MICRO SCALP: Closing {symbol} (+${net_profit:.2f})"), loop)
                 res, msg, _, _ = _close_position_sync(pos.ticket, symbol, "MicroScalp", require_profit=True)
                 if not res:
                      if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"ERROR: MicroScalp Failed {symbol}: {msg}"), loop)
                 return

    else:
        # Tick missing
        # print(f"DEBUG: No Tick for {symbol}, skipping Micro Scalp check.")
        pass

    # Fetch Data for ATR (M5 timeframe)
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 20)
    if rates is None or len(rates) < 15: return

    # ... (ATR Calc omitted for brevity, assumed context match) ...
    # We resume at Breakeven Logic

    # entry_price and current_price already set at top of function; refresh price safely here
    _tick_refresh = mt5.symbol_info_tick(symbol)
    if _tick_refresh:
        current_price = _tick_refresh.bid if pos.type == 0 else _tick_refresh.ask
    # entry_price = pos.price_open (already set above)
    
    # --- 0. Get Symbol Specs for Dynamic Pips ---
    sym_info = mt5.symbol_info(symbol)
    if not sym_info: return
    
    point = sym_info.point 
    
    
    # --- SMART PEAK EXIT (Bollinger & RSI) ---
    # Detect if we are at a statistical peak to capture profit
    try:
         # 1. Get Data (M5 for precision)
         # We need ~20 candles for BB
         rates = mt5.copy_rates_from_pos(pos.symbol, mt5.TIMEFRAME_M5, 0, 25)
         if rates is not None and len(rates) > 20:
             closes = [x['close'] for x in rates]
             current_price = closes[-1]
             
             # 2. Indicators
             upper_bb, mid_bb, lower_bb = calculate_bollinger_bands(closes, 20, 2)
             rsi_val = calculate_rsi(closes, 14)
             
             # MACD (New Algo)
             macd, macd_sig, macd_hist = calculate_macd(closes)
             
             # STOCHASTIC (New Algo)
             highs = [x['high'] for x in rates]
             lows = [x['low'] for x in rates]
             stoch_k, stoch_d = calculate_stochastic(highs, lows, closes)
             
             should_smart_exit = False
             exit_reason = ""
             
             if pos.type == mt5.ORDER_TYPE_BUY:
                  # Peak: Price touching Upper BB OR RSI Overbought
                  # OR MACD Reversal OR Stochastic Crossover High
                  if upper_bb and current_price >= upper_bb:
                       should_smart_exit = True
                       exit_reason = f"Price ({current_price:.5f}) hit Upper BB ({upper_bb:.5f})"
                  elif rsi_val and rsi_val > 75:
                       should_smart_exit = True
                       exit_reason = f"RSI Overbought ({rsi_val:.1f})"
                  elif macd_hist and macd_hist[-1] < 0 and macd_hist[-2] > 0 and rsi_val > 60:
                       # Momentum Shift: MACD flipped Bearish and we are relatively high (RSI > 60)
                        should_smart_exit = True
                        exit_reason = f"MACD Bearish Crossover (Momentum Peak)"
                  elif stoch_k and (stoch_k[-1] < stoch_d[-1]) and stoch_k[-2] > stoch_d[-2] and stoch_k[-1] > 80:
                       # Stochastic Cross Down from Overbought
                        should_smart_exit = True
                        exit_reason = f"Stochastic Bearish Cross (>80)"
                       
             elif pos.type == mt5.ORDER_TYPE_SELL:
                  # Valley: Price touching Lower BB OR RSI Oversold
                  if lower_bb and current_price <= lower_bb:
                       should_smart_exit = True
                       exit_reason = f"Price ({current_price:.5f}) hit Lower BB ({lower_bb:.5f})"
                  elif rsi_val and rsi_val < 25:
                       should_smart_exit = True
                       exit_reason = f"RSI Oversold ({rsi_val:.1f})"
                  elif macd_hist and macd_hist[-1] > 0 and macd_hist[-2] < 0 and rsi_val < 40:
                       # Momentum Shift: MACD flipped Bullish and we are low (RSI < 40)
                        should_smart_exit = True
                        exit_reason = f"MACD Bullish Crossover (Momentum Valley)"
                  elif stoch_k and (stoch_k[-1] > stoch_d[-1]) and stoch_k[-2] < stoch_d[-2] and stoch_k[-1] < 20:
                       # Stochastic Cross Up from Oversold
                        should_smart_exit = True
                        exit_reason = f"Stochastic Bullish Cross (<20)"
             
             # 3. Execution (Strict Net Profit Check)
             if should_smart_exit:
                  # Ensure we are actually profitable (don't exit a peak loss)
                  # A peak in price might still be a loss if entry was terrible.
                  if net_profit > 0.50: # Minimum profit buffer
                       print(f"DEBUG: Smart Peak Exit {symbol}: {exit_reason}")
                       if loop: asyncio.run_coroutine_threadsafe(broadcast_log(f"🧠 SMART EXIT: Closing {symbol} at Peak (+${net_profit:.2f}). Reason: {exit_reason}"), loop)
                       res, msg, _, _ = _close_position_sync(pos.ticket, symbol, "SmartPeak", require_profit=True)
                       if res: return # Exit function if closed
             
    except Exception as e:
         print(f"Smart Exit Error: {e}")

    # Estimate Cost (Commission + Swap) in PIPS
    cost_usd = abs(pos.commission + pos.swap)
    # Estimate Value Per Pip (Approximate for speed, assuming standard lot 1.0 = $10/pip, 0.01 = $0.10/pip)
    # A safer way requires tick_value from symbol_info but let's be conservative.
    # Cost Pips = Cost USD / (Volume * 10) roughly for typical pairs.
    # For Metals, it's different.
    # Let's use a "Min Money" check instead of Pips for the Trailing Trigger?
    # Or just inflate the Pips Distance buffer.
    
    # Base Safe Distance
    base_dist = 50 * point # 5 pips
    
    # If cost is high, increase distance
    # Heuristic: If net_profit < 1.0, keep distance wide.
    # We will enforce: secure_pips_dist must be at least enough to cover Cost + 2 Pips.
    
    # Calculate Precise Monetary Distance needed
    # FIX: safe_commission / safe_swap were undefined — use pos attributes directly
    cost_usd = abs(pos.commission + pos.swap)
    secure_pips_dist = get_required_breakeven_distance(symbol, pos.volume, cost_usd, 0.50)
    
    # Log the calcs occasionally for debugging
    # print(f"DEBUG: {symbol} Cost=${cost_usd:.2f} Vol={pos.volume} -> Required Breakeven Dist={secure_pips_dist:.5f}")
    
    # Fail-safe / Step Trail Buffer
    step_trail_dist = secure_pips_dist * 2 # Step is double the secure buffer
    target_pips_dist = secure_pips_dist * 3 # Trigger activation later

    # --- 1. Breakeven Trigger (Price-Based Authority) ---
    # We calculated 'secure_pips_dist' earlier using the Broker formula.
    # That is the MINIMUM distance we must lock to be safe.
     
    # Trigger: We need Current Price to be BEYOND (Entry + SecureDist + Buffer).
    # Buffer: Let's use 10% more to ensure we don't scrape the spread.
    trigger_dist = secure_pips_dist * 1.5 
     
    new_sl = 0.0
    reason_log = ""
     
    if pos.type == 0: # BUY
        # We want Current > Entry + Trigger
        if current_price > (entry_price + trigger_dist):
            # It is safe to lock.
            # Lock Level: Entry + SecureDist (Guarantees $0.50 Net)
            test_sl = entry_price + secure_pips_dist
              
            # Final Validity Check (Must be below current price by at least spread?)
            # Let's verify against current Bid (which is current_price for Buy exit logic check)
            if test_sl < current_price:
                new_sl = test_sl
                reason_log = f"Secure (Locked +${0.50:.2f})"
                  
    elif pos.type == 1: # SELL
        # We want Current < Entry - Trigger
        if current_price < (entry_price - trigger_dist):
            test_sl = entry_price - secure_pips_dist
              
            if test_sl > current_price:
                new_sl = test_sl
                reason_log = f"Secure (Locked +${0.50:.2f})"
              
    # REVERSAL GUARD: If we were high and dropped, CLOSE MARKET (Don't wait for SL)
    # Requires tracking "High Water Mark" for individual position? 
    # Current Complexity: We don't track per-position-high in RAM persistently easily without DB.
    # Deviation: Use simple "Distance from Peak" if we assume current price was near peak? No.
    # We just ensure SL is tight.
    
    if new_sl != 0.0:
            # Only update if it TIGHTENS the stop (Higher for Buy, Lower for Sell)
            # And SL is not already better
            current_sl = pos.sl
            should_update = False
            
            if pos.type == 0: 
                # For Buy, New SL must be > Current SL, AND New SL < Current Price (Valid Stop)
                if (current_sl == 0.0 or new_sl > current_sl) and new_sl < current_price: should_update = True
            else: 
                # For Sell, New SL must be < Current SL, AND New SL > Current Price
                if (current_sl == 0.0 or new_sl < current_sl) and new_sl > current_price: should_update = True
                     
            if should_update:
                request = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "symbol": symbol,
                    "sl": new_sl,
                    "tp": pos.tp,
                    "magic": 234000
                }
                res = mt5.order_send(request)
                if res.retcode == mt5.TRADE_RETCODE_DONE:
                    print(f"GUARDIAN: Moved SL to {reason_log} {symbol} @ {new_sl} (Profit Locked)")

    # --- 2. ATR Trailing Stop ---
    # Re-calc ATR
    atr = calculate_atr(rates, 14) 
    if not atr: return

    multiplier = risk_settings["atr_multiplier"]
    stop_dist = multiplier * atr
    
    should_update = False
    ideal_sl = 0.0
    
    if pos.type == 0: # BUY
        ideal_sl = current_price - stop_dist
        min_profit_sl = entry_price + secure_pips_dist 
        
        if ideal_sl > min_profit_sl:
             if ideal_sl > pos.sl:
                 should_update = True
        
        if should_update:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": pos.ticket,
                "symbol": symbol,
                "sl": ideal_sl,
                "tp": pos.tp,
                "magic": 234000
            }
            res = mt5.order_send(request)
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                 print(f"GUARDIAN: Trailing Stop {symbol} @ {ideal_sl}")
            
    elif pos.type == 1: # SELL
        ideal_sl = current_price + stop_dist
        min_profit_sl = entry_price - secure_pips_dist 
        
        if ideal_sl < min_profit_sl:
             if pos.sl == 0 or ideal_sl < pos.sl: 
                 should_update = True
                 
        if should_update:
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": pos.ticket,
                "symbol": symbol,
                "sl": ideal_sl,
                "tp": pos.tp,
                "magic": 234000
            }
            res = mt5.order_send(request)
            if res.retcode == mt5.TRADE_RETCODE_DONE:
                 print(f"GUARDIAN: Trailing Stop {symbol} @ {ideal_sl}")

    # --- 2. ATR Trailing Stop ---
    # ... (Replaced by snippet above for brevity, keeping context)

    # --- DEBUG: High Profit Watch ---
    if pos.profit > 5.0:
        sec_sets = risk_settings.get("auto_secure", {})
        msg = f"DEBUG: WATCH High Profit: {symbol} Profit:{pos.profit} | Threshold: {sec_sets.get('threshold')} | Enabled: {sec_sets.get('enabled')}"
        if loop: asyncio.run_coroutine_threadsafe(broadcast_log(msg), loop)




async def oil_watcher_manager():
    """
    The Oil Watcher: Monitors Brent/WTI. 
    Rule: If Oil > +2.0% (Day Change) -> BUY USDINR.
    Frequency: Every 5 seconds.
    """
    await broadcast_log("INFO: The Oil Watcher (Macro Correlation) Started.")
    
    # Cooldown to prevent spamming the same spike
    last_trigger_day = 0 
    
    while True:
        try:
            if mt5_state["connected"] and HAS_MT5 and auto_trade_state["running"]:
                
                # 1. Identify Oil Symbol
                oil_symbol = None
                candidates = ["BRENT", "UKOIL", "XBRUSD", "WTI", "USOIL"]
                for s in candidates:
                    if mt5.symbol_select(s, True):
                        oil_symbol = s
                        break
                
                # 2. Identify USDINR Symbol
                pair_symbol = None
                pair_candidates = ["USDINR", "USDINR.m", "USDINR_T"]
                for p in pair_candidates:
                    if mt5.symbol_select(p, True):
                        pair_symbol = p
                        break
                        
                if oil_symbol and pair_symbol:
                    # 3. Get Daily Change
                    # We need today's Opening Price and Current Price
                    rates = await safe_mt5_call(mt5.copy_rates_from_pos, oil_symbol, mt5.TIMEFRAME_D1, 0, 1)
                    
                    if rates is not None and len(rates) > 0:
                        candle = rates[0]
                        open_price = candle['open']
                        
                        # Get live current price
                        tick = mt5.symbol_info_tick(oil_symbol)
                        if tick:
                            current_price = tick.last if tick.last > 0 else (tick.bid + tick.ask)/2
                            
                            # Calc % Change
                            if open_price > 0:
                                change_pct = ((current_price - open_price) / open_price) * 100
                                
                                # UPDATE STATE for UI
                                auto_trade_state["oil"] = {
                                    "symbol": oil_symbol,
                                    "price": current_price,
                                    "change_pct": change_pct,
                                    "updated": datetime.now().timestamp()
                                }
                                
                                # Log Heartbeat occasionally (every 60s)
                                if datetime.now().second == 0:
                                    await broadcast_log(f"DEBUG: Oil Watcher: {oil_symbol} {change_pct:.2f}%")

                                # 4. The Trigger Rule: > +2.0%
                                if change_pct >= 2.0:
                                    today = datetime.now().day
                                    if last_trigger_day != today:
                                        await broadcast_log(f"ALERT: Oil Spike Detected ({oil_symbol} +{change_pct:.2f}%). Triggering USDINR...")
                                        
                                        # Double check we don't already have USDINR position
                                        positions = await safe_mt5_call(mt5.positions_get, symbol=pair_symbol)
                                        if not positions:
                                             await place_market_order(pair_symbol, "BUY", 0.1, strategy_tag="Oil_Watcher_Macro")
                                             last_trigger_day = today
                                        else:
                                             print("DEBUG: Oil Spike but USDINR already open.")
                
            await asyncio.sleep(5) # High Frequency Check (5s)
            
        except Exception as e:
            print(f"Oil Watcher Error: {e}")
            await asyncio.sleep(10)


async def trailing_stop_manager():
    """Background task: Trailing Stop & Profit Guardian (ATR + Breakeven)."""
    await broadcast_log("INFO: Profit Guardian (ATR Trailing) Started.")
    
    loop = asyncio.get_running_loop()
    
    while True:
        try:
            if mt5_state["connected"] and HAS_MT5:
                 # 1. Fetch All Tickets First (Fast)
                 # We assume fetching position list is fast enough (single call)
                 # or we do even this in thread
                 positions = await safe_mt5_call(mt5.positions_get)
                 
                 if positions:
                     # LOG Heartbeat periodically
                     if datetime.now().second % 60 == 0: # Slower heartbeat to reduce spam
                          # print(f"DEBUG: Guardian Scanning {len(positions)} positions...") # Stdout isn't helping
                          await broadcast_log(f"DEBUG: Guardian Scanning {len(positions)} positions...")

                     for pos in positions:
                         # Process Each in Thread
                         await loop.run_in_executor(None, _process_single_pos_guardian_sync, pos.ticket, loop)
                         # Yield to event loop to allow other requests (like Close All, Trade) to sneak in
                         await asyncio.sleep(0.01) 
                 
            await asyncio.sleep(0.05) # Check every 50ms (High Speed Guardian)
            
        except Exception as e:
            # print(f"Trailing Error: {e}")
            await asyncio.sleep(1)



# REMOVED: Duplicate /tighten_stops endpoint (canonical version is at /tighten_stops below, line ~3228)

async def run_deep_history_sync(days=30):
    """
    Performs a deep sync of history (e.g., on startup).
    """
    await broadcast_log(f"HISTORY: Starting Deep Sync for last {days} days...")
    try:
        if not mt5_state["connected"]:
             print("Deep Sync Skipped: Not Connected.")
             return

        date_to = datetime.now() + timedelta(hours=48) # Future buffer
        date_from = datetime.now() - timedelta(days=days)
        
        deals = await safe_mt5_call(mt5.history_deals_get, date_from, date_to)
        
        if deals:
             items_to_sync = []
             time_offset = mt5_state.get("time_offset", 7200)
             
             for d in deals:
                 if d.entry == 1 or d.entry == 2: # Out or OutBy
                     # Adjust timestamp
                     local_ts = d.time - time_offset
                     # Extract Reason from Comment ("Spidy: Reason")
                     raw_comment = d.comment
                     exit_reason = "Manual/User" 
                     if raw_comment:
                         if "Spidy:" in raw_comment:
                              exit_reason = raw_comment.replace("Spidy:", "").strip()
                         else:
                              exit_reason = raw_comment 

                         # Override with Authoritative Deal Reason Code
                         rc = d.reason
                         # if rc == 0: exit_reason = "User" # DON'T OVERRIDE SPECIFIC COMMENT
                         if rc == 3: exit_reason = "Bot"
                         elif rc == 4: exit_reason = "Stop Loss"
                         elif rc == 5: exit_reason = "Take Profit"
                         elif rc == 6: exit_reason = "Stop Out"

                     items_to_sync.append({
                           "ticket": d.position_id,
                           "symbol": d.symbol,
                           "type": "BUY" if d.type == 0 else "SELL",
                           "volume": d.volume,
                           "price": d.price,
                           "profit": d.profit + d.swap + d.commission,
                           "time": datetime.fromtimestamp(local_ts).strftime("%Y-%m-%d %H:%M:%S"),
                           "reason": exit_reason,
                           "comment": d.comment
                     })
             
             if items_to_sync:
                 loop = asyncio.get_running_loop()
                 await loop.run_in_executor(None, financial_db.sync_from_mt5_history, items_to_sync)
                 await broadcast_log(f"HISTORY: Deep Sync Complete. Processed {len(items_to_sync)} trades.")
        else:
             await broadcast_log(f"HISTORY: Deep Sync found 0 trades.")

    except Exception as e:
        await broadcast_log(f"ERROR: Deep Sync Failed: {e}")

async def history_sync_manager():
    """
    Background Task: Accurate History Sync.
    Checks MT5 periodically for deal history to correct profits.
    """
    print("INFO: History Sync Manager Started.")
    
    loop = asyncio.get_running_loop()
    
    last_sync_time = 0
    
    while True:
        try:
             # Sync every 3 seconds (High Speed for UI)
             now_ts = datetime.now().timestamp()
             if mt5_state["connected"] and HAS_MT5 and (now_ts - last_sync_time > 3.0):
                 
                 last_sync_time = now_ts
                 
                 # Fetch Deals - Last 3 Days by default for routine check
                 # TIMEZONE FIX: Use future date +24h
                 date_from = datetime.now() - timedelta(days=3)
                 date_to = datetime.now() + timedelta(hours=48) 
                 
                 # Use safe_mt5_call to prevent blocking/threading issues
                 deals = await safe_mt5_call(mt5.history_deals_get, date_from, date_to)
                 
                 if deals:
                     items_to_sync = []
                     # Get Offset
                     time_offset = mt5_state.get("time_offset", 7200)
                     
                     count_new = 0
                     for d in deals:
                         if d.entry == 1 or d.entry == 2: # Out or OutBy
                             # Adjust timestamp to Local Time
                             local_ts = d.time - time_offset
                             # Extract Reason from Comment ("Spidy: Reason")
                             raw_comment = d.comment
                             exit_reason = "Manual/User" 
                             if raw_comment:
                                 if "Spidy:" in raw_comment:
                                      exit_reason = raw_comment.replace("Spidy:", "").strip()
                                 else:
                                      exit_reason = raw_comment 

                                 # Override with Authoritative Deal Reason Code
                                 rc = d.reason
                                 # if rc == 0: exit_reason = "User" # DON'T OVERRIDE SPECIFIC COMMENT
                                 if rc == 3: exit_reason = "Bot"
                                 elif rc == 4: exit_reason = "Stop Loss"
                                 elif rc == 5: exit_reason = "Take Profit"
                                 elif rc == 6: exit_reason = "Stop Out" 

                             items_to_sync.append({
                                   "ticket": d.position_id,
                                   "symbol": d.symbol,
                                   "type": "BUY" if d.type == 0 else "SELL",
                                   "volume": d.volume,
                                   "price": d.price,
                                   "profit": d.profit + d.swap + d.commission,
                                   "time": datetime.fromtimestamp(local_ts).strftime("%Y-%m-%d %H:%M:%S"),
                                   "reason": exit_reason,
                                   "comment": d.comment
                             })
                     
                     if items_to_sync:
                          # Sync to DB
                          await loop.run_in_executor(None, financial_db.sync_from_mt5_history, items_to_sync)

                     # UPDATE DAILY PNL STATE (Kill Switch Feeder)
                     # Run every time we fetch deals, regardless of sync items
                     gw_pnl = await loop.run_in_executor(None, financial_db.get_daily_pnl)
                     mt5_state["daily_pnl"] = gw_pnl
                     # print(f"DEBUG: Daily PnL Updated: {gw_pnl}") 
                     if len(items_to_sync) > 0 and datetime.now().second < 5:
                         pass # prevent spam
                             
             await asyncio.sleep(5.0) # Check every 5s (Relaxed from 1s to allow DB time)
             
        except Exception as e:
            print(f"History Sync Error: {e}")
            await asyncio.sleep(5)

@app.post("/reset_stops")
async def reset_stops(api_key: str = Depends(verify_api_key)):
    """Reset to standard risk."""
    risk_settings["atr_multiplier"] = 4.0
    risk_settings["mode"] = "STANDARD"
    await broadcast_log("INFO: Risk settings reset to STANDARD.")
    save_settings() # Persist
    return {"status": "RESET", "multiplier": 2.0}

@app.post("/tighten_stops")
async def tighten_stops(api_key: str = Depends(verify_api_key)):
    """Tighten risk settings (Profit Guardian TIGHT mode)."""
    risk_settings["atr_multiplier"] = 1.5 # Stricter trailing
    risk_settings["mode"] = "TIGHT"
    await broadcast_log("mode: TIGHT | atr_multiplier: 1.5")
    save_settings()
    return {"status": "TIGHTENED", "multiplier": 1.5}

@app.post("/settings/auto_secure")
async def update_auto_secure(payload: dict = Body(...), api_key: str = Depends(verify_api_key)):
    """
    Update Auto-Secure settings.
    Payload: { "enabled": bool, "threshold": float }
    """
    manual_enable = payload.get("enabled")
    if manual_enable is not None:
        risk_settings["auto_secure"]["enabled"] = bool(manual_enable)
        
    manual_thresh = payload.get("threshold")
    if manual_thresh is not None:
        risk_settings["auto_secure"]["threshold"] = float(manual_thresh)
        
    status = "ENABLED" if risk_settings["auto_secure"]["enabled"] else "DISABLED"
    thresh = risk_settings["auto_secure"]["threshold"]
    
    
    await broadcast_log(f"SETTINGS: Auto-Secure {status} (Target: ${thresh})")
    save_settings() # Persist
    return {"status": "UPDATED", "config": risk_settings["auto_secure"]}


# REMOVED: Duplicate /set_sentiment (broken — referenced undefined 'new_sentiment')
# Canonical version is at line ~1575

@app.post("/debug/force_sync")
async def debug_force_sync():
    """Manually trigger history sync."""
    if not HAS_MT5 or not mt5_state["connected"]:
        return {"error": "MT5 Not Connected"}
        
    ts_from = datetime.now().timestamp() - 86400 * 2 # Last 48 hours to be safe
    date_from = datetime.fromtimestamp(ts_from)
    
    loop = asyncio.get_running_loop()
    deals = await loop.run_in_executor(None, mt5.history_deals_get, date_from, datetime.now())
    
    if deals:
        deals_data = []
        for d in deals:
            if d.entry == 1 or d.entry == 2:
                 deals_data.append({
                     "ticket": d.position_id,
                     "symbol": d.symbol,
                     "type": "BUY" if d.type == 0 else "SELL",
                     "volume": d.volume,
                     "price": d.price,
                     "profit": d.profit + d.swap + d.commission,
                     "time": datetime.fromtimestamp(d.time).strftime("%Y-%m-%d %H:%M:%S")
                 })
        
        if deals_data:
            await loop.run_in_executor(None, financial_db.sync_from_mt5_history, deals_data)
            return {"status": "Synced", "count": len(deals_data)}
            
    return {"status": "No Deals Found"}

# --- MISSING DASHBOARD ENDPOINTS ---

@app.post("/toggle_auto")
async def toggle_auto(payload: dict = Body(...), api_key: str = Depends(verify_api_key)):
    """Toggles Auto-Trading On/Off."""
    enable = payload.get("enable", True)
    auto_trade_state["technical"] = technical_cache
    
    # Verbose Log (Heartbeat)
    count = len(technical_cache)
    if count > 0:
        await broadcast_log(f"INFO: Technical Analysis Updated for {count} symbols.")
    
    # Update Persistence
    risk_settings["auto_trade_enabled"] = enable
    save_settings()
    
    # Update In-Memory State (Critical Fix)
    auto_trade_state["running"] = enable
    
    status_str = "ENABLED" if enable else "DISABLED"
    await broadcast_log(f"INFO: Auto-Trading {status_str}")
    return {"status": status_str, "running": enable}

# REMOVED: Duplicate /close_trade endpoint (canonical version with better validation is at line ~1422)
# REMOVED: Duplicate /close_all_trades endpoint (canonical version with background task is at line ~1513)


@app.get("/status")
def get_status():
    mt5_state["auto_trading"] = auto_trade_state["running"]
    # Inject Analysis Data
    mt5_state["analysis"] = auto_trade_state.get("analysis", {})
    mt5_state["sentiment"] = auto_trade_state.get("sentiment", "NEUTRAL") # <-- Expose Sentiment
    mt5_state["oil"] = auto_trade_state.get("oil", {}) # <--- Expose Oil
    mt5_state["dxy"] = auto_trade_state.get("dxy", {}) # <--- Expose DXY
    mt5_state["risk_settings"] = risk_settings

    # --- REAL-TIME UPDATE LOGIC ---
    if HAS_MT5 and mt5_state["connected"]:
        # 1. Update Account Info
        account_info = mt5.account_info()
        if account_info:
            mt5_state["equity"] = round(account_info.equity, 2)
            mt5_state["balance"] = round(account_info.balance, 2)
            mt5_state["profit"] = account_info.profit

        # 2. Update Positions
        positions = mt5.positions_get()
        mt5_state["positions"] = []
        if positions:
            for pos in positions:
                # Use dynamic offset
                time_offset = mt5_state.get("time_offset", 7200)
                local_ts = pos.time - time_offset
                # Calculate standardized ROI for frontend
                comm = getattr(pos, 'commission', 0.0)
                swap = getattr(pos, 'swap', 0.0)
                net_profit_roi = pos.profit + comm + swap
                margin = (pos.volume if getattr(pos, 'volume', 0) > 0 else 0.01) * 200.0
                roi = (net_profit_roi / margin) * 100.0 if margin > 0 else 0.0

                mt5_state["positions"].append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == 0 else "SELL",
                    "volume": pos.volume,
                    "price": pos.price_open,
                    "profit": pos.profit,
                    "roi": roi,
                    "time": str(datetime.fromtimestamp(local_ts))
                })
    # -------------------------------
    
    # Check Weekend (5=Sat, 6=Sun)
    now = datetime.now()
    day_of_week = now.weekday()
    if day_of_week >= 5:
        mt5_state["market_status"] = "CLOSED_WEEKEND"
    else:
        # Re-use Helper to update status if not weekend
        is_open = is_market_open() 
        # But we also want to keep the "Stalled" logic which is extra detail
        
        # Dynamic Market Check: Is data fresh?
        # Check EURUSD tick time
        status_label = "OPEN"
        if HAS_MT5 and mt5_state["connected"]:
            tick = mt5.symbol_info_tick("EURUSD") # Proxy for global market
            if tick:
                last_tick_ts = tick.time
                if (datetime.now().timestamp() - last_tick_ts) > 60: # No ticks for 60s
                     status_label = "STALLED / CLOSED"
            else:
                 status_label = "NO_DATA"
        
        mt5_state["market_status"] = status_label
        
    # Check Terminal Permission (Algo Trading Enabled?)
    if HAS_MT5 and mt5_state["connected"]:
        term_info = mt5.terminal_info()
        if term_info:
             mt5_state["trade_allowed"] = term_info.trade_allowed
             if not term_info.trade_allowed:
                 mt5_state["market_status"] = "ALGO_DISABLED" # Override status to warn user
    else:
        mt5_state["trade_allowed"] = True # Mock default

    mt5_state["server_time"] = now.strftime("%H:%M:%S")
    
    # Real Latency (Ping to Broker Server)
    if HAS_MT5 and mt5_state["connected"]:
        term = mt5.terminal_info()
        if term:
            mt5_state["latency"] = term.ping_last // 1000
        else:
            mt5_state["latency"] = -1
    else:
        mt5_state["latency"] = 24  # Mock

    # UPGRADE 1: Add positions_summary for quick dashboard stats
    positions = mt5_state.get("positions", [])
    mt5_state["positions_summary"] = {
        "count": len(positions),
        "total_pnl": round(sum(p.get("profit", 0.0) for p in positions), 2),
        "buy_count": sum(1 for p in positions if p.get("type") == "BUY"),
        "sell_count": sum(1 for p in positions if p.get("type") == "SELL"),
    }
        
    return mt5_state



# ── NEW: Market Intelligence Endpoint ────────────────────────────────────────
@app.get("/market_intelligence")
async def get_market_intelligence_endpoint():
    """
    Returns Fear & Greed Index + upcoming economic events + macro trading bias.
    Called by the Frontend MarketIntelligence panel every 30s.
    """
    if not HAS_MARKET_INTEL:
        return {"error": "Market Intelligence module not available", "fear_greed": {"score": 50, "label": "Neutral"}, "next_high_impact_event": {}}

    try:
        pulse = await asyncio.to_thread(get_market_pulse)
        # Also pull top headlines if news engine is active
        headlines = []
        if HAS_NEWS:
            try:
                raw = await asyncio.to_thread(news_engine.get_latest_headlines)
                headlines = raw[:5]  # Top 5 for the UI panel
            except Exception:
                pass
        pulse["top_headlines"] = headlines
        return pulse
    except Exception as e:
        return {"error": str(e)}


# ── NEW: Analytics Endpoint ───────────────────────────────────────────────────
@app.get("/analytics")
async def get_analytics_endpoint():
    """
    Returns today's trading performance statistics.
    Win rate, average profit/loss, trade count, and daily PnL.
    """
    try:
        history = financial_db.get_trade_history(limit=500)
        today_str = datetime.now().strftime("%Y-%m-%d")

        today_trades = [
            t for t in history
            if t.get("close_time", "").startswith(today_str) and t.get("profit") is not None
        ]

        total = len(today_trades)
        wins = [t for t in today_trades if float(t.get("profit", 0)) > 0]
        losses = [t for t in today_trades if float(t.get("profit", 0)) < 0]

        win_rate = round((len(wins) / total * 100), 1) if total > 0 else 0.0
        avg_profit = round(sum(float(t["profit"]) for t in wins) / len(wins), 2) if wins else 0.0
        avg_loss = round(sum(float(t["profit"]) for t in losses) / len(losses), 2) if losses else 0.0
        daily_pnl = round(sum(float(t.get("profit", 0)) for t in today_trades), 2)

        # All-time stats
        all_wins = [t for t in history if float(t.get("profit", 0)) > 0]
        all_total = len(history)
        all_win_rate = round((len(all_wins) / all_total * 100), 1) if all_total > 0 else 0.0

        return {
            "today": {
                "total_trades": total,
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": win_rate,
                "avg_profit": avg_profit,
                "avg_loss": avg_loss,
                "daily_pnl": daily_pnl,
            },
            "all_time": {
                "total_trades": all_total,
                "win_rate": all_win_rate,
            },
            "floating_pnl": round(mt5_state.get("profit", 0.0), 2),
            "balance": round(mt5_state.get("balance", 0.0), 2),
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
