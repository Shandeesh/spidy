import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spidy_financial.db")

def check_ticket():
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        target_ticket = 54578949822
        print(f"--- Checking Ticket {target_ticket} ---")
        
        cursor.execute("SELECT * FROM trades WHERE ticket=?", (target_ticket,))
        row = cursor.fetchone()
        
        if row:
            print("Found in DB:")
            print(row)
        else:
            print("NOT FOUND in DB.")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_ticket()
