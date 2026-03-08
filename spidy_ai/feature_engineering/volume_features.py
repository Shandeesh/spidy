import pandas as pd
import numpy as np

class VolumeFeatures:
    @staticmethod
    def add_all_volume_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds volume-based indicators to the DataFrame.
        """
        # VWAP
        # Typical Price * Volume / Cumulative Volume
        tp = (df['high'] + df['low'] + df['close']) / 3
        # Since we might not have 'day' boundaries easily here, we'll do a rolling VWAP or cumulative from start
        # For simplicity in feature engineering (often rolling or full series), we'll do cumulative sum
        df['vwap'] = (tp * df['tick_volume']).cumsum() / df['tick_volume'].cumsum()
        
        # Money Flow Index (MFI)
        # raw_money_flow = typical_price * volume
        # positive flow if typical_price > prev, negative if < prev
        rmf = tp * df['tick_volume']
        
        # Iterate or vectorise
        tp_shift = tp.shift(1)
        pos_flow = np.where(tp > tp_shift, rmf, 0)
        neg_flow = np.where(tp < tp_shift, rmf, 0)
        
        pos_flow_s = pd.Series(pos_flow).rolling(window=14).sum()
        neg_flow_s = pd.Series(neg_flow).rolling(window=14).sum()
        
        mfi_ratio = pos_flow_s / neg_flow_s
        df['mfi'] = 100 - (100 / (1 + mfi_ratio))

        # CMF (Chaikin Money Flow)
        # sum((((C-L) - (H-C)) / (H-L)) * V) / sum(V) over 20 period
        mf_multiplier = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
        mf_volume = mf_multiplier * df['tick_volume']
        
        df['cmf'] = mf_volume.rolling(window=20).sum() / df['tick_volume'].rolling(window=20).sum()

        return df
