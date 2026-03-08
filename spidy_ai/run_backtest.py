import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtesting.engine import BacktestEngine

if __name__ == "__main__":
    print("🕷️ Spidy AI - Auto Backtest Initiated")
    # Generating mock data does not require a feed connection
    engine = BacktestEngine(data_feed=None) 
    engine.run(symbol="EURUSD", periods=500)
