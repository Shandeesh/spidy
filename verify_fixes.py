
import os
import sys
import time
import importlib.util

# Verify Database
def test_db():
    print("--- Testing Database Persistence ---")
    try:
        sys.path.append(r"c:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge")
        import financial_db
        financial_db.init_db()
        
        # Save a test trade
        test_ticket = 999999
        financial_db.save_trade(test_ticket, "TEST", "BUY", 1.0, 100.0, "2025-01-01 12:00:00")
        print("Warning: Trade Saved.")
        
        # Read it back
        history = financial_db.get_trade_history()
        found = False
        for h in history:
            if h['ticket'] == test_ticket:
                print(f"Success: Found Trade {test_ticket} in DB.")
                found = True
                break
        
        if not found:
            print("FAILED: Trade not found in DB.")
            return False
            
        return True
    except Exception as e:
        print(f"FAILED: DB Test Crashed: {e}")
        return False

# Verify Broker Logic
def test_broker_logic():
    print("\n--- Testing Broker Filling Mode Logic ---")
    try:
        # Mock MT5 if not present
        if 'MetaTrader5' not in sys.modules:
            sys.modules['MetaTrader5'] = type('MockMT5', (object,), {
                'symbol_info': lambda s: None,
                'ORDER_FILLING_FOK': 1,
                'ORDER_FILLING_IOC': 2,
                'ORDER_FILLING_RETURN': 0,
                'TRADE_RETCODE_DONE': 10009
            })
        
        # Verify bridge_server import
        spec = importlib.util.spec_from_file_location("bridge_server", r"c:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge\bridge_server.py")
        bridge_server = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge_server)
        
        mode = bridge_server.get_filling_mode("EURUSD")
        print(f"Success: Filling Mode Logic Executed. Result: {mode}")
        return True
    except Exception as e:
        print(f"FAILED: Broker Logic Crashed: {e}")
        return False

def test_files():
    print("\n--- Verifying File Integrity ---")
    files = [
        r"c:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge\financial_db.py",
        r"c:\Users\Shandeesh R P\spidy\AI_Engine\brain\brain_server.py",
        r"c:\Users\Shandeesh R P\spidy\.gitignore"
    ]
    all_exist = True
    for f in files:
        if os.path.exists(f):
            print(f"OK: {os.path.basename(f)} exists.")
        else:
            print(f"MISSING: {f}")
            all_exist = False
    return all_exist

if __name__ == "__main__":
    db_ok = test_db()
    broker_ok = test_broker_logic()
    files_ok = test_files()
    
    if db_ok and broker_ok and files_ok:
        print("\n=== VERIFICATION PASSED ===")
    else:
        print("\n=== VERIFICATION FAILED ===")
