
import sqlite3
import os
import pandas as pd

DB_FILE = os.path.join(r"C:\Users\Shandeesh R P\spidy\Trading_Backend\mt5_bridge", "spidy_financial.db")

def check_db():
    if not os.path.exists(DB_FILE):
        print(f"DB File not found: {DB_FILE}")
        return

    conn = sqlite3.connect(DB_FILE)
    try:
        # Check Trades
        df = pd.read_sql_query("SELECT * FROM trades ORDER BY close_time DESC LIMIT 20", conn)
        if df.empty:
            print("No trades found in DB.")
        else:
            print(f"Found {len(df)} trades in DB. Showing last 20:")
            print(df.to_string())
            
    except Exception as e:
        print(f"Error reading DB: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_db()
