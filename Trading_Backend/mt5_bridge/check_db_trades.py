import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spidy_financial.db")

def check_db():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        print("--- Last 10 Closed Trades in DB ---")
        cursor.execute("SELECT ticket, symbol, profit, close_time, status FROM trades WHERE status='CLOSED' ORDER BY close_time DESC LIMIT 10")
        rows = cursor.fetchall()
        for r in rows:
            print(r)
            
        print("\n--- Count of Trades with Negative Profit ---")
        cursor.execute("SELECT COUNT(*) FROM trades WHERE status='CLOSED' AND profit < 0")
        print(cursor.fetchone()[0])
        
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
