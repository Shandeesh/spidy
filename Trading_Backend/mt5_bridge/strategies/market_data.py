import logging
import random
import datetime

# Try importing yfinance, handle failure gracefully
try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

class MarketDataProvider:
    """
    Handles advanced data feeds: Open Interest (OI), Inter-Market Correlations.
    """
    def __init__(self):
        self.logger = logging.getLogger("MarketDataProvider")
        self.logger.setLevel(logging.INFO)
        self.pcr_cache = {} # {symbol: {"pcr": 1.1, "sentiment": "BULLISH", "updated": time}}
        self.correlation_cache = {} # {symbol: {"correlated_asset": "CL=F", "correlation": 0.85, "signal": "NEUTRAL"}}

    def get_open_interest_pcr(self, symbol: str) -> dict:
        """
        Returns Put-Call Ratio (PCR) for the symbol.
        Currently a STUB that returns simulated data or defaults.
        Future: Connect to Shoonya/NSE API.
        """
        # TODO: Implement Real API Connection
        
        # Stub Logic for Testing
        # Simulate a PCR between 0.5 and 1.5
        # In production without API, return Neutral
        
        # Check cache first (cached for 1 minute)
        if symbol in self.pcr_cache:
            last_update = self.pcr_cache[symbol]["updated"]
            if (datetime.datetime.now() - last_update).total_seconds() < 60:
                return self.pcr_cache[symbol]

        # Generate Stub Data (REMOVE IN PRODUCTION)
        # pcr = round(random.uniform(0.6, 1.4), 2)
        pcr = 1.0 # Default Neutral
        
        sentiment = "NEUTRAL"
        if pcr > 1.2: sentiment = "BULLISH"
        elif pcr < 0.7: sentiment = "BEARISH"
        
        data = {
            "pcr": pcr,
            "sentiment": sentiment,
            "updated": datetime.datetime.now()
        }
        self.pcr_cache[symbol] = data
        return data

    def check_correlation(self, symbol: str) -> str:
        """
        Checks correlated assets for a signal.
        """
        if not HAS_YFINANCE:
            return "NEUTRAL"
        
        # Check Cache
        if symbol in self.correlation_cache:
            entry = self.correlation_cache[symbol]
            if (datetime.datetime.now() - entry["updated"]).total_seconds() < 300: # 5 min cache
                return entry["signal"]
                
        signal = "NEUTRAL"
        
        try:
            # 1. Oil vs USDINR (India Specific)
            # If Oil spikes, USDINR usually rises (Rupee weakens).
            if symbol == "USDINR" or symbol == "USDINR.NSE":
                oil_ticker = "CL=F" # Crude Oil Futures
                oil = yf.Ticker(oil_ticker)
                hist = oil.history(period="1d")
                if not hist.empty:
                    close = hist['Close'].iloc[-1]
                    open_price = hist['Open'].iloc[-1]
                    pct_change = (close - open_price) / open_price
                    
                    if pct_change > 0.02: # +2% Spike
                        return "FORCE_BUY" # Oil up -> Rupee down -> USDINR up
                        
            # 2. DXY vs EURUSD/Gold
            # If DXY spikes, EURUSD/Gold falls.
            if symbol in ["EURUSD", "XAUUSD"]:
                dxy_ticker = "DX-Y.NYB" # US Dollar Index
                dxy = yf.Ticker(dxy_ticker)
                hist = dxy.history(period="1d")
                if not hist.empty:
                    close = hist['Close'].iloc[-1]
                    open_price = hist['Open'].iloc[-1]
                    pct_change = (close - open_price) / open_price
                    
                    if pct_change > 0.005: # +0.5% Spike (Significant for DXY)
                         return "BLOCK_BUY" # Strong Dollar -> Block Buy on Euro/Gold
                    elif pct_change < -0.005:
                         return "BLOCK_SELL" # Weak Dollar -> Block Sell

        except Exception as e:
            self.logger.error(f"Correlation Check Failed: {e}")
            
        # Update Cache
        self.correlation_cache[symbol] = {
            "signal": signal,
            "updated": datetime.datetime.now()
        }
            
        return signal
