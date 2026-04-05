import sqlite3
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spidy_financial.db")

def _get_conn():
    """Helper to get a thread-safe connection with WAL mode enabled."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False, timeout=10.0)
    conn.execute('PRAGMA journal_mode=WAL;')
    conn.execute('PRAGMA synchronous=NORMAL;')
    return conn

def init_db():
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
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
        
        try:
            cursor.execute("ALTER TABLE trades ADD COLUMN exit_reason TEXT")
            print("DB INFO: Added 'exit_reason' column to trades table.")
        except sqlite3.OperationalError:
            pass
        
        conn.commit()
    except Exception as e:
        print(f"CRITICAL: Failed to initialize database: {e}")
    finally:
        if conn: conn.close()
    print(f"INFO: Database {DB_FILE} initialized.")

def save_trade(ticket, symbol, type_str, volume, price, time_str, strategy="Manual", sentiment="Neutral"):
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.cursor()
    
        cursor.execute('''
            INSERT OR IGNORE INTO trades 
            (ticket, symbol, type, volume, open_price, open_time, status, strategy_tag, sentiment_tag)
            VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
        ''', (ticket, symbol, type_str, volume, price, time_str, strategy, sentiment))
        
        cursor.execute('''
            UPDATE trades 
            SET strategy_tag = ?, sentiment_tag = ?
            WHERE ticket = ? AND (strategy_tag IS NULL OR strategy_tag = 'Manual')
        ''', (strategy, sentiment, ticket))
        
        conn.commit()
    except Exception as e:
        print(f"DB ERROR: Failed to save trade {ticket}: {e}")
    finally:
        if conn: conn.close()

def update_trade_close(ticket, close_price, profit, close_time, exit_reason="Unknown"):
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE trades 
            SET close_price = ?, profit = ?, close_time = ?, status = 'CLOSED', exit_reason = ?
            WHERE ticket = ?
        ''', (close_price, profit, close_time, exit_reason, ticket))
        conn.commit()
    except Exception as e:
        print(f"DB ERROR: Failed to close trade {ticket}: {e}")
    finally:
        if conn: conn.close()

def get_trade_history(limit=500):
    history = []
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ticket, symbol, type, volume, open_price, close_price, profit, open_time, close_time, strategy_tag, sentiment_tag, exit_reason 
            FROM trades 
            WHERE status='CLOSED'
            ORDER BY close_time DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        
        for r in rows:
            history.append({
                "ticket": r[0],
                "symbol": r[1],
                "type": r[2],
                "volume": r[3],
                "open_price": r[4],
                "close_price": r[5],
                "profit": r[6],
                "open_time": r[7],
                "close_time": r[8],
                "strategy": r[9] if r[9] else "Manual",
                "sentiment": r[10] if r[10] else "Neutral",
                "exit_reason": r[11] if r[11] else "User/Unknown"
            })
    except Exception as e:
        print(f"DB Read Error: {e}")
    finally:
        if conn: conn.close()
        
    return history

def sync_from_mt5_history(mt5_deals):
    if not mt5_deals: return
    
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        count = 0
        for deal in mt5_deals:
            cursor.execute("SELECT ticket FROM trades WHERE ticket=?", (deal['ticket'],))
            exists = cursor.fetchone()
            
            if not exists:
                reason_code = deal.get('reason', -1)
                reason_str = "User"
                if reason_code == 0: reason_str = "User"
                elif reason_code == 1: reason_str = "User"
                elif reason_code == 2: reason_str = "User"
                elif reason_code == 3: reason_str = "Bot"
                elif reason_code == 4: reason_str = "SL"
                elif reason_code == 5: reason_str = "TP"
                elif reason_code == 6: reason_str = "SO"
                
                if isinstance(reason_code, str): reason_str = reason_code

                cursor.execute('''
                    INSERT INTO trades (ticket, symbol, type, volume, open_price, close_price, profit, open_time, close_time, status, exit_reason, strategy_tag)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'CLOSED', ?, ?)
                ''', (deal['ticket'], deal['symbol'], deal['type'], deal['volume'], 
                      0.0, deal['price'], deal['profit'], deal['time'], deal['time'], reason_str, 
                      "AI (SmartPeak)" if "Spidy" in deal.get('comment', '') or "SmartPeak" in deal.get('comment', '') or "HFT" in deal.get('comment', '') else "Manual"))
                count += 1
            else:
                reason_update = deal.get('reason', 'MT5 Sync')
                cursor.execute("UPDATE trades SET status='CLOSED', profit=?, close_price=?, close_time=?, exit_reason=COALESCE(exit_reason, ?) WHERE ticket=?",
                               (deal['profit'], deal['price'], deal['time'], reason_update, deal['ticket']))
        
        conn.commit()
        if count > 0:
            print(f"DB INFO: Synced {count} missing trades from MT5.")
            
    except Exception as e:
        print(f"DB SYNC ERROR: {e}")
    finally:
        if conn: conn.close()

def get_daily_pnl():
    pnl = 0.0
    conn = None
    try:
        conn = _get_conn()
        cursor = conn.cursor()
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute('''
            SELECT SUM(profit) FROM trades 
            WHERE status='CLOSED' AND close_time LIKE ?
        ''', (f"{today_str}%",))
        
        result = cursor.fetchone()
        if result and result[0] is not None:
            pnl = result[0]
            
    except Exception as e:
        print(f"DB PnL Error: {e}")
    finally:
        if conn: conn.close()
        
    return pnl
