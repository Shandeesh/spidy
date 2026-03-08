from ..base.base_strategy import BaseStrategy
import pandas as pd

class AtrBreakoutStrategy(BaseStrategy):
    def __init__(self, atr_period=14, length=20):
        super().__init__("AtrBreakout")
        self.atr_period = atr_period
        self.length = length

    def generate_signal(self, df: pd.DataFrame) -> dict:
        if df is None or df.empty:
            return {'signal': 'NEUTRAL', 'confidence': 0.0, 'metadata': {}}

        current_close = df['close'].iloc[-1]
        
        # Donchian Channels from manual feature engineering
        # DCL_20_20, DCU_20_20
        dcl_col = f'DCL_{self.length}_{self.length}'
        dcu_col = f'DCU_{self.length}_{self.length}'

        if dcl_col in df.columns and dcu_col in df.columns: 
            lower_bound = df[dcl_col].iloc[-2] 
            upper_bound = df[dcu_col].iloc[-2]
            
            # Or use High/Low rolling check if features missing
        else:
            # Fallback for safety using pandas rolling
            high_n = df['high'].shift(1).rolling(window=self.length).max().iloc[-1]
            low_n = df['low'].shift(1).rolling(window=self.length).min().iloc[-1]
            upper_bound = high_n
            lower_bound = low_n

        signal = "NEUTRAL"
        confidence = 0.0

        # We verify if previous features were roughly correct
        # Logic: Breakout of N-period high/low
        
        # Recalculate High N manually just to be sure we match logic
        high_n = df['high'].iloc[-self.length-1:-1].max()
        low_n = df['low'].iloc[-self.length-1:-1].min()

        if current_close > high_n:
            signal = "BUY"
            confidence = 0.6
        elif current_close < low_n:
            signal = "SELL"
            confidence = 0.6

        return {
            'signal': signal,
            'confidence': confidence,
            'metadata': {
                'high_n': high_n,
                'low_n': low_n
            }
        }
