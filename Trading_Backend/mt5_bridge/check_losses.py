import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spidy_financial.db")

def check_recent_losses():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        print(f"--- Checking DB at {datetime.now()} ---\n")
        
        # Check specifically for recent large losses as seen in screenshot (e.g. around -126)
        cursor.execute("SELECT ticket, symbol, profit, close_time FROM trades WHERE profit < -10.0 ORDER BY close_time DESC LIMIT 10")
        rows = cursor.fetchall()
        
        if not rows:
            print("No recent trades with loss < -10.0 found.")
        else:
            print(f"Found {len(rows)} recent large losses:")
            for r in rows:
                print(f"Ticket: {r[0]} | {r[1]} | Profit: {r[2]} | Time: {r[3]}")
                
        # Check specifically for a ticket from the screenshot if possible.
        # Screenshot shows tickets starting with 54582... e.g. 54582... 
        # distinct large loss is -126.75 XAGUSD.
        
        cursor.execute("SELECT * FROM trades WHERE profit < -120 AND profit > -130")
        precise = cursor.fetchall()
        if precise:
            print(f"\nExact matches for ~ -126 range: {len(precise)}")
            for p in precise:
                 print(p)
        else:
            print("\nNo exact match for -126.xx loss found.")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_recent_losses()
