import json
import time

class StrategyOptimizer:
    def __init__(self):
        pass

    def generate_strategy_pack(self, sentiment_data, trade_history=None):
        """
        Dynamically adjusts MT5 parameters using both real-time sentiment data (internet)
        and historical trade performance (logs/database).
        
        Parameters:
        - sentiment_data: list of dicts/strings representing news headlines and their sentiment
        - trade_history: list of dicts representing previous closed trades from SQLite DB
        
        Returns:
        - Dict with optimized settings: mode, fixed_lot_size, max_daily_loss, atr_multiplier
        """
        # Default fallback settings
        optimized_settings = {
            "symbol": "EURUSD",
            "timeframe": "M15",
            "mode": "STANDARD",
            "fixed_lot_size": 0.05,
            "atr_multiplier": 2.0,
            "max_daily_loss": 50.0,
            "auto_trade_enabled": True,
            "generated_at": time.time(),
            "metrics": {
                "sentiment_score": 0,
                "recent_win_rate": 1.0,
                "consecutive_losses": 0,
                "recent_net_profit": 0.0
            }
        }

        # 1. ANALYZE NEWS SENTIMENT (Internet Gathering)
        sentiment_score = 0
        if sentiment_data:
            for item in sentiment_data:
                if isinstance(item, dict):
                    s = item.get('sentiment', 'neutral').lower()
                    if 'positive' in s or 'bull' in s:
                        sentiment_score += 1
                    elif 'negative' in s or 'bear' in s:
                        sentiment_score -= 1
                elif isinstance(item, str):
                    s = item.lower()
                    if 'bull' in s or 'positive' in s or 'up' in s:
                        sentiment_score += 1
                    elif 'bear' in s or 'negative' in s or 'down' in s:
                        sentiment_score -= 1
        
        optimized_settings["metrics"]["sentiment_score"] = sentiment_score

        # 2. ANALYZE PREVIOUS TRADE RESULTS (Logs & DB)
        win_rate = 0.5
        consecutive_losses = 0
        net_profit = 0.0
        
        if trade_history:
            # Only consider the last 10 trades for short-term feedback loop
            recent_trades = trade_history[:10]
            total_trades = len(recent_trades)
            
            if total_trades > 0:
                wins = sum(1 for t in recent_trades if t.get('profit', 0.0) > 0.0)
                win_rate = wins / total_trades
                net_profit = sum(t.get('profit', 0.0) for t in recent_trades)
                
                # Calculate consecutive losses (working backwards from most recent trade)
                for t in recent_trades:
                    # Treat break-even or negative as loss in risk calculation
                    if t.get('profit', 0.0) <= 0.0:
                        consecutive_losses += 1
                    else:
                        break
                        
        optimized_settings["metrics"]["recent_win_rate"] = round(win_rate, 2)
        optimized_settings["metrics"]["consecutive_losses"] = consecutive_losses
        optimized_settings["metrics"]["recent_net_profit"] = round(net_profit, 2)

        # 3. DYNAMIC PARAMETERS TUNING RULES (Self-Healing / Adaptive Risk)
        if consecutive_losses >= 5:
            # CRITICAL FAILURE MODE: Halt trading to prevent capital wipeout
            optimized_settings["mode"] = "TIGHT"
            optimized_settings["fixed_lot_size"] = 0.01
            optimized_settings["atr_multiplier"] = 1.5
            optimized_settings["max_daily_loss"] = 10.0
            optimized_settings["auto_trade_enabled"] = False # Pause trading
            
        elif consecutive_losses >= 3 or win_rate < 0.40:
            # DEFENSIVE MODE: Tighten risk parameters
            optimized_settings["mode"] = "TIGHT"
            optimized_settings["fixed_lot_size"] = 0.02
            optimized_settings["atr_multiplier"] = 1.5
            optimized_settings["max_daily_loss"] = 20.0
            
        elif win_rate >= 0.65 and net_profit > 0:
            # EXCELLENT PERFORMANCE MODE: Enable optimization scaling
            if sentiment_score > 0:
                optimized_settings["mode"] = "AGGRESSIVE"
                optimized_settings["fixed_lot_size"] = 0.10
                optimized_settings["atr_multiplier"] = 3.0
                optimized_settings["max_daily_loss"] = 100.0
            else:
                optimized_settings["mode"] = "STANDARD"
                optimized_settings["fixed_lot_size"] = 0.08
                optimized_settings["atr_multiplier"] = 2.5
                optimized_settings["max_daily_loss"] = 80.0
                
        else:
            # STANDARD/NORMAL MODE: Balanced settings
            if sentiment_score < 0:
                optimized_settings["mode"] = "CONSERVATIVE"
                optimized_settings["fixed_lot_size"] = 0.04
                optimized_settings["atr_multiplier"] = 2.0
                optimized_settings["max_daily_loss"] = 40.0
            else:
                optimized_settings["mode"] = "STANDARD"
                optimized_settings["fixed_lot_size"] = 0.05
                optimized_settings["atr_multiplier"] = 2.0
                optimized_settings["max_daily_loss"] = 50.0

        return optimized_settings

if __name__ == "__main__":
    # Test stub
    optimizer = StrategyOptimizer()
    
    # Mock data simulating a recovery regime
    mock_headlines = [
        {"title": "USD surges after CPI report", "sentiment": "negative"},
        {"title": "Fed hints at interest rate cuts", "sentiment": "positive"},
        {"title": "Market volume increases", "sentiment": "positive"}
    ]
    
    mock_history = [
        {"ticket": 101, "profit": -10.0},
        {"ticket": 102, "profit": -5.0},
        {"ticket": 103, "profit": -2.0},
        {"ticket": 104, "profit": 15.0},
        {"ticket": 105, "profit": 30.0}
    ]
    
    pack = optimizer.generate_strategy_pack(mock_headlines, mock_history)
    print("Test Results:")
    print(json.dumps(pack, indent=2))
