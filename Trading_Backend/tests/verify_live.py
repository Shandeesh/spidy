import sys
import os
import pandas as pd
import MetaTrader5 as mt5
import time

# Add mt5_bridge to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mt5_bridge"))

from strategy_manager import StrategyManager
from strategies.technical_analysis import TechnicalAnalyzer

def connect_mt5():
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        quit()
    print(f"MT5 Connected: {mt5.terminal_info().name}")

def get_live_data(symbol, n=300):
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, n)
    if rates is None:
        print(f"Failed to get data for {symbol}")
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def test_strategies():
    print("---------------------------------------------------")
    print("     SPIDY LIVE STRATEGY VERIFICATION (MT5)        ")
    print("---------------------------------------------------")

    # 1. Connect
    connect_mt5()
    
    # 2. Setup Manager
    try:
        manager = StrategyManager()
        print(f"[OK] StrategyManager Loaded. Total Strategies: {len(manager.strategies)}")
    except Exception as e:
        print(f"[FAIL] Manager Init Error: {e}")
        return

    # 3. Get Data
    symbol = "EURUSD"
    print(f"\n[INFO] Fetching Live Data for {symbol}...")
    df = get_live_data(symbol)
    
    if df is None:
        print("[FAIL] No Data.")
        return

    current_price = df['close'].iloc[-1]
    print(f"[INFO] Current Price: {current_price}")

    # 4. Update State (Calculates Indicators)
    print("[INFO] Updating Technical State...")
    manager.update_technical_state(symbol, df, current_price)
    
    # 5. Execute All Strategies
    print(f"\n{'STRATEGY NAME':<35} | {'STATUS':<6} | {'SIGNAL'}")
    print("-" * 75)
    
    state = manager.market_state.get(symbol, {})
    
    # Prepare Packet
    data_packet = {
        "df": df,
        "price": current_price,
        "adx": state.get("adx", 0),
        "rsi": state.get("rsi", 50),
        "vwap": state.get("vwap", current_price)
    }

    pass_count = 0
    fail_count = 0

    for strategy in manager.strategies:
        name = strategy.get_name()
        try:
            # Manually trigger analyze to see output even if "generate_signal" filters it
            result = strategy.analyze(symbol, data_packet, manager.market_state)
            
            signal = "WAIT"
            if result:
                signal = result.get("signal", "WAIT")
                if "confidence" in result:
                    signal += f" ({result['confidence']})"
            
            print(f"{name:<35} | PASS   | {signal}")
            pass_count += 1
            
        except Exception as e:
            print(f"{name:<35} | FAIL   | {e}")
            fail_count += 1

    print("-" * 75)
    print(f"VERIFICATION COMPLETE: {pass_count} PASSED, {fail_count} FAILED")
    
    mt5.shutdown()

if __name__ == "__main__":
    with open("verify_results.txt", "w") as f:
        sys.stdout = f
        test_strategies()
        sys.stdout = sys.__stdout__
    print("Verification execution finished. Check 'verify_results.txt'.")
