import unittest
import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mt5_bridge"))

from strategies.risk.kelly import KellyCriterion
from strategies.execution.vwap_strategy import VWAPStrategy

class TestRiskExecution(unittest.TestCase):
    
    def test_kelly_calculation(self):
        # W=0.55, R=2.0
        # K = 0.55 - (0.45 / 2.0) = 0.55 - 0.225 = 0.325 (32.5%)
        # Half Kelly = 16.25%
        # Cap 5%
        
        share = KellyCriterion.calculate_fraction(0.55, 2.0, fraction_multiplier=0.5)
        # Should be 0.1625
        self.assertAlmostEqual(share, 0.1625)
        
        amount = KellyCriterion.get_suggested_risk_per_trade(10000, 0.55, 2.0)
        # 10000 * min(0.1625, 0.05) -> 10000 * 0.05 = 500
        self.assertEqual(amount, 500.0)

    def test_vwap_crossover(self):
        strategy = VWAPStrategy()
        
        # Fake DF
        # Volume constant.
        # Prices:
        # [100, 100, 100, 100, ... ] -> VWAP = 100.
        # Last price jumps to 102.
        
        prices = [100.0] * 10
        prices.append(102.0)
        
        df = pd.DataFrame({'close': prices, 'high': prices, 'low': prices, 'tick_volume': [100]*11})
        data = {"df": df}
        
        # Calc logic: VWAP should be slightly above 100 due to last 102?
        # (100*100*10 + 102*100*1) / (100*11) = (100000 + 10200) / 1100 = 110200/1100 = 100.18
        
        # Prev Price = 100. Current = 102.
        # VWAP = 100.18.
        # 100 < 100.18 AND 102 > 100.18
        # Cross UP!
        
        result = strategy.analyze("TEST", data, {})
        
        self.assertEqual(result.get("signal"), "BUY")
        self.assertTrue("VWAP" in result.get("reason"))

if __name__ == '__main__':
    unittest.main()
