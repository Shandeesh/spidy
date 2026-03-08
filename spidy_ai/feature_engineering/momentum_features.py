import pandas as pd
import numpy as np

class MomentumFeatures:
    @staticmethod
    def add_all_momentum_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds momentum-based indicators to the DataFrame.
        """
        # Ensure numeric
        close = pd.to_numeric(df['close'], errors='coerce').fillna(0)
        high = pd.to_numeric(df['high'], errors='coerce').fillna(0)
        low = pd.to_numeric(df['low'], errors='coerce').fillna(0) # Not used directly here but good practice
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).fillna(0)
        loss = (-delta.where(delta < 0, 0)).fillna(0)
        
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Stochastic RSI uses the RSI values
        # StochRSI = (RSI - MinRSI) / (MaxRSI - MinRSI)
        window = 14
        min_rsi = df['rsi'].rolling(window=window).min()
        max_rsi = df['rsi'].rolling(window=window).max()
        
        # Avoid division by zero
        denom = max_rsi - min_rsi
        denom = denom.replace(0, 1e-10) 
        
        df['STOCHRSIk_14_14_3_3'] = (df['rsi'] - min_rsi) / denom

        # Williams %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
        hh = high.rolling(window=14).max()
        ll = low.rolling(window=14).min()
        denom_wr = hh - ll
        denom_wr = denom_wr.replace(0, 1e-10)
        
        df['willr'] = -100 * ((hh - close) / denom_wr)

        # CCI = (TP - SMA(TP)) / (0.015 * MeanDeviation)
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(window=14).mean()
        mad = tp.rolling(window=14).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
        
        mad = mad.replace(0, 1e-10)
        
        df['cci'] = (tp - sma_tp) / (0.015 * mad)

        return df
