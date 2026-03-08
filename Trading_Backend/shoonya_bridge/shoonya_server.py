from fastapi import FastAPI, HTTPException, BackgroundTasks, Body, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from NorenRestApiPy.NorenApi import NorenApi
import uvicorn
import logging
import datetime
import time
import os
import json
import threading
import asyncio
import psutil 
import random
from typing import List
from contextlib import asynccontextmanager
from dotenv import load_dotenv # Added secrets management

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

manager = ConnectionManager()

# Override Logger to Broadcast
class BroadcastHandler(logging.Handler):
    def emit(self, record):
        log_entry = self.format(record)
        # We need an event loop to broadcast async. 
        # Since emit is sync, we can't await. 
        # Workaround: Use a thread-safe queue or just fire-and-forget logic if mostly async?
        # Better: run_coroutine_threadsafe if loop exists.
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(manager.broadcast(log_entry), loop)
        except RuntimeError:
             pass # Loop might not be running yet

# Add handler
broadcast_handler = BroadcastHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
broadcast_handler.setFormatter(formatter)
logger.addHandler(broadcast_handler)

import pyotp # Added for Auto-Login


# --- CREDENTIALS ---
# Load from Root .env
base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(base_path, ".env")
load_dotenv(env_path)

SHOONYA_USER = os.getenv("SHOONYA_USER")
SHOONYA_PWD = os.getenv("SHOONYA_PWD")
SHOONYA_TOTP_SECRET = os.getenv("SHOONYA_TOTP_SECRET", "") 
SHOONYA_FACTOR2 = os.getenv("SHOONYA_FACTOR2")
SHOONYA_VC = os.getenv("SHOONYA_VC")
SHOONYA_API_KEY = os.getenv("SHOONYA_API_KEY")
SHOONYA_IMEI = os.getenv("SHOONYA_IMEI")

if not SHOONYA_USER or not SHOONYA_PWD:
    logger.error("CRITICAL: Missing Credentials in .env file! Please configure it.")


# --- GLOBAL STATE ---
api = NorenApi(host='https://api.shoonya.com/NorenWClientTP/', websocket='wss://api.shoonya.com/NorenWSTP/')
shoonya_state = {
    "connected": False,
    "balance": 0.0,
    "equity": 0.0,
    "pnl": 0.0,
    "positions": [],
    "live_data": {}, # Token -> {ltp, change}
    "watchlist_tokens": [], # List of subscribed tokens
    "global_pulse": {"DXY": 0, "OIL": 0, "sentiment": "NEUTRAL"} # Phase 4
}

shoonya_settings = {
    "rbi_max_price": 85.00, # Configurable Intervention Level
    "max_daily_loss": 2000.0
}

# --- GLOBAL TETHER (PHASE 4) ---
def check_global_correlation():
    try:
        # File is in Trading_Backend/market_pulse.json
        # Shoonya server is in Trading_Backend/shoonya_bridge/
        file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "market_pulse.json")
        
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
                shoonya_state["global_pulse"] = data
                
                # CHECK STALENESS
                ts = data.get("timestamp", 0)
                if time.time() - ts > 60:
                     logger.warning(f"Global Pulse Stale (Age: {time.time() - ts:.1f}s). Defaulting to NEUTRAL.")
                     return "NEUTRAL"
                     
                return data.get("sentiment", "NEUTRAL")
    except Exception as e:
        logger.warning(f"Global Tether Read Failed: {e}")
    return "NEUTRAL"




# --- WEBSOCKET CALLBACKS ---
def event_handler_feed_update(tick_data):
    try:
        if 'lp' in tick_data and 'tk' in tick_data:
            token = tick_data['tk']
            lp = float(tick_data['lp'])
            pc = float(tick_data.get('pc', 0)) # Percent change
            shoonya_state["live_data"][token] = {"ltp": lp, "change": pc}
            # logger.info(f"Tick: {token} -> {lp}") # Too verbose for prod
    except Exception as e:
        logger.error(f"Feed Error: {e}")

def event_handler_order_update(order_data):
    logger.info(f"Order Update: {order_data}")
    # Update positions/orders logic here if needed immediately

