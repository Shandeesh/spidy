import MetaTrader5 as mt5
import time

def verify_execution():
    print("---------------------------------------------------")
    print("     SPIDY LIVE EXECUTION VERIFICATION (MT5)       ")
    print("---------------------------------------------------")

    # 1. Connect
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        quit()
    
    info = mt5.terminal_info()
    print(f"[OK] Connected to: {info.name}")
    print(f"[OK] Algo Trading Allowed: {info.trade_allowed}")
    
    if not info.trade_allowed:
        print("[FAIL] Algo Trading is DISABLED in MT5 Terminal. Please enable it button 'Algo Trading'.")
        return

    symbol = "EURUSD"
    selected = mt5.symbol_select(symbol, True)
    if not selected:
        print(f"[FAIL] Failed to select {symbol}")
        return

    # 2. Prepare Safe Order (Pending Buy Limit far below price)
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        print(f"[FAIL] {symbol} not found")
        return

    price = symbol_info.ask
    safe_price = price - 0.0500 # 500 pips below, very safe
    
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": 0.01,
        "type": mt5.ORDER_TYPE_BUY_LIMIT,
        "price": safe_price,
        "sl": 0.0,
        "tp": 0.0,
        "deviation": 20,
        "magic": 999999,
        "comment": "Spidy Execution Verify",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    print(f"\n[INFO] Attempting to place PENDING BUY LIMIT @ {safe_price:.5f}...")
    
    # 3. Send Order
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[FAIL] Order execution failed: {result.comment} ({result.retcode})")
        return
        
    order_ticket = result.order
    print(f"[PASS] Order Placed Successfully! Ticket: {order_ticket}")
    
    # 4. Cleanup (Delete Order)
    print(f"[INFO] Deleting Test Order {order_ticket}...")
    time.sleep(1) # Wait a moment
    
    delete_request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order": order_ticket,
        "magic": 999999,
    }
    
    del_result = mt5.order_send(delete_request)
    
    if del_result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[WARN] Failed to delete order: {del_result.comment} ({del_result.retcode})")
        print("PLEASE MANUALLY DELETE THE PENDING ORDER IN MT5.")
    else:
        print(f"[PASS] Order Deleted Successfully.")

    print("\n---------------------------------------------------")
    print("     EXECUTION ENGINE VERIFIED: OPERATIONAL        ")
    print("---------------------------------------------------")
    
    mt5.shutdown()

if __name__ == "__main__":
    with open("execution_results.txt", "w") as f:
        import sys
        sys.stdout = f
        verify_execution()
        sys.stdout = sys.__stdout__
    print("Execution verification finished. Check 'execution_results.txt'.")
