import pandas as pd

class XGBoostModel:
    def __init__(self):
        self.model = None

    def train(self, X: pd.DataFrame, y: pd.Series):
        """
        Trains the XGBoost model.
        """
        print("Training XGBoost Model...")
        pass

    def predict(self, X: pd.DataFrame):
        """
        Returns predictions.
        """
        return [0.5] * len(X)
