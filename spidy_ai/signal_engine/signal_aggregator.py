from .confidence_engine import ConfidenceEngine
from .correlation_filter import CorrelationFilter

class SignalAggregator:
    def __init__(self, threshold=1.0):
        self.threshold = threshold
        self.confidence_engine = ConfidenceEngine()
        self.correlation_filter = CorrelationFilter()

    def aggregate(self, filtered_signals: list) -> tuple:
        """
        Aggregates list of (strategy_name, score) into a decision and net score.
        Used by main.py and test_integration.py.
        """
        if not filtered_signals:
            return "HOLD", 0.0

        total_score = sum(score for name, score in filtered_signals)
        
        if total_score >= self.threshold:
            return "BUY", total_score
        elif total_score <= -self.threshold:
            return "SELL", total_score
        else:
            return "HOLD", total_score

    def aggregate_signals(self, strategy_signals: list, regime_data: dict) -> str:
        """
        Aggregates multiple strategy signal dicts into a final decision string.
        """
        valid_signals = []
        for s in strategy_signals:
            if s.get('signal') != "NEUTRAL":
                s['final_confidence'] = self.confidence_engine.calculate_confidence(s, regime_data)
                valid_signals.append(s)
        
        if not valid_signals:
            return "HOLD"
            
        best_signal = max(valid_signals, key=lambda x: x['final_confidence'])
        if best_signal['final_confidence'] > 0.6: 
            return best_signal['signal']
            
        return "HOLD"
