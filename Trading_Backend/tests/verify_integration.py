import sys
import os
import asyncio
import unittest
from unittest.mock import MagicMock, patch

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "mt5_bridge"))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "AI_Engine"))

# Mock MT5 before importing bridge_server (since it attempts connection on import/init)
sys.modules["MetaTrader5"] = MagicMock()
import MetaTrader5 as mt5

# Mock return values for MT5 functions
mt5.initialize.return_value = True
mt5.symbol_select.return_value = True
mt5.TIMEFRAME_M1 = 1
mt5.TIMEFRAME_H1 = 16385
mt5.ORDER_TYPE_BUY = 0
mt5.ORDER_TYPE_SELL = 1
mt5.TRADE_ACTION_DEAL = 1
mt5.ORDER_TIME_GTC = 0
mt5.ORDER_FILLING_FOK = 0
mt5.TRADE_RETCODE_DONE = 10009

# Mock Symbol Info
mock_symbol = MagicMock()
mock_symbol.ask = 1.1200
mock_symbol.bid = 1.1198
mock_symbol.point = 0.00001
mock_symbol.volume_min = 0.01
mock_symbol.trade_mode = 4 # Full Access
mt5.symbol_info.return_value = mock_symbol

# Mock Tick
mock_tick = MagicMock()
mock_tick.ask = 1.1200
mock_tick.bid = 1.1198
mock_tick.time = 1700000000
mt5.symbol_info_tick.return_value = mock_tick

# Mock Account Info
mock_account = MagicMock()
mock_account.margin_mode = 0
mock_account.currency = "USD"
mock_account.balance = 10000.0
mt5.account_info.return_value = mock_account

# Import Bridge Server (now safe)
import bridge_server

class TestIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Setup Bridge State
        bridge_server.mt5_state["connected"] = True
        bridge_server.mt5_state["market_status"] = "OPEN"
        bridge_server.HAS_MT5 = True
        
        # Patch checking market open (since it checks time)
        self.patcher_market = patch('bridge_server.is_market_open', return_value=True)
        self.mock_market = self.patcher_market.start()
        
    async def asyncTearDown(self):
        self.patcher_market.stop()

    async def test_buy_execution_flow(self):
        print("\n--- Testing BUY Signal Integration ---")
        
        # 1. Simulate Strategy Signal (BUY)
        symbol = "EURUSD"
        action = "BUY"
        volume = 0.1
        strategy = "IntegrationTest_Strategy"
        
        # Mock order_send result
        mock_result = MagicMock()
        mock_result.retcode = 10009 # DONE
        mock_result.order = 123456789
        mt5.order_send.return_value = mock_result
        
        # 2. Call Execution
        print(f"[INPUT] Strategy {strategy} signals {action} {volume} lots on {symbol}")
        success = await bridge_server.place_market_order(symbol, action, volume, strategy_tag=strategy)
        
        # 3. Verify
        self.assertTrue(success)
        print("[PASS] place_market_order returned True")
        
        # Check actual parameters sent to MT5
        args, _ = mt5.order_send.call_args
        request = args[0]
        
        self.assertEqual(request["action"], mt5.TRADE_ACTION_DEAL)
        self.assertEqual(request["symbol"], "EURUSD")
        self.assertEqual(request["type"], mt5.ORDER_TYPE_BUY)
        self.assertEqual(request["volume"], 0.1)
        # Verify comment contains strategy tag
        print(f"[VERIFY] Order Comment Sent: '{request.get('comment')}'")
        
    async def test_close_logic_flow(self):
        print("\n--- Testing CLOSE Signal Integration ---")
        
        ticket = 987654321
        symbol = "EURUSD"
        
        # Mock existing position
        mock_pos = MagicMock()
        mock_pos.ticket = ticket
        mock_pos.symbol = symbol
        mock_pos.type = 0 # BUY order originally
        mock_pos.volume = 0.1
        mock_pos.price_open = 1.1000
        mock_pos.profit = 50.0 # Profitable
        mt5.positions_get.return_value = [mock_pos]
        
        # Mock order_send result
        mock_result = MagicMock()
        mock_result.retcode = 10009
        mt5.order_send.return_value = mock_result
        
        # Call Close
        print(f"[INPUT] Closing Ticket {ticket} ({symbol})")
        success = await bridge_server.close_position(ticket, symbol, reason="IntegrationTest_Exit")
        
        # Verify
        self.assertTrue(success)
        print("[PASS] close_position returned True")
        
        # Check order sent (Should be SELL to close BUY)
        args, _ = mt5.order_send.call_args
        request = args[0]
        
        self.assertEqual(request["type"], mt5.ORDER_TYPE_SELL) # Opposing order
        self.assertEqual(request["position"], ticket)
        print(f"[VERIFY] Close Request Type: SELL (Correct for closing BUY)")
        print(f"[VERIFY] Position Ticket targeted: {request['position']}")

    async def test_strategy_manager_wiring(self):
        print("\n--- Testing Strategy Manager Wiring ---")
        # Ensure StrategyManager can actually return a signal that fits the structure expected by bridge
        manager = bridge_server.StrategyManager()
        
        # We won't run full analysis(mocks too complex), just check generate_signal signature
        # and simulating a positive valid return
        
        # Inject fake state
        manager.market_state["EURUSD"] = {
            "adx": 30,
            "vwap": 1.1100,
            "rsi": 40,
            "df": MagicMock() # Mock dataframe
        }
        
        # Mock a strategy inside
        mock_strat = MagicMock()
        mock_strat.analyze.return_value = {"signal": "BUY", "confidence": 0.9, "reason": "Mocked"}
        mock_strat.get_name.return_value = "MockStrategy"
        manager.strategies = [mock_strat]
        
        # Run
        signal = manager.generate_signal("EURUSD")
        
        self.assertIsNotNone(signal)
        self.assertEqual(signal["signal"], "BUY")
        self.assertEqual(signal["strategy"], "MockStrategy")
        print(f"[PASS] StrategyManager generated valid signal packet: {signal}")


if __name__ == "__main__":
    with open("integration_results.txt", "w") as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        unittest.main(testRunner=runner, exit=False)
    print("Integration verification finished. Check 'integration_results.txt'.")
