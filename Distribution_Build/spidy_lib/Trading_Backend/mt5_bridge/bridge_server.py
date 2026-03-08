from fastapi import FastAPI, Body, WebSocket, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import json

import asyncio
import threading
from datetime import datetime
import financial_db # Import the new DB module
from economic_calendar import calendar # Import Economic Calendar

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    HAS_MT5 = False
    print("CRITICAL: MetaTrader5 module not found. Please install it.")


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("INFO: Auto-connecting to MT5...")
    financial_db.init_db() # Init Database
    await connect_mt5()
    asyncio.create_task(auto_trader_loop())
    asyncio.create_task(update_technical_indicators()) # Add Analysis Loop
    asyncio.create_task(trailing_stop_manager())
    asyncio.create_task(ai_general_loop()) # The General (Strategy Update)
    yield
    # Shutdown logic (optional)
    print("INFO: Shutting down Bridge...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock shared state (fallback)
mt5_state = {"connected": False, "equity": 10000.0}
clients = []
log_history = [] # Buffer for last 50 logs
technical_cache = {} # Cache for RSI/EMA: { "EURUSD": { "rsi": 55.4, "trend": "BULLISH", "ema": 1.0544, "updated": timestamp } }

log_history = [] # Buffer for last 50 logs

# Concurrency Control
ticket_lock = threading.Lock()
processing_tickets = set()


@app.get("/symbols")
def get_symbols():
    """Returns a list of tradable symbols."""
    # Default list
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "BTCUSD", "ETHUSD", "SP500", "US30", "NAS100"]
    
    # Needs to be tested if getting all symbols is too slow
    # if HAS_MT5 and mt5_state["connected"]:
    #    try:
    #        # limited fetch?
    #        pass 
    #    except:
    #        pass
            
    return {"symbols": symbols}

@app.get("/")
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

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    print(f"DEBUG: WebSocket Connection Request from {websocket.client}")
    await websocket.accept()
    print("DEBUG: WebSocket Accepted")
    clients.append(websocket)
    
    # Send history to new client
    for msg in log_history:
        try:
             await websocket.send_text(msg)
        except:
             pass
             
    try:
        while True:
            await asyncio.sleep(1) # Keep connection alive
    except:
        if websocket in clients:
            clients.remove(websocket)

async def broadcast_log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    formatted_msg = f"[{timestamp}] {message}"
    
    # Write to local file (append mode)
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, "system_logs.txt")
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(formatted_msg + "\n")
    except Exception as e:
        print(f"Log Write Error: {e}")

    # Add to history (keep last 50)
    log_history.append(formatted_msg)
    if len(log_history) > 50:
        log_history.pop(0)
    
    # Broadcast to all connected clients
    if not clients:
         print(f"DEBUG: No clients connected. Log buffered: {message[:30]}...")
    else:
         print(f"DEBUG: Broadcasting to {len(clients)} clients: {message[:30]}...")

    for client in clients:
        try:
            await client.send_text(formatted_msg)
        except:
            if client in clients:
                clients.remove(client)

@app.post("/connect")
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

