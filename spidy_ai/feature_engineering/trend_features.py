import pandas as pd
import numpy as np
import traceback

class TrendFeatures:
    @staticmethod
    def add_all_trend_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds trend-based indicators to the DataFrame using standard pandas.
        """
        try:
            # Ensure copy to avoid setting on slice if passed a slice, but we want to return full DF with features
            df = df.copy()
            
            close = pd.to_numeric(df['close'], errors='coerce').fillna(0)
            high = pd.to_numeric(df['high'], errors='coerce').fillna(0)
            low = pd.to_numeric(df['low'], errors='coerce').fillna(0)

            # EMA
            df['ema_9'] = close.ewm(span=9, adjust=False).mean()
            df['ema_21'] = close.ewm(span=21, adjust=False).mean()
            df['ema_50'] = close.ewm(span=50, adjust=False).mean()
            df['ema_200'] = close.ewm(span=200, adjust=False).mean()

            # MACD (12, 26, 9)
            k = close.ewm(span=12, adjust=False).mean()
            d = close.ewm(span=26, adjust=False).mean()
            df['MACD_12_26_9'] = k - d
            df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean()
            df['MACDh_12_26_9'] = df['MACD_12_26_9'] - df['MACDs_12_26_9']

            # ADX (Simple implementation)
            # Use bfill() method directly
            prev_close = close.shift(1).bfill()
            
            h_l = high - low
            h_pc = abs(high - prev_close)
            l_pc = abs(low - prev_close)
            
            tr_df = pd.concat([h_l, h_pc, l_pc], axis=1)
            df['tr'] = tr_df.max(axis=1)
            
            up_move = high - high.shift(1).bfill()
            down_move = low.shift(1).bfill() - low
            
            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
            
            df['plus_dm'] = plus_dm
            df['minus_dm'] = minus_dm
            
            window = 14
            df['atr_smooth'] = df['tr'].ewm(alpha=1/window, adjust=False).mean()
            
            atr_smooth_safe = df['atr_smooth'].replace(0, 1e-10)

            plus_dm_smooth = df['plus_dm'].ewm(alpha=1/window, adjust=False).mean()
            minus_dm_smooth = df['minus_dm'].ewm(alpha=1/window, adjust=False).mean()

            df['plus_di'] = 100 * (plus_dm_smooth / atr_smooth_safe)
            df['minus_di'] = 100 * (minus_dm_smooth / atr_smooth_safe)
            
            di_sum = df['plus_di'] + df['minus_di']
            di_sum_safe = di_sum.replace(0, 1e-10)
            
            df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / di_sum_safe
            df['ADX_14'] = df['dx'].ewm(alpha=1/window, adjust=False).mean()

            # Supertrend
            length = 10
            multiplier = 3.0
            df['atr_st'] = df['tr'].rolling(window=length).mean()
            
            hl2 = (high + low) / 2
            df['basic_upperband'] = hl2 + (multiplier * df['atr_st'])
            df['basic_lowerband'] = hl2 - (multiplier * df['atr_st'])
            
            df['SUPERT_10_3.0'] = df['basic_upperband'] 
            
            # Cleanup
            cols_to_drop = ['tr', 'plus_dm', 'minus_dm', 'dx', 'atr_smooth', 'plus_di', 'minus_di', 'atr_st', 'basic_upperband', 'basic_lowerband']
            df.drop(columns=[c for c in cols_to_drop if c in df.columns], inplace=True)
            
            return df
        except Exception:
            print("Error in TrendFeatures:")
            traceback.print_exc()
            # Return original df to avoid crash, but signals will fail safely
            return df
