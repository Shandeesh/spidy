import sys

# Force console output to use UTF-8 to prevent cp1252 UnicodeEncodeErrors on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import os

print("Verifying Spidy AI Installation...")

try:
    import pandas
    print("[OK] pandas")
    import numpy
    print("[OK] numpy")
    import torch
    print("[OK] torch")
except ImportError as e:
    print(f"[FAIL] Missing dependency: {e}")

print("\nVerifying Import Structure...")
try:
    from data_feed.metatrader_feed import MetaTraderFeed
    from feature_engineering.feature_store import FeatureStore
    from strategies.base.base_strategy import BaseStrategy
    from ml.models.lstm_short import LSTMShort
    from dashboard import app
    print("[OK] All modules importable.")
except Exception as e:
    print(f"[FAIL] Import Error: {e}")