async def update_technical_indicators():
    """Background loop to calculate RSI & Trend for active symbols"""
    print("INFO: Market Analyzer (Technical) Started.")
    while True:
        if not mt5_state["connected"] or not server_settings["auto_trade_enabled"]:
            await asyncio.sleep(5)
            continue
            
        try:
            # Get list of symbols we care about
            symbols = list(set([p['symbol'] for p in mt5_state.get('positions', [])] + 
                             ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US30", "BTCUSD"]))
            
            for symbol in symbols:
                # Get M1 bars for HFT context
                bars = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 60)
                if bars is None or len(bars) < 50:
                    continue
                    
                close_prices = [x['close'] for x in bars]
                current_price = close_prices[-1]
                
                # Calculate
                rsi = calculate_rsi(close_prices, 14)
                ema_50 = calculate_ema(close_prices, 50)
                
                # Determine Trend
                trend = "NEUTRAL"
                if current_price > ema_50:
                    trend = "BULLISH"
                elif current_price < ema_50:
                    trend = "BEARISH"
                
                # Store
                technical_cache[symbol] = {
                    "rsi": rsi,
                    "ema": ema_50,
                    "trend": trend,
                    "updated": datetime.now()
                }
                
                # Debug (Optional)
                # print(f"DEBUG: {symbol} RSI:{rsi:.1f} Trend:{trend}")
                
        except Exception as e:
            print(f"ERROR: Analysis Loop Failed: {e}")
            
        await asyncio.sleep(2) # Update every 2 seconds

# --- PREVIOUS CODE CONTINUES ---


# --- HELPER: Technical Analysis ---
def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    
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
            
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    if avg_loss == 0:
        return 100.0
        
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
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
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_adx(rates, period=14):
    """Calculates Average Directional Index (ADX)."""
    if len(rates) < period * 2:
        return 25.0 # Default to 'Trending' to avoid blocking if not enough data
        
    # Pre-calculating True Range and Directional Movement
    tr_list = []
    dm_plus_list = []
    dm_minus_list = []
    
    for i in range(1, len(rates)):
        high = rates[i]['high']
        low = rates[i]['low']
        prev_close = rates[i-1]['close']
        
        # True Range
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list.append(tr)
        
        # Directional Movement
        up_move = high - rates[i-1]['high']
        down_move = rates[i-1]['low'] - low
        
        if up_move > down_move and up_move > 0:
            dm_plus_list.append(up_move)
        else:
            dm_plus_list.append(0.0)
            
        if down_move > up_move and down_move > 0:
            dm_minus_list.append(down_move)
        else:
            dm_minus_list.append(0.0)
    
    # Smooth with EMA/Wilder's
    # Simplified Smoothing for cleanup
    def smooth(data, per):
        if not data: return 0.0
        val = sum(data[:per]) / per
        for d in data[per:]:
            val = (val * (per - 1) + d) / per
        return val

    tr_smooth = smooth(tr_list, period)
    dm_plus_smooth = smooth(dm_plus_list, period)
    dm_minus_smooth = smooth(dm_minus_list, period)
    
    if tr_smooth == 0: return 0.0
    
    di_plus = (dm_plus_smooth / tr_smooth) * 100
    di_minus = (dm_minus_smooth / tr_smooth) * 100
    
    dx = 0.0
    if (di_plus + di_minus) > 0:
        dx = (abs(di_plus - di_minus) / (di_plus + di_minus)) * 100
        
    # ADX is smoothed DX
    # We would need history of DX, for now we return DX as proxy for instant momentum
    # Or calculate rough ADX
    return dx # Returning DX for faster reaction to momentum shifts

async def update_technical_indicators():
    """Background loop to calculate RSI & Trend for active symbols"""
    print("INFO: Market Analyzer (Technical) Started.")
    while True:
        if not mt5_state["connected"]:
            await asyncio.sleep(5)
            continue
            
        try:
            # DYNAMIC LIST: Fetch all symbols visible in Market Watch
            # This ensures we analyze everything the user wants to trade (CADJPY, AUDJPY, etc.)
            mt5_symbols = mt5.symbols_get()
            if mt5_symbols:
                # Filter for visible only to save resources? 
                # mt5.symbols_get() returns all available on server? No, usually allows filtering.
                # standard call returns 'all' or 'all selected'? 
                # To get only Market Watch: mt5.symbols_get(group="*,!*") ? No.
                # Best way: Check .select property.
                symbols = [s.name for s in mt5_symbols if s.select]
            else:
                # Fallback
                symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US30", "BTCUSD", "USDCAD", "AUDUSD", "EURJPY", "GBPJPY", "CADJPY", "AUDJPY", "XAGUSD"]
            
            # Limit to prevent overload (e.g. max 30)
            # Prioritize standard list if too many, but for now scan all selected.
            
            for symbol in symbols:
                # ... existing analysis logic ...
                bars = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 70)
                if bars is None or len(bars) < 60:
                    continue
                    
                close_prices = [x['close'] for x in bars]
                current_price = close_prices[-1]
                
                # Prepare Rate List for ADX (Need High/Low)
                rates_list = [{'high': x['high'], 'low': x['low'], 'close': x['close']} for x in bars]
                
                rsi = calculate_rsi(close_prices, 14)
                ema_50 = calculate_ema(close_prices, 50)
                adx = calculate_adx(rates_list, 14)
                
                trend = "NEUTRAL"
                if current_price > ema_50: trend = "BULLISH"
                elif current_price < ema_50: trend = "BEARISH"
                
                technical_cache[symbol] = {
                    "rsi": rsi,
                    "ema": ema_50,
                    "adx": adx,
                    "trend": trend,
                    "updated": datetime.now()
                }
        except Exception as e:
            print(f"ERROR: Analysis Loop Failed: {e}")
            
        await asyncio.sleep(2)


async def connect_mt5():
    if HAS_MT5:
        # Attempts to connect, if fails, tries to launch from common paths
        path_to_try = None
        common_paths = [
            r"C:\Program Files\MetaTrader 5\terminal64.exe",
            r"C:\Program Files\MetaTrader 5\terminal.exe"
        ]
        
        # --- SMART CONNECT: Check existing first ---
        # Don't shutdown if we are already good
        if mt5.initialize():
            # Already initialized or essentially connected
            # Double check terminal info
            term_info = mt5.terminal_info()
            if term_info and term_info.connected:
                 await broadcast_log("INFO: Smart Connect: Already connected to MT5.")
                 # Fall through to update state below
            else:
                 # Not connected really, try clean shutdown
                 mt5.shutdown()
        else:
             mt5.shutdown()
        # ------------------------------------------
        
        # Check default first
        if not mt5.initialize():
            err_code = mt5.last_error()
            logger_msg = f"INFO: Standard Initialize failed ({err_code}), attempting specific paths..."
            await broadcast_log(logger_msg)
            
            # Try specific paths
            import os
            for p in common_paths:
                if os.path.exists(p):
                    await broadcast_log(f"INFO: Found MT5 at {p}, launching...")
                    if mt5.initialize(path=p):
                         path_to_try = p
                         break
            
        if not path_to_try and not mt5.initialize():
             logger_msg = f"INFO: Standard Initialize failed ({mt5.last_error()}). Attempting FORCE LAUNCH via subprocess..."
             await broadcast_log(logger_msg)
             
             # Force Launch
             import subprocess
             import time
             exe_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
             if os.path.exists(exe_path):
                 try:
                     subprocess.Popen(exe_path)
                     await broadcast_log("INFO: Process launched. Waiting 15s for MT5 to warm up...")
                     await asyncio.sleep(15) 
                     
                     # Retry Attach
                     if mt5.initialize():
                         await broadcast_log("SUCCESS: Connected after Force Launch.")
                     else:
                         raise Exception(f"Still failed after launch: {mt5.last_error()}")
                 except Exception as e:
                     await broadcast_log(f"ERROR: Force Launch failed: {e}")
                     return {"error": str(e)}
             else:
                 await broadcast_log(f"ERROR: MT5 not found at {exe_path}")
                 return {"error": "MT5 executable not found"}

        mt5_state["connected"] = True
        account_info = mt5.account_info()
        if account_info:
            mt5_state["equity"] = account_info.equity
            mt5_state["balance"] = account_info.balance
            mt5_state["profit"] = account_info.profit
            
            # Fetch Open Positions
            positions = mt5.positions_get()
            mt5_state["positions"] = []
            
            # Auto-calculate offset if possible, or use fixed
            # We observed Server is ~2h (7200s) ahead of Local. 
            # To show Local Time, we subtract 7200s.
            time_offset = 7200 
            
            if positions:
                for pos in positions:
                    # Adjust time to be Local-relative
                    local_ts = pos.time - time_offset
                    time_str = str(datetime.fromtimestamp(local_ts))
                    
                    # Ensure DB tracks this open position
                    # financial_db.save_trade(pos.ticket, pos.symbol, "BUY" if pos.type==0 else "SELL", pos.volume, pos.price_open, time_str)

                    mt5_state["positions"].append({
                        "ticket": pos.ticket,
                        "symbol": pos.symbol,
                        "type": "BUY" if pos.type == 0 else "SELL",
                        "volume": pos.volume,
                        "price": pos.price_open,
                        "profit": pos.profit,
                        "time": str(datetime.fromtimestamp(local_ts))
                    })
            
            await broadcast_log(f"INFO: MT5 Connected. Account: {account_info.login}")
        else:
            await broadcast_log("INFO: MT5 Connected (No account info)")
        
        return {"msg": "Connected to Real MT5"}
    else:
        # No Mock Fallback - Strict Real Data Only
        mt5_state["connected"] = False
        await broadcast_log("ERROR: MT5 Library missing or Connection Failed. Cannot trade.")
        return {"error": "MT5 Not Connected"}


