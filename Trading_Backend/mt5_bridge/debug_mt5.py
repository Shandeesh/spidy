import MetaTrader5 as mt5
import sys

print(f"Python Executable: {sys.executable}")
print(f"MetaTrader5 Package Version: {mt5.__version__}")
print(f"MetaTrader5 Author: {mt5.__author__}")

print("\n--- Attempting Initialize (Default) ---")
if mt5.initialize():
    print("SUCCESS: Connected to MT5")
    print(mt5.terminal_info())
    print(mt5.version())
    mt5.shutdown()
else:
    print("FAILED: Default Initialize")
    print(f"Error: {mt5.last_error()}")

print("\n--- Attempting Initialize (Specific Paths) ---")
paths = [
    r"C:\Program Files\MetaTrader 5\terminal64.exe",
    r"C:\Program Files\MetaTrader 5\terminal.exe"
]

for p in paths:
    print(f"Trying path: {p}")
    if mt5.initialize(path=p):
        print(f"SUCCESS: Connected using {p}")
        mt5.shutdown()
    else:
        print(f"FAILED. Error: {mt5.last_error()}")
