import unittest
import sys
import os

# Add the backend to path so tests can find modules
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mt5_bridge"))

# Import all test modules
from test_strategies import TestStrategies
from test_trend_strategies import TestTrendStrategies
from test_momentum_strategies import TestMomentumStrategies
from test_volatility_strategies import TestVolatilityStrategies
from test_ml_strategies import TestMLStrategies
from test_risk_execution import TestRiskExecution

def run_suite():
    # Initialize a test loader
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add tests from all modules
    suite.addTests(loader.loadTestsFromTestCase(TestStrategies))
    suite.addTests(loader.loadTestsFromTestCase(TestTrendStrategies))
    suite.addTests(loader.loadTestsFromTestCase(TestMomentumStrategies))
    suite.addTests(loader.loadTestsFromTestCase(TestVolatilityStrategies))
    suite.addTests(loader.loadTestsFromTestCase(TestMLStrategies))
    suite.addTests(loader.loadTestsFromTestCase(TestRiskExecution))

    # Run the suite
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("\nAll Strategy Modules Verified Successfully.")
        exit(0)
    else:
        print("\nSome Strategy Modules Failed Verification.")
        exit(1)

if __name__ == "__main__":
    run_suite()
