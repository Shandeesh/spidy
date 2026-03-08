import sys
import os
import pandas as pd
import numpy as np

# Add project root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from feature_engineering.feature_store import FeatureStore
from regime_detection.regime_detector import RegimeDetector
from strategies.registry import StrategyRegistry
from signal_engine.signal_aggregator import SignalAggregator
from risk_management.risk_manager import RiskManager
from execution.order_router import OrderRouter
from ml.ensemble.ensemble_engine import EnsembleEngine
from ml.models.lstm_short import LSTMShort

def verify_full_system():
    print("🚀 Starting Full System Verification...")
    
    # 1. Mock Data
    print("1. Generating Mock Data...")
    periods = 200
    data = {
        'time': pd.date_range(start='2024-01-01', periods=periods, freq='1min'),
        'open': np.linspace(100, 105, periods),
        'high': np.linspace(101, 106, periods),
        'low': np.linspace(99, 104, periods),
        'close': np.linspace(100.5, 105.5, periods),
        'tick_volume': np.random.randint(100, 1000, periods)
    }
    df = pd.DataFrame(data)
    
    # 2. Features
    print("2. Testing Feature Engineering...")
    fs = FeatureStore()
    df = fs.generate_features(df)
    if 'rsi' in df.columns and 'atr' in df.columns:
        print("   ✅ Features Generated")
    else:
        print("   ❌ Features Missing")
        return

    # 3. Regime
    print("3. Testing Regime Detection...")
    rd = RegimeDetector()
    regime = rd.detect_regime(df)
    print(f"   ✅ Detected Regime: {regime}")

    # 4. Strategies
    print("4. Testing Strategy Registry...")
    registry = StrategyRegistry()
    signals = []
    for strategy in registry.get_active_strategies():
        sig = strategy.generate_signal(df)
        signals.append(sig)
    print(f"   ✅ Generated {len(signals)} signals")

    # 5. Signal Aggregation
    print("5. Testing Signal Aggregator...")
    sa = SignalAggregator()
    final_signal = sa.aggregate_signals(signals, {"regime": regime})
    print(f"   ✅ Final Signal: {final_signal}")

    # 6. ML System
    print("6. Testing ML System...")
    lstm = LSTMShort()
    pred = lstm.predict(df)
    print(f"   ✅ ML Prediction: {pred}")

    # 7. Risk Management
    print("7. Testing Risk Management...")
    rm = RiskManager()
    account_info = {'balance': 10000, 'equity': 10000}
    safe = rm.check_risk(account_info, {'signal': final_signal})
    print(f"   ✅ Risk Check: {'Safe' if safe else 'Unsafe'}")
    
    # 8. Execution
    print("8. Testing Execution Logic...")
    router = OrderRouter(None) # Mock feed
    if final_signal != "NO_TRADE" and safe:
       router.execute_order({'signal': final_signal}, 0.1)
    
    print("✅ Full System Verification Complete!")

if __name__ == "__main__":
    verify_full_system()
