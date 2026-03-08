import MetaTrader5 as mt5

print("Checking MT5 Constants:")
try:
    print(f"SYMBOL_FILLING_FOK: {mt5.SYMBOL_FILLING_FOK}")
except AttributeError:
    print("SYMBOL_FILLING_FOK: Not Found")

try:
    print(f"SYMBOL_FILLING_IOC: {mt5.SYMBOL_FILLING_IOC}")
except AttributeError:
    print("SYMBOL_FILLING_IOC: Not Found")
    
# Check what DOES exist
print("\nDir mt5 (filtered):")
count = 0
for x in dir(mt5):
    if "FILLING" in x:
        print(x)
