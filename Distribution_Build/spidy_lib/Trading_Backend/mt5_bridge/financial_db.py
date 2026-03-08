import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spidy_financial.db")

def init_db():
    """Initialize the SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create Trades Table
    # Stores both Active and Closed trades
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            ticket INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            type TEXT NOT NULL,
            volume REAL NOT NULL,
            open_price REAL NOT NULL,
            close_price REAL,
            profit REAL DEFAULT 0.0,
            open_time TEXT NOT NULL,
            close_time TEXT,
            status TEXT DEFAULT 'OPEN', 
            sentiment_tag TEXT, 
            strategy_tag TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print(f"INFO: Database {DB_FILE} initialized.")

def save_trade(ticket, symbol, type_str, volume, price, time_str, strategy="Manual", sentiment="Neutral"):
    """Saves a NEW trade execution (OPEN)."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO trades 
            (ticket, symbol, type, volume, open_price, open_time, status, strategy_tag, sentiment_tag)
            VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
        ''', (ticket, symbol, type_str, volume, price, time_str, strategy, sentiment))
        conn.commit()
    except Exception as e:
        print(f"DB ERROR: Failed to save trade {ticket}: {e}")
    finally:
        conn.close()

def update_trade_close(ticket, close_price, profit, close_time):
    """Updates a trade when it is CLOSED."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE trades 
            SET close_price = ?, profit = ?, close_time = ?, status = 'CLOSED'
            WHERE ticket = ?
        ''', (close_price, profit, close_time, ticket))
        conn.commit()
    except Exception as e:
        print(f"DB ERROR: Failed to close trade {ticket}: {e}")
    finally:
        conn.close()

def get_trade_history(limit=50):
    """Fetches closed trades for history UI."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    trades = []
    try:
        query = '''
            SELECT ticket, symbol, type, volume, open_price, close_price, profit, open_time, close_time, status
            FROM trades
            ORDER BY open_time DESC
        '''
        
        if limit and limit > 0:
             query += f" LIMIT {limit}"
             cursor.execute(query)
        else:
             cursor.execute(query)
        
        rows = cursor.fetchall()
        for r in rows:
            trades.append({
                "ticket": r[0],
                "symbol": r[1],
                "type": r[2],
                "volume": r[3],
                "open_price": r[4],
                "close_price": r[5],
                "profit": r[6],
                "time": r[8] if r[8] else r[7], # Use close time if available, else open
                "status": r[9]
            })
    except Exception as e:
        print(f"DB ERROR: Fetch history failed: {e}")
    finally:
        conn.close()
        
    return trades

def sync_from_mt5_history(mt5_deals):
    """
    Syncs history from MT5 into DB to ensure we don't miss trades 
    if the bot was offline during the close.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    count = 0
    try:
        for deal in mt5_deals:
            # Check if this ticket exists
            cursor.execute("SELECT ticket FROM trades WHERE ticket=?", (deal['ticket'],))
            exists = cursor.fetchone()
            
            if not exists:
                # Insert as a closed trade directly
                # Note: MT5 'deal' is the EXIT deal. We need to infer some data or just store what we have.
                cursor.execute('''
                    INSERT INTO trades (ticket, symbol, type, volume, open_price, close_price, profit, open_time, close_time, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'CLOSED')
                ''', (deal['ticket'], deal['symbol'], deal['type'], deal['volume'], 
                      0.0, deal['price'], deal['profit'], deal['time'], deal['time']))
                count += 1
            else:
                # Ensure it is marked CLOSED if it isn't
                cursor.execute("UPDATE trades SET status='CLOSED', profit=?, close_price=? WHERE ticket=? AND status='OPEN'",
                               (deal['profit'], deal['price'], deal['ticket']))
        
        conn.commit()
        if count > 0:
            print(f"DB INFO: Synced {count} missing trades from MT5.")
            
    except Exception as e:
        print(f"DB SYNC ERROR: {e}")
    finally:
        conn.close()
