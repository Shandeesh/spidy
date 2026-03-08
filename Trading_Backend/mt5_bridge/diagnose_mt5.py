
import sys
import socket
import os

print("--- DIAGNOSTIC START ---")

# 1. Check Twisted/Python Environment
print(f"Python Executable: {sys.executable}")
print(f"Working Directory: {os.getcwd()}")

# 2. Check MetaTrader5 Library
try:
    import MetaTrader5 as mt5
    print(f"MetaTrader5 Package Version: {mt5.__version__}")
    print(f"MetaTrader5 Author: {mt5.__author__}")
except ImportError:
    print("CRITICAL: MetaTrader5 module NOT installed.")
    sys.exit(1)

# 3. Check MT5 Connection
print("Attempting mt5.initialize()...")
if mt5.initialize():
    print("SUCCESS: mt5.initialize() returned True")
    info = mt5.terminal_info()
    if info:
        print(f"Terminal Connected: {info.connected}")
        print(f"Trade Allowed: {info.trade_allowed}")
        print(f"Path: {info.path}")
    else:
        print("WARNING: mt5.terminal_info() returned None")
    
    account = mt5.account_info()
    if account:
        print(f"Account: {account.login} (Equity: {account.equity})")
    else:
        print("WARNING: No Account Info found (User might not be logged in)")
        
    mt5.shutdown()
else:
    err = mt5.last_error()
    print(f"FAILURE: mt5.initialize() failed. Error Code: {err}")
    # Try common paths
    paths = [
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"C:\Program Files\MetaTrader 5\terminal.exe"
    ]
    for p in paths:
        if os.path.exists(p):
            print(f"Found MT5 at {p}, trying explicit path...")
            if mt5.initialize(path=p):
                print(f"SUCCESS: Connected via {p}")
                mt5.shutdown()
                break
            else:
                print(f"Failed via {p}: {mt5.last_error()}")

# 4. Check Port 8000
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('127.0.0.1', 8000))
if result == 0:
    print("Port 8000 is OPEN (Something is listening)")
else:
    print(f"Port 8000 is CLOSED (Nothing is listening). Code: {result}")
sock.close()

print("--- DIAGNOSTIC END ---")