# Helper: Check Filling Mode
def get_filling_mode(symbol):
    """Determines the correct filling mode for the symbol."""
    if not HAS_MT5: return mt5.ORDER_FILLING_FOK
    
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


# Helper: Check Market Status
def is_market_open():
    """Checks if market is open and trading is allowed."""
    # 1. Check Weekend (Saturday=5, Sunday=6)
    # Note: Market usually closes Friday 5PM EST and opens Sunday 5PM EST.
    # Simple check: If Saturday or Sunday (UTC/Local depending on sys), block.
    now = datetime.now()
    if now.weekday() >= 5: 
        mt5_state["market_status"] = "CLOSED_WEEKEND"
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

    # 2. Connection
    if not HAS_MT5 or not mt5_state["connected"]:
        return False, "MT5 Disconnected"

    # 3. Data Freshness (< 5s)
    # Note: tick.time_msc is int epoch ms. datetime.now().timestamp() is float seconds.
    # We compare in seconds.
    server_time = tick.time # timestamp in seconds
    local_time = datetime.now().timestamp()
    if (local_time - server_time) > 5.0:
        return False, f"Stale Data (Lag: {local_time - server_time:.2f}s)"

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
    
    # 5. Spread Check
    if tick.ask > 0:
        spread = tick.ask - tick.bid
        profit_points = spread / tick.ask
        if profit_points > 0.0005: # 0.05% Max Spread (Configurable?)
            return False, f"Spread too high ({profit_points:.5f})"
            
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

    # 1. Symbol Select
    if not mt5.symbol_select(symbol, True):
        await broadcast_log(f"ERROR: Symbol {symbol} not found")
        return False

    # 2. Price & Type
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        await broadcast_log(f"ERROR: No info for {symbol}")
        return False

    # 2.5 Volume Correction (Fix for 10014)
    # If requested volume < min_volume, we must adjust or reject.
    # We'll auto-adjust to min_volume to ensure trade execution if safe.
    if volume < symbol_info.volume_min:
        await broadcast_log(f"WARNING: Volume {volume} too small for {symbol}. Adjusting to {symbol_info.volume_min}")
        volume = symbol_info.volume_min
    
    # Check Max Volume just in case
    # if volume > symbol_info.volume_max: ...

    if action == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = symbol_info.ask
    else:
        order_type = mt5.ORDER_TYPE_SELL
        price = symbol_info.bid

    # 3. Request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": 234000,
        "comment": "Spidy AI SMA",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": get_filling_mode(symbol), # Dynamic Filling Mode
    }

    # 4. Send
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        await broadcast_log(f"ERROR: Auto-Trade Order Failed: {result.comment} ({result.retcode})")
        return False
    
    await broadcast_log(f"SUCCESS: Auto-Trade {action} Filled @ {price}")
    
    # Save to DB
    trade_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    financial_db.save_trade(result.order, symbol, action, volume, price, trade_time, strategy=strategy_tag)
    
    return True

@app.post("/trade")
async def execute_trade(signal: dict = Body(...)):
    if not mt5_state["connected"]:
        await broadcast_log("ERROR: Trade failed. MT5 not connected.")
        return {"error": "MT5 not connected"}
    
    # Use the refactored logic via the same internal path? 
    # Actually, let's keep the API endpoint wrapper simple and use the internal function if possible,
    # Or just keep separate to avoid breaking changes if I missed something above.
    # For now, I will REUSE the new function to ensure consistency.
    
    action = signal.get('action', 'ORDER').upper()
    symbol = signal.get('symbol', 'EURUSD').upper()
    volume = float(signal.get('volume', 0.01))
    
    log_msg = f"TRADE: Received Manual {action} on {symbol} (Vol: {volume})"
    print(log_msg)
    await broadcast_log(log_msg)
    
    await broadcast_log(log_msg)
    
    success = await place_market_order(symbol, action, volume, strategy_tag="Manual_API")
    if success:
        return {"status": "FILLED"}
    else:
        return {"status": "FAILED"}


