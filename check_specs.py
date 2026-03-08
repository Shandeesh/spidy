
import MetaTrader5 as mt5
import time

if not mt5.initialize():
    print("Failed to init MT5")
    quit()

symbols = ["XAGUSD", "XAUUSD", "EURUSD"]

print(f"{'SYMBOL':<10} | {'POINT':<10} | {'CONTRACT':<10} | {'PRICE':<10} | {'VAL_1_PIP (0.01)':<15}")
print("-" * 70)

for s in symbols:
    info = mt5.symbol_info(s)
    if not info:
        print(f"{s:<10} | NOT FOUND")
        continue
        
    tick = mt5.symbol_info_tick(s)
    price = tick.bid if tick else 0.0
    
    # Value of 100 points (10 pips?) 
    # Let's say 1.00 price move
    # Value = 0.01 * contract * 1.00
    val_1_usd_move = 0.01 * info.trade_contract_size * 1.0
    
    print(f"{s:<10} | {info.point:<10} | {info.trade_contract_size:<10} | {price:<10} | ${val_1_usd_move:<15}")

mt5.shutdown()
