import pandas as pd
import numpy as np
from ..strategies.registry import StrategyRegistry
from ..feature_engineering.feature_store import FeatureStore
from ..signal_engine.signal_aggregator import SignalAggregator
from ..risk_management.risk_manager import RiskManager

class BacktestEngine:
    def __init__(self, data_feed=None):
        self.feed = data_feed # Can be None if we generate mock data
        self.registry = StrategyRegistry()
        self.feature_store = FeatureStore()
        self.signal_aggregator = SignalAggregator()
        self.risk_manager = RiskManager()
        
        self.initial_capital = 10000.0
        self.equity = self.initial_capital
        self.balance = self.initial_capital
        self.positions = [] # List of active positions
        self.trade_history = []

    def load_data(self, symbol, periods):
        """
        Loads data either from feed or generates mock data for testing.
        """
        if self.feed and self.feed.connected:
             return self.feed.get_historical_data(symbol, timeframe=1, num_candles=periods) # Simplified
        
        # Generator for Mock Data if no feed
        print(f"Generating {periods} mock candles for {symbol}...")
        dates = pd.date_range(end=pd.Timestamp.now(), periods=periods, freq='1min')
        
        # Random Walk
        start_price = 1.1000 if 'EUR' in symbol else 100.0
        returns = np.random.normal(0, 0.0001, periods)
        price_curve = start_price * (1 + returns).cumprod()
        
        data = {
            'time': dates,
            'open': price_curve,
            'high': price_curve * (1 + np.abs(np.random.normal(0, 0.0002, periods))),
            'low': price_curve * (1 - np.abs(np.random.normal(0, 0.0002, periods))),
            'close': price_curve * (1 + np.random.normal(0, 0.0001, periods)),
            'tick_volume': np.random.randint(100, 500, periods)
        }
        df = pd.DataFrame(data)
        
        # Fix High/Low
        df['high'] = df[['open', 'close', 'high']].max(axis=1)
        df['low'] = df[['open', 'close', 'low']].min(axis=1)
        
        return df

    def run(self, symbol="EURUSD", timeframe="M1", periods=1000):
        print(f"🚀 Starting Backtest for {symbol} ({periods} candles)...")
        
        # 1. Get Data
        df = self.load_data(symbol, periods)
        if df is None:
            print("❌ No data loaded.")
            return
            
        # 2. Generate Features
        print("📊 Generating features...")
        df = self.feature_store.generate_features(df)
        
        # 3. Iterate Candle by Candle (Simulated)
        # We need a 'warmup' period for indicators
        warmup = 50
        print("🔄 Running simulation...")
        
        for i in range(warmup, len(df)):
            # Slice concept: The engine sees data up to index 'i'
            # To be efficient, we usually pre-calculate signals on full DF, 
            # but strict backtesting does it step-by-step or shifts signals.
            # Here we will use the pre-calculated features at row 'i'.
            
            # This is a simplification. Strategy should ideally receive the slice to avoid lookahead,
            # but our strategies use .iloc[-1] on the passed DF. 
            # So we pass window_df.
            
            window_df = df.iloc[:i+1] # potentially slow in loop, for demo ok
            current_bar = df.iloc[i]
            
            # Detect Regime (using latest data)
            # In real optimization, regime might be computed on longer timeframe
            regime = "UNKNOWN" # Placeholder or use RegimeDetector
            
            # Get Signals
            active_strategies = self.registry.get_active_strategies()
            signals = []
            for strategy in active_strategies:
                # We optimization: Strategies are stateless mostly, they look at DF.
                # Passing full sliced DF is safest correctness-wise.
                sig = strategy.generate_signal(window_df)
                signals.append(sig)
                
            # Aggregate
            final_decision = self.signal_aggregator.aggregate_signals(signals, {"regime": regime})
            
            # Logic: Trade
            if final_decision == "BUY":
                self.open_position(symbol, "BUY", current_bar['close'], current_bar['time'])
            elif final_decision == "SELL":
                self.open_position(symbol, "SELL", current_bar['close'], current_bar['time'])
            
            # Manage Open Positions (Simulated)
            self.manage_positions(current_bar)
            
        self.close_all_positions(df.iloc[-1])
        
        # Summary
        profit = self.equity - self.initial_capital
        print("-" * 30)
        print(f"🏁 Backtest Finished.")
        print(f"Initial Capital: ${self.initial_capital:.2f}")
        print(f"Final Equity:    ${self.equity:.2f}")
        print(f"Total Return:    {profit:.2f} ({(profit/self.initial_capital)*100:.2f}%)")
        print(f"Total Trades:    {len(self.trade_history)}")
        print("-" * 30)
        
        return {"final_equity": self.equity, "trades": len(self.trade_history)}

    def open_position(self, symbol, type, price, time):
        # Simple Logic: Only one position at a time for demo
        if self.positions:
            return
            
        # Risk Calc
        size = 0.1 # Standard lots fixed for demo
        # SL/TP could be added here
        
        print(f"  [TRADE] OPEN {type} @ {price:.5f} at {time}")
        self.positions.append({
            'symbol': symbol,
            'type': type,
            'entry_price': price,
            'entry_time': time,
            'size': size
        })

    def manage_positions(self, current_bar):
        # Exit Logic: Simple random or fixed visual
        # Let's close if profit > X or loss > Y (Take Profit / Stop Loss)
        # OR Close on reversal signal (not implemented in loop above for simplicity)
        
        for pos in list(self.positions):
            current_price = current_bar['close']
            pnl = 0
            if pos['type'] == 'BUY':
                pnl = (current_price - pos['entry_price']) * 100000 * pos['size'] # roughly for EURUSD
            else:
                pnl = (pos['entry_price'] - current_price) * 100000 * pos['size']
            
            # Simple TP/SL
            if pnl > 50 or pnl < -20:
                print(f"  [TRADE] CLOSE {pos['type']} @ {current_price:.5f} PnL: ${pnl:.2f}")
                self.balance += pnl
                self.equity = self.balance
                self.trade_history.append(pnl)
                self.positions.remove(pos)

    def close_all_positions(self, current_bar):
         for pos in list(self.positions):
            current_price = current_bar['close']
            pnl = 0
            if pos['type'] == 'BUY':
                pnl = (current_price - pos['entry_price']) * 100000 * pos['size']
            else:
                pnl = (pos['entry_price'] - current_price) * 100000 * pos['size']
            
            print(f"  [TRADE] CLOSE ALL {pos['type']} @ {current_price:.5f} PnL: ${pnl:.2f}")
            self.balance += pnl
            self.equity = self.balance
            self.trade_history.append(pnl)
            self.positions.remove(pos)
