from ..base.base_strategy import BaseStrategy
import pandas as pd

class EmaCrossStrategy(BaseStrategy):
    def __init__(self, short_period=9, long_period=21):
        super().__init__("EmaCross")
        self.short_period = short_period
        self.long_period = long_period

    def generate_signal(self, df: pd.DataFrame) -> dict:
        if df is None or df.empty:
            return {'signal': 'NEUTRAL', 'confidence': 0.0, 'metadata': {}}

        # Ensure we have enough data
        if len(df) < self.long_period + 1:
             return {'signal': 'NEUTRAL', 'confidence': 0.0, 'metadata': {}}

        # Get latest values from pre-calculated features
        # Assuming FeatureStore has run
        short_col = f'ema_{self.short_period}'
        long_col = f'ema_{self.long_period}'
        
        if short_col not in df.columns or long_col not in df.columns:
             # Determine if we can calculate on fly or just return Neutral
             # Since we moved to manual, we rely on FeatureStore
             return {'signal': 'NEUTRAL', 'confidence': 0.0, 'metadata': {'error': 'Missing features'}}

        short_ema = df[short_col].iloc[-1]
        long_ema = df[long_col].iloc[-1]
        
        prev_short_ema = df[short_col].iloc[-2]
        prev_long_ema = df[long_col].iloc[-2]
        
        signal = "NEUTRAL"
        confidence = 0.0

        # Crossover Logic
        if prev_short_ema < prev_long_ema and short_ema > long_ema:
            signal = "BUY"
            confidence = 0.8
        elif prev_short_ema > prev_long_ema and short_ema < long_ema:
            signal = "SELL"
            confidence = 0.8

        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {
                'short_ema': short_ema,
                'long_ema': long_ema
            }
        }
