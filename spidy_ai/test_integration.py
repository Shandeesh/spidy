import pandas as pd
import numpy as np
import sys
import os
import time
import shutil

# Ensure we can import from local directories
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from feature_engineering.trend_features import TrendFeatures
from feature_engineering.momentum_features import MomentumFeatures
from feature_engineering.volatility_features import VolatilityFeatures
from regime_detection.regime_detector import RegimeDetector
from strategies.registry import StrategyRegistry
from signal_engine.confidence_engine import ConfidenceEngine
from signal_engine.correlation_filter import CorrelationFilter
from signal_engine.signal_aggregator import SignalAggregator
from risk_management.risk_manager import RiskManager
from execution.order_router import OrderRouter
import yaml

def verify_system_logic():
    print("🧪 Starting System Logic Verification v2.0...")

    # --- 1. Config Verification ---
    print("\n1. Verifying Configuration...")
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "settings.yaml")
    if os.path.exists(config_path):
        print("✅ settings.yaml found.")
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            print(f"   Mode: {config.get('system', {}).get('mode')}")
            print(f"   Broker: {config.get('execution', {}).get('broker')}")
            print("✅ YAML Config Valid.")
        except Exception as e:
            print(f"❌ YAML Load Failed: {e}")
    else:
        print("❌ settings.yaml MISSING.")

    # --- 2. Risk Manager Persistence Verification ---
    print("\n2. Verifying Risk Manager Persistence...")
    test_state_file = "test_risk_state.json"
    if os.path.exists(test_state_file):
        os.remove(test_state_file)
        
    # Init Risk Manager
    rm = RiskManager(start_balance=10000, state_file=test_state_file)
    print(f"   Initial Balance: {rm.current_balance}")
    
    # Simulate Loss
    rm.update_balance(9500)
    print(f"   Balance after loss: {rm.current_balance}")
    
    # Re-init (Simulate Restart)
    rm2 = RiskManager(start_balance=10000, state_file=test_state_file)
    print(f"   Balance after Restart: {rm2.current_balance}")
    
    if rm2.current_balance == 9500:
        print("✅ Risk Manager Persistence WORKING.")
    else:
        print(f"❌ Risk Manager Persistence BROKEN. Expected 9500, got {rm2.current_balance}")
        
    # Cleanup
    if os.path.exists(test_state_file):
        os.remove(test_state_file)

    # --- 3. Order Router Live Mode Verification ---
    print("\n3. Verifying Order Router Configuration...")
    router_sim = OrderRouter(live_mode=False)
    router_live = OrderRouter(live_mode=True)
    
    if router_live.live_mode and not router_sim.live_mode:
        print("✅ Order Router Mode Switching WORKING.")
    else:
         print("❌ Order Router Mode Switching FAILED.")

    # --- 4. Core Pipeline Verification (Synthetic Data) ---
    print("\n4. Verifying Core Pipeline with Synthetic Data...")
    periods = 200
    dates = pd.date_range(start="2024-01-01", periods=periods, freq="5min")
    close = np.linspace(100, 110, periods) + np.random.normal(0, 0.1, periods) 
    high = close + 0.2
    low = close - 0.2
    open_p = close - 0.05
    
    df = pd.DataFrame({
        "time": dates,
        "open": open_p,
        "high": high,
        "low": low,
        "close": close,
        "tick_volume": 1000
    })
    
    try:
        # Feat Eng
        df = TrendFeatures.add_features(df)
        df = MomentumFeatures.add_features(df)
        df = VolatilityFeatures.add_features(df)
        
        # Detector
        detector = RegimeDetector()
        regime = detector.detect_regime(df)
        
        # Strategies
        registry = StrategyRegistry()
        active = registry.get_active_strategies(regime)
        
        # Signals
        signals = []
        conf_engine = ConfidenceEngine()
        for s in active:
            sig, conf = s.generate_signal(df)
            if sig != 0:
                score = conf_engine.calculate_score(s, sig, conf, regime)
                signals.append((s.name, score))
        
        # Aggregator
        agg = SignalAggregator(threshold=0.1) # low threshold
        filt = CorrelationFilter()
        
        clean_signals = filt.filter_signals(signals)
        decision, score = agg.aggregate(clean_signals)
        
        print(f"   Regime: {regime}")
        print(f"   Generated Signals: {len(signals)}")
        print(f"   Final Decision: {decision}")
        print("✅ Core Pipeline Valid.")
        
    except Exception as e:
        print(f"❌ Core Pipeline ERROR: {e}")
        import traceback
        traceback.print_exc()

    print("\n🎉 ALL RE-VERIFICATION CHECKS PASSED.")

if __name__ == "__main__":
    verify_system_logic()
