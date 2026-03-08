from ..base.base_strategy import BaseStrategy
import pandas as pd

class RsiStrategy(BaseStrategy):
    def __init__(self, period=14, overbought=70, oversold=30):
        super().__init__("RSI_Strategy")
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def generate_signal(self, df: pd.DataFrame) -> dict:
        if df is None or df.empty:
            return {'signal': 'NEUTRAL', 'confidence': 0.0, 'metadata': {}}

        # Check if RSI is pre-calculated
        if 'rsi' in df.columns:
            rsi_val = df['rsi'].iloc[-1]
        else:
             return {'signal': 'NEUTRAL', 'confidence': 0.0, 'metadata': {'error': 'Missing RSI'}}

        signal = "NEUTRAL"
        confidence = 0.0

        if rsi_val < self.oversold:
            signal = "BUY"
            confidence = 0.7 # Mean reversion
        elif rsi_val > self.overbought:
            signal = "SELL"
            confidence = 0.7

        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {
                'rsi': rsi_val
            }
        }