# Helper: Internal Close Position (Sync)
def _close_position_sync(ticket: int, symbol: str):
    """Synchronous blocking function to close a position."""
    
    # 1. Concurrency Check
    with ticket_lock:
        if ticket in processing_tickets:
             return False, "BUSY_PROCESSING", 0.0
        processing_tickets.add(ticket)
    
    try:
        if not mt5_state["connected"] or not HAS_MT5:
            return False, "MT5_NOT_CONNECTED", 0.0

        # Check if position exists
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            return False, "NOT_FOUND", 0.0
        
        pos = positions[0]
        
        # Close means opening an opposing order
        action = mt5.TRADE_ACTION_DEAL
        type_op = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if type_op == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask
        
        request = {
            "action": action,
            "symbol": symbol,
            "volume": pos.volume,
            "type": type_op,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 234000,
            "comment": "Spidy AI Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": get_filling_mode(symbol),
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return False, f"{result.comment} ({result.retcode})", 0.0
            
        return True, "CLOSED", price
        
    finally:
        # Always release the ticket
        with ticket_lock:
             processing_tickets.discard(ticket)


async def close_position(ticket: int, symbol: str):
    """Async wrapper for closing position."""
    loop = asyncio.get_running_loop()
    
    # Run blocking call in thread
    success, msg, price = await loop.run_in_executor(None, _close_position_sync, ticket, symbol)
    
    if success:
        if msg == "MOCK_CLOSE":
             await broadcast_log(f"MOCK: Closed position {ticket}")
        else:
             await broadcast_log(f"SUCCESS: Closed Position {ticket} @ {price}")
             # Update DB
             close_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
             financial_db.update_trade_close(ticket, price, 0.0, close_time)
    else:
        if msg == "BUSY_PROCESSING":
             # Optional: Don't spam log for busy
             pass
        elif msg == "NOT_FOUND":
             await broadcast_log(f"ERROR: Position {ticket} not found to close.")
        else:
             await broadcast_log(f"ERROR: Close Failed: {msg}")

             
    return success


@app.post("/close_trade")
async def api_close_trade(payload: dict = Body(...)):
    """API Endpoint to close a trade."""
    ticket = int(payload.get("ticket"))
    symbol = payload.get("symbol")
    
    if not ticket or not symbol:
        return {"error": "Missing ticket or symbol"}
        
    success = await close_position(ticket, symbol)
    if success:
        return {"status": "CLOSED", "ticket": ticket}
    else:
        return {"status": "FAILED", "ticket": ticket}

async def _process_close_all_background(profitable_only: bool):
    """Background task to close positions."""
    await broadcast_log(f"COMMAND: Starting Close All (Profitable Only: {profitable_only})...")
    
    if not mt5_state["connected"] and HAS_MT5:
         await broadcast_log("ERROR: MT5 Not Connected")
         return 

    closed_count = 0
    # 1. Get Current positions
    if HAS_MT5:
        # Offload positions_get to thread
        loop = asyncio.get_running_loop()
        positions = await loop.run_in_executor(None, mt5.positions_get)
        
        if positions:
            for pos in positions:
                should_close = True
                
                # Filter by Profit
                if profitable_only and pos.profit <= 0:
                    should_close = False
                    
                if should_close:
                    await broadcast_log(f"CLOSING: Ticket {pos.ticket} (Profit: {pos.profit})")
                    if await close_position(pos.ticket, pos.symbol):
                        closed_count += 1
                        # Small delay to prevent flooding
                        await asyncio.sleep(0.1)
            # Small delay to prevent flooding
                        await asyncio.sleep(0.1)
    else:
        await broadcast_log("ERROR: Cannot Close All. MT5 not connected.")

        
    await broadcast_log(f"COMMAND: Close All Completed. Total Closed: {closed_count}")

@app.post("/close_all_trades")
async def api_close_all_trades(background_tasks: BackgroundTasks, payload: dict = Body(...)):
    """
    Closes all trades match criteria (Background Task).
    payload: { "profitable_only": bool }
    """
    profitable_only = payload.get("profitable_only", False)
    
    # Start in background
    background_tasks.add_task(_process_close_all_background, profitable_only)
    
    return {"status": "ACCEPTED", "message": "Close All started in background."}


async def enforce_sentiment_bias(sentiment):
    """
    Closes existing positions that contradict the new global sentiment.
    Example: If Sentiment -> BEARISH, Close all BUYS.
    """

    if not HAS_MT5 or not mt5.initialize(): return
    if not is_market_open(): return # Safety Check

    await broadcast_log(f"🛡️ DEFENSE: Enforcing Sentiment Bias: {sentiment}")
    
    positions = mt5.positions_get()
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
            await broadcast_log(f"⚠️ CLOSING {pos.symbol} (Ticket {pos.ticket}) due to {reason}")
            await close_position(pos.ticket, pos.symbol)
            closed_count += 1
            await asyncio.sleep(0.1) # Throttle
            
    if closed_count > 0:
        await broadcast_log(f"🛡️ DEFENSE: Closed {closed_count} counter-trend positions.")




@app.get("/symbols")
def get_symbols():
    if HAS_MT5 and mt5_state["connected"]:
        # Fetch all symbols (or a subset to be safe/fast)
        # getting all might be slow, let's try getting all and filtering for major ones if needed
        # For now, let's just return all capable of being selected
        symbols = mt5.symbols_get()
        if symbols:
            # simple list of names
            return {"symbols": [s.name for s in symbols]}
        else:
             return {"symbols": []}
    else:
        # No Mock List
        return {"symbols": []}

# Auto-Trading State
auto_trade_state = {
    "running": True, 
    "analysis": {}, 
    "sentiment": "NEUTRAL",
    "bias": "NEUTRAL", # Approved Trade Direction: BULLISH_ONLY, BEARISH_ONLY, NEUTRAL (Both)
    "macro_context": "Normal" # Or "Unstable"
}

@app.post("/set_sentiment")
async def set_sentiment(payload: dict = Body(...)):
    """Updates the global market sentiment (driven by AI)."""
    s = payload.get("sentiment", "NEUTRAL").upper()
    auto_trade_state["sentiment"] = s
    await broadcast_log(f"SENTIMENT: Updated Global Sentiment to {s}")
    return {"status": "OK", "sentiment": s}

# Persistence File
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "server_settings.json")

