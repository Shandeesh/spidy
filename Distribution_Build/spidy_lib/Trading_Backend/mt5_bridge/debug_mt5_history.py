import MetaTrader5 as mt5
from datetime import datetime
import time

def debug_mt5():
    if not mt5.initialize():
        print(f"Failed to initialize MT5, error code = {mt5.last_error()}")
        return

    print(f"MT5 Initialized. Version: {mt5.version()}")
    
    # 1. Check Time
    # Get current server time from a quote
    tick = mt5.symbol_info_tick("EURUSD")
    if tick:
        server_timestamp = tick.time
        local_timestamp = datetime.now().timestamp()
        server_dt = datetime.fromtimestamp(server_timestamp)
        local_dt = datetime.fromtimestamp(local_timestamp)
        print(f"Server Time (EURUSD Tick): {server_dt} (Ts: {server_timestamp})")
        print(f"Local Time (System):       {local_dt} (Ts: {local_timestamp})")
        print(f"Offset (Server - Local):   {server_timestamp - local_timestamp} seconds")
    else:
        print("Could not get tick for time check.")

    print(f"\n--- Checking Active Positions ---")
    positions = mt5.positions_get()
    if positions:
        print(f"Found {len(positions)} active positions.")
        # Just print first one
        pos = positions[0]
        print(f"First Pos Time: {pos.time} -> {datetime.fromtimestamp(pos.time)}")
    else:
        print("No active positions.")

    # 2. Check History
    print(f"\n--- Checking Trade History (Last 30 Days) ---")
    from_date = datetime.now().timestamp() - (30 * 24 * 60 * 60)
    to_date = datetime.now().timestamp() + (24 * 60 * 60)
    
    deals = mt5.history_deals_get(from_date, to_date)
    
    if deals:
        print(f"Found {len(deals)} total deals.")
        entry_counts = {0: 0, 1: 0, 2: 0, 3: 0, "Other": 0}
        for deal in deals:
            if deal.entry in entry_counts:
                entry_counts[deal.entry] += 1
            else:
                entry_counts["Other"] += 1
        
        print(f"Deal Types Distribution: {entry_counts}")
        print("Legend: 0=IN (Open), 1=OUT (Close), 2=INOUT (Reverse), 3=OUT_BY (CloseBy)")
    else:
        print(f"No history deals found. Last Error: {mt5.last_error()}")

    mt5.shutdown()

if __name__ == "__main__":
    import sys
    # Redirect stdout to file
    with open("debug_results_utf8.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        debug_mt5()
        sys.stdout = sys.__stdout__
    print("Debug run complete. Check debug_results_utf8.txt")
