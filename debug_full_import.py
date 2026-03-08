import sys
import os

# Mimic the location of bridge_server.py
base_dir = r"c:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge"

print("--- Testing NewsFetcher ---")
p1 = os.path.abspath(os.path.join(base_dir, "../../AI_Engine/internet_gathering"))
print(f"Path 1: {p1}")
sys.path.append(p1)
try:
    from news_fetcher import NewsFetcher
    print("SUCCESS: NewsFetcher")
except Exception as e:
    print(f"FAIL: NewsFetcher - {e}")

print("\n--- Testing StrategyOptimizer ---")
p2 = os.path.abspath(os.path.join(base_dir, "../../AI_Engine/strategy_optimizer"))
print(f"Path 2: {p2}")
sys.path.append(p2)
try:
    from pack_generator import StrategyOptimizer
    print("SUCCESS: StrategyOptimizer")
except Exception as e:
    print(f"FAIL: StrategyOptimizer - {e}")
