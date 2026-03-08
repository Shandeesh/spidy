
import MetaTrader5 as mt5
import sqlite3
import os
from datetime import datetime, timedelta
import time
import math

DB_FILE = os.path.join(r"C:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge", "spidy_financial.db")

def repair_history():
    print("Initializing MT5...")
    if not mt5.initialize():
        print(f"MT5 Init Failed: {mt5.last_error()}")
        return

    # 1. Calculate Offset
    time_offset = 7200 # Default
    if mt5.symbol_select("EURUSD", True):
        tick = mt5.symbol_info_tick("EURUSD")
        if tick:
            server_ts = tick.time
            local_ts = datetime.now().timestamp()
            diff = server_ts - local_ts
            time_offset = diff
            print(f"Calculated Time Offset: {time_offset:.2f}s")

    # 2. Fetch History (Last 30 Days)
    now = datetime.now()
    from_date = now - timedelta(days=30)
    to_date = now + timedelta(hours=24)
    
    print(f"Fetching deals from {from_date} to {to_date}...")
    deals = mt5.history_deals_get(from_date, to_date)
    
    if deals:
        print(f"Found {len(deals)} total deals.")
        count = 0
        updated = 0
        
        conn = None
        try:
            conn = sqlite3.connect(DB_FILE, timeout=10) # 10s timeout for locking
            cursor = conn.cursor()
            
            print("Starting DB operations...")
            for d in deals:
                try:
                    if d.entry == 1 or d.entry == 2: # OUT or OUT_BY
                        
                        # Adjust time
                        local_ts = d.time - time_offset
                        time_str = datetime.fromtimestamp(local_ts).strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Check existence
                        cursor.execute("SELECT ticket FROM trades WHERE ticket=?", (d.position_id,))
                        exists = cursor.fetchone()
                        
                        # Reason Parsing
                        # Reason Parsing
                        comment = d.comment or ""
                        reason_str = "User"
                        
                        if "Spidy:" in comment:
                             reason_str = comment.replace("Spidy:", "").strip()
                        elif "sl" in comment.lower(): reason_str = "Stop Loss"
                        elif "tp" in comment.lower(): reason_str = "Take Profit"

                        reason_code = d.reason
                        # Only override if specific engine reason (SL/TP/Bot)
                        # Avoid overriding generic "User" code (0) if we found a specific Spidy reason
                        if reason_code == 3: reason_str = "Bot"
                        elif reason_code == 4: reason_str = "SL"
                        elif reason_code == 5: reason_str = "TP"
                        elif reason_code == 6: reason_str = "SO"

                        # Strategy Tag Parsing
                        strategy = "Manual"
                        comment = d.comment or ""
                        
                        # Fix: Check Entry Deal for original comment if Exit comment is generic (SL/TP)
                        # Fetch all deals for this position
                        pos_deals = mt5.history_deals_get(position=d.position_id)
                        if pos_deals:
                            for pd in pos_deals:
                                if pd.entry == 0: # ENTRY_IN
                                    entry_comment = pd.comment or ""
                                    # Check Entry Comment
                                    # Check Entry Comment
                                    if "Spidy" in entry_comment or "SmartPeak" in entry_comment or "HFT" in entry_comment or "Bot" in entry_comment:
                                         strategy = "AI (SmartPeak)"
                                         break

                        # Fallback to current comment if entry didn't help (e.g. manual entry but named comment?)
                        if strategy == "Manual":
                            if "Spidy" in comment or "SmartPeak" in comment or "HFT" in comment or "Bot" in comment:
                                 strategy = "AI (SmartPeak)"

                        if not exists:
                            # INSERT
                            pos_type = "BUY" if d.type == 1 else "SELL" 
                            cursor.execute('''
                                INSERT INTO trades (ticket, symbol, type, volume, open_price, close_price, profit, open_time, close_time, status, strategy_tag, exit_reason)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'CLOSED', ?, ?)
                            ''', (d.position_id, d.symbol, pos_type, d.volume, 
                                  0.0, d.price, d.profit + d.swap + d.commission, time_str, time_str, strategy, reason_str))
                            count += 1
                        else:
                            # UPDATE (Backfill Strategy Tag if missing)
                            cursor.execute('''
                                UPDATE trades 
                                SET status='CLOSED', profit=?, close_price=?, close_time=?, strategy_tag=?, exit_reason=?
                                WHERE ticket=?
                            ''', (d.profit + d.swap + d.commission, d.price, time_str, strategy, reason_str, d.position_id))
                            if cursor.rowcount > 0:
                                updated += 1
                except Exception as e:
                    print(f"Error processing deal {d.ticket}: {e}")
                    import traceback
                    traceback.print_exc()

            conn.commit()
            print(f"Repair Complete. Inserted: {count}, Updated: {updated}")
            
        except sqlite3.OperationalError as e:
            print(f"DB Locked or Error: {e}")
        finally:
            if conn: conn.close()
            
    else:
        print("No deals found.")
 
    print("Shutting down MT5...")
    mt5.shutdown()

if __name__ == "__main__":
    repair_history()
