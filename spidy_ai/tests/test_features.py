import sys
import os
import pandas as pd
import numpy as np

# Add the project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from feature_engineering.feature_store import FeatureStore

def test_features():
    print("Testing Feature Engineering...")
    
    # Create dummy data
    data = {
        'time': pd.date_range(start='2024-01-01', periods=200, freq='1min'),
        'open': np.random.uniform(100, 200, 200),
        'high': np.random.uniform(100, 200, 200),
        'low': np.random.uniform(100, 200, 200),
        'close': np.random.uniform(100, 200, 200),
        'tick_volume': np.random.randint(100, 1000, 200)
    }
    df = pd.DataFrame(data)
    
    # Enforce basic constraints
    df['high'] = df[['open', 'close', 'high', 'low']].max(axis=1)
    df['low'] = df[['open', 'close', 'high', 'low']].min(axis=1)

    print("Generated dummy data:")
    print(df.head())

    fs = FeatureStore()
    features = fs.generate_features(df)
    
    if features is not None and not features.empty:
        print("✅ Feature generation successful")
        print(f"Original shape: {df.shape}, Features shape: {features.shape}")
        print("Columns:", features.columns.tolist())
        
        # Check specific features
        if 'rsi' in features.columns and 'atr' in features.columns:
            print("✅ RSI and ATR found")
        else:
            print("❌ Correct columns not found")
    else:
        print("❌ Feature generation failed")

if __name__ == "__main__":
    test_features()
