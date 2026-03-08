from strategies.technical_analysis import TechnicalAnalyzer
from strategies.market_data import MarketDataProvider
from strategies.ai_modules import AIVisionModule, SocialVelocityModule, SelfHealingModule
# from strategies.execution.meta_strategy import MetaConsensusStrategy # Temporarily Disabled

import pandas as pd
import logging

class StrategyManager:
    """
    Central coordinator for all strategic modules (Technicals, Data, AI).
    Now supports Modular Strategies via the BaseStrategy interface.
    """
    def __init__(self):
        # State storage: { "EURUSD": { "regime": "TRENDING", "bias": "BUY_ONLY", "adx": 30.5, "vwap": 1.0550 } }
        self.market_state = {} 
        self.logger = logging.getLogger("StrategyManager")
        self.logger.setLevel(logging.INFO)
        self.market_data = MarketDataProvider()
        self.ai_vision = AIVisionModule()
        self.social_tracker = SocialVelocityModule()
        self.self_healer = SelfHealingModule()
        
        # --- REGISTER STRATEGIES ---
        self.strategies = []
        
        # Strategies cleared for redesign
        
        self.logger.info(f"Strategies Loaded: {[s.get_name() for s in self.strategies]}")

    def register_strategy(self, strategy):
        """Registers a new strategy module."""
        self.strategies.append(strategy)

    def update_technical_state(self, symbol: str, df: pd.DataFrame, current_price: float):
        """
        Updates the technical state (ADX, VWAP) AND runs Strategies to update Regime/Signals.
        Should be called periodically (e.g., every minute).
        """
        try:
            # 1. Base Calculations (Common Indicators)
            if len(df) > 30:
                df_adx = TechnicalAnalyzer.calculate_adx(df)
                last_adx = df_adx['ADX'].iloc[-1]
            else:
                last_adx = 0

            vwap_val = TechnicalAnalyzer.calculate_vwap(df)
            bias = TechnicalAnalyzer.get_vwap_bias(current_price, vwap_val)
            
            # 2. RSI Calculation (Needed for Pilot Strategy)
            # Assuming TechnicalAnalyzer has RSI. If not, we might need to compute it here or use df.
            # Minimal RSI calc for now if helper missing:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            # FIX 13: Replace zeros in loss with tiny epsilon to prevent ZeroDivisionError
            loss = loss.replace(0, 1e-10)
            rs = gain / loss
            current_rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # Prepare Data Packet for Strategies
            data_packet = {
                "df": df,
                "price": current_price,
                "adx": last_adx,
                "vwap": vwap_val,
                "rsi": current_rsi
            }

            # 3. Update Basic State
            if symbol not in self.market_state: self.market_state[symbol] = {}
            self.market_state[symbol].update({
                "adx": round(last_adx, 2),
                "bias": bias,
                "vwap": round(vwap_val, 5),
                "rsi": round(current_rsi, 2),
                "df": df, # CACHE THE DATAFRAME
                "updated": pd.Timestamp.now()
            })
            
            # 4. RUN STRATEGIES (Regime Detection)
            # First, find the RegimeDetector to update state
            # for strategy in self.strategies:
            #     if isinstance(strategy, RegimeDetector):
            #         result = strategy.analyze(symbol, data_packet, self.market_state)
            #         if result.get("signal") == "INFO":
            #              self.market_state[symbol]["regime"] = result.get("regime")
            
            # 5. Gap Strategy Logic (Legacy - Kept for now)
            orb_levels = TechnicalAnalyzer.calculate_orb_levels(df)
            if orb_levels:
                 self.market_state[symbol]["orb"] = orb_levels
            
        except Exception as e:
            self.logger.error(f"Error updating strategy state for {symbol}: {e}")

    def filter_signal(self, symbol: str, signal_type: str, current_price: float, strategy_tag: str) -> tuple[bool, str]:
        """
        Applies strategic filters to a proposed trade.
        Returns (Allowed: bool, Reason: str).
        """
        if symbol not in self.market_state:
            self.market_state[symbol] = {} 

        state = self.market_state[symbol]
        
        # --- Filter 0: Self-Healing (Blacklist) ---
        is_blacklisted, reason = self.self_healer.is_blacklisted(symbol)
        if is_blacklisted:
             return False, f"Strategy Block: Self-Healing Blacklist ({reason})"
        
        # --- Filter 2: VWAP Bias (Legacy but safe) ---
        vwap_bias = state.get("bias", "NEUTRAL")
        if vwap_bias == "BUY_ONLY" and signal_type == "SELL":
            return False, f"Strategy Block: Price {current_price} > VWAP {state.get('vwap')} (Bias: BUY ONLY)"
        if vwap_bias == "SELL_ONLY" and signal_type == "BUY":
            return False, f"Strategy Block: Price {current_price} < VWAP {state.get('vwap')} (Bias: SELL ONLY)"

        # --- Filter 4: Asset Correlation (The Global Shield) ---
        correlation_signal = self.market_data.check_correlation(symbol)
        if correlation_signal == "BLOCK_BUY" and signal_type == "BUY":
             return False, "Strategy Block: Correlated Asset Block (e.g. DXY Bullish)"
        if correlation_signal == "BLOCK_SELL" and signal_type == "SELL":
             return False, "Strategy Block: Correlated Asset Block (e.g. DXY Bearish)"

        return True, "Strategy Approved"
    
    def generate_signal(self, symbol: str) -> dict:
        """
        Polls all registered strategies for a trade signal.
        FIX 12: Was always returning None because MetaConsensus was commented out.
        Now uses a simple majority-vote on the collected valid_signals.
        """
        if symbol not in self.market_state: return None
        
        # Retrieve latest data from state (or cache)
        state = self.market_state[symbol]
        
        # Reconstruct Data Packet with DF
        data_packet = {
            "df": state.get("df"),
            "adx": state.get("adx"),
            "rsi": state.get("rsi"),
            "price": state.get("vwap"),  # Approximated
            "vwap": state.get("vwap")
        }
        
        # 1. GATHER ALL VOTES
        valid_signals = []
        
        for strategy in self.strategies:
            try:
                result = strategy.analyze(symbol, data_packet, self.market_state)
                
                if result.get("signal") in ["BUY", "SELL"]:
                     allowed, reason = self.filter_signal(symbol, result["signal"], 0, strategy.get_name())
                     if allowed:
                          valid_signals.append({
                              "signal": result["signal"],
                              "strategy": strategy.get_name(),
                              "confidence": result.get("confidence", 0.5),
                              "reason": result.get("reason", "")
                          })
            except Exception as e:
                self.logger.error(f"Strategy {strategy.get_name()} failed on {symbol}: {e}")
                continue
        
        if not valid_signals:
            return None
        
        # 2. SIMPLE MAJORITY VOTE (replaces always-None MetaConsensus stub)
        buy_votes  = [s for s in valid_signals if s["signal"] == "BUY"]
        sell_votes = [s for s in valid_signals if s["signal"] == "SELL"]
        
        if len(buy_votes) >= len(sell_votes) and buy_votes:
            winner = buy_votes
            final_signal = "BUY"
        elif sell_votes:
            winner = sell_votes
            final_signal = "SELL"
        else:
            return None
        
        avg_conf = sum(s["confidence"] for s in winner) / len(winner)
        reasons  = ", ".join(s["strategy"] for s in winner[:3])  # Top 3 strategies
        
        return {
            "signal": final_signal,
            "symbol": symbol,
            "confidence": round(avg_conf, 3),
            "reason": f"MetaVote ({len(winner)}/{len(valid_signals)} strategies): {reasons}",
            "strategy": "MetaVote"
        }

    def check_vision_signal(self, symbol: str) -> dict:
        """Legacy Vision Check"""
        result = self.ai_vision.analyze_chart(symbol)
        if result and result.get("confidence") == "High" and "pattern" in result:
             action = result.get("action", "WAIT")
             if action != "WAIT":
                  return {
                       "signal": action,
                       "symbol": symbol,
                       "reason": f"AI Vision: {result['pattern']}",
                       "confidence": "High"
                  }
        return None

    def check_gap_signal(self, symbol: str, current_price: float) -> dict:
        """Legacy Gap Check (ORB)"""
        if symbol not in self.market_state: return None
        state = self.market_state[symbol]
        orb_levels = state.get("orb")
        if not orb_levels: return None
        breakout = TechnicalAnalyzer.check_orb_breakout(current_price, orb_levels)
        if breakout == "BUY_BREAKOUT":
             return {"signal": "BUY", "reason": "Gap Strategy (ORB High Break)", "sl": orb_levels['orb_low']}
        elif breakout == "SELL_BREAKOUT":
             return {"signal": "SELL", "reason": "Gap Strategy (ORB Low Break)", "sl": orb_levels['orb_high']}
        return None

    def update_h1_trend(self, symbol: str, df: pd.DataFrame):
        try:
             if len(df) < 200:
                  trend = "UNCERTAIN"
             else:
                  ema_200 = df['close'].ewm(span=200, adjust=False).mean().iloc[-1]
                  current = df['close'].iloc[-1]
                  trend = "BULLISH" if current > ema_200 else "BEARISH"
             
             if symbol not in self.market_state: self.market_state[symbol] = {}
             self.market_state[symbol]["h1_trend"] = trend
        except Exception as e:
             self.logger.error(f"Error updating H1 trend for {symbol}: {e}")

    def get_status(self, symbol: str):
        return self.market_state.get(symbol, {})
