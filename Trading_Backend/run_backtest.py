"""
Example Backtest Script
Demonstrates how to run a backtest with a simple RSI strategy
"""

import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(__file__))

from backtesting_engine import BacktestEngine, PaperOrderBook
from fetch_historical_data import HistoricalDataFetcher
import json

def calculate_rsi(prices, period=14):
    """Calculate RSI indicator."""
    if len(prices) < period + 1:
        return 50.0  # Neutral
        
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
            
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100.0
        
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


class RSIStrategy:
    """
    Simple RSI Mean Reversion Strategy:
    - BUY when RSI < 30 (oversold)
    - SELL when RSI > 70 (overbought)
    - Close opposite positions
    """
    
    def __init__(self, rsi_period=14, oversold=30, overbought=70, lot_size=0.01):
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.lot_size = lot_size
        self.price_history = []
        
    def execute(self, orderbook: PaperOrderBook, bar: pd.Series, symbol: str, timestamp):
        """Strategy logic executed on each bar."""
        # Update price history
        self.price_history.append(bar['close'])
        
        # Need enough data for RSI
        if len(self.price_history) < self.rsi_period + 1:
            return
            
        # Calculate RSI
        rsi = calculate_rsi(self.price_history, self.rsi_period)
        
        # Get current positions
        has_buy = any(pos['type'] == 'BUY' for pos in orderbook.positions.values())
        has_sell = any(pos['type'] == 'SELL' for pos in orderbook.positions.values())
        
        # Trading Logic
        if rsi < self.oversold and not has_buy:
            # Oversold - Enter BUY
            # Close any SELL positions first
            for ticket, pos in list(orderbook.positions.items()):
                if pos['type'] == 'SELL':
                    orderbook.close_position(ticket, bar['close'], timestamp)
                    
            # Open BUY
            sl = bar['close'] - (bar['close'] * 0.01)  # 1% SL
            tp = bar['close'] + (bar['close'] * 0.02)  # 2% TP
            orderbook.execute_order(symbol, 'BUY', self.lot_size, bar['close'], 
                                   sl=sl, tp=tp, timestamp=timestamp)
                                   
        elif rsi > self.overbought and not has_sell:
            # Overbought - Enter SELL
            # Close any BUY positions first
            for ticket, pos in list(orderbook.positions.items()):
                if pos['type'] == 'BUY':
                    orderbook.close_position(ticket, bar['close'], timestamp)
                    
            # Open SELL
            sl = bar['close'] + (bar['close'] * 0.01)  # 1% SL
            tp = bar['close'] - (bar['close'] * 0.02)  # 2% TP
            orderbook.execute_order(symbol, 'SELL', self.lot_size, bar['close'],
                                   sl=sl, tp=tp, timestamp=timestamp)
                                   
        # Close on neutral zone (Optional - could just let SL/TP handle it)
        elif 40 < rsi < 60:
            # Close all positions in neutral zone
            for ticket in list(orderbook.positions.keys()):
                orderbook.close_position(ticket, bar['close'], timestamp)


def run_backtest():
    """Main backtest execution."""
    print("=" * 60)
    print("SPIDY BACKTEST - RSI Mean Reversion Strategy")
    print("=" * 60)
    
    # 1. Fetch Historical Data
    print("\n[1/3] Fetching Historical Data...")
    
    csv_file = "EURUSD_M5_30days.csv"
    
    # Try to load from existing CSV first
    if os.path.exists(csv_file):
        print(f"Loading data from {csv_file}...")
        df = pd.read_csv(csv_file)
        df['time'] = pd.to_datetime(df['time'])
    else:
        # Fetch from MT5
        fetcher = HistoricalDataFetcher()
        df = fetcher.fetch_data(
            symbol="EURUSD",
            timeframe=5,  # M5
            days_back=30,
            output_file=csv_file
        )
        fetcher.disconnect()
        
    if df is None or len(df) == 0:
        print("ERROR: No data available for backtesting!")
        return
        
    print(f"Loaded {len(df)} bars from {df['time'].min()} to {df['time'].max()}")
    
    # 2. Initialize Strategy
    print("\n[2/3] Initializing Strategy...")
    strategy = RSIStrategy(rsi_period=14, oversold=30, overbought=70, lot_size=0.1)
    
    # 3. Run Backtest
    print("\n[3/3] Running Backtest...")
    engine = BacktestEngine(
        historical_data=df,
        strategy_func=strategy.execute,
        initial_balance=10000.0
    )
    
    results = engine.run(symbol="EURUSD")
    
    # 4. Display Results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)
    
    print(f"\n💰 Financial Performance:")
    print(f"   Initial Balance:  ${results['initial_balance']:,.2f}")
    print(f"   Final Equity:     ${results['final_equity']:,.2f}")
    print(f"   Total Return:     ${results['total_return']:,.2f}")
    print(f"   Return %:         {results['return_pct']:.2f}%")
    
    print(f"\n📊 Trade Statistics:")
    print(f"   Total Trades:     {results['total_trades']}")
    print(f"   Winning Trades:   {results['winning_trades']}")
    print(f"   Losing Trades:    {results['losing_trades']}")
    print(f"   Win Rate:         {results['win_rate']:.2f}%")
    
    print(f"\n⚠️  Risk Metrics:")
    print(f"   Max Drawdown:     ${results['max_drawdown']:,.2f}")
    print(f"   Recovery Factor:  {results['recovery_factor']:.2f}")
    print(f"   Profit Factor:    {results['profit_factor']:.2f}")
    
    # 5. Export Results
    output_file = "backtest_results.json"
    engine.orderbook.export_results(output_file)
    
    print(f"\n✅ Full results exported to: {output_file}")
    print("=" * 60)
    
    return results


if __name__ == "__main__":
    try:
        run_backtest()
    except KeyboardInterrupt:
        print("\n\nBacktest interrupted by user.")
    except Exception as e:
        print(f"\n\nERROR: {e}")
        import traceback
        traceback.print_exc()
