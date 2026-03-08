import sys
import os

print("Verifying Spidy AI Installation...")

try:
    import pandas
    print("✅ pandas")
    import numpy
    print("✅ numpy")
    import torch
    print("✅ torch")
    import streamlit
    print("✅ streamlit")
    import xgboost
    print("✅ xgboost")
except ImportError as e:
    print(f"❌ Missing dependency: {e}")

print("\nVerifying Import Structure...")
try:
    from data_feed.metatrader_feed import MetaTraderFeed
    from feature_engineering.feature_store import FeatureStore
    from strategies.base.base_strategy import BaseStrategy
    from ml.models.lstm_short import LSTMShortTerm
    from dashboard import app
    print("✅ All modules importable.")
except Exception as e:
    print(f"❌ Import Error: {e}")
