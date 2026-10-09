import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd

import signal_classifier


@unittest.skipUnless(signal_classifier._HAS_SKL, "scikit-learn is required")
class SignalClassifierTests(unittest.TestCase):
    def setUp(self):
        self._old_model_path = signal_classifier._MODEL_PATH
        self._temp_dir = tempfile.TemporaryDirectory()
        signal_classifier._MODEL_PATH = os.path.join(self._temp_dir.name, "model.pkl")

    def tearDown(self):
        signal_classifier._MODEL_PATH = self._old_model_path
        self._temp_dir.cleanup()

    @staticmethod
    def _history():
        rows = []
        start = datetime(2024, 1, 1)
        for index in range(100):
            is_buy = index % 2 == 0
            rows.append({
                "action_enc": int(is_buy),
                "profit_label": int(is_buy),
                "profit": 10.0 if is_buy else -5.0,
                "closed_at": start + timedelta(hours=index),
                "sentiment": 1 if is_buy else -1,
                "hour": index % 24,
                "day_of_week": index % 7,
                "strategy_enc": 10 if is_buy else 20,
                "symbol_enc": 30,
                "volume_log": 0.01,
                "rsi": 0.70 if is_buy else 0.30,
                "adx": 0.40,
                "trend": 1 if is_buy else -1,
            })
        return pd.DataFrame(rows)

    def test_deploys_only_after_chronological_risk_gate_passes(self):
        classifier = signal_classifier.SignalClassifier(min_win_probability=0.60)
        with patch.object(signal_classifier, "extract_features_from_db", return_value=self._history()):
            report = classifier.train()

        self.assertEqual(report["status"], "trained")
        self.assertGreater(report["selected_holdout"]["profit_factor"], 1.0)
        self.assertGreater(report["selected_holdout"]["sharpe"], 0.0)
        self.assertTrue(os.path.exists(signal_classifier._MODEL_PATH))

        prediction = classifier.predict("BUY", "BULLISH", 10, 1, "Trend", "EURUSD", 0.01)
        self.assertEqual(prediction["signal"], "BUY")
        self.assertTrue(prediction["trained"])

    def test_rejects_model_when_recent_regime_breaks_profitability(self):
        history = self._history()
        # The old relationship reverses in the holdout: a model fitted on the
        # earlier samples would select losing BUY trades, so it must not deploy.
        recent_buys = (history.index >= 70) & (history["action_enc"] == 1)
        history.loc[recent_buys, "profit"] = -10.0
        history.loc[recent_buys, "profit_label"] = 0
        # Preserve some positive outcomes in the holdout, but in a pattern the
        # old model does not select, so the evaluation is still meaningful.
        recent_sells = (history.index >= 70) & (history["action_enc"] == 0) & (history.index % 4 == 1)
        history.loc[recent_sells, "profit"] = 5.0
        history.loc[recent_sells, "profit_label"] = 1

        classifier = signal_classifier.SignalClassifier(min_win_probability=0.60)
        with patch.object(signal_classifier, "extract_features_from_db", return_value=history):
            report = classifier.train()

        self.assertEqual(report["status"], "rejected")
        self.assertFalse(os.path.exists(signal_classifier._MODEL_PATH))


if __name__ == "__main__":
    unittest.main()
