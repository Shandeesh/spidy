from strategies.base_strategy import BaseStrategy


class MetaConsensusStrategy(BaseStrategy):
    """
    The 'Grandmaster' Strategy that combines inputs from all other strategies.
    Uses a Voting/Ensemble approach to filter noise and increase win rate.
    """
    def __init__(self, strategies=None, min_votes=3):
        super().__init__("MetaConsensus")
        self.strategies = strategies if strategies else []
        self.min_votes = min_votes
        
    def set_strategies(self, strategies):
        self.strategies = strategies

    def analyze(self, symbol: str, data: dict, market_state: dict) -> dict:
        """
        Aggregates signals from all registered strategies.
        """
        votes = []
        full_reasons = []
        
        # Breakdown by category for sophisticated weighting
        trend_votes = 0
        momentum_votes = 0
        volatility_votes = 0
        
        for strategy in self.strategies:
            # Skip self to prevent recursion
            if strategy.get_name() == "MetaConsensus": continue
            if "Detector" in strategy.get_name(): continue # Skip detectors
            
            try:
                # We assume strategies are stateless per call or handle their own state
                # Note: This technically re-runs analysis if called from outside, 
                # but if integrated into StrategyManager, we might pass pre-calculated results.
                # For now, we assume we receive the results list directly? 
                # No, standard interface is analyze.
                # BUT, StrategyManager will likely gather results first.
                pass 
            except Exception:
                continue
                
        # This class is largely a Logic Helper. 
        # The actual aggregation happens in StrategyManager.
        return {"signal": "HOLD"}
        
    def aggregate_results(self, results: list) -> dict:
        """
        Takes a list of {signal, strategy, confidence} dictionaries and determines the final call.
        """
        if not results:
            return {"signal": "HOLD", "reason": "No inputs"}
            
        buy_votes = 0
        sell_votes = 0
        
        buy_reasons = []
        sell_reasons = []
        
        weights = {
            "Strong": 2.0,
            "Normal": 1.0
        }
        
        for res in results:
            sig = res.get("signal")
            conf = res.get("confidence", 0.0)
            name = res.get("strategy", "Unknown")
            
            # Weighted Voting
            # Weighted Voting
            weight = 1.0
            
            # High Confidence Override (Allow Solo-Trade)
            if conf >= 0.85:
                weight = 2.0 
            # Strong Confidence Boost
            elif conf > 0.75:
                weight = 1.5
            
            # Trend Strategies get a slight nudge if not already maxed
            if "Trend" in name and weight < 2.0: 
                weight *= 1.2
            
            if sig == "BUY":
                buy_votes += weight
                buy_reasons.append(f"{name}({weight:.1f})")
            elif sig == "SELL":
                sell_votes += weight
                sell_reasons.append(f"{name}({weight:.1f})")
                
        # Decision Logic
        threshold = self.min_votes
        
        if buy_votes >= threshold and buy_votes > sell_votes:
            return {
                "signal": "BUY",
                "confidence": min(buy_votes / (threshold * 2), 1.0),
                "reason": f"Consensus BUY (Votes: {buy_votes:.1f} vs {sell_votes:.1f}) | Contributors: {', '.join(buy_reasons[:3])}",
                "strategy": "MetaConsensus"
            }
            
        if sell_votes >= threshold and sell_votes > buy_votes:
             return {
                "signal": "SELL",
                "confidence": min(sell_votes / (threshold * 2), 1.0),
                "reason": f"Consensus SELL (Votes: {sell_votes:.1f} vs {buy_votes:.1f}) | Contributors: {', '.join(sell_reasons[:3])}",
                "strategy": "MetaConsensus"
            }
            
        return {"signal": "HOLD", "reason": f"Mixed/Weak Signals (B:{buy_votes:.1f} S:{sell_votes:.1f})"}
