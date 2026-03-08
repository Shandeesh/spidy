import pandas as pd
import numpy as np

class VolatilityFeatures:
    @staticmethod
    def add_all_volatility_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds volatility-based indicators to the DataFrame.
        """
        close = pd.to_numeric(df['close'], errors='coerce').fillna(0)
        high = pd.to_numeric(df['high'], errors='coerce').fillna(0)
        low = pd.to_numeric(df['low'], errors='coerce').fillna(0)

        # ATR (14)
        df['h-l'] = high - low
        df['h-pc'] = abs(high - close.shift(1))
        df['l-pc'] = abs(low - close.shift(1))
        tr = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        df['atr'] = tr.ewm(alpha=1/14, adjust=False).mean() # Wilder's smoothing
        
        # Bollinger Bands (20, 2)
        sma_20 = close.rolling(window=20).mean()
        std_20 = close.rolling(window=20).std()
        df['BBL_20_2.0'] = sma_20 - (2 * std_20)
        df['BBM_20_2.0'] = sma_20
        df['BBU_20_2.0'] = sma_20 + (2 * std_20)

        # Donchian Channels (20)
        df['DCL_20_20'] = low.rolling(window=20).min()
        df['DCM_20_20'] = (high.rolling(window=20).max() + low.rolling(window=20).min()) / 2
        df['DCU_20_20'] = high.rolling(window=20).max()

        # Keltner Channels (EMA 20 + 2*ATR10) - Approximation
        ema_20 = close.ewm(span=20, adjust=False).mean()
        atr_10 = tr.ewm(alpha=1/10, adjust=False).mean()
        df['KC_20'] = ema_20
        df['KC_Upper'] = ema_20 + (2 * atr_10)
        df['KC_Lower'] = ema_20 - (2 * atr_10)

        # Cleanup
        cols_to_drop = ['h-l', 'h-pc', 'l-pc']
        df.drop(columns=[c for c in cols_to_drop if c in df.columns], inplace=True)

        return df