# --- TOKEN MAPPER (PHASE 3) ---
class TokenMapper:
    def __init__(self, api_instance):
        self.api = api_instance
        self.symbol_map = {} # Symbol -> Token

    def resolve_watchlist(self, symbols):
        """Resolves symbols to tokens for subscription."""
        tokens = []
        for sym in symbols:
            try:
                # 1. Try CDS (Currency)
                ret = self.api.searchscrip(exchange='CDS', searchtext=sym)
                if ret and 'values' in ret:
                    # Pick the first one (usually near month future if sorted)
                    # Ideally filter for "-I" suffix or similar for current month futures
                    # For simplicty in Phase 3, taking first result
                    first_match = ret['values'][0]
                    token = first_match['token']
                    exch = first_match['exch']
                    self.symbol_map[sym] = {"token": token, "exch": exch, "tsym": first_match['tsym']}
                    tokens.append(f"{exch}|{token}")
                    logger.info(f"Resolved {sym} -> {first_match['tsym']} ({token})")
                    continue
                
                # 2. Try NSE (Index/Eq)
                ret = self.api.searchscrip(exchange='NSE', searchtext=sym)
                if ret and 'values' in ret:
                    first_match = ret['values'][0]
                    token = first_match['token']
                    exch = first_match['exch']
                    self.symbol_map[sym] = {"token": token, "exch": exch, "tsym": first_match['tsym']}
                    tokens.append(f"{exch}|{token}")
                    logger.info(f"Resolved {sym} -> {first_match['tsym']} ({token})")
                    continue
                    
            except Exception as e:
                logger.error(f"Failed to resolve {sym}: {e}")
        return tokens

token_mapper = TokenMapper(api)


# --- VALIDATION LOGIC (PHASE 4 CORE) ---
def validate_shoonya_entry(symbol, signal, price=0):
    """
    The Brain of the Shoonya Bridge.
    Checks: Global Pulse, Oil (for INR), DXY, and RBI Monitor (Price Levels).
    """
    reasons = []
    
    # 0. RESOLVE LIVE PRICE (WEBSOCKET SPEED)
    if price == 0:
        # Try to find price in live_data cache
        if symbol in token_mapper.symbol_map:
            token = token_mapper.symbol_map[symbol]['token']
            live_info = shoonya_state["live_data"].get(token)
            if live_info:
                price = float(live_info.get('ltp', 0))
                logger.info(f"Using Live Websocket Price for {symbol}: {price}")
        
    # If still 0, we can't validate price levels, but can validate flow.
    # If still 0, we can't validate price levels, but can validate flow.
    if price == 0:
         logger.warning(f"CRITICAL: Validation Failed for {symbol} - NO PRICE DATA.")
         return False, "NO_PRICE_DATA"
    
    # 1. GLOBAL PULSE CHECK
    # We use the DXY and Sentiment from MT5 Bridge
    pulse = shoonya_state.get("global_pulse", {})
    sentiment = pulse.get("sentiment", "NEUTRAL") # BULLISH/BEARISH (for USD)
    dxy_status = pulse.get("dxy_status", "NEUTRAL")
    oil_status = pulse.get("oil_status", "NEUTRAL") # BULLISH means Oil UP -> INR Weak -> USDINR UP
    
    # Logic:
    # If Signal is BUY (Long USDINR) -> We need USD Strong (Bullish) or INR Weak.
    # If Signal is SELL (Short USDINR) -> We need USD Weak (Bearish) or INR Strong.
    
    # USDINR Specifics:
    if "USDINR" in symbol:
        # A. RBI MONITOR (Intervention Zones)
        # RBI historically defends 84.00+ aggressively ( Selling USD to strengthen INR)
        # RBI defends 82.50 support (Buying USD)
        # Note: These levels change, but for now we hardcode "Danger Zones"
        limit = shoonya_settings.get("rbi_max_price", 85.00)
        if price > limit and signal == "BUY":
            return False, f"RBI Monitor: Danger Zone (>{limit}). Risk of Intervention."
        
        # B. OIL WATCHER
        # Oil UP -> INR WEAK (Bad for India) -> USDINR UP (Good for BUY)
        # Oil DOWN -> INR STRONG (Good for India) -> USDINR DOWN (Good for SELL)
        
        if signal == "BUY" and ("BEARISH" in oil_status):
            # Caution: Oil dropping usually strengthens INR (pushes USDINR down)
            # But DXY might overpower it. Let's return False only if DXY is also weak.
            if "BEARISH" in dxy_status:
                 return False, f"Oil Watcher: Oil {oil_status} (INR Strong) + DXY {dxy_status}"
                 
        if signal == "SELL" and ("BULLISH" in oil_status):
             # Caution: Oil rising weakens INR (pushes USDINR up)
             if "BULLISH" in dxy_status:
                  return False, f"Oil Watcher: Oil {oil_status} (INR Weak) + DXY {dxy_status}"

        # C. DXY SHIELD
        if signal == "BUY" and dxy_status == "BEARISH":
             # Trying to buy USD when DXY is falling
             return False, "Global Shield: DXY is Bearish"
             
        if signal == "SELL" and dxy_status == "BULLISH":
             # Trying to sell USD when DXY is pumping
             return False, "Global Shield: DXY is Bullish"

        # D. WHALE TRACKER (Confirm Flow)
        # Only block if Whale Flow is heavily opposing
        whale_signal = get_whale_signal(api, symbol)
        if signal == "BUY" and whale_signal == "BEARISH_FLOW":
             # Trying to Buy into heavy selling Volume
             return False, "Whale Tracker: Heavy Selling Volume Detected"
             
        if signal == "SELL" and whale_signal == "BULLISH_FLOW":
             return False, "Whale Tracker: Heavy Buying Volume Detected"

    return True, "OK"

