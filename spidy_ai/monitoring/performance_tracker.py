class PerformanceTracker:
    def __init__(self):
        self.trades = []

    def log_trade(self, trade_info: dict):
        self.trades.append(trade_info)

    def get_metrics(self):
        return {"total_trades": len(self.trades), "profit_loss": 0.0}
