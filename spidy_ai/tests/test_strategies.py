import sys
import os
import pandas as pd
import numpy as np

# Add the project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from strategies.registry import StrategyRegistry
from feature_engineering.feature_store import FeatureStore

def test_strategies():
    print("Testing Strategies...")
    
    # Create dummy data
    periods = 100
    data = {
        'time': pd.date_range(start='2024-01-01', periods=periods, freq='1min'),
        'open': np.linspace(100, 110, periods),
        'high': np.linspace(102, 112, periods),
        'low': np.linspace(98, 108, periods),
        'close': np.linspace(101, 111, periods),
        'tick_volume': np.random.randint(100, 1000, periods)
    }
    df = pd.DataFrame(data)
    
    # Add features
    fs = FeatureStore()
    df = fs.generate_features(df)
    
    # Initialize Registry
    registry = StrategyRegistry()
    print(f"Strategies registered: {list(registry.strategies.keys())}")
    
    for name, strategy in registry.strategies.items():
        print(f"Testing {name}...")
        result = strategy.generate_signal(df)
        print(f"  Signal: {result}")
        if 'signal' in result and 'confidence' in result:
            print(f"  ✅ {name} returned valid structure")
        else:
            print(f"  ❌ {name} returned invalid structure")

if __name__ == "__main__":
    test_strategies()
