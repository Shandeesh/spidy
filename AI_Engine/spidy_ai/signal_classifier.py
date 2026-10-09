"""Risk-aware classifier trained from closed trade history.

The classifier is a trade filter, not a trade generator.  It is deployed only
when it passes a chronological out-of-sample gate; otherwise live execution
continues to rely on the existing strategy and risk controls.
"""
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_MODEL_PATH = os.path.join(_HERE, "model.pkl")
_SCHEMA_VERSION = 2

try:
    import joblib
    import numpy as np
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, balanced_accuracy_score, brier_score_loss
    _HAS_SKL = True
except ImportError:
    _HAS_SKL = False

from feature_engineer import extract_features_from_db, build_inference_row

FEATURE_COLS = [
    "action_enc", "sentiment", "hour", "day_of_week", "strategy_enc",
    "symbol_enc", "volume_log", "rsi", "adx", "trend",
]
TARGET_COL = "profit_label"
MIN_SAMPLES = 60
MIN_EVAL_TRADES = 12
DEFAULT_MIN_WIN_PROBABILITY = 0.60


def _risk_metrics(profits):
    """Summarise realised trade PnL without making return guarantees."""
    values = np.asarray(profits, dtype=float)
    if len(values) == 0:
        return {"trades": 0, "net_profit": 0.0, "profit_factor": 0.0,
                "sharpe": 0.0, "sortino": 0.0, "max_drawdown": 0.0}

    equity = np.cumsum(values)
    peaks = np.maximum.accumulate(np.r_[0.0, equity])
    drawdown = peaks[1:] - equity
    downside = values[values < 0]
    std = values.std(ddof=1) if len(values) > 1 else 0.0
    downside_std = downside.std(ddof=1) if len(downside) > 1 else 0.0
    gross_profit = values[values > 0].sum()
    gross_loss = abs(values[values < 0].sum())

    sharpe = float(values.mean() / std * np.sqrt(len(values))) if std else (float("inf") if values.mean() > 0 else 0.0)
    sortino = float(values.mean() / downside_std * np.sqrt(len(values))) if downside_std else (float("inf") if values.mean() > 0 else 0.0)
    return {
        "trades": int(len(values)),
        "net_profit": round(float(values.sum()), 4),
        "profit_factor": round(float(gross_profit / gross_loss), 4) if gross_loss else float("inf"),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "max_drawdown": round(float(drawdown.max()) if len(drawdown) else 0.0, 4),
    }


