from .confidence_engine import ConfidenceEngine
from .correlation_filter import CorrelationFilter

class SignalAggregator:
    def __init__(self):
        self.confidence_engine = ConfidenceEngine()
        self.correlation_filter = CorrelationFilter()

    def aggregate_signals(self, strategy_signals: list, regime_data: dict) -> str:
        """
        Aggregates multiple strategy signals into a final decision.
        """
        # 1. Collect Valid Signals
        valid_signals = []
        for s in strategy_signals:
            if s['signal'] != "NEUTRAL":
                # 2. Adjust Confidence
                s['final_confidence'] = self.confidence_engine.calculate_confidence(s, regime_data)
                valid_signals.append(s)
        
        if not valid_signals:
            return "NO_TRADE"
            
        # 3. Simple Voting or Highest Confidence
        # Let's pick the one with highest confidence for now
        best_signal = max(valid_signals, key=lambda x: x['final_confidence'])
        
        if best_signal['final_confidence'] > 0.6: # Threshold
            return best_signal['signal']
            
        return "NO_TRADE"
