import sys
import asyncio
from unittest.mock import MagicMock, AsyncMock

# 1. Mock MetaTrader5 BEFORE importing bridge_server
mock_mt5 = MagicMock()
sys.modules["MetaTrader5"] = mock_mt5

# Mock other specific imports that might cause issues
sys.modules["financial_db"] = MagicMock()
sys.modules["economic_calendar"] = MagicMock()
sys.modules["strategy_manager"] = MagicMock()
sys.modules["watchdog_service"] = MagicMock()
sys.modules["influxdb_manager"] = MagicMock()
sys.modules["AI_Engine.sentiment_analyzer"] = MagicMock() # Mock submodule if needed or handled by logic
# We might need to handle the import paths in bridge_server, let's see.

# Set up the path so it can find things if needed
import os
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'Trading_Backend'))
sys.path.append(os.path.join(os.getcwd(), 'Trading_Backend', 'mt5_bridge'))

# Now Import
try:
    import bridge_server
except ImportError as e:
    # If it fails due to relative imports, we might need to fix paths or just copy logic.
    # bridge_server assumes it's run from its dir usually. 
    # Let's try to patch sys.path further.
    pass

# Patch global variables in bridge_server
bridge_server.HAS_MT5 = True
bridge_server.mt5_state["connected"] = True
bridge_server.mt5 = mock_mt5

# Mock close_position to avoid actual trading calls
bridge_server.close_position = AsyncMock(return_value=True)
bridge_server.broadcast_log = AsyncMock()

async def run_test():
    print("--- TEST START ---")
    
    # CASE 1: Position with Net Profit 0.10 (Should Close if threshold 0.05)
    mock_pos_win = MagicMock()
    mock_pos_win.ticket = 100
    mock_pos_win.symbol = "EURUSD"
    mock_pos_win.profit = 0.15
    mock_pos_win.swap = -0.02
    mock_pos_win.commission = -0.03
    # Net: 0.10
    
    # CASE 2: Position with Net Profit 0.02 (Should NOT Close if threshold 0.05)
    mock_pos_small = MagicMock()
    mock_pos_small.ticket = 101
    mock_pos_small.symbol = "GBPUSD"
    mock_pos_small.profit = 0.05
    mock_pos_small.swap = -0.01
    mock_pos_small.commission = -0.02
    # Net: 0.02
    
    # CASE 3: Position with Loss (Should NOT Close if profitable_only=True)
    mock_pos_loss = MagicMock()
    mock_pos_loss.ticket = 102
    mock_pos_loss.symbol = "USDJPY"
    mock_pos_loss.profit = -10.0
    mock_pos_loss.swap = 0.0
    mock_pos_loss.commission = -0.05
    
    mock_mt5.positions_get.return_value = [mock_pos_win, mock_pos_small, mock_pos_loss]
    
    print("\n[TEST 1] Threshold $0.05")
    await bridge_server._process_close_all_background(profitable_only=True, threshold=0.05)
    
    # Check Calls
    # Win (100) should be closed
    # Small (101) should be skipped
    # Loss (102) should be skipped
    
    calls = bridge_server.close_position.call_args_list
    tickets_closed = [c[0][0] for c in calls]
    
    if 100 in tickets_closed: print("[PASS] Ticket 100 Closed (Correct)")
    else: print("[FAIL] Ticket 100 FAILED to close")
    
    if 101 in tickets_closed: print("[FAIL] Ticket 101 Closed (Should be SKIPPED)")
    else: print("[PASS] Ticket 101 Skipped (Correct)")
    
    if 102 in tickets_closed: print("[FAIL] Ticket 102 Closed (Should be SKIPPED)")
    else: print("[PASS] Ticket 102 Skipped (Correct)")

    # RESET
    bridge_server.close_position.reset_mock()
    
    print("\n[TEST 2] Threshold $0.01")
    await bridge_server._process_close_all_background(profitable_only=True, threshold=0.01)
    
    # Win (100) -> Net 0.10 > 0.01 -> CLOSE
    # Small (101) -> Net 0.02 > 0.01 -> CLOSE
    
    calls = bridge_server.close_position.call_args_list
    tickets_closed = [c[0][0] for c in calls]
    
    if 100 in tickets_closed and 101 in tickets_closed:
        print("[PASS] Both Ticket 100 and 101 Closed (Correct)")
    else:
        print(f"[FAIL] Failed: Closed {tickets_closed}")

if __name__ == "__main__":
    try:
        asyncio.run(run_test())
    except Exception as e:
        print(f"Test Failed: {e}")
