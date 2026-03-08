import financial_db
import os

# Create dummy DB if needed (init_db checks existence)
financial_db.init_db()

# Insert dummy data
financial_db.save_trade(99901, "EURUSD", "BUY", 0.01, 1.0500, "2023-01-01 10:00:00")
financial_db.update_trade_close(99901, 1.0510, 10.0, "2023-01-01 10:05:00")

financial_db.save_trade(99902, "GBPUSD", "SELL", 0.02, 1.2500, "2023-01-01 11:00:00")
financial_db.update_trade_close(99902, 1.2490, 20.0, "2023-01-01 11:05:00")

# Test Fetch All
print("Testing Unlimited Fetch...")
history = financial_db.get_trade_history(limit=None)
print(f"Items fetched: {len(history)}")
for h in history:
    print(h)

# Test Fetch Limit
print("\nTesting Limit 1...")
history_limited = financial_db.get_trade_history(limit=1)
print(f"Items fetched: {len(history_limited)}")