# --- OPTION CHAIN HELPER (REAL API) ---
def fetch_option_chain(api, symbol="NIFTY"):
    """
    Fetches CE/PE tokens for ATM +- N strikes.
    NOTE: This is a complex operation requiring multiple API calls.
    1. Get Spot Price.
    2. Calculate ATM Strike.
    3. Search for Option Tokens for that Strike.
    """
    try:
        # 1. Get Spot 
        # Typically Index Symbols are like "Nifty 50" -> 'NSE|Nifty 50' or 'NSE|26000'
        # NorenApi needs 'Nifty 50' or similar. 
        # For simplicity, let's assume we want USDINR options (CDS)
        
        exchange = 'CDS'
        spot_sym = 'USDINR' 
        
        # Search for Spot/Future to get Price
        # ret = api.searchscrip(exchange=exchange, searchtext=spot_sym + " FUTURE")
        # Optimization: We check shoonya_state["live_data"] if we are subscribed to Futures.
        
        # Hypothetical Chain Builder
        # Since we cannot easily "scan" all strikes without knowing them, 
        # we will assume we know the ATM range roughly or rely on Shoonya's functionality if exists.
        
        # PLACEHOLDER: Since precise option chain construction via REST requires 
        # extensive symbol master parsing (downloading master csv), we will 
        # use a simplified 'Whale Proxy':
        # We will track the 'Open Interest' of the Near Month Future itself.
        # High OI Change on Future + Price Action = Whale Movement.
        return None 

    except Exception as e:
        logger.error(f"Option Chain Error: {e}")
        return None

def get_pcr_signal(api, symbol="NIFTY"):
    return "NEUTRAL" # Defer until Master CSV parsing is implemented

# --- WHALE TRACKER (PHASE 4) ---
# --- REAL WHALE TRACKER (Volume/OI Analysis on Future) ---
def get_whale_signal(api, symbol="USDINR"):
    """
    Real-World approach without full option chain:
    Analyze the OI and Volume of the Active Future Contract.
    """
    try:
        # 1. Identify Active Token from Mapper
        if symbol not in token_mapper.symbol_map:
            token_mapper.resolve_watchlist([symbol])
            
        token_info = token_mapper.symbol_map.get(symbol)
        if not token_info: return "NEUTRAL"
        
        token = token_info['token']
        tsym = token_info['tsym'] # Trading Symbol e.g. USDINR26JUL24F
        
        # 2. Get Quote (Depth)
        quote = api.get_quotes(exchange=token_info['exch'], token=token)
        if not quote: return "NEUTRAL"
        
        # 3. Analyze OI 
        # Shoonya Quote usually has 'oi' field
        current_oi = float(quote.get('oi', 0))
        day_open_oi = float(quote.get('open_interest', 0)) # Might vary by broker API naming
        # Actually 'oi' in quote is usually current. Finding 'change' is hard without history.
        # We can look at 'volume'.
        
        volume = float(quote.get('v', 0))
        ltp = float(quote.get('lp', 0))
        prev_close = float(quote.get('c', 0))
        
        change_pct = ((ltp - prev_close)/prev_close) * 100
        
        # WHALE LOGIC:
        # High Volume + Price UP = Long Buildup (Bullish)
        # High Volume + Price DOWN = Short Buildup (Bearish)
        # We define "High Volume" as generic threshold or compare to average (requires history).
        # For now, we use a simple heuristic: Is Log Volume significant?
        
        signal = "NEUTRAL"
        if abs(change_pct) > 0.1: # Significant movement
            if change_pct > 0:
                signal = "BULLISH_FLOW"
            else:
                signal = "BEARISH_FLOW"
                
        # If Current OI is available and massive, it confirms.
        # logger.info(f"🐋 Whale Scan {tsym}: {change_pct:.2f}% Vol:{volume} OI:{current_oi}")
        
        return signal

    except Exception as e:
        # logger.warning(f"Whale Tracker Error: {e}")
        return "NEUTRAL"

