import sys
import os
import pandas as pd
import numpy as np

# Add the project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from feature_engineering.feature_store import FeatureStore
from regime_detection.regime_detector import RegimeDetector

def test_regime():
    print("Testing Regime Detection...")
    
    # Create dummy data with strong trend characteristics
    # Creating a series that goes up steadily
    periods = 100
    data = {
        'time': pd.date_range(start='2024-01-01', periods=periods, freq='1min'),
        'open': np.linspace(100, 200, periods),
        'high': np.linspace(102, 202, periods),
        'low': np.linspace(98, 198, periods),
        'close': np.linspace(101, 201, periods),
        'tick_volume': np.random.randint(100, 1000, periods)
    }
    df = pd.DataFrame(data)
    
    # Add features (needed for regime detection)
    fs = FeatureStore()
    df = fs.generate_features(df)
    
    print("Features generated. Columns:", df.columns.tolist())
    
    detector = RegimeDetector()
    regime = detector.detect_regime(df)
    
    print(f"Detected Regime: {regime}")
    
    details = detector.get_regime_details(df)
    print("Regime Details:", details)
    
    if regime != "UNKNOWN":
        print("✅ Regime detection functioning")
    else:
        print("❌ Regime detection returned UNKNOWN")

if __name__ == "__main__":
    test_regime()
