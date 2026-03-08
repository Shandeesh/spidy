import pandas as pd
import numpy as np
import datetime

class TechnicalAnalyzer:
    """
    Handles calculation of advanced technical indicators like ADX, VWAP, MACD, SuperTrend, and multi-timeframe analysis.
    Designed to work with pandas DataFrames of OHLCV data.
    """

    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculates ADX (Average Directional Index) using Wilder's method.
        Expects DF with columns: 'high', 'low', 'close'.
        Returns DF with 'ADX', 'PLUS_DI', 'MINUS_DI' columns.
        """
        if len(df) < period * 2:
            return df

        df = df.copy()
        
        # True Range
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift(1))
        df['tr2'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)

        # Directional Movement
        df['plus_dm'] = df['high'] - df['high'].shift(1)
        df['minus_dm'] = df['low'].shift(1) - df['low']
        
        # Logic for +DM and -DM
        df['plus_dm'] = np.where((df['plus_dm'] > df['minus_dm']) & (df['plus_dm'] > 0), df['plus_dm'], 0.0)
        df['minus_dm'] = np.where((df['minus_dm'] > df['plus_dm']) & (df['minus_dm'] > 0), df['minus_dm'], 0.0)

        # Wilder's Smoothing Function
        def wilder_smooth(series, period):
            return series.ewm(alpha=1/period, adjust=False).mean()

        # Smooth TR, +DM, -DM
        df['tr_smooth'] = wilder_smooth(df['tr'], period)
        df['plus_dm_smooth'] = wilder_smooth(df['plus_dm'], period)
        df['minus_dm_smooth'] = wilder_smooth(df['minus_dm'], period)

        # Calculate DI (Safe Division)
        df['plus_di'] = np.where(df['tr_smooth'] != 0, 100 * (df['plus_dm_smooth'] / df['tr_smooth']), 0.0)
        df['minus_di'] = np.where(df['tr_smooth'] != 0, 100 * (df['minus_dm_smooth'] / df['tr_smooth']), 0.0)

        # Calculate DX (Safe Division)
        sum_di = df['plus_di'] + df['minus_di']
        df['dx'] = np.where(sum_di != 0, 100 * abs(df['plus_di'] - df['minus_di']) / sum_di, 0.0)

        # Calculate ADX (Smooth DX)
        df['ADX'] = wilder_smooth(df['dx'], period)

        return df

    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> float:
        """
        Calculates the Volume Weighted Average Price (VWAP) for the given dataframe.
        Ideally receiving data for the current session (intraday).
        Expects columns: 'high', 'low', 'close', 'tick_volume' (or 'volume').
        """
        if df.empty:
            return 0.0
        
        # Use typical price: (High + Low + Close) / 3
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        
        # Use tick_volume if volume not present (common in MT5)
        volume_col = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
        if volume_col not in df.columns:
            # Fallback if no volume at all, just return mean close (not VWAP but safe)
            return df['close'].mean()

        volume = df[volume_col]
        total_volume = volume.sum()
        
        if total_volume == 0:
            return typical_price.mean() # Fallback
        
        # Cumulative calc
        vwap = (typical_price * volume).sum() / total_volume
        
        return vwap

    @staticmethod
    def identify_market_regime(adx_value: float, adx_threshold: float = 25.0) -> str:
        """
        Returns 'TRENDING' if adx > threshold, else 'RANGING'.
        """
        if adx_value > adx_threshold:
            return "TRENDING"
        else:
            return "RANGING"

    @staticmethod
    def get_vwap_bias(current_price: float, vwap_value: float) -> str:
        """
        Returns 'BUY' if Price > VWAP, 'SELL' if Price < VWAP.
        """
        if current_price > vwap_value:
            return "BUY_ONLY"  # Bias is Long
        elif current_price < vwap_value:
            return "SELL_ONLY" # Bias is Short
        return "NEUTRAL"
        
    @staticmethod
    def calculate_orb_levels(df: pd.DataFrame, start_time: str = "09:15", end_time: str = "09:30") -> dict:
        """
        Calculates Opening Range Breakout (ORB) High and Low.
        Expects DF with 'time' column (datetime objects) or index.
        """
        try:
            if 'time' not in df.columns:
                return None
            
            # Note: This logic assumes 'time' is datetime64[ns]
            # If not, caller must ensure conversion.
            # Assuming dataframe has adequate rows for the day
            
            # For simplicity in this static method, we parse HH:MM
            # Getting Date from first row to ensure we filter for THAT day
            
            base_date = df['time'].dt.date.iloc[-1] # Use latest date in DF
            
            # Create datetime objects for start/end on that date
            start_dt = datetime.datetime.strptime(f"{base_date} {start_time}", "%Y-%m-%d %H:%M")
            end_dt = datetime.datetime.strptime(f"{base_date} {end_time}", "%Y-%m-%d %H:%M")
            
            mask = (df['time'] >= start_dt) & (df['time'] <= end_dt)
            orb_df = df.loc[mask]
            
            if orb_df.empty:
                return None
                
            orb_high = orb_df['high'].max()
            orb_low = orb_df['low'].min()
            
            return {"orb_high": orb_high, "orb_low": orb_low}
            
        except Exception as e:
            return None

    @staticmethod
    def calculate_stochastic_rsi(df: pd.DataFrame, period=14, smoothK=3, smoothD=3):
        """
        Calculates Stochastic RSI (StochRSI).
        Returns DataFrame with 'stoch_k', 'stoch_d'.
        """
        df = df.copy()
        
        # Calculate RSI first (if not present)
        if 'rsi' not in df.columns:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
        
        # Calculate StochRSI
        min_rsi = df['rsi'].rolling(window=period).min()
        max_rsi = df['rsi'].rolling(window=period).max()
        df['stoch_rsi'] = (df['rsi'] - min_rsi) / (max_rsi - min_rsi)
        
        # Calculate K and D (Smoothing)
        df['stoch_k'] = df['stoch_rsi'].rolling(window=smoothK).mean() * 100
        df['stoch_d'] = df['stoch_k'].rolling(window=smoothD).mean()
        
        return df

    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period=20, std_dev=2.0):
        """
        Calculates Bollinger Bands.
        Returns DF with 'bb_upper', 'bb_lower', 'bb_mid', 'bb_width'.
        """
        df = df.copy()
        df['bb_mid'] = df['close'].rolling(window=period).mean()
        df['bb_std'] = df['close'].rolling(window=period).std()
        
        df['bb_upper'] = df['bb_mid'] + (std_dev * df['bb_std'])
        df['bb_lower'] = df['bb_mid'] - (std_dev * df['bb_std'])
        
        # Band Width (for Squeeze detection)
        # (Upper - Lower) / Mid
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
        
        return df

    @staticmethod
    def calculate_keltner_channels(df: pd.DataFrame, period=20, multiplier=1.5, atr_period=10):
        """
        Calculates Keltner Channels.
        Mid = EMA(period).
        Upper = Mid + (Multiplier * ATR).
        Lower = Mid - (Multiplier * ATR).
        """
        df = df.copy()
        
        # Ensure ATR is present
        if 'atr' not in df.columns:
            # Quick ATR calc if missing (Simplified or use full ADX method)
            # Re-using logic from ADX part or simple TR rolling
            df['tr0'] = abs(df['high'] - df['low'])
            df['tr1'] = abs(df['high'] - df['close'].shift(1))
            df['tr2'] = abs(df['low'] - df['close'].shift(1))
            df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
            df['atr'] = df['tr'].rolling(window=atr_period).mean()
            
        df['kc_mid'] = df['close'].ewm(span=period, adjust=False).mean()
        df['kc_upper'] = df['kc_mid'] + (multiplier * df['atr'])
        df['kc_lower'] = df['kc_mid'] - (multiplier * df['atr'])
        
        return df

    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast=12, slow=26, signal=9):
        """
        Calculates MACD, Signal, and Histogram.
        """
        df = df.copy()
        df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['hist'] = df['macd'] - df['signal']
        return df

    @staticmethod
    def calculate_supertrend(df: pd.DataFrame, period=10, multiplier=3.0):
        """
        Calculates SuperTrend Indicator.
        Returns DataFrame with 'SuperTrend' and 'TrendDirection' (1=Up, -1=Down).
        """
        df = df.copy()
        
        # ATR Calculation
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift(1))
        df['tr2'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
        df['atr'] = df['tr'].rolling(period).mean()

        # Basic Bands
        df['upper_basic'] = (df['high'] + df['low']) / 2 + (multiplier * df['atr'])
        df['lower_basic'] = (df['high'] + df['low']) / 2 - (multiplier * df['atr'])

        # Final Bands
        df['upper_band'] = df['upper_basic']
        df['lower_band'] = df['lower_basic']
        df['supertrend'] = 0.0
        
        # Iterative calculation for SuperTrend logic
        # (This is slow in pure Python loop but necessary for ST logic)
        for i in range(period, len(df)):
            # Upper Band Logic
            if df['upper_basic'].iloc[i] < df['upper_band'].iloc[i-1] or df['close'].iloc[i-1] > df['upper_band'].iloc[i-1]:
                df.at[df.index[i], 'upper_band'] = df['upper_basic'].iloc[i]
            else:
                df.at[df.index[i], 'upper_band'] = df['upper_band'].iloc[i-1]

            # Lower Band Logic
            if df['lower_basic'].iloc[i] > df['lower_band'].iloc[i-1] or df['close'].iloc[i-1] < df['lower_band'].iloc[i-1]:
                df.at[df.index[i], 'lower_band'] = df['lower_basic'].iloc[i]
            else:
                df.at[df.index[i], 'lower_band'] = df['lower_band'].iloc[i-1]

        # Trend Logic
        df['trend'] = 1 # 1 is Up, -1 is Down
        
        for i in range(period, len(df)):
            prev_trend = df['trend'].iloc[i-1]
            prev_st = df['supertrend'].iloc[i-1]
            
            if prev_trend == 1:
                if df['close'].iloc[i] < df['lower_band'].iloc[i]:
                    df.at[df.index[i], 'trend'] = -1
                    df.at[df.index[i], 'supertrend'] = df['upper_band'].iloc[i]
                else:
                    df.at[df.index[i], 'trend'] = 1
                    df.at[df.index[i], 'supertrend'] = df['lower_band'].iloc[i]
            else: # prev_trend == -1
                if df['close'].iloc[i] > df['upper_band'].iloc[i]:
                    df.at[df.index[i], 'trend'] = 1
                    df.at[df.index[i], 'supertrend'] = df['lower_band'].iloc[i]
                else:
                    df.at[df.index[i], 'trend'] = -1
                    df.at[df.index[i], 'supertrend'] = df['upper_band'].iloc[i]
                    
        return df

    @staticmethod
    def calculate_williams_r(df: pd.DataFrame, period=14):
        """
        Calculates Williams %R.
        Formula: %R = (Highest High - Close) / (Highest High - Lowest Low) * -100
        """
        df = df.copy()
        low_min = df['low'].rolling(window=period).min()
        high_max = df['high'].rolling(window=period).max()
        
        df['williams_r'] = ((high_max - df['close']) / (high_max - low_min)) * -100
        
        return df

