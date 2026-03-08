import requests
from bs4 import BeautifulSoup
import json

class NewsFetcher:
    def __init__(self):
        self.sources = [
            "https://finance.yahoo.com/topic/stock-market-news/"
        ]

    def get_latest_headlines(self):
        """
        Fetches headlines from Yahoo Finance RSS.
        """
        headlines = []
        try:
            import feedparser
            # Yahoo Finance Top News RSS
            feed_url = "https://finance.yahoo.com/news/rssindex"
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries[:5]: # Top 5
                # Simple keyword sentiment (naive)
                title = entry.title
                sentiment = "neutral"
                lower_title = title.lower()
                
                if any(x in lower_title for x in ["soars", "jumps", "rally", "high", "gain", "bull", "optimism"]):
                    sentiment = "positive"
                elif any(x in lower_title for x in ["drops", "falls", "plunge", "low", "loss", "bear", "crash", "fear"]):
                    sentiment = "negative"
                    
                headlines.append({"title": title, "sentiment": sentiment})
                
        except ImportError:
            print("Error: feedparser module not found. Please pip install feedparser.")
            # Fallback - Safety
            return [{"title": "System: News Feed Unavailable (Missing Lib)", "sentiment": "neutral"}]
        except Exception as e:
            print(f"Error fetching news: {e}")
            return [{"title": f"System: News Error ({str(e)})", "sentiment": "neutral"}]
        
        return headlines

    def get_dxy_status(self):
        """
        Fetches the US Dollar Index (DXY) status.
        Returns: { "price": float, "change_pct": float, "status": "BULLISH"|"BEARISH"|"NEUTRAL" }
        """
        try:
            # Try yfinance first (Most accurate)
            import yfinance as yf
            ticker = yf.Ticker("DX-Y.NYB") # DXY Symbol on Yahoo
            # Get fast data
            hist = ticker.history(period="1d", interval="1m") # 1m data for immediate trend
            
            if hist.empty:
                # Fallback to daily if minute data fails (market closed)
                hist = ticker.history(period="5d")
            
            if not hist.empty:
                current = hist["Close"].iloc[-1]
                open_price = hist["Open"].iloc[0] # Open of the session
                
                # Calculate change
                change = current - open_price
                change_pct = (change / open_price) * 100
                
                status = "NEUTRAL"
                if change_pct > 0.1: status = "BULLISH" # +0.1% is solid green
                if change_pct < -0.1: status = "BEARISH" # -0.1% is solid red
                
                return {
                    "price": round(current, 3),
                    "change_pct": round(change_pct, 4),
                    "status": status
                }
                
        except ImportError:
            print("Warning: yfinance not found. Cannot fetch DXY.")
        except Exception as e:
            print(f"DXY Fetch Error: {e}")
            
        # Fallback Safe
        return { "price": 0.0, "change_pct": 0.0, "status": "NEUTRAL" }

if __name__ == "__main__":
    fetcher = NewsFetcher()
    print(json.dumps(fetcher.get_latest_headlines(), indent=2))
