import asyncio
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mt5_bridge"))

from strategy_manager import StrategyManager

# Mocking the interaction
async def run_live_simulation():
    print("--- STARTING LIVE SIMULATION OF 50+ STRATEGIES ---")
    
    manager = StrategyManager()
    
    # 1. Create Mock Data that TRIGGERS a strategy
    # let's trigger Bollinger Squeeze Breakout (Buy)
    # Price flat then jumps up
    prices = [1.1000 + ((-1)**i * 0.0001) for i in range(30)] # Flat
    prices.append(1.1050) # Breakout
    
    df = pd.DataFrame({
        'close': prices, 
        'high': [p + 0.0001 for p in prices],
        'low': [p - 0.0001 for p in prices],
        'tick_volume': [1000]*31
    })
    
    symbol = "EURUSD"
    current_price = 1.1050
    
    print(f"Feeding Data to {symbol}: Price Jump to {current_price}...")
    
    # 2. Update State (Simulating bridge_server loop)
    # This runs RegimeDetector and caches DF
    manager.update_technical_state(symbol, df, current_price)
    
    # Check Regime
    regime = manager.market_state.get(symbol, {}).get("regime")
    print(f"Detected Regime: {regime}")
    
    # 3. Generate Signal (Simulating bridge_server loop)
    print("Checking for Signals...")
    signal = manager.generate_signal(symbol)
    
    if signal:
        print(f"\n✅ SIGNAL GENERATED!")
        print(f"Type: {signal['signal']}")
        print(f"Strategy: {signal['strategy']}")
        print(f"Reason: {signal['reason']}")
        print(f"Confidence: {signal['confidence']}")
        print("\n--> This would trigger 'place_market_order' in bridge_server.py")
    else:
        print("\n❌ NO SIGNAL GENERATED. (Unexpected)")
        
    print("\n--- SIMULATION COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(run_live_simulation())
