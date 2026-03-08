import time
import pandas as pd
import sys
import os
import yaml

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Imports
from data_feed.metatrader_feed import MetaTraderFeed
from feature_engineering.feature_store import FeatureStore
from feature_engineering.trend_features import TrendFeatures
from feature_engineering.momentum_features import MomentumFeatures
from feature_engineering.volatility_features import VolatilityFeatures
from regime_detection.regime_detector import RegimeDetector
from strategies.registry import StrategyRegistry
from signal_engine.confidence_engine import ConfidenceEngine
from signal_engine.correlation_filter import CorrelationFilter
from signal_engine.signal_aggregator import SignalAggregator
from risk_management.risk_manager import RiskManager
from risk_management.position_sizer import PositionSizer
from execution.order_router import OrderRouter
from execution.vwap_executor import VWAPExecutor
from ml.models.xgboost_model import XGBoostModel
from ml.ensemble.ensemble_engine import EnsembleEngine

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config", "settings.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    print("⚠️ Config not found, using defaults.")
    return {}

def run_spidy_ai():
    print("🕷️ Spidy AI - Enterprise Trading System Initializing...")
    
    # 0. Load Config
    config = load_config()
    system_cfg = config.get("system", {})
    risk_cfg = config.get("risk", {})
    exec_cfg = config.get("execution", {})
    
    symbol = system_cfg.get("symbol", "EURUSD")
    mode = system_cfg.get("mode", "SIMULATION")
    live_mode = (mode == "LIVE")
    
    print(f"   Mode: {mode}")
    print(f"   Symbol: {symbol}")

    # 1. Initialize Components
    feed = MetaTraderFeed(symbol, 5) 
    if not feed.connect():
        print("❌ Failed to connect to Data Feed (MT5). Exiting.")
        return

    feature_store = FeatureStore()
    regime_detector = RegimeDetector()
    strategy_registry = StrategyRegistry()
    confidence_engine = ConfidenceEngine()
    correlation_filter = CorrelationFilter()
    signal_aggregator = SignalAggregator(threshold=2.0)
    
    xgb_model = XGBoostModel()
    ensemble = EnsembleEngine()
    
    risk_manager = RiskManager(
        start_balance=risk_cfg.get("start_balance", 10000),
        max_daily_dd_pct=risk_cfg.get("max_daily_drawdown_pct", 0.05),
        max_total_dd_pct=risk_cfg.get("max_total_drawdown_pct", 0.15)
    )
    
    position_sizer = PositionSizer(risk_per_trade_pct=risk_cfg.get("risk_per_trade_pct", 0.01))
    
    order_router = OrderRouter(broker=exec_cfg.get("broker", "MT5"), live_mode=live_mode)
    vwap_executor = VWAPExecutor(order_router)

    # 2. State Machine
    current_position = "FLAT" # FLAT, LONG, SHORT
    
    print("✅ All components initialized. Starting Loop...")

    try:
        while True:
            # Check Risk Immediately
            if not risk_manager.can_trade():
                print("🛑 Kill Switch Active. Closing all positions.")
                order_router.close_position(symbol)
                current_position = "FLAT"
                time.sleep(60)
                continue

            print("\n--- New Cycle ---")
            
            # A. Get Data
            df = feed.get_candles(n=500)
            if df is None or df.empty:
                print("Waiting for data...")
                time.sleep(5)
                continue
                
            # B. Features & Regime
            df = TrendFeatures.add_features(df)
            df = MomentumFeatures.add_features(df)
            df = VolatilityFeatures.add_features(df)
            feature_store.load_data(df)
            
            latest_data = feature_store.get_latest()
            current_close = latest_data['close']
            regime = regime_detector.detect_regime(df)
            print(f"Price: {current_close:.5f} | Regime: {regime}")

            # C. Signals
            active_strategies = strategy_registry.get_active_strategies(regime)
            raw_signals = []
            for strategy in active_strategies:
                signal, conf = strategy.generate_signal(df)
                if signal != 0:
                    score = confidence_engine.calculate_score(strategy, signal, conf, regime)
                    raw_signals.append((strategy.name, score))

            filtered_signals = correlation_filter.filter_signals(raw_signals)
            decision, net_score = signal_aggregator.aggregate(filtered_signals)
            print(f"Aggregated Decision: {decision} (Score: {net_score:.2f})")
            
            # D. Execution Logic (State Machine)
            if decision == "BUY":
                if current_position == "SHORT":
                    print("🔄 Reversing SHORT -> LONG")
                    order_router.close_position(symbol)
                    current_position = "FLAT"
                    
                if current_position == "FLAT":
                    # Calculate Stats
                    atr = latest_data.get('ATR', 0.0010)
                    sl_dist = atr * 1.5 
                    sl_price = current_close - sl_dist
                    tp_price = current_close + (sl_dist * 2)
                    size = position_sizer.calculate_size(risk_manager.current_balance, current_close, sl_price)
                    
                    if size > 0:
                        success = vwap_executor.execute_carefully(symbol, "BUY", size, current_close, current_close) # Mock VWAP
                        if success: current_position = "LONG"
            
            elif decision == "SELL":
                if current_position == "LONG":
                     print("🔄 Reversing LONG -> SHORT")
                     order_router.close_position(symbol)
                     current_position = "FLAT"
                     
                if current_position == "FLAT":
                    atr = latest_data.get('ATR', 0.0010)
                    sl_dist = atr * 1.5 
                    sl_price = current_close + sl_dist
                    tp_price = current_close - (sl_dist * 2)
                    size = position_sizer.calculate_size(risk_manager.current_balance, current_close, sl_price)
                    
                    if size > 0:
                        success = vwap_executor.execute_carefully(symbol, "SELL", size, current_close, current_close)
                        if success: current_position = "SHORT"

            # E. PnL % Auto-Close Monitor (Net PnL)
            # ---------------------------------------------
            # E. PnL % Auto-Close Monitor (Net PnL)
            # ---------------------------------------------
            # Feature: Close trade if Loss > 30% or Profit > 70%
            # Scan ALL open positions, not just the current symbol
            all_open_positions = order_router.get_open_positions(symbol=None) 
            
            if all_open_positions:
                for pos in all_open_positions:
                    # Calculate Net Profit
                    gross_profit = pos['profit']
                    commission = pos.get('commission', 0.0)
                    swap = pos.get('swap', 0.0)
                    net_profit = gross_profit + commission + swap
                    
                    price_open = pos['price_open']
                    price_curr = pos['price_current']
                    
                    if price_open > 0:
                        # Price Move ROI logic
                        raw_pct = (price_curr - price_open) / price_open
                        if pos['type'] == 'SELL': raw_pct = -raw_pct
                        
                        leverage = 100 
                        real_net_roi = raw_pct * leverage * 100
                        
                        # Debug Print to see what the system calculates
                        # print(f"Tick {pos['ticket']} ({pos['symbol']}): PnL {net_profit:.2f}, ROI {real_net_roi:.2f}%")

                        if real_net_roi <= -30:
                             print(f"📉 Stop Loss (Net): {pos['symbol']} Ticket {pos['ticket']} ROI {real_net_roi:.2f}% (Net PnL {net_profit:.2f}). Closing.")
                             order_router.close_position(pos['symbol'], pos['ticket'])
                             # If we closed the symbol we are currently trading, reset state
                             if pos['symbol'] == symbol:
                                 current_position = "FLAT"
                             
                        elif real_net_roi >= 70:
                             print(f"🚀 Take Profit (Net): {pos['symbol']} Ticket {pos['ticket']} ROI {real_net_roi:.2f}% (Net PnL {net_profit:.2f}). Closing.")
                             order_router.close_position(pos['symbol'], pos['ticket'])
                             if pos['symbol'] == symbol:
                                 current_position = "FLAT"
                        
            # F. Exit Logic (Wait)
            
            # 1-Second Polling for high-frequency monitoring
            time.sleep(1) 
            
    except KeyboardInterrupt:
        print("\nShutting down Spidy AI...")
        feed.shutdown()

if __name__ == "__main__":
    run_spidy_ai()
