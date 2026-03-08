import asyncio

# Mock Data
profit_peaks = {}

class MockPosition:
    def __init__(self, ticket, profit):
        self.ticket = ticket
        self.profit = profit
        self.swap = 0.0
        self.commission = 0.0
        self.symbol = "EURUSD"

async def mock_broadcast(msg):
    print(f"LOG: {msg}")

async def test_logic(pos, current_peak_in_db):
    # Setup global mock
    profit_peaks[pos.ticket] = current_peak_in_db
    
    # Logic extracted from bridge_server.py
    net_profit = pos.profit + pos.swap + pos.commission
    
    current_peak = profit_peaks.get(pos.ticket, 0.0)
    if net_profit > current_peak:
        profit_peaks[pos.ticket] = net_profit
        print(f"DEBUG: New Peak for #{pos.ticket}: ${net_profit:.2f}")
        current_peak = net_profit # Update local var

    should_close = False
    
    if current_peak > 2.00:
        pullback_threshold = current_peak * 0.80 # Allow 20% pullback
        print(f"   [Check] Current Peak: {current_peak}, Threshold: {pullback_threshold}, Net: {net_profit}")
        
        if net_profit < pullback_threshold and net_profit > 0.50:
             print(f"   >>> TRIGGER CLOSE! (Dropped below {pullback_threshold})")
             should_close = True
        else:
             print("   >>> HOLD (Within bounds)")
    else:
        print("   >>> HOLD (Peak too low)")
        
    return should_close

async def run_simulation():
    print("--- Simulation Start ---")
    
    # Scenario: Profit climbs to $5.00 then drops
    # 1. Profit $1.00
    p1 = MockPosition(1, 1.00)
    await test_logic(p1, 0.0)
    
    # 2. Profit $2.50
    p2 = MockPosition(1, 2.50)
    await test_logic(p2, profit_peaks[1])
    
    # 3. Profit $5.00 (Peak)
    p3 = MockPosition(1, 5.00)
    await test_logic(p3, profit_peaks[1])
    
    # 4. Profit $4.50 (Drop 10% - Should Hold)
    # Threshold = 5.0 * 0.8 = 4.0
    p4 = MockPosition(1, 4.50)
    await test_logic(p4, profit_peaks[1])
    
    # 5. Profit $3.90 (Drop > 20% - Should Close)
    # 3.90 < 4.0
    p5 = MockPosition(1, 3.90)
    await test_logic(p5, profit_peaks[1])

if __name__ == "__main__":
    asyncio.run(run_simulation())
