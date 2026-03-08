import MetaTrader5 as mt5
import os
import time
import sys

# Setup logging
log_file = "mt5_launch_test.log"
def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")
    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] {msg}\n")

log("--- Starting MT5 Launch Test ---")

# 1. Check Module
try:
    log(f"MetaTrader5 Version: {mt5.__version__}")
except Exception as e:
    log(f"CRITICAL: MetaTrader5 module error: {e}")
    sys.exit(1)

# 2. Check Path
mt5_path = r"C:\Program Files\MetaTrader 5\terminal64.exe"
log(f"Checking path: {mt5_path}")
if not os.path.exists(mt5_path):
    log(f"ERROR: Path does not exist!")
    # Try dynamic find
    log("Attempting dynamic search...")
    # (Simplified search logic)
    found = False
    for root in [r"C:\Program Files", r"C:\Program Files (x86)"]:
        if os.path.exists(root):
            for d in os.listdir(root):
                if "MetaTrader" in d:
                    cand = os.path.join(root, d, "terminal64.exe")
                    if os.path.exists(cand):
                        log(f"Found candidate: {cand}")
                        mt5_path = cand
                        found = True
                        break
        if found: break
else:
    log("Path exists.")

# 3. Attempt Initialize
log("Attempting mt5.initialize()...")
if mt5.initialize(path=mt5_path):
    log("SUCCESS: MT5 Initialized via Python API")
    info = mt5.terminal_info()
    log(f"Terminal Info: {info}")
    mt5.shutdown()
else:
    log(f"FAILED: mt5.initialize() failed. Error: {mt5.last_error()}")
    
    # 4. Attempt Native Launch
    log("Attempting os.startfile() (Native Launch)...")
    try:
        os.startfile(mt5_path)
        log("os.startfile triggered. Waiting 10s...")
        time.sleep(10)
        if mt5.initialize(path=mt5_path):
             log("SUCCESS: Connected after native launch.")
        else:
             log(f"FAILED: Still cannot connect. {mt5.last_error()}")
    except Exception as e:
        log(f"Native launch exception: {e}")

log("--- Test Complete ---")
