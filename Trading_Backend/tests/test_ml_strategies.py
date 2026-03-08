import unittest
import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mt5_bridge"))

from strategies.ml.regression_strategy import LinearRegressionStrategy
from strategies.ml.lstm_strategy import LSTMStrategy

class TestMLStrategies(unittest.TestCase):
    
    def test_linreg_uptrend(self):
        strategy = LinearRegressionStrategy(window_size=20, forecast_horizon=1)
        
        # Create perfect uptrend
        prices = [100.0 + i for i in range(50)]
        df = pd.DataFrame({'close': prices})
        data = {"df": df}
        
        result = strategy.analyze("TEST", data, {})
        
        # Slope should be positive (1.0). Prediction > Current.
        self.assertEqual(result.get("signal"), "BUY")
        self.assertTrue("LinReg" in result.get("reason"))
        
    def test_lstm_mock_buy(self):
        strategy = LSTMStrategy()
        
        # Mock needs 3 continuous green candles
        # O: 10, C: 11
        # O: 11, C: 12
        # O: 12, C: 13
        
        closes = [10.0] * 50
        opens = [10.0] * 50
        
        # Update last 3
        closes[-3] = 11; opens[-3] = 10
        closes[-2] = 12; opens[-2] = 11
        closes[-1] = 13; opens[-1] = 12
        
        df = pd.DataFrame({'close': closes, 'open': opens})
        data = {"df": df}
        
        result = strategy.analyze("TEST", data, {})
        
        self.assertEqual(result.get("signal"), "BUY")
        self.assertTrue("LSTM" in result.get("reason"))

if __name__ == '__main__':
    unittest.main()
