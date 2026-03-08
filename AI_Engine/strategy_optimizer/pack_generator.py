import json
import time

class StrategyOptimizer:
    def __init__(self):
        pass

    def generate_strategy_pack(self, sentiment_data):
        """
        Uses sentiment data to adjust MT5 parameters.
        """
        base_strategy = {
            "symbol": "EURUSD",
            "timeframe": "M15",
            "risk_percent": 1.0,
            "strategies": ["RSI", "MACD"]
        }

        # Logic: If news is positive/volatile, tighten stops or change risk
        score = sum([1 if x['sentiment'] == 'positive' else -1 for x in sentiment_data])
        
        if score > 0:
            base_strategy["risk_percent"] = 1.5
            base_strategy["mode"] = "AGGRESSIVE"
        else:
            base_strategy["risk_percent"] = 0.5
            base_strategy["mode"] = "CONSERVATIVE"

        base_strategy["generated_at"] = time.time()
        return base_strategy

if __name__ == "__main__":
    from internet_gathering.news_fetcher import NewsFetcher
    news = NewsFetcher().get_latest_headlines()
    
    optimizer = StrategyOptimizer()
    pack = optimizer.generate_strategy_pack(news)
    
    print(json.dumps(pack, indent=2))
