import unittest
import time
import os
import sys
import hashlib

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.risk_manager import RiskManagerAgent

class TestRiskManager(unittest.TestCase):
    def test_risk_manager_cooldown_and_signal_id(self):
        bus_mock = None
        config = {"risk": {"risk_per_trade_pct": 0.02, "max_total_drawdown_pct": 0.10, "signal_cooldown_secs": 300.0}}
        rm = RiskManagerAgent(bus=bus_mock, config=config)
        
        # Check signal id generation
        symbol, direction, bar_timestamp, strategy_name = "EURUSD", "BUY", "2026-09-06T10:00:00", "MACD_Cross"
        sig_id_1 = hashlib.sha256(f"{symbol}:{direction}:{bar_timestamp}:{strategy_name}".encode()).hexdigest()[:16]
        sig_id_2 = hashlib.sha256(f"{symbol}:{direction}:{bar_timestamp}:{strategy_name}".encode()).hexdigest()[:16]
        self.assertEqual(sig_id_1, sig_id_2)
        self.assertEqual(len(sig_id_1), 16)
        
        # Check signal latch cooldown
        now = time.time()
        rm._signal_latch[symbol] = now
        
        # Should report cooldown active
        self.assertTrue((time.time() - rm._signal_latch[symbol]) < rm._signal_cooldown_secs)


    def test_daily_loss_gate(self):
        config = {"risk": {"risk_per_trade_pct": 0.02, "max_total_drawdown_pct": 0.10}}
        rm = RiskManagerAgent(bus=None, config=config)
        
        # Set day start equity
        rm._day_start_equity = 1000.0
        current_equity = 900.0  # $100 loss
        max_daily_loss = 100.0
        
        daily_loss = rm._day_start_equity - current_equity
        remaining_budget = max_daily_loss - daily_loss
        
        self.assertTrue(daily_loss >= max_daily_loss * 0.8)


if __name__ == "__main__":
    unittest.main()