# Default Settings
DEFAULT_SETTINGS = {
    "atr_multiplier": 2.0, # Default wide stop
    "fixed_lot_size": 0.02, # Configurable Lot Size
    "scalp_target_usd": 10.0, # Configurable Profit Target
    "breakeven_pct": 0.005, # 0.5% profit triggers BE
    "mode": "STANDARD", # or "TIGHT"
    "auto_secure": {
        "enabled": False,
        "threshold": 10.0 # Default $10 profit target to close
    }
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
        print(f"Error saving settings: {e}")

# Initialize Settings
risk_settings = load_settings()

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
                "type_filling": mt5.ORDER_FILLING_RETURN,
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
                "type_filling": mt5.ORDER_FILLING_RETURN,
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

# Import News Fetcher
import sys
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../AI_Engine/internet_gathering")))
    from news_fetcher import NewsFetcher
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../AI_Engine/strategy_optimizer")))
    from pack_generator import StrategyOptimizer
    
    news_engine = NewsFetcher()
    strategy_engine = StrategyOptimizer()
    HAS_NEWS = True
except ImportError as e:
    print(f"WARNING: NewsFetcher not found. AI General will be disabled. Error: {e}")
    HAS_NEWS = False
except Exception as e:
    print(f"WARNING: Unexpected error importing NewsFetcher: {e}")
    HAS_NEWS = False

async def ai_general_loop():
    """
    The General (Master Logic) - Uses REAL Internet Information via NewsFetcher.
    Updates global sentiment based on Yahoo Finance Data.
    """
    print("INFO: AI General (Real-Time News) Started.")
    
    if not HAS_NEWS:
        await broadcast_log("WARNING: NewsFetcher missing. Defaulting to NEUTRAL mode.")
        return
        
    # Initial State
    last_sentiment = "NEUTRAL"

    while True:
        try:
            # 1. Fetch Real News

            headlines = await asyncio.to_thread(news_engine.get_latest_headlines)
            
            # 1b. Fetch GLOBAL SHIELD (DXY)
            dxy_data = await asyncio.to_thread(news_engine.get_dxy_status)
            auto_trade_state["dxy"] = dxy_data
            
            if headlines:
                # 2. Analyze Aggregate Sentiment
                bullish_score = 0
                bearish_score = 0
                
                log_digest = "NEWS UPDATE:\n"
                
                for h in headlines[:5]: # Check top 5
                    s = h.get('sentiment', 'neutral')
                    log_digest += f"- {h['title']} ({s})\n"
                    
                    if s == "positive": bullish_score += 1
                    if s == "negative": bearish_score += 1
                
                # 3. Determine Mode
                new_sentiment = "NEUTRAL"
                if bullish_score > bearish_score:
                    new_sentiment = "BULLISH"
                elif bearish_score > bullish_score:
                    new_sentiment = "BEARISH"
                
                # Update State only if changed
                if new_sentiment != auto_trade_state.get("sentiment"):
                     auto_trade_state["sentiment"] = new_sentiment
                     msg = f"GLOBAL SENTIMENT SHIFT: {new_sentiment} (Bull:{bullish_score} Bear:{bearish_score})"
                     await broadcast_log(msg)
                
                # Log Shield Status
                if dxy_data:
                     try:
                         dxy_status = dxy_data.get("status")
                         dxy_change = dxy_data.get("change_pct", 0.0)
                         await broadcast_log(f"SHIELD: DXY is {dxy_status} ({dxy_change}%)")
                     except:
                         pass
                         
                # 4. ACTIVE DEFENSE: Enforce Sentiment Bias
                if new_sentiment != last_sentiment:
                     await enforce_sentiment_bias(new_sentiment)
                     last_sentiment = new_sentiment

                # 5. STRATEGY OPTIMIZATION (Dynamic Risk)
                if headlines:
                    pack = strategy_engine.generate_strategy_pack(headlines)
                    
                    # Apply Strategy Pack
                    new_mode = pack.get("mode", "STANDARD")
                    risk_percent = pack.get("risk_percent", 1.0)
                    
                    # Map to Bridge Settings
                    # Risk Percent 1.5 -> Lot 0.03
                    # Risk Percent 0.5 -> Lot 0.01
                    base_lot = 0.02
                    new_lot = round(base_lot * risk_percent, 2)
                    if new_lot < 0.01: new_lot = 0.01
                    
                    if risk_settings.get("mode") != new_mode:
                        await broadcast_log(f"🧠 STRATEGY UPDATE: Switching to {new_mode} Mode (Lot: {new_lot})")
                        risk_settings["mode"] = new_mode if new_mode in ["STANDARD", "TIGHT"] else "STANDARD"
                        risk_settings["fixed_lot_size"] = new_lot
                        save_settings()

            else:
                pass

            
            # 2. Check Time of Day (Liquidity)
            current_hour = datetime.now().hour
            if 8 <= current_hour <= 17:
                 auto_trade_state["macro_context"] = "High Liquidity"
            else:
                 auto_trade_state["macro_context"] = "Low Liquidity"
                 
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
    logger_msg = "INFO: Spidy HFT Scalper + Spider Web Started (Speed: 0.1s)"
    print(logger_msg)
    await broadcast_log(logger_msg)
    
    # STARTUP WARMUP: Prevent immediate trading on bad data/noise
    warmup_duration = 15 # Seconds
    start_time = datetime.now().timestamp()
    await broadcast_log(f"INFO: System Warmup Active. Trading paused for {warmup_duration}s...")
    
    # Symbols to HFT on
    symbols_to_scan = []
    
    # Initial scan
    if HAS_MT5 and mt5.initialize():
        # Get ALL symbols in Market Watch
        symbols_info = mt5.symbols_get() # This gets all available in server, we want Market Watch
        # actually symbols_total could be huge. We only want 'selected' 
        # But symbols_get() returns all. We can filter by select=True IF we used symbol_info but iterating all is slow.
        # Efficient way: mt5.symbols_get() is fine if we assume user didn't select 1000 symbols.
        # Better: mt5.symbols_total() -> NO.
        # Correct: mt5.symbols_get(group="*,!*EUR*,!*GB*") NO.
        
        # We will use this approach: Get all, filter by 'selected' or just trust the user's setup if possible.
        # Actually mt5.symbols_get() allows specific group but not 'selected'.
        # Wait, the best way for "Market Watch" is ensuring we only trade what we can see.
        # Let's try to get all and filter manually or just assume a reasonable set. 
        # Optimally: We rely on what the user enabled in MT5.
        
        # Let's iterate all known symbols? No too slow.
        # We will poll `mt5.symbols_get()` which creates a list of all symbols on server? No.
        
        # REVISION: We can't easily get "Market Watch Only" via Python API efficiently without iterating.
        # So we will define a "Universal List" of majors + a way for user to add?
        # OR we just re-scan every minute.
        pass
    
    # To be safe and fast, we'll start with Common + Crypto and check if selected.
    # If user wants more, they should ensure they are selected.
    
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
                if datetime.now().second % 5 == 0:
                     print("DEBUG: Warmup... Collecting Data")
                await asyncio.sleep(1)
                continue
            elif (datetime.now().timestamp() - start_time) < (warmup_duration + 2):
                 # One-time log after warmup
                 pass # We rely on normal logs or add a flag if needed, effectively "Active" now

            # 0. STRICT MARKET CHECK
            if not is_market_open():
                if datetime.now().second % 10 == 0: # Log only occasionally
                    print("INFO: Market Closed. HFT Sleeping...")
                await asyncio.sleep(5)
                continue

            # 0. Refresh Symbol List (Every 10s to pick up new Market Watch items)
            if datetime.now().timestamp() - symbols_refresh_time > 10:
                # We fetch ALL symbols that are selected (=Visible in Market Watch)
                # Note: symbols_get returns ALL if no arg. 
                # There is no direct "get_selected" in basic API. 
                # Workaround: We iterate checking symbol_info(s).selected? Slow.
                
                # Faster Workaround: We ask MT5 for all, filtering is hard.
                # Let's stick to a robust list of 50 common pairs + Crypto.
                # OR we accept that we only scan what we defined.
                
                # USER REQUEST: "Analyas ALL trades"
                # Let's try to fetch all symbols present in MarketWatch via `mt5.symbols_get()`? No.
                
                # IMPLEMENTATION: We will blindly try the top 50 most common tickers. 
                # If they are selected, we trade them.
                
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
                
                # This is still not "ALL". 
                # To truly get ALL "Market Watch" symbols efficiently:
                # We can loop through `mt5.symbols_total()`? No.
                
                # Let's go with the candidate list for safety + speed. 
                # Scanning 10000 symbols every 0.1s is impossible for Python.
                
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
                
                # SENSITIVITY ADJUSTMENT: Increased from 0.001% to 0.005% to reduce noise
                is_pump = pct_change > 0.00005 
                is_dump = pct_change < -0.00005
                
                signal = None
                
                # --- STRATEGY: HFT SNIPER ---
                # Bias/Shield Logic is now properly handled in validate_entry
                # But we need raw signal first
                
                if is_pump: signal = "BUY"
                if is_dump: signal = "SELL"
                
                # Lead-Lag Logic (EURUSD -> XAUUSD)
                # ... (Kept existing visual logic, but signal validation will happen below)
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
                     is_valid, reason = validate_entry(symbol, signal, tick, "HFT")
                     
                     if is_valid:
                         # Extra HFT Check: Max Positions
                         open_positions = mt5.positions_get(symbol=symbol)
                         if not open_positions or len(open_positions) < 3:
                             
                             logger_tag = f"HFT_Vel_{pct_change*10000:.2f}"
                             await broadcast_log(f"HFT: {signal} {symbol} (Vel {pct_change*100:.5f}%)")
                             
                             # Execute!
                             lot_size = risk_settings.get("fixed_lot_size", 0.01)
                             await place_market_order(symbol, signal, volume=lot_size, strategy_tag=logger_tag)
                             
                             # Cooldown
                             tick_state[symbol]["last_price"] = curr_price
                             await asyncio.sleep(0.5) 
                             continue
                     else:
                         # Log rejection only if significant signal (debug)
                         # await broadcast_log(f"HFT REJECT: {signal} {symbol} -> {reason}")
                         pass

                # Update State
                tick_state[symbol]["last_price"] = curr_price
                
                
            # --- STRATEGY: TECHNICAL SCANNER (Every 1 Second) ---
            # Analyzes RSI / Trend for Symbols
            if datetime.now().timestamp() - scanner_last_update > 1.0:
                 for symbol in symbols_to_scan:
                     # Skip if recent HFT action (optional, but let's be aggressive)
                     
                     # 1. Fetch M15 Data
                     rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M15, 0, 20)
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
                         # We fetch fresh tick for validation
                         tick = current_ticks.get(symbol) or mt5.symbol_info_tick(symbol)
                         if not tick: continue
                         
                         is_valid, reason = validate_entry(symbol, scan_signal, tick, "Scanner")
                         
                         if is_valid:
                             # Check max positions
                             open_positions = mt5.positions_get(symbol=symbol)
                             if not open_positions or len(open_positions) < 3:
                                  tag = f"RSI_{rsi:.1f}_{trend}"
                                  await broadcast_log(f"SCANNER: {scan_signal} {symbol} (RSI {rsi:.1f}, {trend})")
                                  
                                  lot = risk_settings.get("fixed_lot_size", 0.01)
                                  await place_market_order(symbol, scan_signal, volume=lot, strategy_tag=tag)
                                  
                 scanner_last_update = datetime.now().timestamp()


            # Update Spider Web (Grid) every 10 seconds (Strategy 2)
            # WE PASS THE TICKS WE JUST COLLECTED TO SAVE TIME
            if datetime.now().timestamp() - grid_last_update > 10:
                await update_spider_web(symbols_to_scan, shared_ticks=current_ticks)
                grid_last_update = datetime.now().timestamp()

            # EXTREME SPEED
            await asyncio.sleep(0.1) # 100ms Loop

        except Exception as e:
            print(f"HFT Error: {e}")
            await asyncio.sleep(1)

