import sys
import os
import MetaTrader5 as mt5

# Add the project root to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from data_feed.metatrader_feed import MetaTraderFeed
from data_feed.data_validator import DataValidator

def test_feed():
    print("Testing MetaTraderFeed...")
    feed = MetaTraderFeed() 
    
    # We assume MT5 is installed and we might not need login for basic connection if terminal is open
    if feed.connect():
        print("✅ Connected to MT5")
        
        symbol = "EURUSD"
        print(f"Fetching data for {symbol}...")
        df = feed.get_historical_data(symbol, mt5.TIMEFRAME_M1, 100)
        
        if df is not None:
            print(f"✅ Fetched {len(df)} rows")
            print(df.head())
            
            print("Validating data...")
            cleaned_df = DataValidator.validate_ohlcv(df)
            
            if cleaned_df is not None:
                print("✅ Data Validated and Cleaned")
                print(cleaned_df.describe())
            else:
                print("❌ Data Validation Failed")
        else:
            print("❌ Failed to fetch data. Ensure Market Watch has the symbol.")
            
        feed.disconnect()
    else:
        print("❌ Failed to connect to MT5")

if __name__ == "__main__":
    test_feed()
