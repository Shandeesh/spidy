"""
Historical Data Fetcher for Backtesting
Extracts data from MT5 and prepares it for backtest engine
"""

import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timedelta
import os

class HistoricalDataFetcher:
    """Fetch and export historical data from MT5."""
    
    def __init__(self):
        self.connected = False
        
    def connect(self):
        """Connect to MT5."""
        if not mt5.initialize():
            print(f"MT5 initialization failed: {mt5.last_error()}")
            return False
        self.connected = True
        return True
        
    def fetch_data(self, symbol="EURUSD", timeframe=mt5.TIMEFRAME_M5, 
                   days_back=30, output_file=None):
        """
        Fetch historical bars from MT5.
        
        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe constant (M1, M5, H1, etc.)
            days_back: How many days of history to fetch
            output_file: Optional CSV file to save data
            
        Returns:
            pandas DataFrame
        """
        if not self.connected:
            if not self.connect():
                return None
                
        # Enable symbol
        if not mt5.symbol_select(symbol, True):
            print(f"Failed to select {symbol}")
            return None
            
        # Calculate start date
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Fetch bars
        rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)
        
        if rates is None or len(rates) == 0:
            print(f"No data received for {symbol}")
            return None
            
        # Convert to DataFrame
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Select relevant columns
        df = df[['time', 'open', 'high', 'low', 'close', 'tick_volume']]
        df.rename(columns={'tick_volume': 'volume'}, inplace=True)
        
        print(f"Fetched {len(df)} bars for {symbol} ({timeframe})")
        print(f"Date Range: {df['time'].min()} to {df['time'].max()}")
        
        # Save to CSV if requested
        if output_file:
            df.to_csv(output_file, index=False)
            print(f"Data saved to {output_file}")
            
        return df
        
    def disconnect(self):
        """Shutdown MT5 connection."""
        if self.connected:
            mt5.shutdown()
            self.connected = False


# Example Usage
if __name__ == "__main__":
    fetcher = HistoricalDataFetcher()
    
    # Fetch 30 days of EUR/USD M5 data
    df = fetcher.fetch_data(
        symbol="EURUSD",
        timeframe=mt5.TIMEFRAME_M5,
        days_back=30,
        output_file="EURUSD_M5_30days.csv"
    )
    
    if df is not None:
        print("\nSample Data:")
        print(df.head())
        print(f"\nTotal Bars: {len(df)}")
        
    fetcher.disconnect()
