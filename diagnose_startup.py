
import os
import MetaTrader5 as mt5
import psutil

print("--- MT5 DIAGNOSTIC ---")

# 1. Check Package
print(f"MT5 Package Version: {mt5.__version__}")
print(f"MT5 Author: {mt5.__author__}")

# 2. Check Paths
common_paths = [
    "C:\\Program Files\\MetaTrader 5\\terminal64.exe",
    "C:\\Program Files\\FTMO MetaTrader 5\\terminal64.exe",
    "C:\\Program Files (x86)\\MetaTrader 5\\terminal64.exe",
    "D:\\MetaTrader 5\\terminal64.exe",
    "C:\\Users\\Administrator\\Desktop\\MetaTrader 5\\terminal64.exe"
]

found_path = None
for p in common_paths:
    exists = os.path.exists(p)
    print(f"Path Check: {p} -> {exists}")
    if exists and not found_path:
        found_path = p

if found_path:
    print(f"Found MT5 at: {found_path}")
    
    # 3. Attempt Launch
    print("Attempting to initialize MT5 with this path...")
    try:
        if mt5.initialize(path=found_path):
            print("SUCCESS: MT5 Initialized!")
            info = mt5.terminal_info()
            print(f"Terminal Info: {info}")
            mt5.shutdown()
        else:
            print(f"FAILED: Initialized returned False. Error: {mt5.last_error()}")
    except Exception as e:
        print(f"EXCEPTION during init: {e}")

else:
    print("CRITICAL: No known MT5 path found on disk.")
    
    # 4. Attempt Blind Launch (Registry)
    print("Attempting Blind Init (Registry)...")
    if mt5.initialize():
        print("SUCCESS: Blind Init Worked!")
        print(f"Path used: {mt5.terminal_info().path}")
        mt5.shutdown()
    else:
        print(f"FAILED: Blind Init failed. Error: {mt5.last_error()}")

# 5. Check Running Processes
print("\nScanning Running Processes for 'terminal64':")
for proc in psutil.process_iter(['pid', 'name', 'exe']):
    if proc.info['name'] and 'terminal64' in proc.info['name']:
        print(f"FOUND RUNNING: PID {proc.info['pid']} | {proc.info['exe']}")
