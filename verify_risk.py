
# Simulation of Risk Logic

class MockSymbolInfo:
    def __init__(self, name, point, contract_size, bid, ask):
        self.name = name
        self.point = point
        self.trade_contract_size = contract_size
        self.bid = bid
        self.ask = ask

def calculate_max_sl_risk(symbol_info, volume, max_risk_usd=3.0):
    contract_size = symbol_info.trade_contract_size
    if contract_size == 0: return 0.0
    
    # Calculate Max Price Difference allowed
    max_price_diff = max_risk_usd / (volume * contract_size)
    
    return max_price_diff

def test_trade_logic(symbol_info, volume=0.01, max_risk=3.0):
    print(f"--- TESTING {symbol_info.name} (Vol: {volume}) ---")
    
    # 1. Calc SL
    calc_sl = calculate_max_sl_risk(symbol_info, volume, max_risk)
    std_sl = 500 * symbol_info.point
    
    sl_dist = min(calc_sl, std_sl)
    
    print(f"Calculated Max SL Dist: {calc_sl:.5f}")
    print(f"Standard SL Dist: {std_sl:.5f}")
    print(f"Chosen SL: {sl_dist:.5f}")
    
    # 2. Spread Check
    spread = symbol_info.ask - symbol_info.bid
    print(f"Spread: {spread:.5f}")
    
    if sl_dist < (spread * 2.0):
        print("RESULT: REJECTED (Spread too high for this Risk)")
        return False
    else:
        print("RESULT: ACCEPTED")
        return True

# CASE 1: XAGUSD (Silver)
# Contract 5000. Price 30.00. Spread 0.03.
# Risk $3.00. Vol 0.01.
# Risk = 0.01 * 5000 * Dist = 50 * Dist
# Dist = 3 / 50 = 0.06
s_silver = MockSymbolInfo("XAGUSD", 0.001, 5000.0, 30.00, 30.03) # Spread 0.03
test_trade_logic(s_silver)

print("\n")

# CASE 2: XAGUSD (Wide Spread)
# Spread 0.05. Required SL 0.06. 0.06 < (0.05 * 2 = 0.10) ? Yes. REJECT.
s_silver_wide = MockSymbolInfo("XAGUSD", 0.001, 5000.0, 30.00, 30.05) 
test_trade_logic(s_silver_wide)

print("\n")

# CASE 3: EURUSD (Forex)
# Contract 100000. Price 1.1000. Spread 0.00010.
# Risk $3.00. Vol 0.01.
# Risk = 0.01 * 100000 * Dist = 1000 * Dist
# Dist = 3 / 1000 = 0.00300 (30 pips)
# Std SL = 500 * 0.00001 = 0.00500 (50 pips)
# Chosen: 0.00300.
# Check: 0.00300 > 0.00010 * 2 ? Yes. ACCEPT.
s_eur = MockSymbolInfo("EURUSD", 0.00001, 100000.0, 1.10000, 1.10010)
test_trade_logic(s_eur)

print("\n")

# CASE 4: XAUUSD (Gold)
# Contract 100. Price 2000.00. Spread 0.30.
# Risk $3.00. Vol 0.01.
# Risk = 0.01 * 100 * Dist = 1 * Dist
# Dist = 3 / 1 = 3.00.
# Std SL = 500 * 0.01 = 5.00.
# Chosen: 3.00.
# Check: 3.00 > 0.30 * 2 (0.60)? Yes. ACCEPT.
s_gold = MockSymbolInfo("XAUUSD", 0.01, 100.0, 2000.00, 2000.30)
test_trade_logic(s_gold)
