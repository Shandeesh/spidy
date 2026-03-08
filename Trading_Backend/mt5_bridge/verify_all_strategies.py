import sys
import os
import pandas as pd
import numpy as np
import logging
import traceback

# Setup paths
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Strategy Manager to discover strategies
from strategy_manager import StrategyManager

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("StrategyVerifier")

def create_mock_data():
    """Creates a robust mock dataframe covering 200 bars."""
    dates = pd.date_range(end=pd.Timestamp.now(), periods=200, freq='1min')
    df = pd.DataFrame(index=dates)
    
    # Create realistic price movement
    np.random.seed(42)
    df['close'] = 100 + np.random.randn(200).cumsum()
    df['high'] = df['close'] + np.random.rand(200)
    df['low'] = df['close'] - np.random.rand(200)
    df['open'] = df['close'].shift(1).fillna(100)
    df['tick_volume'] = np.random.randint(100, 1000, 200)
    
    # Ensure expected columns exist
    df['time'] = df.index
    
    return df

def generate_mock_packet(df):
    """Generates the data packet passed to strategies."""
    return {
        "df": df,
        "price": df['close'].iloc[-1],
        "adx": 25.0,
        "vwap": df['close'].mean(),
        "rsi": 50.0
    }

def verify_strategies():
    print("---------------------------------------------------")
    print("STRATEGY DIAGNOSTIC TOOL")
    print("---------------------------------------------------")
    
    manager = StrategyManager()
    
    # Mock Data
    df = create_mock_data()
    packet = generate_mock_packet(df)
    market_state = {"TEST_SYM": {"regime": "RANGING", "bias": "NEUTRAL", "vwap": 100.0}}
    
    working = []
    broken = []
    silent = [] # Ran but returned no signal (which is fine, but needs checking)
    
    print(f"\nScanning {len(manager.strategies)} registered strategies...\n")
    
    for strategy in manager.strategies:
        name = strategy.get_name()
        try:
            # Run Analysis
            result = strategy.analyze("TEST_SYM", packet, market_state)
            
            if result is None:
                print(f"xx [BROKEN] {name}: Returned None (Expected dict)")
                broken.append((name, "Returned None"))
                continue
                
            signal = result.get("signal")
            
            if signal in ["BUY", "SELL"]:
                print(f"✅ [WORKING] {name} -> Signal: {signal}")
                working.append(name)
            elif signal in ["HOLD", "WAIT", "INFO"]:
                print(f"⚠️ [SILENT]  {name} -> Signal: {signal}")
                silent.append(name)
            else:
                print(f"xx [BROKEN] {name}: Invalid Signal '{signal}'")
                broken.append((name, f"Invalid Signal: {signal}"))
                
        except Exception as e:
            print(f"xx [CRASH]  {name}: {str(e)}")
            # traceback.print_exc()
            broken.append((name, str(e)))
            
    print("\n---------------------------------------------------")
    print(f"SUMMARY Results:")
    print(f"WORKING: {len(working)}")
    print(f"SILENT:  {len(silent)} (Technically working, just no trade)")
    print(f"BROKEN:  {len(broken)}")
    print("---------------------------------------------------")
    
    if broken:
        print("\nFAILURE REPORT:")
        for name, reason in broken:
            print(f"- {name}: {reason}")

    print("\n---------------------------------------------------")
    print("TESTING MANAGER CONSENSUS")
    print("---------------------------------------------------")
    # Force some state to trigger multiple strategies
    # e.g. Breakout High
    manager.market_state["TEST_SYM"] = {
        "regime": "TRENDING", 
        "bias": "NEUTRAL", 
        "vwap": 90.0,
        "adx": 35.0,
        "rsi": 40.0,
        "df": df # Crucial for strategies to run inside generate_signal
    }
    
    print("Requesting Signal from Manager (Expect Consensus)...")
    consensus = manager.generate_signal("TEST_SYM")
    if consensus:
        print(f"✅ CONSENSUS SIGNAL: {consensus['signal']}")
        print(f"   Reason: {consensus['reason']}")
        print(f"   Strategy: {consensus['strategy']}")
    else:
        print("x NO CONSENSUS REACHED (Check logs for individual failures)")

    print("\n---------------------------------------------------")
    print("TESTING SOLO STRONG STRATEGY (SUPERTREND)")
    print("---------------------------------------------------")
    
    # Mock return from SuperTrend ONLY
    solo_signal = [{
        "signal": "BUY",
        "strategy": "SuperTrend",
        "confidence": 0.95, 
        "reason": "Force Test"
    }]
    
    from strategies.execution.meta_strategy import MetaConsensusStrategy
    meta = MetaConsensusStrategy(min_votes=2.0)
    decision = meta.aggregate_results(solo_signal)
    
    if decision.get("signal") == "BUY":
        print(f"✅ SOLO TEST PASSED: SuperTrend (0.95) -> {decision['signal']} ({decision['reason']})")
    else:
        print(f"x SOLO TEST FAILED: Result was {decision.get('signal')} ({decision.get('reason')})")

if __name__ == "__main__":
    # verify_strategies()
    # Redirect stdout to file to avoid terminal encoding issues
    with open("strategy_report.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        verify_strategies()
        sys.stdout = sys.__stdout__
    print("Diagnosis complete. Results written to strategy_report.txt")
