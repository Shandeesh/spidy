import sys
import os
import pandas as pd
import numpy as np

# Add the project root to sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__))))

from feature_engineering.feature_store import FeatureStore

def debug_features():
    print("🕷️ Debugging Features...")
    periods = 200
    dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq='1min')
    data = {
        'time': dates,
        'open': np.linspace(100, 105, periods),
        'high': np.linspace(101, 106, periods),
        'low': np.linspace(99, 104, periods),
        'close': np.linspace(100.5, 105.5, periods),
        'tick_volume': np.random.randint(100, 500, periods)
    }
    df = pd.DataFrame(data)
    
    fs = FeatureStore()
    df = fs.generate_features(df)
    
    print("Columns:", df.columns.tolist())
    if 'ema_9' in df.columns:
        print("✅ EMA_9 Present")
    else:
        print("❌ EMA_9 Missing")

if __name__ == "__main__":
    debug_features()
