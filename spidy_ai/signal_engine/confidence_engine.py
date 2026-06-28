class ConfidenceEngine:
    def __init__(self):
        pass

    def calculate_confidence(self, signal_data: dict, regime_data: dict) -> float:
        """
        Adjusts signal confidence based on market regime and other factors.
        """
        base_confidence = signal_data.get('confidence', 0.5)
        regime = regime_data.get('regime', 'UNKNOWN')
        
        adjusted_confidence = base_confidence 
        if regime == "STRONG_TREND":
            adjusted_confidence *= 1.1
        elif regime == "RANGING":
            adjusted_confidence *= 0.9
            
        return min(max(adjusted_confidence, 0.0), 1.0)

    def calculate_score(self, strategy, signal, conf, regime) -> float:
        """
        Calculates a score (direction * confidence) adjusted by regime.
        Used by main.py and test_integration.py.
        """
        adjusted = conf
        strategy_name = strategy.name if hasattr(strategy, 'name') else str(strategy)
        
        if regime == "STRONG_TREND":
            if "Cross" in strategy_name or "MACD" in strategy_name or "Breakout" in strategy_name:
                adjusted *= 1.2
        elif regime == "RANGING":
            if "RSI" in strategy_name:
                adjusted *= 1.2
            else:
                adjusted *= 0.7
                
        # Determine direction multiplier
        direction = 0
        if isinstance(signal, str):
            if signal == "BUY":
                direction = 1
            elif signal == "SELL":
                direction = -1
        elif isinstance(signal, (int, float)):
            if signal > 0:
                direction = 1
            elif signal < 0:
                direction = -1
                
        return float(direction * adjusted)