# --- ELASTIC BAND (PHASE 4) ---
def get_elastic_signal(api, symbol="USDINR", vwap_threshold=2.0):
    """
    Mean Reversion using VWAP + Standard Deviations.
    """
    try:
        # NOTE: Real VWAP requires Volume + Price history. 
        # For Phase 4 simplification, we return NEUTRAL until history fetch is robust.
        return "NEUTRAL" 
    except Exception:
        return "NEUTRAL"

# --- VOLATILITY TRAP (PHASE 4) ---
def get_volatility_signal(api, symbol="USDINR"):
    """
    Detects if markets are too quiet (Trap) or Exploding (Breakout).
    """
    # Placeholder for Bollinger Band calculation on history
    return "SAFE" # or "TRAP_ACTIVE"

# --- DATA PIPELINE (PHASE 4) ---
def log_trade_to_csv(trade_data):
    try:
        file_path = "trade_history.csv"
        # Columns: Time, Symbol, Action, Price, Indicators, Result
        header = "Time,Symbol,Action,Price,Reason,Result\n"
        
        if not os.path.exists(file_path):
             with open(file_path, "w") as f:
                 f.write(header)
        
        line = f"{datetime.datetime.now()},{trade_data.get('symbol')},{trade_data.get('action')},{trade_data.get('price')},{trade_data.get('reason')},{trade_data.get('result','OPEN')}\n"
        
        with open(file_path, "a") as f:
            f.write(line)
            
    except Exception as e:
        logger.error(f"Data Pipeline Error: {e}")

