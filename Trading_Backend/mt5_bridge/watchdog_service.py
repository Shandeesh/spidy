import threading
import time
import MetaTrader5 as mt5
from datetime import datetime, timedelta
import asyncio

class Watchdog:
    """
    Phase 1: The 'Fortress' Watchdog.
    Monitors System Health and Daily P&L.
    Triggers 'Kill Switch' if conditions are violated.
    """
    def __init__(self, bridge_server_ref, max_daily_loss=100.0):
        self.bridge = bridge_server_ref # Reference to main bridge for state updates
        self.max_daily_loss = abs(float(max_daily_loss)) # Ensure positive value
        self.check_interval = 2.0 # Check every 2 seconds
        self._stop_event = threading.Event()
        self._kill_event = threading.Event()
        self._thread = None
        self.running = False
        self.current_daily_pnl = 0.0
        
    def start(self):
        if self.running: return
        print(f"🛡️ WATCHDOG: Initializing... (Limit: -${self.max_daily_loss:.2f})")
        self.running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False
        self._stop_event.set()

    def _monitor_loop(self):
        print("🛡️ WATCHDOG: Active and Monitoring.")
        while self.running and not self._stop_event.is_set():
            try:
                # 1. Calculate P&L
                pnl = self._calculate_daily_pnl()
                self.current_daily_pnl = pnl
                
                # Update Bridge State (for UI/API visibility)
                # Thread-safe update of the dict
                self.bridge.mt5_state["daily_pnl"] = pnl
                
                # 2. Check Kill Condition
                # If PnL is negative and deeper than max_loss (e.g. -150 < -100)
                if pnl < (-1 * self.max_daily_loss):
                    if not self._kill_event.is_set(): # Only trigger once
                        print(f"🚨 WATCHDOG TRIGGERED: Daily Loss ${pnl:.2f} exceeds Limit -${self.max_daily_loss:.2f}")
                        self._activate_kill_switch()
                        
            except Exception as e:
                print(f"Watchdog Error: {e}")
                
            time.sleep(self.check_interval)

    def _calculate_daily_pnl(self):
        """Calculates Realized Profit Today + Current Floating Profit."""
        # FIX: Do not call mt5.initialize() directly if bridge says disconnected.
        # This prevents 'Zombie' relaunches of the specific terminal if user closed it.
        if not self.bridge.mt5_state.get("connected", False):
            return 0.0
            
        if not mt5.initialize(): return 0.0
        
        # 1. Realized Profit (Today)
        now = datetime.now()
        start_of_day = datetime(now.year, now.month, now.day)
        
        deals = mt5.history_deals_get(start_of_day, now)
        realized_profit = 0.0
        if deals:
            for deal in deals:
                if deal.entry == mt5.DEAL_ENTRY_OUT or deal.entry == mt5.DEAL_ENTRY_INOUT:
                    realized_profit += deal.profit
                    realized_profit += deal.swap
                    realized_profit += deal.commission
        
        # 2. Floating Profit (Open Positions)
        # Note: Some traders prefer Equity-based drawdown. 
        # Standard Daily Loss usually includes open positions.
        floating_profit = 0.0
        positions = mt5.positions_get()
        if positions:
            for pos in positions:
                floating_profit += pos.profit
                floating_profit += pos.swap
        
        total_pnl = realized_profit + floating_profit
        return total_pnl

    def _activate_kill_switch(self):
        """Executes the Shutdown Sequence."""
        self._kill_event.set()
        
        # 1. Disable Auto-Trading Logic immediately
        print("💀 WATCHDOG: Disabling Auto-Trade...")
        self.bridge.auto_trade_state["running"] = False
        self.bridge.auto_trade_state["sentiment"] = "HALTED_BY_WATCHDOG"
        
        # 2. Trigger Close All (Async via Bridge)
        # We need to call the async function from this sync thread.
        try:
            loop = self.bridge.loop # Ensure bridge has loop reference
            if loop and loop.is_running():
                print("💀 WATCHDOG: Requesting Emergency Close All... [DISABLED by User Request]")
                asyncio.run_coroutine_threadsafe(self.bridge.broadcast_log("🚨 KILL SWITCH ACTIVATED! Auto-Trade HALTED. (Positions HELD for Recovery)"), loop)
                # FIX: Do NOT Close positions. Just Stop Buying.
                # asyncio.run_coroutine_threadsafe(self.bridge._process_close_all_background(profitable_only=False), loop) 
        except Exception as e:
            print(f"Watchdog Fail-Safe Error: {e}")
            
        # 3. Notification (Mock)
        # print("Sending SMS Alert...")
