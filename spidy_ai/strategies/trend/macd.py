from ..base.base_strategy import BaseStrategy

class MACDStrategy(BaseStrategy):
    """
    Trend strategy using MACD crossover.
    """
    def __init__(self):
        super().__init__(
            name="MACD_Standard",
            strategy_type="TREND",
            base_weight=1.4
        )

    def is_applicable(self, market_regime):
        # Good for Strong and Weak Trends
        return market_regime in ["STRONG_TREND", "WEAK_TREND"]

    def generate_signal(self, df):
        if df is None or len(df) < 2:
            return 0, 0.0

        if 'MACD' not in df.columns or 'MACD_SIGNAL' not in df.columns:
            return 0, 0.0

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        curr_macd = curr['MACD']
        curr_sig = curr['MACD_SIGNAL']
        prev_macd = prev['MACD']
        prev_sig = prev['MACD_SIGNAL']

        signal = 0
        confidence = 0.0

        # Bullish Crossover: MACD crosses above Signal
        if prev_macd <= prev_sig and curr_macd > curr_sig:
            signal = 1
            confidence = 0.75
            
            # Boost if Histogram is getting stronger (example logic)
            if 'MACD_HIST' in curr and curr['MACD_HIST'] > prev['MACD_HIST']:
                confidence += 0.1

        # Bearish Crossover: MACD crosses below Signal
        elif prev_macd >= prev_sig and curr_macd < curr_sig:
            signal = -1
            confidence = 0.75
            
            if 'MACD_HIST' in curr and curr['MACD_HIST'] < prev['MACD_HIST']:
                confidence += 0.1

        return signal, confidence