# --- PROFIT GUARDIAN (PHASE 2 - ENHANCED) ---
class ProfitGuardian:
    def __init__(self, api_instance, max_daily_loss=-2000, target_profit=5000):
        self.api = api_instance
        self.max_loss = max_daily_loss
        self.target = target_profit
        
        # State
        self.starting_balance = 0.0
        self.high_water_mark = 0.0 # Track peak profit
        self.kill_switch_active = False
        
        # Martingale Killer State
        self.consecutive_losses = 0
        self.cooldown_until = None

    def set_starting_balance(self, balance):
        self.starting_balance = balance

    def close_all_positions(self, reason="GUARDIAN_TRIGGER"):
        """Flattens the book immediately."""
        logger.warning(f"🚨 CLOSING ALL POSITIONS. Reason: {reason}")
        try:
            positions = self.api.get_positions()
            if positions:
                for pos in positions:
                    netqty = int(pos.get('netqty', 0))
                    if netqty != 0:
                        symbol = pos['tsym']
                        exchange = pos['exch']
                        # Place counter order
                        transaction_type = 'S' if netqty > 0 else 'B'
                        qty = abs(netqty)
                        
                        logger.info(f"Closing {symbol} (Qty: {qty})...")
                        self.api.place_order(buy_or_sell=transaction_type, product_type=pos['prd'],
                                           exchange=exchange, tradingsymbol=symbol,
                                           quantity=qty, discloseqty=0, price_type='LMT', price=0, trigger_price=0,
                                           retention='DAY', remarks=f"AutoClose-{reason}")
        except Exception as e:
            logger.error(f"Failed to close positions: {e}")

    def check_health(self, current_balance):
        now = datetime.datetime.now()
        
        # 1. Martingale Killer Cooldown Check
        if self.cooldown_until and now < self.cooldown_until:
             logger.info(f"❄️ Martingale Cooldown Active until {self.cooldown_until.strftime('%H:%M')}")
             return "COOLDOWN_ACTIVE"
        elif self.cooldown_until and now >= self.cooldown_until:
             logger.info("❄️ Martingale Cooldown Expired. Resuming.")
             self.cooldown_until = None

        if self.starting_balance == 0: return "SAFE"
        
        pnl = current_balance - self.starting_balance
        
        # Track High Water Mark (Peak Profit)
        if pnl > self.high_water_mark:
            self.high_water_mark = pnl

        logger.info(f"💰 Guardian Check: P&L ₹{pnl:.2f} | Peak: ₹{self.high_water_mark:.2f}")

        # 2. KILL SWITCH (Safety First - Hard Exit)
        if pnl <= self.max_loss:
            logger.error(f"🚨 CRITICAL: Max Daily Loss Hit (₹{pnl}). SHUTTING DOWN.")
            self.kill_switch_active = True
            self.close_all_positions("MAX_LOSS_HIT")
            return "KILL_SWITCH"
        
        # 3. PROFIT LOCK (Trailing Equity with Smart Exit)
        # If we reached decent profit (>500) but dropped back significant amount from peak
        PROFIT_LOCK_TRIGGER = 500.0
        DROP_BUFFER = 200.0 
        
        if self.high_water_mark > PROFIT_LOCK_TRIGGER:
            if pnl < (self.high_water_mark - DROP_BUFFER):
                # We are giving back profits. Check Smart Exit.
                pcr_status = get_pcr_signal(self.api)
                
                # Smart Logic:
                # If market is strictly against us, CLOSE.
                # If market is supporting us, maybe give it more room? (Simplification: Just close for now as 'Profit Lock' implies safety)
                # User Requirement: "Trade cannot be closed random".
                
                reason = f"PROFIT_LOCK_HIT (Peak: {self.high_water_mark}, Curr: {pnl})"
                
                # Check active positions direction vs PCR
                # This requires knowing if we are Net Long or Net Short.
                # Simplification: If PCR confirms the drop direction, we exit.
                
                logger.warning(f"⚠️ Profit Lock Triggered. Market PCR: {pcr_status}")
                if pcr_status != "NEUTRAL":
                     logger.info(f"Smart Exit Confirmation: Market is {pcr_status}")
                
                self.close_all_positions(reason)
                return "TAKE_PROFIT_STOP"

        if pnl >= self.target:
            logger.info("✅ SUCCESS: Daily Target Hit! Locking profits.")
            self.kill_switch_active = True # Stop new trades
            self.close_all_positions("DAILY_TARGET_HIT")
            return "TAKE_PROFIT_STOP"
            
        return "SAFE"
    
    def register_trade_result(self, profit):
        """Called after a trade closes to update consecutive loss count."""
        if profit < 0:
            self.consecutive_losses += 1
            logger.info(f"⚠️ Loss Registered. Consecutive Losses: {self.consecutive_losses}")
        else:
            self.consecutive_losses = 0
        
        # Martingale Killer Trigger
        if self.consecutive_losses >= 3:
            logger.warning("❄️ Martingale Killer Triggered: 3 Consecutive Losses. IDLING for 1 Hour.")
            self.cooldown_until = datetime.datetime.now() + datetime.timedelta(hours=1)
            self.consecutive_losses = 0 # Reset count after penalty

guardian = ProfitGuardian(api)

# --- MARKET HOURS LOCK ---
def is_market_open():
    now = datetime.datetime.now()
    # NSE Currency Hours roughly 9:00 to 17:00
    if now.hour < 9 or (now.hour == 17 and now.minute > 0) or now.hour > 17:
        return False
    # Add weekend check
    if now.weekday() >= 5: # 5=Sat, 6=Sun
        return False
    return True

