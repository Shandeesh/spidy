import pandas as pd
from .regime_rules import RegimeRules

class RegimeDetector:
    def __init__(self):
        pass

    def detect_regime(self, df: pd.DataFrame) -> str:
        """
        Detects the current market regime based on the latest data in the DataFrame.
        Expected features: ADX, ATR.
        """
        if df is None or df.empty:
            return "UNKNOWN"
            
        current = df.iloc[-1]
        
        # Ensure necessary features exist
        if 'ADX_14' not in current and 'DMP_14' not in current: 
            # pandas-ta sometimes outputs names like ADX_14, DMP_14, DMN_14 or just ADX, etc.
            # We need to be robust. FeatureStore should have standardized this or we check cols.
            # For this simple implementation, we'll try standard names or their aliases from our feature store
            # In our feature store trend_features.py, ta.adx returns ADX_14, DMP_14, DMN_14 by default.
            pass

        # Try to find ADX column
        adx_col = next((col for col in df.columns if col.startswith('ADX')), None)
        if not adx_col:
            return "UNKNOWN_NO_ADX"
            
        adx_value = current[adx_col]
        
        # Try to find ATR column
        atr_col = next((col for col in df.columns if col.startswith('ATRr') or col == 'atr'), 'atr') # ta.atr usually 'ATRr_14' or 'atr'
        if atr_col not in df.columns:
            # Maybe search for it
            atr_col = next((col for col in df.columns if 'ATR' in col), None)
            
        is_trending = adx_value > RegimeRules.ADX_TRENDING_THRESHOLD
        
        # Basic Logic
        if is_trending:
            return RegimeRules.STRONG_TREND
        else:
            return RegimeRules.RANGING

    def get_regime_details(self, df: pd.DataFrame) -> dict:
        """
        Returns a detailed dictionary of the regime.
        """
        regime = self.detect_regime(df)
        
        # Get latest ADX
        adx_col = next((col for col in df.columns if col.startswith('ADX')), 'ADX')
        adx_val = df.iloc[-1][adx_col] if adx_col in df.columns else 0
        
        return {
            "regime": regime,
            "adx": adx_val
        }
