from .base.base_strategy import BaseStrategy
from .trend.ema_cross import EmaCrossStrategy
from .momentum.rsi import RsiStrategy
from .volatility.atr_breakout import AtrBreakoutStrategy

class StrategyRegistry:
    def __init__(self):
        self.strategies = {}
        self.load_strategies()

    def load_strategies(self):
        """
        Initialize and register all available strategies.
        """
        # Instantiate strategies with default params
        # In a real app, these might come from config
        self.register(EmaCrossStrategy())
        self.register(RsiStrategy())
        self.register(AtrBreakoutStrategy())

    def register(self, strategy: BaseStrategy):
        self.strategies[strategy.name] = strategy

    def get_strategy(self, name: str) -> BaseStrategy:
        return self.strategies.get(name)

    def get_active_strategies(self, regime=None):
        active = [s for s in self.strategies.values() if s.is_enabled()]
        if regime:
            active = [s for s in active if not hasattr(s, "is_applicable") or s.is_applicable(regime)]
        return active


    def enable_strategy(self, name: str):
        if name in self.strategies:
            self.strategies[name].enable()

    def disable_strategy(self, name: str):
        if name in self.strategies:
            self.strategies[name].disable()