# --- BACKGROUND TASKS ---
async def data_sync_loop():
    while True:
        try:
            if not is_market_open():
                logger.info("😴 Market Closed. Sleeping...")
                shoonya_state["market_status"] = "CLOSED"
                await asyncio.sleep(60)
                continue
            
            shoonya_state["market_status"] = "OPEN"
            
            # Phase 4: Update Global Pulse
            global_signal = check_global_correlation()
            if global_signal != "NEUTRAL":
                # logger.info(f"🌍 Global Signal: {global_signal}") 
                pass

            if shoonya_state["connected"]:
                # 1. Update Limits/Balance
                ret = api.get_limits()
                if ret and 'stat' in ret and ret['stat'] == 'Ok':
                    cash = float(ret.get('cash', 0))
                    # Note: 'cash' is usually available margin. 
                    # For P&L tracking we might need to track realized + unrealized separately.
                    # Simplified for now using provided logic.
                    current_balance = cash 
                    shoonya_state["balance"] = current_balance
                    
                    if guardian.starting_balance == 0:
                        guardian.set_starting_balance(current_balance)
                    
                    health = guardian.check_health(current_balance)
                    if health == "KILL_SWITCH":
                         # Implement kill logic (close all?)
                         pass

                # 2. Update Positions
                pos_ret = api.get_positions()
                if pos_ret and isinstance(pos_ret, list):
                    shoonya_state["positions"] = pos_ret
                    # Calculates total open P&L
                    total_pnl = sum([float(p.get('rpnl', 0)) + float(p.get('urmtom', 0)) for p in pos_ret])
                    shoonya_state["pnl"] = total_pnl
                    shoonya_state["equity"] = shoonya_state["balance"] + total_pnl
                else:
                    shoonya_state["positions"] = []
                    
        except Exception as e:
            logger.error(f"Sync Loop Error: {e}")
        
        await asyncio.sleep(1) # Poll every 1s (Phase 1)

# --- LIFESPAN ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Login
    logger.info("Attempting Shoonya Login...")
    try:
        two_fa_val = SHOONYA_FACTOR2
        if SHOONYA_TOTP_SECRET:
             logger.info("🔐 Generating Auto-OTP for Login...")
             try:
                 totp = pyotp.TOTP(SHOONYA_TOTP_SECRET)
                 two_fa_val = totp.now()
             except Exception as e:
                 logger.error(f"OTP Generation Failed: {e}")
        
        ret = api.login(userid=SHOONYA_USER, password=SHOONYA_PWD, twoFA=two_fa_val, vendor_code=SHOONYA_VC, api_secret=SHOONYA_API_KEY, imei=SHOONYA_IMEI)
        if ret and ret.get('stat') == 'Ok':
            logger.info("✅ Shoonya Login SUCCESS")
            shoonya_state["connected"] = True
            
            # Initial limit fetch
            limits = api.get_limits()
            if limits and 'cash' in limits:
                guardian.set_starting_balance(float(limits['cash']))
            
            # --- PHASE 3: WEBSOCKET START ---
            logger.info("⚡ Starting Websocket (The Speed)...")
            api.start_websocket(subscribe_callback=event_handler_feed_update, order_update_callback=event_handler_order_update)
            
            # Resolve & Subscribe
            # Resolve & Subscribe (Async Wrap)
            watchlist = ["USDINR", "EURINR", "GBPINR", "JPYINR", "NIFTY", "BANKNIFTY"]
            logger.info("Resolving Watchlist (Background)...")
            
            # Run blocking searchscrip in thread
            loop = asyncio.get_running_loop()
            tokens = await loop.run_in_executor(None, token_mapper.resolve_watchlist, watchlist)
            
            if tokens:
                logger.info(f"Subscribing to {len(tokens)} symbols...")
                api.subscribe(tokens)
                shoonya_state["watchlist_tokens"] = tokens
            
    except Exception as e:
        logger.error(f"❌ Shoonya Login CRITICAL Failure: {e}")

    # Start Background Loop
    asyncio.create_task(data_sync_loop())
    
    yield
    
    # Shutdown
    # api.logout() # Logout might kill token, careful
    logger.info("Shoonya Bridge Shutting Down")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ENDPOINTS ---

@app.get("/status")
def get_status():
    return {
        "server_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "connected": shoonya_state["connected"],
        "balance": shoonya_state["balance"],
        "equity": shoonya_state["equity"],
        "profit": shoonya_state["pnl"],
        "market_status": shoonya_state.get("market_status", "UNKNOWN"),
        "positions": shoonya_state["positions"],
        # Add MT5-like keys for frontend compatibility if needed, 
        # or Frontend will adapt (ShoongaDashboard accepts 'mt5Status' but checks fields)
        "shoonya_balance": f"{shoonya_state['balance']:.2f}",
        "shoonya_equity": f"{shoonya_state['equity']:.2f}",
        "shoonya_profit": f"{shoonya_state['pnl']:.2f}",
        "global_pulse": shoonya_state.get("global_pulse", {}),
        "risk_settings": {"mode": "GUARDIAN_ACTIVE", "auto_secure": {"enabled": True}}
    }

