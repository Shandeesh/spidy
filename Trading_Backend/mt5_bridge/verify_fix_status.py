
import MetaTrader5 as mt5
import sqlite3
import os
from datetime import datetime, timedelta
import time

DB_FILE = os.path.join(r"C:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge", "spidy_financial.db")

def check_status():
    if not mt5.initialize():
        print(f"MT5 Init Failed: {mt5.last_error()}")
        return

    # 1. Get Deals from Today (Server Time)
    # broad range
    now = datetime.now()
    from_date = now - timedelta(hours=24)
    to_date = now + timedelta(hours=24)
    
    deals = mt5.history_deals_get(from_date, to_date)
    
    mt5_deals_map = {}
    if deals:
        for d in deals:
            if d.entry == 1 or d.entry == 2: # OUT or OUT_BY
                mt5_deals_map[d.position_id] = d
    
    print(f"MT5: Found {len(mt5_deals_map)} closed deals in last 24h.")
    
    # 2. Get DB Trades
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT ticket, status, close_time FROM trades WHERE status='CLOSED'")
    db_rows = cursor.fetchall()
    conn.close()
    
    db_tickets = {r[0]: r for r in db_rows}
    print(f"DB: Found {len(db_tickets)} CLOSED trades total (all time).")
    
    # 3. Compare
    missing_in_db = []
    for ticket, deal in mt5_deals_map.items():
        if ticket not in db_tickets:
            missing_in_db.append(ticket)
            
    print(f"Missing in DB (from last 24h): {len(missing_in_db)}")
    if missing_in_db:
        print(f"First 10 missing tickets: {missing_in_db[:10]}")
        # Print details of first missing
        first_missing = mt5_deals_map[missing_in_db[0]]
        print(f"Details of Missing Ticket {first_missing.position_id}: Time={first_missing.time} ({datetime.fromtimestamp(first_missing.time)})")

    mt5.shutdown()

if __name__ == "__main__":
    check_status()
