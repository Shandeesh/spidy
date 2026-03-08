
import sys
import os
sys.path.append(r'c:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge')
sys.path.append(r'c:\Users\Shandeesh R P\spidy\AI_Engine')
sys.path.append(r'c:\Users\Shandeesh R P\spidy\Trading_Backend')

try:
    from strategy_manager import StrategyManager
    sm = StrategyManager()
    print("SUCCESS: StrategyManager initialized with 0 strategies.")
    print(f"Strategies Loaded: {len(sm.strategies)}")
except ImportError as e:
    print(f"ERROR: Import failed: {e}")
except Exception as e:
    print(f"ERROR: Runtime failed: {e}")