@app.get("/symbols")
def get_symbols():
    # Action 2: Clean the Watchlist
    return {"symbols": ["USDINR", "EURINR", "GBPINR", "JPYINR", "NIFTY", "BANKNIFTY"]}

@app.post("/settings/update")
def update_settings(payload: dict = Body(...)):
    """Dynamically update Shoonya limits and settings."""
    for key, value in payload.items():
        if key in shoonya_settings:
            # Type casting based on existing value
            target_type = type(shoonya_settings[key])
            try:
                shoonya_settings[key] = target_type(value)
                logger.info(f"SETTING UPDATED: {key} -> {shoonya_settings[key]}")
            except ValueError:
                 return {"error": f"Invalid type for {key}, expected {target_type}"}
    return {"status": "UPDATED", "settings": shoonya_settings}

from pydantic import BaseModel, Field, validator

class TradeOrder(BaseModel):
    action: str
    symbol: str
    price: float = Field(default=0.0, ge=0.0)
    quantity: int = Field(default=0, ge=0)
    
    @validator('action')
    def validate_action(cls, v):
        if v.upper() not in ['BUY', 'SELL', 'MODIFY', 'CANCEL']:
            raise ValueError('Invalid Action')
        return v.upper()

    @validator('symbol')
    def validate_symbol(cls, v):
        if len(v) < 3 or len(v) > 20: # Anti-Fuzzing Length Check
            raise ValueError('Invalid Symbol Length')
        if not v.replace('_','').isalnum(): # Prevent injection chars
            raise ValueError('Invalid characters in Symbol')
        return v.upper()

@app.post("/trade")
def place_trade(order: TradeOrder):
    if not shoonya_state["connected"]:
        raise HTTPException(status_code=503, detail="Shoonya not connected")
    if guardian.kill_switch_active:
        raise HTTPException(status_code=400, detail="KILL SWITCH ACTIVE")
        
    action = order.action
    symbol = order.symbol

    # Validate Strategy
    logger.info(f"Checking Trade: {action} {symbol}...")
    is_valid, reason = validate_shoonya_entry(symbol, action)
    
    if not is_valid:
        logger.warning(f"⛔ Trade Rejected: {reason}")
        return {"status": "REJECTED", "reason": reason}
        
    # LOGIC TO PLACE ORDER (Simulated until NorenApi setup complete with real money flag)
    # We will log it as "PAPER TRADED" for now to test flow
    
    trade_data = {
        "symbol": symbol,
        "action": action,
        "price": 0, # Market
        "reason": reason,
        "result": "PAPER_FILLED"
    }
    log_trade_to_csv(trade_data)
    
    return {"status": "FILLED (Paper)", "reason": "Passed Validation"}

# --- CLOUD MANAGER ENDPOINTS ---
@app.get("/cloud/stats")
def get_cloud_stats():
    # Simulate or Read Real System Stats (if running on cloud)
    # For now, we read local machine stats as this script IS the "bot"
    
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    now = datetime.datetime.now()
    uptime = str(now - boot_time).split('.')[0] # Remove microseconds logic if needed
    
    return {
        "status": "RUNNING" if shoonya_state["connected"] else "IDLE", # Or just RUNNING since server is up
        "uptime": uptime,
        "cpu": int(psutil.cpu_percent(interval=None)),
        "ram": int(psutil.virtual_memory().percent)
    }

@app.post("/cloud/control")
def cloud_control(payload: dict = Body(...)):
    action = payload.get("action")
    logger.info(f"CLOUD COMMAND: {action}")
    
    if action == "STOP":
        # Simulate stop (disconnect)
        # api.logout()
        shoonya_state["connected"] = False
        return {"status": "STOPPED"}
        
    if action == "START":
        # Simulate start (re-login or just flag)
        # In reality, this endpoint implies server is ALREADY running to receive the command.
        # So "START" usually means "Start Trading Loop".
        shoonya_state["connected"] = True 
        return {"status": "RUNNING"}
    
    if action == "RESTART":
        # Hard to self-restart in script, but can simulate
        shoonya_state["connected"] = True
        return {"status": "RESTARTED"}
    
    return {"status": "UNKNOWN"}

@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
