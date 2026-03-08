
class MockPosition:
    def __init__(self, ticket, symbol, type_op, volume, price_open, profit, swap, commission, sl, tp):
        self.ticket = ticket
        self.symbol = symbol
        self.type = type_op
        self.volume = volume
        self.price_open = price_open
        self.profit = profit
        self.swap = swap
        self.commission = commission
        self.sl = sl
        self.tp = tp

# Simulation of the Logic added to bridge_server.py
def test_breakeven_logic(pos, current_price, point=0.00001):
    cost_usd = abs(pos.commission + pos.swap)
    net_profit = pos.profit + pos.commission + pos.swap
    
    print(f"--- TEST CASE: {pos.symbol} ---")
    print(f"Profit: ${pos.profit}, Comm: ${pos.commission}, Swap: ${pos.swap}")
    print(f"Net Profit: ${net_profit:.2f} | Cost: ${cost_usd:.2f}")
    
    trigger_val = cost_usd + 0.20
    print(f"Trigger Needed: > ${trigger_val:.2f}")
    
    new_sl = 0.0
    reason_log = ""
    
    entry_price = pos.price_open
    
    if net_profit > trigger_val:
         if net_profit > 1.00:
              secure_ratio = 0.40
              lock_pips = (current_price - entry_price) * secure_ratio if pos.type == 0 else (entry_price - current_price) * secure_ratio
              if pos.type == 0: new_sl = entry_price + abs(lock_pips)
              else: new_sl = entry_price - abs(lock_pips)
              reason_log = "Stage 2 (Net +$1.00)"
              
         elif net_profit > 0.30: 
              safe_dist = 20 * point
              if net_profit > 0.40:
                  safe_dist = 30 * point
              
              if pos.type == 0: new_sl = entry_price + safe_dist
              else: new_sl = entry_price - safe_dist
              reason_log = "Stage 1 (Cover Costs)"

    if new_sl != 0.0:
        print(f"RESULT: MOVED SL to {new_sl} ({reason_log})")
        return True
    else:
        print("RESULT: NO CHANGE")
        return False

# Setup Test Cases
# 1. Losing Trade (Should do nothing)
p1 = MockPosition(1, "EURUSD", 0, 0.01, 1.05000, -0.50, 0, -0.07, 0, 0)
test_breakeven_logic(p1, 1.04950)

# 2. Small Profit but not covering cost (Profit 0.10, Cost 0.07) -> Net 0.03. Trigger approx 0.27. No change.
p2 = MockPosition(2, "EURUSD", 0, 0.01, 1.05000, 0.10, 0, -0.07, 0, 0)
test_breakeven_logic(p2, 1.05010)

# 3. Good Profit (Profit 0.40, Cost 0.07) -> Net 0.33. Trigger 0.27. Should Trigger Stage 1.
p3 = MockPosition(3, "EURUSD", 0, 0.01, 1.05000, 0.40, 0, -0.07, 0, 0)
test_breakeven_logic(p3, 1.05040)

# 4. Deep Profit (Profit 2.00, Cost 0.07) -> Net 1.93. Should Trigger Stage 2.
p4 = MockPosition(4, "EURUSD", 0, 0.01, 1.05000, 2.00, 0, -0.07, 0, 0)
test_breakeven_logic(p4, 1.05200)