# Startup logic moved to lifespan
# @app.on_event("startup") deprecated

# Helper: Sync Single Position Processing (Guardian)
def _process_single_pos_guardian_sync(pos_ticket):
    """Sync function to check and update stops for ONE position."""
    if not mt5_state["connected"] or not HAS_MT5:
        return

    # Re-fetch position to be fresh and safe
    positions = mt5.positions_get(ticket=pos_ticket)
    if not positions:
        return

    pos = positions[0]
    symbol = pos.symbol
    
    # --- MICRO SCALP EXIT (HFT Mode) ---
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        # SENSIBLE HFT TARGET: Minimum $0.50 guaranteed
        target_usd = risk_settings.get("scalp_target_usd", 0.50)
        if target_usd < 0.50: target_usd = 0.50 # Force minimum catch
        
        # Hard Take Profit (Scalp)
        if pos.profit >= target_usd:
             # LOG for verification
             print(f"DEBUG: Micro Scalp Exit {symbol} Profit:{pos.profit}")
             res, msg, p = _close_position_sync(pos.ticket, symbol)
             return

    # Fetch Data for ATR (M5 timeframe)
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 20)
    if rates is None or len(rates) < 15: return

    # ... (ATR Calc omitted for brevity, assumed context match) ...
    # We resume at Breakeven Logic
    
    current_price = mt5.symbol_info_tick(symbol).bid if pos.type == 0 else mt5.symbol_info_tick(symbol).ask
    entry_price = pos.price_open
    
    # --- 0. Get Symbol Specs for Dynamic Pips ---
    sym_info = mt5.symbol_info(symbol)
    if not sym_info: return
    
    point = sym_info.point 
    
    target_pips_dist = 150 * point # 150 points = 15 pips (High clearance)
    secure_pips_dist = 50 * point  # 50 points = 5 pips (Solid profit)
    step_trail_dist = 100 * point  

    # --- 1. Breakeven Trigger ---
    profit_dist = current_price - entry_price if pos.type == 0 else entry_price - current_price
    
    # Define Distances
    # Stage 1: Early Protection (Trigger > 8 pips, Secure 3 pips)
    early_trigger = 80 * point 
    early_secure = 30 * point
    
    # Stage 2: Solid Verified (Trigger > 15 pips, Secure 5 pips)
    # Using target_pips_dist and secure_pips_dist from variables above
    
    new_sl = 0.0
    reason_log = ""

    # Priority Check: Higher profit overrides lower
    if profit_dist > target_pips_dist:
         # Stage 2: Secure 5 pips
         new_sl = entry_price + (secure_pips_dist if pos.type==0 else -secure_pips_dist)
         reason_log = "Stage 2 (Solid Profit)"
         
         # Step Trailing
         if profit_dist > step_trail_dist:
               lock_dist = profit_dist * 0.60
               new_sl = entry_price + lock_dist if pos.type == 0 else entry_price - lock_dist
               reason_log = "Step Trail (60% Locked)"
               
    elif profit_dist > early_trigger:
         # Stage 1: Secure 3 pips (Crucial for preventing -0.01)
         new_sl = entry_price + (early_secure if pos.type==0 else -early_secure)
         reason_log = "Stage 1 (Early Secure)"
    
    if new_sl != 0.0:
            # Only update if it TIGHTENS the stop (Higher for Buy, Lower for Sell)
            # And SL is not already better
            current_sl = pos.sl
            should_update = False
            
            if pos.type == 0: 
                if (current_sl == 0.0) or (new_sl > current_sl): should_update = True
            else: 
                if (current_sl == 0.0) or (new_sl < current_sl): should_update = True
                     
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

    # --- 3. Auto-Secure Profit Trigger (Hard Take Profit) ---
    secure_conf = risk_settings.get("auto_secure", {})
    if secure_conf.get("enabled"):
            threshold = float(secure_conf.get("threshold", 10.0))
            if pos.profit >= threshold:
                # Close Logic Duplicate for Sync
                _close_position_sync(pos.ticket, symbol)


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
                 positions = await loop.run_in_executor(None, mt5.positions_get)
                 
                 if positions:
                     for pos in positions:
                         # Process Each in Thread
                         await loop.run_in_executor(None, _process_single_pos_guardian_sync, pos.ticket)
                         # Yield to event loop to allow other requests (like Close All, Trade) to sneak in
                         await asyncio.sleep(0.01) 
                 
            await asyncio.sleep(0.1) # Check every 100ms (High Speed Guardian)
            
        except Exception as e:
            # print(f"Trailing Error: {e}")
            await asyncio.sleep(5)


