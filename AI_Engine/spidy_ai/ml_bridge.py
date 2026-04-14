"""
ML Bridge — connects SignalClassifier to the live bridge state.
Fetches current market context (RSI, trend, sentiment) from bridge state
and runs inference to produce a ML-augmented signal.
"""
import os
import sys
from datetime import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from signal_classifier import get_classifier


def get_ml_signal(symbol: str, action: str, technical_cache: dict,
                  mt5_state: dict) -> dict:
    """
    Produces an ML-augmented signal for a proposed trade.

    Args:
        symbol:          Trading symbol, e.g. 'EURUSD'
        action:          'BUY' or 'SELL'
        technical_cache: Bridge's live indicator cache {symbol: {rsi, trend, ...}}
        mt5_state:       Bridge's live state dict (for sentiment)

    Returns dict:
        {
          "symbol":          str,
          "action":          str,
          "signal":          "BUY"|"SELL"|"HOLD",
          "win_probability": float,
          "confidence":      float,
          "trained":         bool
        }
    """
    clf = get_classifier()

    sentiment   = mt5_state.get("sentiment", "NEUTRAL") or "NEUTRAL"
    now         = datetime.now()
    hour        = now.hour
    day_of_week = now.weekday()

    tech = technical_cache.get(symbol, {})
    strategy = tech.get("strategy", "Live_Auto")

    result = clf.predict(
        action=action,
        sentiment=sentiment,
        hour=hour,
        day_of_week=day_of_week,
        strategy=strategy,
    )

    result["symbol"] = symbol
    result["action"] = action
    return result
