class PositionSizer:
    def __init__(self, risk_per_trade=0.01):
        self.risk_per_trade = risk_per_trade

    def calculate_size(self, account_balance: float, entry_price: float, stop_loss: float) -> float:
        """
        Calculates position size based on risk percent and stop loss distance.
        """
        if account_balance <= 0 or entry_price <= 0 or stop_loss <= 0:
            return 0.0

        risk_amount = account_balance * self.risk_per_trade
        sl_distance = abs(entry_price - stop_loss)
        
        if sl_distance == 0:
            return 0.0
            
        # Standard Lots Calculation (assuming forex standard lot = 100,000 units)
        # This is simplified. Real logic needs pip value, contract size etc.
        # size = risk_amount / sl_distance
        
        # For now, return raw units
        units = risk_amount / sl_distance
        return units
