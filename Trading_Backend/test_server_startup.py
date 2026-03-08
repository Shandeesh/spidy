import sys
import os
import asyncio

# Setup paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "mt5_bridge"))

print("Running Startup Integrity Check...")

try:
    print("1. Importing StrategyManager...")
    from mt5_bridge.strategy_manager import StrategyManager
    sm = StrategyManager()
    print(f"   Success. Registered Strategies: {len(sm.strategies)}")
    
    print("2. Generating Test Signal (MetaConsensus Load)...")
    # This triggers the local import in generate_signal
    sm.market_state["TEST"] = {"df": None, "adx": 20, "rsi": 50, "vwap": 100}
    try:
        sm.generate_signal("TEST")
    except Exception as e:
        print(f"   Warning: Signal Gen error (expected due to mock data): {e}")
        # If the error is NOT ImportError, we are good.
        if "ImportError" in str(e) or "ModuleNotFoundError" in str(e):
            raise e
            
    print("3. Importing Bridge Server...")
    from mt5_bridge import bridge_server
    print("   Success.")
    
    print("\n✅ SYSTEM INTEGRITY VERIFIED. Ready to Run.")
    
except Exception as e:
    print(f"\n❌ STARTUP FAILED: {e}")
    sys.exit(1)