@app.post("/tighten_stops")
async def tighten_stops():
    """AI Trigger to enter "Risk-Free" mode (Tighter Stops)."""
    risk_settings["atr_multiplier"] = 1.2 # Tighten from 2.0 to 1.2
    risk_settings["mode"] = "TIGHT"
    msg = "WARNING: Market volatility detected. Profit Guardian set to TIGHT mode (Multiplier 1.2)."
    await broadcast_log(msg)
    save_settings() # Persist
    return {"status": "TIGHTENED", "multiplier": 1.2}

@app.post("/reset_stops")
async def reset_stops():
    """Reset to standard risk."""
    risk_settings["atr_multiplier"] = 4.0
    risk_settings["mode"] = "STANDARD"
    await broadcast_log("INFO: Risk settings reset to STANDARD.")
    save_settings() # Persist
    return {"status": "RESET", "multiplier": 2.0}

@app.post("/settings/auto_secure")
async def update_auto_secure(payload: dict = Body(...)):
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


@app.post("/toggle_auto")
async def toggle_auto_trade(enable: bool = Body(..., embed=True)):
    auto_trade_state["running"] = enable
    status = "ENABLED" if enable else "DISABLED"
    await broadcast_log(f"INFO: Auto-Trading {status}")
    return {"status": "success", "auto_trading": enable}

