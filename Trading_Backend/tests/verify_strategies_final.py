
import sys
import os
import contextlib
import pandas as pd
import numpy as np

# Suppress stderr to avoid TF noise
@contextlib.contextmanager
def suppress_stderr():
    with open(os.devnull, "w") as devnull:
        old_stderr = sys.stderr
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stderr = old_stderr

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mt5_bridge"))

# Mock classes
class MockMarketData:
    def check_correlation(self, symbol):
        return "NEUTRAL"

def main():
    print("---------------------------------------------------", flush=True)
    print("     SPIDY STRATEGY FUNCTIONAL VERIFICATION", flush=True)
    print("---------------------------------------------------", flush=True)
    
    try:
        with suppress_stderr():
            from strategy_manager import StrategyManager
            manager = StrategyManager()
            manager.market_data = MockMarketData() 
        print(f"[OK] Manager Init. Strategies: {len(manager.strategies)}", flush=True)
    except Exception as e:
        print(f"[FAIL] Manager Init Error: {e}", flush=True)
        return

    # Synthetic Data (Uptrend)
    dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='1min')
    df = pd.DataFrame(index=dates)
    values = np.linspace(1.1000, 1.1200, 100) 
    noise = np.random.normal(0, 0.0005, 100)
    df['close'] = values + noise
    df['high'] = df['close'] + 0.0002
    df['low'] = df['close'] - 0.0002
    df['open'] = df['close'] 
    df['tick_volume'] = 100
    
    symbol = "TEST_EURUSD"
    print(f"\n[INFO] Running Analysis on {symbol}...", flush=True)
    
    # Update State
    with suppress_stderr():
        manager.update_technical_state(symbol, df, df['close'].iloc[-1])

    # Test Each
    print(f"{'STRATEGY':<25} | {'STATUS':<6} | {'SIGNAL'}", flush=True)
    print("-" * 60, flush=True)
    
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
            
            with suppress_stderr():
                result = strategy.analyze(symbol, data_packet, manager.market_state)
            
            signal = "-"
            if result:
                signal = str(result.get("signal", "INFO"))
            
            print(f"{name:<25} | PASS   | {signal}", flush=True)
            
        except Exception as e:
            print(f"{name:<25} | FAIL   | {str(e)}", flush=True)

    print("-" * 60, flush=True)
    print("Verification Done.", flush=True)

if __name__ == "__main__":
    main()
