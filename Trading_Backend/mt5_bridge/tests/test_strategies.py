import sys
import os
import pandas as pd
import unittest
from unittest.mock import MagicMock

# Add parent directory to path to allow imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import the new modules
from strategies.technical_analysis import TechnicalAnalyzer
from strategies.market_data import MarketDataProvider
from strategies.ai_modules import AIVisionModule, SocialVelocityModule, SelfHealingModule
from strategy_manager import StrategyManager

class TestStrategySystem(unittest.TestCase):
    
    def test_technical_analyzer_adx(self):
        print("\nTesting TechnicalAnalyzer ADX...")
        # Create dummy OHLCV data
        data = {
            'high': [10, 12, 11, 13, 15] * 10,
            'low': [8, 9, 8, 10, 12] * 10,
            'close': [9, 11, 10, 12, 14] * 10
        }
        df = pd.DataFrame(data)
        # We need enough data (50 rows)
        
        result = TechnicalAnalyzer.calculate_adx(df, period=14)
        self.assertIn('ADX', result.columns)
        print("ADX Calculation: OK")

    def test_technical_analyzer_vwap(self):
        print("\nTesting TechnicalAnalyzer VWAP...")
        data = {
            'high': [10, 12],
            'low': [8, 10],
            'close': [9, 11],
            'tick_volume': [100, 200]
        }
        df = pd.DataFrame(data)
        vwap = TechnicalAnalyzer.calculate_vwap(df)
        self.assertTrue(isinstance(vwap, float))
        print(f"VWAP Calculation: {vwap} OK")

    def test_market_data(self):
        print("\nTesting MarketDataProvider...")
        provider = MarketDataProvider()
        
        # Test PCR Stub
        pcr_data = provider.get_open_interest_pcr("NSE_TEST")
        self.assertIn("pcr", pcr_data)
        print(f"PCR Stub: {pcr_data} OK")

    def test_strategy_manager_init(self):
        print("\nTesting StrategyManager Integration...")
        manager = StrategyManager()
        self.assertTrue(hasattr(manager, 'market_state'))
        self.assertTrue(hasattr(manager, 'ai_vision'))
        print("StrategyManager Initialization: OK")

if __name__ == '__main__':
    unittest.main()
