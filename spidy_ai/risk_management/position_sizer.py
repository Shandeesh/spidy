class PositionSizer:
    """Calculate a conservatively capped position size in standard lots."""

    def __init__(
        self,
        risk_per_trade=0.01,
        *,
        risk_per_trade_pct=None,
        max_lot_size=1.0,
        contract_size=100_000,
    ):
        # ``risk_per_trade_pct`` is the name used by settings.yaml. Keep the
        # original fractional argument for existing callers.
        if risk_per_trade_pct is not None:
            risk_per_trade = risk_per_trade_pct
        self.risk_per_trade = max(0.0, float(risk_per_trade))
        self.max_lot_size = max(0.0, float(max_lot_size))
        self.contract_size = max(1.0, float(contract_size))

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
            
        # ``sl_distance`` is a price difference, so risk per standard lot is
        # distance × contract size. Returning raw units fed values such as
        # 100,000 directly into MT5's *lot* field.
        risk_per_lot = sl_distance * self.contract_size
        if risk_per_lot <= 0:
            return 0.0

        return min(risk_amount / risk_per_lot, self.max_lot_size)
