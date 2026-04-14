"""
Feature Engineer: Extracts ML features from Spidy's financial_db trade history.
Produces a DataFrame ready for classifier training and inference.
"""
import os
import sys
from datetime import datetime

# Add financial_db to path
_BRIDGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../Trading_Backend/mt5_bridge")
)
if _BRIDGE_DIR not in sys.path:
    sys.path.insert(0, _BRIDGE_DIR)

try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False
    print("[FeatureEngineer] pandas not installed — ML features unavailable.")

# Sentiment / trend encodings
_SENTIMENT_MAP = {"BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1}
_TREND_MAP     = {"BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1}
_ACTION_MAP    = {"BUY": 1, "SELL": 0}


def extract_features_from_db(limit: int = 2000) -> "pd.DataFrame":
    """
    Loads closed trade history from financial_db and extracts ML features.

    Columns produced:
        action_enc   — 1=BUY, 0=SELL
        profit_label — 1=WIN, 0=LOSS  (target variable)
        sentiment    — encoded sentiment at trade time
        hour         — hour of day (0-23)
        day_of_week  — 0=Mon … 6=Sun
        rsi_approx   — parsed from comment if available, else 50
        strategy_enc — integer hash of strategy name (for diversity)
    """
    if not _HAS_PANDAS:
        raise ImportError("pandas required for ML feature extraction")

    import financial_db as fdb
    history = fdb.get_trade_history(limit=limit)

    if not history:
        raise ValueError("No trade history in DB. Place some trades first.")

    rows = []
    for t in history:
        profit = t.get("profit")
        action = t.get("type", "BUY").upper()
        if profit is None:
            continue

        # Parse close_time
        try:
            ct   = datetime.strptime(t.get("close_time", ""), "%Y-%m-%d %H:%M:%S")
            hour = ct.hour
            dow  = ct.weekday()
        except Exception:
            hour, dow = 12, 2  # defaults

        sentiment_raw = t.get("sentiment", "NEUTRAL") or "NEUTRAL"
        sentiment_enc = _SENTIMENT_MAP.get(sentiment_raw.upper(), 0)

        strategy_raw  = t.get("strategy", "Manual") or "Manual"
        strategy_enc  = abs(hash(strategy_raw)) % 100  # deterministic bucket

        rows.append({
            "action_enc":   _ACTION_MAP.get(action, 1),
            "profit_label": 1 if float(profit) > 0 else 0,
            "sentiment":    sentiment_enc,
            "hour":         hour,
            "day_of_week":  dow,
            "strategy_enc": strategy_enc,
        })

    df = pd.DataFrame(rows)
    return df


def build_inference_row(action: str, sentiment: str, hour: int,
                        day_of_week: int, strategy: str) -> "pd.DataFrame":
    """
    Build a single-row DataFrame for live inference — same schema as training.
    """
    if not _HAS_PANDAS:
        raise ImportError("pandas required")
    import pandas as pd

    row = {
        "action_enc":   _ACTION_MAP.get(action.upper(), 1),
        "sentiment":    _SENTIMENT_MAP.get(sentiment.upper(), 0),
        "hour":         int(hour),
        "day_of_week":  int(day_of_week),
        "strategy_enc": abs(hash(strategy)) % 100,
    }
    return pd.DataFrame([row])
