from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, name: str):
        self.name = name
        self.enabled = True

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> dict:
        """
        Generates a trading signal based on the dataframe.
        
        :param df: DataFrame with features
        :return: dict with keys: 'signal' (BUY, SELL, NEUTRAL), 'confidence' (0.0-1.0), 'metadata' (dict)
        """
        pass

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def is_enabled(self):
        return self.enabled
