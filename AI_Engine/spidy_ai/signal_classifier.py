"""
Signal Classifier — RandomForest model trained on historical trade outcomes.
Predicts whether a proposed trade is likely to WIN or LOSE.

Usage:
    clf = SignalClassifier()
    clf.train()                     # train from DB history
    result = clf.predict("BUY", "BULLISH", hour=10, day_of_week=1, strategy="RSI_Cross")
    # {"signal": "BUY", "confidence": 0.74, "win_probability": 0.74}
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MODEL_PATH = os.path.join(_HERE, "model.pkl")

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score
    import joblib
    import pandas as pd
    _HAS_SKL = True
except ImportError:
    _HAS_SKL = False

from feature_engineer import extract_features_from_db, build_inference_row

FEATURE_COLS = ["action_enc", "sentiment", "hour", "day_of_week", "strategy_enc"]
TARGET_COL   = "profit_label"
MIN_SAMPLES  = 30   # min rows needed to train meaningfully


class SignalClassifier:
    """
    RandomForest-based win/loss predictor for trade signals.
    Falls back to a neutral 0.5 confidence if model is untrained.
    """

    def __init__(self):
        if not _HAS_SKL:
            print("[SignalClassifier] scikit-learn not available — predictions disabled.")
        self._model = None
        self._trained = False
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> bool:
        if not _HAS_SKL:
            return False
        if os.path.exists(_MODEL_PATH):
            try:
                self._model   = joblib.load(_MODEL_PATH)
                self._trained = True
                print(f"[SignalClassifier] Model loaded from {_MODEL_PATH}")
                return True
            except Exception as e:
                print(f"[SignalClassifier] Model load failed: {e}")
        return False

    def _save(self) -> None:
        if self._model is not None:
            joblib.dump(self._model, _MODEL_PATH)
            print(f"[SignalClassifier] Model saved to {_MODEL_PATH}")

    # ── Training ──────────────────────────────────────────────────────────────

    def train(self) -> dict:
        """
        Train the classifier from financial_db trade history.
        Returns a report dict with accuracy and sample count.
        """
        if not _HAS_SKL:
            return {"error": "scikit-learn not installed"}

        try:
            df = extract_features_from_db(limit=5000)
        except Exception as e:
            return {"error": str(e)}

        if len(df) < MIN_SAMPLES:
            return {
                "error": f"Insufficient data: {len(df)} trades (need {MIN_SAMPLES}+). "
                         "Keep trading and retry."
            }

        X = df[FEATURE_COLS]
        y = df[TARGET_COL]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y if y.nunique() > 1 else None
        )

        clf = RandomForestClassifier(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=3,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        clf.fit(X_train, y_train)

        y_pred = clf.predict(X_test)
        acc    = accuracy_score(y_test, y_pred)

        self._model   = clf
        self._trained = True
        self._save()

        report = {
            "status":          "trained",
            "samples":         int(len(df)),
            "test_accuracy":   round(float(acc), 4),
            "features":        FEATURE_COLS,
            "win_pct_in_data": round(float(y.mean()), 4),
        }
        print(f"[SignalClassifier] {report}")
        return report

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict(self, action: str, sentiment: str, hour: int,
                day_of_week: int, strategy: str = "Auto") -> dict:
        """
        Predict win probability for a proposed trade.

        Returns:
            {
              "signal":          "BUY" | "SELL" | "HOLD",
              "win_probability": float (0-1),
              "confidence":      float (0-1),
              "trained":         bool
            }
        """
        if not _HAS_SKL or not self._trained or self._model is None:
            return {
                "signal":          action,
                "win_probability": 0.5,
                "confidence":      0.5,
                "trained":         False,
            }

        try:
            row   = build_inference_row(action, sentiment, hour, day_of_week, strategy)
            X     = row[FEATURE_COLS]
            proba = self._model.predict_proba(X)[0]
            # proba[1] = probability of WIN (class=1)
            win_prob = float(proba[1]) if len(proba) > 1 else 0.5
            # Confidence = how far from 0.5 the prediction is
            confidence = abs(win_prob - 0.5) * 2  # [0, 1]

            # Signal decision
            if win_prob >= 0.60:
                signal = action      # Confirm the intended direction
            elif win_prob <= 0.40:
                signal = "HOLD"      # Model says likely lose — hold off
            else:
                signal = action      # Neutral — trust the strategy

            return {
                "signal":          signal,
                "win_probability": round(win_prob, 4),
                "confidence":      round(confidence, 4),
                "trained":         True,
            }
        except Exception as e:
            return {
                "signal":          action,
                "win_probability": 0.5,
                "confidence":      0.5,
                "trained":         False,
                "error":           str(e),
            }


# Module-level singleton (loaded once, reused across requests)
_classifier: SignalClassifier | None = None


def get_classifier() -> SignalClassifier:
    global _classifier
    if _classifier is None:
        _classifier = SignalClassifier()
    return _classifier