class SignalClassifier:
    """A conservative, persisted classifier for filtering proposed trades."""

    def __init__(self, min_win_probability=DEFAULT_MIN_WIN_PROBABILITY):
        self.min_win_probability = float(min_win_probability)
        self._model = None
        self._trained = False
        self._metadata = {}
        if not _HAS_SKL:
            print("[SignalClassifier] scikit-learn not available — predictions disabled.")
        self._load()

    def _load(self):
        if not _HAS_SKL or not os.path.exists(_MODEL_PATH):
            return False
        try:
            payload = joblib.load(_MODEL_PATH)
            if not isinstance(payload, dict) or payload.get("schema_version") != _SCHEMA_VERSION:
                print("[SignalClassifier] Ignoring incompatible saved model.")
                return False
            if payload.get("feature_columns") != FEATURE_COLS:
                print("[SignalClassifier] Ignoring saved model with a different feature schema.")
                return False
            self._model = payload["model"]
            self._metadata = payload.get("metadata", {})
            self.min_win_probability = float(payload.get("min_win_probability", self.min_win_probability))
            self._trained = True
            print(f"[SignalClassifier] Risk-gated model loaded from {_MODEL_PATH}")
            return True
        except Exception as exc:
            print(f"[SignalClassifier] Model load failed: {exc}")
            return False

    def _save(self):
        if self._model is None:
            return
        joblib.dump({
            "schema_version": _SCHEMA_VERSION,
            "feature_columns": FEATURE_COLS,
            "min_win_probability": self.min_win_probability,
            "metadata": self._metadata,
            "model": self._model,
        }, _MODEL_PATH)

    @staticmethod
    def _win_probability(model, features):
        probabilities = model.predict_proba(features)
        classes = list(model.classes_)
        return probabilities[:, classes.index(1)] if 1 in classes else np.zeros(len(features))

    def train(self, min_win_probability=None):
        """Train chronologically and deploy only when the holdout is acceptable.

        The most recent 30% of closed trades form the out-of-sample holdout.
        This prevents future outcomes leaking into training and makes retraining
        reject models that only look good in sample.
        """
        if not _HAS_SKL:
            return {"status": "rejected", "reason": "scikit-learn not installed"}
        threshold = float(min_win_probability or self.min_win_probability)
        if not 0.5 < threshold < 1.0:
            return {"status": "rejected", "reason": "min_win_probability must be between 0.5 and 1.0"}

        try:
            df = extract_features_from_db(limit=5000)
        except Exception as exc:
            return {"status": "rejected", "reason": str(exc)}
        if len(df) < MIN_SAMPLES:
            return {"status": "rejected", "reason": f"Need at least {MIN_SAMPLES} closed trades; found {len(df)}."}

        df = df.sort_values("closed_at", kind="stable").reset_index(drop=True)
        split = max(int(len(df) * 0.70), MIN_SAMPLES // 2)
        train_df, test_df = df.iloc[:split], df.iloc[split:]
        if (len(test_df) < MIN_EVAL_TRADES or train_df[TARGET_COL].nunique() < 2
                or test_df[TARGET_COL].nunique() < 2):
            return {"status": "rejected", "reason": "Insufficient chronologically valid train/holdout classes."}

        model = RandomForestClassifier(
            n_estimators=400,
            max_depth=6,
            min_samples_leaf=5,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(train_df[FEATURE_COLS], train_df[TARGET_COL])
        probabilities = self._win_probability(model, test_df[FEATURE_COLS])
        predictions = (probabilities >= 0.5).astype(int)
        selected = probabilities >= threshold
        selected_metrics = _risk_metrics(test_df.loc[selected, "profit"].to_numpy())
        baseline_metrics = _risk_metrics(test_df["profit"].to_numpy())
        brier = brier_score_loss(test_df[TARGET_COL], probabilities)

        gate_passed = (
            selected_metrics["trades"] >= MIN_EVAL_TRADES
            and selected_metrics["net_profit"] > 0
            and selected_metrics["profit_factor"] > 1.0
            and selected_metrics["sharpe"] > 0
            and selected_metrics["max_drawdown"] <= baseline_metrics["max_drawdown"]
        )
        report = {
            "status": "trained" if gate_passed else "rejected",
            "samples": int(len(df)),
            "train_samples": int(len(train_df)),
            "holdout_samples": int(len(test_df)),
            "threshold": threshold,
            "accuracy": round(float(accuracy_score(test_df[TARGET_COL], predictions)), 4),
            "balanced_accuracy": round(float(balanced_accuracy_score(test_df[TARGET_COL], predictions)), 4),
            "brier_score": round(float(brier), 4),
            "selected_holdout": selected_metrics,
            "all_holdout": baseline_metrics,
            "reason": "Passed chronological risk-adjusted deployment gate." if gate_passed
                      else "Holdout did not meet risk-adjusted deployment criteria.",
        }
        if not gate_passed:
            return report

        self._model = model
        self._trained = True
        self.min_win_probability = threshold
        self._metadata = report
        self._save()
        print(f"[SignalClassifier] {report}")
        return report

    def predict(self, action, sentiment, hour, day_of_week, strategy="Auto", symbol="UNKNOWN", volume=0.0,
                rsi=50.0, adx=20.0, trend="NEUTRAL"):
        """Return HOLD unless a deployed model clears the configured threshold."""
        if action not in {"BUY", "SELL"}:
            return {"signal": "HOLD", "win_probability": 0.5, "confidence": 0.0, "trained": self._trained}
        if not _HAS_SKL or not self._trained or self._model is None:
            return {"signal": "HOLD", "win_probability": 0.5, "confidence": 0.0, "trained": False,
                    "reason": "No risk-gated model is deployed."}
        try:
            row = build_inference_row(action, sentiment, hour, day_of_week, strategy, symbol, volume, rsi, adx, trend)
            win_prob = float(self._win_probability(self._model, row[FEATURE_COLS])[0])
            approved = win_prob >= self.min_win_probability
            return {
                "signal": action if approved else "HOLD",
                "win_probability": round(win_prob, 4),
                "confidence": round(max(0.0, (win_prob - 0.5) * 2), 4),
                "trained": True,
                "threshold": self.min_win_probability,
                "reason": "Model approved" if approved else "Below risk-adjusted entry threshold",
            }
        except Exception as exc:
            return {"signal": "HOLD", "win_probability": 0.5, "confidence": 0.0, "trained": False,
                    "reason": f"Inference unavailable: {exc}"}


_classifier = None


def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = SignalClassifier()
    return _classifier
