from .position_sizer import PositionSizer

class RiskManager:
    def __init__(self):
        self.position_sizer = PositionSizer()
        self.max_drawdown = 0.05 # 5%
        self.daily_loss_limit = 0.02 # 2%

    def check_risk(self, account_info: dict, signal: dict) -> bool:
        """
        Checks if the trade is safe to take.
        """
        if 'equity' not in account_info or 'balance' not in account_info:
            return False
            
        # Check Drawdown
        current_equity = account_info['equity']
        initial_balance = account_info.get('initial_balance', current_equity) # Fallback
        
        drawdown = (initial_balance - current_equity) / initial_balance
        if drawdown > self.max_drawdown:
            return False
            
        return True

    def calculate_trade_size(self, account_info, entry, sl):
        return self.position_sizer.calculate_size(account_info['balance'], entry, sl)
