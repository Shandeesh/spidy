import unittest
import sys
import os
import pandas as pd

# Add mt5_bridge to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mt5_bridge"))

from strategies.regime_detector import RegimeDetector
from strategies.rsi_mean_reversion import RSIMeanReversion

class TestStrategies(unittest.TestCase):
    
    def test_regime_detector_trending(self):
        strategy = RegimeDetector()
        
        # Mock Data: High ADX
        data = {"adx": 35.0, "df": pd.DataFrame({"dummy": range(50)})} # minimal DF to pass checks
        state = {}
        
        result = strategy.analyze("EURUSD", data, state)
        self.assertEqual(result.get("regime"), "TRENDING")

    def test_regime_detector_ranging(self):
        strategy = RegimeDetector()
        
        # Mock Data: Low ADX
        data = {"adx": 15.0, "df": pd.DataFrame({"dummy": range(50)})}
        state = {}
        
        result = strategy.analyze("EURUSD", data, state)
        self.assertEqual(result.get("regime"), "RANGING")

    def test_rsi_mean_reversion_buy(self):
        strategy = RSIMeanReversion()
        
        # Mock State: RANGING
        state = {"EURUSD": {"regime": "RANGING"}}
        # Mock Data: Oversold RSI
        data = {"rsi": 25.0}
        
        result = strategy.analyze("EURUSD", data, state)
        self.assertEqual(result.get("signal"), "BUY")
        self.assertTrue("Oversold" in result.get("reason"))

    def test_rsi_mean_reversion_trend_blocked(self):
        strategy = RSIMeanReversion()
        
        # Mock State: TRENDING
        state = {"EURUSD": {"regime": "TRENDING"}}
        data = {"rsi": 25.0}
        
        result = strategy.analyze("EURUSD", data, state)
        self.assertEqual(result.get("signal"), "HOLD") # Should block
        self.assertTrue("Trending" in result.get("reason"))

if __name__ == '__main__':
    unittest.main()
