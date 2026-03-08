
import sys
import os
import pandas as pd
import numpy as np
import logging

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mt5_bridge"))

from strategy_manager import StrategyManager

# Mock classes to avoid dependencies
class MockMarketData:
    def check_correlation(self, symbol):
        return "NEUTRAL"

def main():
    log_file = "strategy_verification_results.txt"
    # Clear file first
    with open(log_file, "w", encoding="utf-8") as f:
        f.write("")
        
    def log(msg):
        # Append mode for safety
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
        # Also print to stdout for debugging if needed, but simple
        print(msg)

    log("---------------------------------------------------")
    log("     SPIDY STRATEGY SYSTEM VERIFICATION")
    log("---------------------------------------------------")
    
    # 1. Initialize Manager
    try:
        manager = StrategyManager()
        manager.market_data = MockMarketData() 
        log(f"[OK] StrategyManager Initialized")
        log(f"[OK] Registered Strategies: {len(manager.strategies)}")
    except Exception as e:
        log(f"[FATAL] Failed to initialize StrategyManager: {e}")
        import traceback
        log(traceback.format_exc())
        return

    # 2. Create Synthetic Data (Uptrend)
    log("\n[INFO] Generating Synthetic Market Data (Uptrend)...")
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='1min')
    df = pd.DataFrame(index=dates)
    values = np.linspace(1.1000, 1.1200, 100) 
    noise = np.random.normal(0, 0.0005, 100)
    df['close'] = values + noise
    df['high'] = df['close'] + 0.0002
    df['low'] = df['close'] - 0.0002
    df['open'] = df['close'] 
    df['tick_volume'] = 100
    
    # 3. Test Each Strategy
    log("\n---------------------------------------------------")
    log(f"{'STRATEGY NAME':<30} | {'STATUS':<10} | {'MESSAGE'}")
    log("---------------------------------------------------")
    
    symbol = "TEST_EURUSD"
    # Ensure state init
    manager.market_state[symbol] = {}
    try:
        manager.update_technical_state(symbol, df, df['close'].iloc[-1])
    except Exception as e:
        log(f"[ERROR] Technical State Update Failed: {e}")

    for strategy in manager.strategies:
        name = strategy.get_name()
        try:
            state = manager.market_state[symbol]
            data_packet = {
                "df": df,
                "price": state.get("vwap", 1.1100), 
                "adx": state.get("adx", 0),
                "rsi": state.get("rsi", 50),
                "vwap": state.get("vwap", 1.1100)
            }
            
            result = strategy.analyze(symbol, data_packet, manager.market_state)
            
            msg = "OK"
            if result:
                msg = f"Returned: {result.get('signal', 'Data')}"
                
            log(f"{name:<30} | [PASS]     | {msg}")
            
        except Exception as e:
            log(f"{name:<30} | [FAIL]     | Error: {str(e)}")

    log("---------------------------------------------------")
    log("Verification Complete.")

if __name__ == "__main__":
    main()
