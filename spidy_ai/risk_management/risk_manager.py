import json
import os
from .position_sizer import PositionSizer

class RiskManager:
    def __init__(self, start_balance=10000.0, max_daily_dd_pct=0.05, max_total_dd_pct=0.15, state_file=None):
        self.position_sizer = PositionSizer()
        self.start_balance = start_balance
        self.current_balance = start_balance
        self.max_daily_dd_pct = max_daily_dd_pct
        self.max_total_dd_pct = max_total_dd_pct
        self.state_file = state_file
        
        self.max_drawdown = max_total_dd_pct
        self.daily_loss_limit = max_daily_dd_pct
        
        self.load_state()

    def load_state(self):
        if self.state_file and os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.current_balance = data.get('current_balance', self.start_balance)
            except Exception:
                pass

    def save_state(self):
        if self.state_file:
            try:
                with open(self.state_file, 'w') as f:
                    json.dump({'current_balance': self.current_balance}, f)
            except Exception:
                pass

    def update_balance(self, new_balance: float):
        self.current_balance = new_balance
        self.save_state()

    def can_trade(self) -> bool:
        """
        Checks if current drawdown allows trading.
        """
        drawdown = (self.start_balance - self.current_balance) / self.start_balance
        if drawdown > self.max_total_dd_pct:
            return False
        return True

    def check_risk(self, account_info: dict, signal: dict) -> bool:
        """
        Checks if the trade is safe to take.
        """
        if 'equity' not in account_info or 'balance' not in account_info:
            return False
            
        current_equity = account_info['equity']
        initial_balance = account_info.get('initial_balance', current_equity)
        
        drawdown = (initial_balance - current_equity) / initial_balance
        if drawdown > self.max_drawdown:
            return False
            
        return True

    def calculate_trade_size(self, account_info, entry, sl):
        balance = account_info.get('balance', self.current_balance)
        return self.position_sizer.calculate_size(balance, entry, sl)
