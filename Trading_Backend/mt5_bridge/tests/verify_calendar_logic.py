
import asyncio
import logging

# Mock objects
class MockCalendar:
    def is_event_nearby(self, symbol, minutes_before=5, minutes_after=1):
        return True, "Upcoming High Impact Event"

async def mock_close_position(ticket, symbol, reason, require_profit=False):
    # Mocking the FAILSAFE check in bridge_server
    return await mock_close_position_sync(ticket, symbol, reason, require_profit)

async def mock_close_position_sync(ticket, symbol, reason, require_profit=False):
    print(f"ATTEMPTING CLOSE {symbol} ({ticket}) Reason: {reason} ReqProfit: {require_profit}")
    
    # Find pos in Mock State
    pos = next((p for p in mt5_state["positions"] if p["ticket"] == ticket), None)
    if not pos: return False, "NOT_FOUND"

    if require_profit:
        net_profit = pos["profit"] + pos["swap"] + pos["commission"]
        if net_profit < 0:
            print(f"FAILSAFE ABORTED: Ticket {ticket} NetProfit {net_profit}")
            return False, "FAILSAFE_ABORT"
    
    print(f"SUCCESS CLOSING {symbol} ({ticket})")
    return True, "CLOSED"

async def mock_broadcast_log(msg):
    print(f"LOG: {msg}")

# Mock State
mt5_state = {
    "connected": True,
    "positions": [
        {"ticket": 101, "symbol": "EURUSD", "profit": 10.0, "swap": -1.0, "commission": -2.0}, # Net +7.0
        {"ticket": 102, "symbol": "EURUSD", "profit": -5.0, "swap": 0.0, "commission": 0.0}, # Net -5.0
        {"ticket": 103, "symbol": "EURUSD", "profit": 0.50, "swap": -0.40, "commission": -0.20},  # Net -0.10 (Should ABORT)
    ]
}

calendar = MockCalendar()

async def test_logic():
    print("--- Starting Test ---")
    open_symbols = list(set([p['symbol'] for p in mt5_state.get('positions', [])]))
    for sym in open_symbols:
            is_event, msg = calendar.is_event_nearby(sym, minutes_before=5, minutes_after=1)
            if is_event and "Upcoming" in msg:
                await mock_broadcast_log(f"🚨 CALENDAR SNIPER: {msg}. Initiating Safety Close (Profitable Only).")
                # Close this symbol's trades IF Profitable
                for pos in mt5_state.get('positions', []):
                    if pos['symbol'] == sym:
                         # We simulate the logic in bridge_server where we call close_position with require_profit=True
                         await mock_close_position(pos['ticket'], pos['symbol'], reason="Event Safety", require_profit=True)

    print("--- Test Complete ---")

if __name__ == "__main__":
    asyncio.run(test_logic())
