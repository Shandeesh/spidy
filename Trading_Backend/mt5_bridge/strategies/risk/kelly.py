class KellyCriterion:
    """
    Kelly Criterion Calculation Module.
    K% = W - (1 - W) / R
    Where:
    W = Winning Probability (0.0 to 1.0)
    R = Win/Loss Ratio
    """
    @staticmethod
    def calculate_fraction(win_rate: float, risk_reward_ratio: float, fraction_multiplier: float = 0.5) -> float:
        """
        Calculates the optimal capital fraction to risk.
        Includes a 'fraction_multiplier' (Half-Kelly, Quarter-Kelly) for safety, 
        as Full Kelly is often too volatile.
        """
        if risk_reward_ratio <= 0:
            return 0.0
            
        # Kelly Formula
        # K = W - (1-W)/R
        kelly_pct = win_rate - ((1 - win_rate) / risk_reward_ratio)
        
        # Apply safety multiplier (Half Kelly is standard practice)
        safe_kelly = kelly_pct * fraction_multiplier
        
        # Clip to safe ranges (e.g., never risk more than 5% or less than 0)
        # Assuming this returns fraction of ACCOUNT EQUITY to risk.
        # usually we risk 1-2%. If Kelly says 10%, we might cap it.
        
        return max(0.0, safe_kelly)

    @staticmethod
    def get_suggested_risk_per_trade(capital: float, win_rate: float = 0.55, risk_reward: float = 2.0) -> float:
        """
        Returns the dollar amount to risk on the next trade.
        """
        k_fraction = KellyCriterion.calculate_fraction(win_rate, risk_reward)
        
        # Hard Cap at 5% risk per trade for safety
        k_fraction = min(k_fraction, 0.05)
        
        return capital * k_fraction
