import MetaTrader5 as mt5
from datetime import datetime
import time

def debug_deals():
    if not mt5.initialize():
        print("MT5 Init Failed")
        return

    print(f"--- Fetching Deals (Last 24 Hours) ---")
    
    # Last 24 hours
    from_date = datetime.now().timestamp() - 86400
    from_date_dt = datetime.fromtimestamp(from_date)
    
    deals = mt5.history_deals_get(from_date_dt, datetime.now())
    
    if deals is None:
        print("No deals found or error.")
        print(mt5.last_error())
    else:
        print(f"Total Deals Found: {len(deals)}")
        count = 0
        for d in deals:
            # Filter for large losses
            if d.profit < -100.0: 
                print(f"Ticket:{d.ticket} | PosID:{d.position_id} | Entry:{d.entry} | Profit:{d.profit} | Reason:{d.reason} | Time:{d.time}")
            count += 1
            
    mt5.shutdown()

if __name__ == "__main__":
    debug_deals()
