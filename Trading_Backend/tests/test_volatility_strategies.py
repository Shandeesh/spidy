import unittest
import sys
import os
import pandas as pd
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mt5_bridge"))

from strategies.volatility.bollinger_squeeze import BollingerSqueezeStrategy
from strategies.volatility.keltner_channel import KeltnerChannelStrategy

class TestVolatilityStrategies(unittest.TestCase):
    
    def test_bb_squeeze_breakout(self):
        strategy = BollingerSqueezeStrategy(period=10, std=2.0)
        
        # Create Squeeze Scenario:
        # Price oscillating slightly around 100 -> Low Std Dev
        prices = [100.0 + ((-1)**i * 0.1) for i in range(30)]
        # Last bar shoots up to Breakout
        prices.append(105.0) 
        
        df = pd.DataFrame({'close': prices})
        data = {"df": df}
        
        result = strategy.analyze("TEST", data, {})
        
        if result.get("signal") != "BUY":
            print(f"BB Squeeze Test Failed. Result: {result}")
            # Debug
            # We need to see BB Width
            from strategies.technical_analysis import TechnicalAnalyzer
            df_bb = TechnicalAnalyzer.calculate_bollinger_bands(df, 10, 2.0)
            print("Debug BB Width tail:")
            print(df_bb['bb_width'].tail())
            
        self.assertEqual(result.get("signal"), "BUY")
        self.assertTrue("Squeeze" in result.get("reason"))

    def test_keltner_breakout_down(self):
        # Narrow channel (Multiplier 0.5) to ensure breakout despite EMA lag
        strategy = KeltnerChannelStrategy(period=20, multiplier=0.5, atr_period=10)
        
        # Create Stable Channel
        data_len = 50
        df = pd.DataFrame({
            'high': [100.0] * data_len,
            'low': [90.0] * data_len,
            'close': [95.0] * data_len 
        })
        
        # ATR calculation needs movement? 
        # TR = max(H-L, H-Cp, L-Cp).
        # H=100, L=90 => TR=10. ATR~10.
        # Mid=95. Upper=105. Lower=85.
        
        # Breakout Down: Close < 85.
        # Let's set close to 80.
        
        df.iloc[-1] = {'high': 95, 'low': 70, 'close': 80} 
        
        data = {"df": df}
        result = strategy.analyze("TEST", data, {})
        
        if result.get("signal") != "SELL":
             print(f"Keltner Test Failed. Result: {result}")
             
        self.assertEqual(result.get("signal"), "SELL")
        self.assertTrue("Keltner" in result.get("reason"))

if __name__ == '__main__':
    unittest.main()
