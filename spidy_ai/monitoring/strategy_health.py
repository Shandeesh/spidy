class StrategyHealth:
    """
    Tracks real-time performance of every strategy.
    Decides if a strategy should be disabled due to poor performance.
    """
    def __init__(self):
        # Dictionary to hold stats: { "strategy_name": { "wins": 0, "losses": 0, "pnl": 0.0, ... } }
        self.stats = {}

    def register_strategy(self, strategy_name):
        if strategy_name not in self.stats:
            self.stats[strategy_name] = {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "pnl": 0.0,
                "consecutive_losses": 0,
                "active": True
            }

    def update_trade(self, strategy_name, pnl):
        """
        Update stats after a trade closes.
        """
        if strategy_name not in self.stats:
            self.register_strategy(strategy_name)
            
        s = self.stats[strategy_name]
        s["trades"] += 1
        s["pnl"] += pnl
        
        if pnl > 0:
            s["wins"] += 1
            s["consecutive_losses"] = 0
        else:
            s["losses"] += 1
            s["consecutive_losses"] += 1
            
        # Check Kill Condition
        self._check_health(strategy_name)

    def _check_health(self, strategy_name):
        s = self.stats[strategy_name]
        
        # Rule 1: Kill if 5 losses in a row
        if s["consecutive_losses"] >= 5:
            print(f"HEALTH ALERT: Disabling {strategy_name} due to 5 consecutive losses.")
            s["active"] = False
            
        # Rule 2: Kill if Win Rate < 30% after 10 trades
        if s["trades"] >= 10:
            win_rate = s["wins"] / s["trades"]
            if win_rate < 0.30:
                 print(f"HEALTH ALERT: Disabling {strategy_name} due to low win rate ({win_rate:.2f}).")
                 s["active"] = False

    def is_healthy(self, strategy_name):
        if strategy_name not in self.stats:
             return True # Assume innocent until proven guilty
        return self.stats[strategy_name]["active"]
        
    def get_report(self):
        return self.stats
