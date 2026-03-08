from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    """
    Abstract Base Class for all Trading Strategies.
    All strategies must implement the `analyze` method.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def analyze(self, symbol: str, data: dict, market_state: dict) -> dict:
        """
        Analyzes the market data and returns a signal.
        
        Args:
            symbol (str): The financial instrument symbol (e.g., "EURUSD").
            data (dict): A dictionary containing relevant market data (price, indicators, OHLCV dataframe).
            market_state (dict): The global market state (Regime, Bias, etc.).
            
        Returns:
            dict: A signal dictionary. 
                  Format: { "signal": "BUY"|"SELL"|"HOLD", "confidence": 0.0-1.0, "reason": str }
        """
        pass

    def get_name(self) -> str:
        return self.name
