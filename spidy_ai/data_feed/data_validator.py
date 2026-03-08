import pandas as pd
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    REQUIRED_COLUMNS = ['time', 'open', 'high', 'low', 'close', 'tick_volume']

    @staticmethod
    def validate_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
        """
        Validates and cleans OHLCV DataFrame.
        
        :param df: Raw DataFrame from Data Feed
        :return: Cleaned and validated DataFrame, or None if invalid
        """
        if df is None or df.empty:
            logger.error("DataFrame is empty or None")
            return None

        # Check for required columns
        missing_cols = [col for col in DataValidator.REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            logger.error(f"Missing required columns: {missing_cols}")
            return None

        # Check for NaN values
        if df[DataValidator.REQUIRED_COLUMNS].isnull().values.any():
            logger.warning("NaN values found in OHLCV data. Dropping rows with NaNs.")
            df.dropna(subset=DataValidator.REQUIRED_COLUMNS, inplace=True)

        # Ensure sorted by time
        if not df['time'].is_monotonic_increasing:
            logger.warning("Data not sorted by time. Sorting now.")
            df.sort_values(by='time', inplace=True)

        # Reset index
        df.reset_index(drop=True, inplace=True)

        # Basic logical checks (High >= Low, etc.)
        invalid_rows = df[ (df['high'] < df['low']) | (df['high'] < df['open']) | (df['high'] < df['close']) ]
        if not invalid_rows.empty:
            logger.warning(f"Found {len(invalid_rows)} rows with invalid price logic (e.g. High < Low).")
            # For now, we might just log this, or drop them. 
            # In a strict production system, we might want to drop or correct them.
            # Let's clean them to avoid breaking indicators.
            df = df.drop(invalid_rows.index).reset_index(drop=True)

        return df