@app.get("/status")
def get_status():
    mt5_state["auto_trading"] = auto_trade_state["running"]
    # Inject Analysis Data
    mt5_state["analysis"] = auto_trade_state.get("analysis", {})
    mt5_state["sentiment"] = auto_trade_state.get("sentiment", "NEUTRAL") # <-- Expose Sentiment
    mt5_state["risk_settings"] = risk_settings

    # --- REAL-TIME UPDATE LOGIC ---
    if HAS_MT5 and mt5_state["connected"]:
        # 1. Update Account Info
        account_info = mt5.account_info()
        if account_info:
            mt5_state["equity"] = account_info.equity
            mt5_state["balance"] = account_info.balance
            mt5_state["profit"] = account_info.profit

        # 2. Update Positions
        positions = mt5.positions_get()
        mt5_state["positions"] = []
        time_offset = 7200 # Server is ahead
        
        if positions:
            for pos in positions:
                local_ts = pos.time - time_offset
                mt5_state["positions"].append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == 0 else "SELL",
                    "volume": pos.volume,
                    "price": pos.price_open,
                    "profit": pos.profit,
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
            mt5_state["latency"] = term.ping_last // 1000 # Microseconds to ms if high prec, usually is just int ms
        else:
            mt5_state["latency"] = -1
    else:
        mt5_state["latency"] = 24 # Mock
        
    return mt5_state

@app.get("/history")
def get_history():
    """Fetches closed trades (deals) for history."""
    if not mt5_state["connected"] and HAS_MT5:
         return {"history": []}
         
    history_data = []
    
    # 1. Fetch from DB first (Persistent)
    db_history = financial_db.get_trade_history(limit=None)
    if db_history:
        history_data = db_history
    
    if HAS_MT5 and mt5_state["connected"]:
        # Get history for last 30 days
        from_date = datetime.now().timestamp() - (30 * 24 * 60 * 60)
        to_date = datetime.now().timestamp() + (24 * 60 * 60) # Future buffer
        
        # We assume same server time offset
        time_offset = 7200

        # filter for ENTRY_OUT (Closings) which finalize profit
        deals = mt5.history_deals_get(from_date, to_date)
        
        if deals:
            real_deals = []
            for deal in deals:
                # ENTRY_OUT = 1 (Exit of a position)
                if deal.entry == 1: 
                    local_ts = deal.time - time_offset
                    real_deals.append({
                        "ticket": deal.ticket,
                        "symbol": deal.symbol,
                        "type": "BUY" if deal.type == 0 else "SELL", # 0=Buy, 1=Sell usually for deals too, roughly
                        "volume": deal.volume,
                        "price": deal.price,
                        "profit": deal.profit,
                        "time": str(datetime.fromtimestamp(local_ts))
                    })
            
            # Sync to DB
            financial_db.sync_from_mt5_history(real_deals)
            
            # If DB was empty or we want fresh, we can prefer MT5 list
            # But DB has sentiment tags, so we prefer DB list, but we just synced so DB is up to date.
            # Let's re-fetch from DB to get the merged result
            history_data = financial_db.get_trade_history(limit=None)

    else:
        # Mock History
        if not history_data: # Only use mock if DB is empty
            history_data = [
                {"ticket": 9991, "symbol": "EURUSD", "type": "BUY", "volume": 0.5, "price": 1.0650, "profit": 55.0, "time": str(datetime.now())},
                {"ticket": 9992, "symbol": "GBPUSD", "type": "SELL", "volume": 0.1, "price": 1.2400, "profit": -12.5, "time": str(datetime.now())}
            ]
        
    return {"history": history_data}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
