import sys
import os
import pandas as pd
import unittest
import datetime

# Add parent directory to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the new modules
from strategies.technical_analysis import TechnicalAnalyzer
from strategy_manager import StrategyManager

class TestGapStrategy(unittest.TestCase):
    
    def test_orb_calculation(self):
        print("\nTesting ORB Calculation...")
        
        # Create Dummy Data for 9:15 to 9:45
        times = pd.date_range(start="2025-01-01 09:00:00", periods=60, freq="1min")
        
        # High of 9:15-9:30 will be 100
        # Low of 9:15-9:30 will be 90
        highs = [95] * 60
        lows = [92] * 60
        
        # Set specific high/low inside the window
        highs[20] = 100 # 09:20
        lows[25] = 90  # 09:25
        
        df = pd.DataFrame({
            "time": times,
            "high": highs,
            "low": lows,
            "close": [93] * 60
        })
        
        levels = TechnicalAnalyzer.calculate_orb_levels(df, start_time="09:15", end_time="09:30")
        
        self.assertIsNotNone(levels)
        self.assertEqual(levels['orb_high'], 100)
        self.assertEqual(levels['orb_low'], 90)
        print(f"ORB Levels: {levels} OK")
        
    def test_orb_breakout(self):
        print("\nTesting ORB Breakout Signal...")
        levels = {"orb_high": 100, "orb_low": 90}
        
        # Test Buy Breakout
        sig = TechnicalAnalyzer.check_orb_breakout(101, levels)
        self.assertEqual(sig, "BUY_BREAKOUT")
        
        # Test Sell Breakout
        sig = TechnicalAnalyzer.check_orb_breakout(89, levels)
        self.assertEqual(sig, "SELL_BREAKOUT")
        
        # Test Neutral
        sig = TechnicalAnalyzer.check_orb_breakout(95, levels)
        self.assertEqual(sig, "NEUTRAL")
        
        print("ORB Signals: OK")

if __name__ == '__main__':
    unittest.main()
